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

MIS_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
MIS_WARMUP_URL = "https://mis.twse.com.tw/stock/index.jsp"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
    "Referer": "https://mis.twse.com.tw/stock/index.jsp",
}


def _now_iso() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now(TAIPEI_TZ).date().isoformat()


def _normal_stock_code(code: str) -> bool:
    return bool(re.fullmatch(r"\d{4}", str(code or "").strip()))


def _to_float(v: Any) -> float | None:
    if v is None:
        return None

    if isinstance(v, (int, float)):
        try:
            return float(v)
        except Exception:
            return None

    s = str(v).strip()

    if s in {"", "-", "--", "—", "null", "None", "NaN"}:
        return None

    s = s.replace(",", "").replace("%", "").replace("＋", "+").replace("－", "-").replace("−", "-")

    try:
        return float(s)
    except Exception:
        m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None


def _chunks(xs: list[str], size: int):
    for i in range(0, len(xs), size):
        yield xs[i:i + size]


def _market_from_ex(ex: str) -> str:
    ex = str(ex or "").lower()
    if ex == "tse":
        return "TWSE"
    if ex == "otc":
        return "TPEX"
    return ""


def _symbol_from_row(row: dict[str, Any]) -> str:
    ex = str(row.get("ex") or "").lower()
    code = str(row.get("c") or "").strip()

    if ex == "tse":
        return f"tse_{code}.tw"
    if ex == "otc":
        return f"otc_{code}.tw"
    return ""


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

            conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_quote_symbols(
              stock_code TEXT PRIMARY KEY,
              symbol TEXT NOT NULL,
              market TEXT,
              source TEXT,
              updated_at TEXT
            )
            """)
        else:
            rows = conn.execute("PRAGMA table_info(stock_quotes)").fetchall()
            cols = {r["name"] for r in rows}

            for col, typ in {
                "change": "REAL",
                "volume": "REAL",
                "amount": "REAL",
                "market": "TEXT",
                "source": "TEXT",
                "trade_date": "TEXT",
            }.items():
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

            conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_quote_symbols(
              stock_code TEXT PRIMARY KEY,
              symbol TEXT NOT NULL,
              market TEXT,
              source TEXT,
              updated_at TEXT
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


def _row_to_quote(row: dict[str, Any], fallback_names: dict[str, str]) -> dict[str, Any] | None:
    code = str(row.get("c") or "").strip()

    if not _normal_stock_code(code):
        return None

    # z = 最近成交價。若沒有成交，z 可能是 "-"。
    last_price = _to_float(row.get("z"))

    # y = 昨收。若今天完全沒成交，用 y 當估值用價格，避免畫面一直是 "-"。
    prev_close = _to_float(row.get("y"))

    price = last_price if last_price is not None and last_price > 0 else prev_close

    if price is None or price <= 0:
        return None

    change = None
    change_pct = None

    if prev_close is not None and prev_close > 0:
        change = price - prev_close
        change_pct = change / prev_close * 100.0

    # v 通常是累積成交量，台股語境接近「張」。這裡轉成股數，讓 amount 變成元。
    volume_lots = _to_float(row.get("v"))
    volume_shares = volume_lots * 1000.0 if volume_lots is not None else None
    amount = price * volume_shares if volume_shares is not None else None

    # tlong 是毫秒時間戳；若沒有就用今日。
    trade_date = _today()
    tlong = _to_float(row.get("tlong"))
    if tlong:
        try:
            trade_date = datetime.fromtimestamp(tlong / 1000.0, tz=TAIPEI_TZ).date().isoformat()
        except Exception:
            trade_date = _today()

    ex = str(row.get("ex") or "").lower()
    market = _market_from_ex(ex)
    symbol = _symbol_from_row(row)

    name = str(fallback_names.get(code) or row.get("n") or code)

    return {
        "stock_code": code,
        "stock_name": name,
        "symbol": symbol,
        "price": price,
        "change": change,
        "change_pct": change_pct,
        "volume": volume_shares,
        "amount": amount,
        "open": _to_float(row.get("o")),
        "high": _to_float(row.get("h")),
        "low": _to_float(row.get("l")),
        "market": market,
        "trade_date": trade_date,
        "source": "twse_mis",
        "raw_z": row.get("z"),
        "raw_y": row.get("y"),
    }


def _warmup_session(session: requests.Session) -> None:
    try:
        session.get(MIS_WARMUP_URL, headers=HEADERS, timeout=15)
    except Exception:
        pass


def fetch_mis_quotes(
    codes: list[str],
    batch_codes: int = 40,
    sleep_sec: float = 1.0,
) -> dict[str, dict[str, Any]]:
    """
    不先判斷上市/上櫃，直接同時查：
    tse_2330.tw 和 otc_2330.tw

    MIS 有回有效資料者就存。若同一 code 同時回，保留有成交量或價格較合理者。
    """
    clean_codes = []
    seen = set()

    for c in codes:
        c = str(c or "").strip()
        if _normal_stock_code(c) and c not in seen:
            seen.add(c)
            clean_codes.append(c)

    session = requests.Session()
    _warmup_session(session)

    found_rows: dict[str, dict[str, Any]] = {}
    total_batches = (len(clean_codes) + batch_codes - 1) // batch_codes

    for idx, batch in enumerate(_chunks(clean_codes, batch_codes), start=1):
        symbols = []

        for code in batch:
            symbols.append(f"tse_{code}.tw")
            symbols.append(f"otc_{code}.tw")

        params = {
            "ex_ch": "|".join(symbols),
            "json": "1",
            "delay": "0",
            "_": str(int(time.time() * 1000)),
        }

        print(f"MIS batch {idx}/{total_batches}: codes={len(batch)}, symbols={len(symbols)}", flush=True)

        try:
            r = session.get(MIS_URL, params=params, headers=HEADERS, timeout=30)

            if r.status_code != 200:
                print(f"MIS HTTP {r.status_code}: {r.text[:160]}", flush=True)
                time.sleep(sleep_sec)
                continue

            payload = r.json()
            arr = payload.get("msgArray") or []

            for row in arr:
                if not isinstance(row, dict):
                    continue

                code = str(row.get("c") or "").strip()

                if not _normal_stock_code(code):
                    continue

                # 沒有 z/y 的就跳過。
                price_candidate = _to_float(row.get("z")) or _to_float(row.get("y"))
                if price_candidate is None:
                    continue

                old = found_rows.get(code)

                if old is None:
                    found_rows[code] = row
                    continue

                # 同一 code 若 tse/otc 都回，保留成交量比較大的，或 z 有值的。
                old_z = _to_float(old.get("z"))
                new_z = _to_float(row.get("z"))
                old_v = _to_float(old.get("v")) or 0
                new_v = _to_float(row.get("v")) or 0

                if (new_z is not None and old_z is None) or new_v > old_v:
                    found_rows[code] = row

        except Exception as e:
            print(f"MIS exception: {e}", flush=True)

        time.sleep(sleep_sec)

    fallback_names = get_all_stock_codes_from_holdings()

    quotes: dict[str, dict[str, Any]] = {}

    for code, row in found_rows.items():
        q = _row_to_quote(row, fallback_names)
        if q:
            quotes[code] = q

    return quotes


def save_quotes(quotes: dict[str, dict[str, Any]]) -> int:
    if not quotes:
        return 0

    now = _now_iso()
    saved = 0

    ensure_quote_tables()

    with get_conn() as conn:
        for code, q in quotes.items():
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
                        q.get("stock_name"),
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
                        q.get("stock_name"),
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

                symbol = str(q.get("symbol") or "").strip()
                if symbol:
                    conn.execute(
                        """
                        INSERT INTO stock_quote_symbols(stock_code, symbol, market, source, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT (stock_code) DO UPDATE SET
                          symbol=EXCLUDED.symbol,
                          market=EXCLUDED.market,
                          source=EXCLUDED.source,
                          updated_at=EXCLUDED.updated_at
                        """,
                        (
                            code,
                            symbol,
                            q.get("market"),
                            "twse_mis",
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
                        q.get("stock_name"),
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
                        q.get("stock_name"),
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

                symbol = str(q.get("symbol") or "").strip()
                if symbol:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO stock_quote_symbols(stock_code, symbol, market, source, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            code,
                            symbol,
                            q.get("market"),
                            "twse_mis",
                            now,
                        ),
                    )

            saved += 1

    return saved


def update_stock_quotes_from_twse_mis(
    batch_codes: int = 40,
    sleep_sec: float = 1.0,
) -> dict[str, Any]:
    names = get_all_stock_codes_from_holdings()
    codes = sorted(names.keys())

    print(f"Start TWSE MIS update: holding stock codes={len(codes)}", flush=True)

    quotes = fetch_mis_quotes(
        codes,
        batch_codes=batch_codes,
        sleep_sec=sleep_sec,
    )

    saved = save_quotes(quotes)
    missing = [c for c in codes if c not in quotes]

    print(f"TWSE MIS saved={saved}, missing={len(missing)}", flush=True)

    if missing:
        print("Missing examples: " + ", ".join(missing[:120]), flush=True)

    return {
        "updated_at": _now_iso(),
        "source": "twse_mis",
        "holding_codes": len(codes),
        "quotes_saved": saved,
        "missing_count": len(missing),
        "missing": missing[:120],
    }


if __name__ == "__main__":
    result = update_stock_quotes_from_twse_mis(
        batch_codes=int(os.getenv("TWSE_MIS_BATCH_CODES", "40")),
        sleep_sec=float(os.getenv("TWSE_MIS_SLEEP_SEC", "1.0")),
    )
    print(result)
