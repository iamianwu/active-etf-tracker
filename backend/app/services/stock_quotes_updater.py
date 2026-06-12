from __future__ import annotations

import os
import re
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

from ..database import get_conn, init_db, normal_stock_condition

TAIPEI_TZ = ZoneInfo("Asia/Taipei")

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
}


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        if isinstance(v, str):
            s = v.strip().replace(",", "").replace("%", "")
            if s in {"", "-", "--", "—", "null", "None"}:
                return None
            return float(s)
        return float(v)
    except Exception:
        return None


def _to_int(v: Any) -> int | None:
    x = _to_float(v)
    return int(x) if x is not None else None


def _normal_stock_code(code: str) -> bool:
    return bool(re.fullmatch(r"\d{4}", str(code or "").strip()))


def _chunks(xs: list[str], size: int):
    for i in range(0, len(xs), size):
        yield xs[i:i + size]


def ensure_quote_tables() -> None:
    init_db()

    with get_conn() as conn:
        if conn.postgres:
            conn.execute("ALTER TABLE stock_quotes ADD COLUMN IF NOT EXISTS change DOUBLE PRECISION")
            conn.execute("ALTER TABLE stock_quotes ADD COLUMN IF NOT EXISTS volume DOUBLE PRECISION")
            conn.execute("ALTER TABLE stock_quotes ADD COLUMN IF NOT EXISTS amount DOUBLE PRECISION")
            conn.execute("ALTER TABLE stock_quotes ADD COLUMN IF NOT EXISTS market TEXT")
            conn.execute("ALTER TABLE stock_quotes ADD COLUMN IF NOT EXISTS source TEXT")
            conn.execute("ALTER TABLE stock_quotes ADD COLUMN IF NOT EXISTS trade_date TEXT")

            conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_price_history(
              stock_code TEXT NOT NULL,
              trade_date TEXT NOT NULL,
              stock_name TEXT,
              open DOUBLE PRECISION,
              high DOUBLE PRECISION,
              low DOUBLE PRECISION,
              close DOUBLE PRECISION,
              change DOUBLE PRECISION,
              change_pct DOUBLE PRECISION,
              volume DOUBLE PRECISION,
              amount DOUBLE PRECISION,
              market TEXT,
              source TEXT,
              updated_at TEXT,
              PRIMARY KEY(stock_code, trade_date)
            )
            """)
        else:
            rows = conn.execute("PRAGMA table_info(stock_quotes)").fetchall()
            cols = {r["name"] for r in rows}

            add_cols = {
                "change": "REAL",
                "volume": "REAL",
                "amount": "REAL",
                "market": "TEXT",
                "source": "TEXT",
                "trade_date": "TEXT",
            }

            for col, typ in add_cols.items():
                if col not in cols:
                    conn.execute(f"ALTER TABLE stock_quotes ADD COLUMN {col} {typ}")

            conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_price_history(
              stock_code TEXT NOT NULL,
              trade_date TEXT NOT NULL,
              stock_name TEXT,
              open REAL,
              high REAL,
              low REAL,
              close REAL,
              change REAL,
              change_pct REAL,
              volume REAL,
              amount REAL,
              market TEXT,
              source TEXT,
              updated_at TEXT,
              PRIMARY KEY(stock_code, trade_date)
            )
            """)


def get_all_stock_codes_from_holdings() -> dict[str, str]:
    ensure_quote_tables()

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT stock_code, MAX(stock_name) AS stock_name
            FROM holdings h
            WHERE {normal_stock_condition('h')}
            GROUP BY stock_code
            ORDER BY stock_code
            """
        ).fetchall()

    out: dict[str, str] = {}
    for r in rows:
        code = str(r["stock_code"]).strip()
        if _normal_stock_code(code):
            out[code] = str(r["stock_name"] or code).strip()
    return out


def _candidate_symbols(codes: list[str]) -> list[str]:
    symbols: list[str] = []

    for code in codes:
        # 台灣上市通常是 .TW，上櫃通常是 .TWO。
        # 我們兩個都查，實際有回價格的那個才存。
        symbols.append(f"{code}.TW")
        symbols.append(f"{code}.TWO")

    return symbols


def _market_from_symbol(symbol: str) -> str:
    if symbol.endswith(".TW"):
        return "TWSE"
    if symbol.endswith(".TWO"):
        return "TPEX"
    return ""


def fetch_yahoo_quotes(codes: list[str], batch_size: int = 80, sleep_sec: float = 0.15) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}

    symbols = _candidate_symbols(codes)

    for batch in _chunks(symbols, batch_size):
        params = {
            "symbols": ",".join(batch),
            "lang": "zh-TW",
            "region": "TW",
            "corsDomain": "finance.yahoo.com",
        }

        r = requests.get(YAHOO_QUOTE_URL, params=params, headers=HEADERS, timeout=25)
        if r.status_code != 200:
            raise RuntimeError(f"Yahoo quote HTTP {r.status_code}: {r.text[:300]}")

        payload = r.json()
        results = payload.get("quoteResponse", {}).get("result", []) or []

        for q in results:
            symbol = str(q.get("symbol") or "")
            m = re.match(r"^(\d{4})\.(TW|TWO)$", symbol)
            if not m:
                continue

            code = m.group(1)
            price = _to_float(q.get("regularMarketPrice"))
            if price is None or price <= 0:
                continue

            market_time = q.get("regularMarketTime")
            if market_time:
                try:
                    trade_date = datetime.fromtimestamp(int(market_time), tz=TAIPEI_TZ).date().isoformat()
                except Exception:
                    trade_date = datetime.now(TAIPEI_TZ).date().isoformat()
            else:
                trade_date = datetime.now(TAIPEI_TZ).date().isoformat()

            item = {
                "stock_code": code,
                "stock_name": q.get("shortName") or q.get("longName") or code,
                "symbol": symbol,
                "price": price,
                "change": _to_float(q.get("regularMarketChange")),
                "change_pct": _to_float(q.get("regularMarketChangePercent")),
                "volume": _to_float(q.get("regularMarketVolume")),
                "open": _to_float(q.get("regularMarketOpen")),
                "high": _to_float(q.get("regularMarketDayHigh")),
                "low": _to_float(q.get("regularMarketDayLow")),
                "previous_close": _to_float(q.get("regularMarketPreviousClose")),
                "market": _market_from_symbol(symbol),
                "trade_date": trade_date,
                "source": "yahoo",
            }

            volume = item["volume"]
            item["amount"] = price * volume if volume is not None else None

            # 若 TW / TWO 兩個都回，優先保留有 volume 的；同分則優先 TW。
            old = found.get(code)
            if old is None:
                found[code] = item
            else:
                old_vol = _to_float(old.get("volume")) or 0
                new_vol = _to_float(item.get("volume")) or 0
                if new_vol > old_vol or (new_vol == old_vol and item["market"] == "TWSE"):
                    found[code] = item

        time.sleep(sleep_sec)

    return found


def save_stock_quotes(quotes: dict[str, dict[str, Any]], fallback_names: dict[str, str]) -> int:
    now = datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")
    saved = 0

    ensure_quote_tables()

    with get_conn() as conn:
        for code, q in quotes.items():
            name = str(q.get("stock_name") or fallback_names.get(code) or code)

            if conn.postgres:
                conn.execute(
                    """
                    INSERT INTO stock_quotes(
                      stock_code, stock_name, price, change, change_pct,
                      volume, amount, market, source, trade_date, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (stock_code) DO UPDATE SET
                      stock_name=COALESCE(EXCLUDED.stock_name, stock_quotes.stock_name),
                      price=EXCLUDED.price,
                      change=EXCLUDED.change,
                      change_pct=EXCLUDED.change_pct,
                      volume=EXCLUDED.volume,
                      amount=EXCLUDED.amount,
                      market=EXCLUDED.market,
                      source=EXCLUDED.source,
                      trade_date=EXCLUDED.trade_date,
                      updated_at=EXCLUDED.updated_at
                    """,
                    (
                        code,
                        name,
                        q.get("price"),
                        q.get("change"),
                        q.get("change_pct"),
                        q.get("volume"),
                        q.get("amount"),
                        q.get("market"),
                        q.get("source"),
                        q.get("trade_date"),
                        now,
                    ),
                )

                conn.execute(
                    """
                    INSERT INTO stock_price_history(
                      stock_code, trade_date, stock_name, open, high, low, close,
                      change, change_pct, volume, amount, market, source, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (stock_code, trade_date) DO UPDATE SET
                      stock_name=EXCLUDED.stock_name,
                      open=EXCLUDED.open,
                      high=EXCLUDED.high,
                      low=EXCLUDED.low,
                      close=EXCLUDED.close,
                      change=EXCLUDED.change,
                      change_pct=EXCLUDED.change_pct,
                      volume=EXCLUDED.volume,
                      amount=EXCLUDED.amount,
                      market=EXCLUDED.market,
                      source=EXCLUDED.source,
                      updated_at=EXCLUDED.updated_at
                    """,
                    (
                        code,
                        q.get("trade_date"),
                        name,
                        q.get("open"),
                        q.get("high"),
                        q.get("low"),
                        q.get("price"),
                        q.get("change"),
                        q.get("change_pct"),
                        q.get("volume"),
                        q.get("amount"),
                        q.get("market"),
                        q.get("source"),
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stock_quotes(
                      stock_code, stock_name, price, change, change_pct,
                      volume, amount, market, source, trade_date, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code,
                        name,
                        q.get("price"),
                        q.get("change"),
                        q.get("change_pct"),
                        q.get("volume"),
                        q.get("amount"),
                        q.get("market"),
                        q.get("source"),
                        q.get("trade_date"),
                        now,
                    ),
                )

                conn.execute(
                    """
                    INSERT OR REPLACE INTO stock_price_history(
                      stock_code, trade_date, stock_name, open, high, low, close,
                      change, change_pct, volume, amount, market, source, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code,
                        q.get("trade_date"),
                        name,
                        q.get("open"),
                        q.get("high"),
                        q.get("low"),
                        q.get("price"),
                        q.get("change"),
                        q.get("change_pct"),
                        q.get("volume"),
                        q.get("amount"),
                        q.get("market"),
                        q.get("source"),
                        now,
                    ),
                )

            saved += 1

    return saved


def update_stock_quotes(batch_size: int = 80, sleep_sec: float = 0.15) -> dict[str, Any]:
    names = get_all_stock_codes_from_holdings()
    codes = sorted(names.keys())

    print(f"Start update_stock_quotes: holding stock codes={len(codes)}", flush=True)

    if not codes:
        return {
            "updated_at": datetime.now(TAIPEI_TZ).isoformat(timespec="seconds"),
            "codes": 0,
            "quotes": 0,
            "missing": [],
        }

    quotes = fetch_yahoo_quotes(codes, batch_size=batch_size, sleep_sec=sleep_sec)
    saved = save_stock_quotes(quotes, names)

    missing = [c for c in codes if c not in quotes]

    print(f"Stock quotes saved={saved}, missing={len(missing)}", flush=True)
    if missing:
        print("Missing examples: " + ", ".join(missing[:50]), flush=True)

    return {
        "updated_at": datetime.now(TAIPEI_TZ).isoformat(timespec="seconds"),
        "codes": len(codes),
        "quotes": saved,
        "missing_count": len(missing),
        "missing": missing[:100],
    }


if __name__ == "__main__":
    result = update_stock_quotes(
        batch_size=int(os.getenv("QUOTE_BATCH_SIZE", "80")),
        sleep_sec=float(os.getenv("QUOTE_SLEEP_SEC", "0.15")),
    )
    print(result)
