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
            if s in {"", "-", "--", "—", "null", "None", "NaN"}:
                return None
            return float(s)
        return float(v)
    except Exception:
        return None


def _normal_stock_code(code: str) -> bool:
    return bool(re.fullmatch(r"\d{4}", str(code or "").strip()))


def _chunks(xs: list[str], size: int):
    for i in range(0, len(xs), size):
        yield xs[i:i + size]


def _now_iso() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now(TAIPEI_TZ).date().isoformat()


def _market_from_symbol(symbol: str) -> str:
    if symbol.endswith(".TW"):
        return "TWSE"
    if symbol.endswith(".TWO"):
        return "TPEX"
    return ""


def _code_from_symbol(symbol: str) -> str | None:
    m = re.match(r"^(\d{4})\.(TW|TWO)$", str(symbol or ""))
    return m.group(1) if m else None


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


def load_symbol_cache(codes: list[str]) -> dict[str, str]:
    if not codes:
        return {}

    ensure_quote_tables()

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT stock_code, symbol
            FROM stock_quote_symbols
            WHERE symbol IS NOT NULL AND symbol <> ''
            """
        ).fetchall()

    cache: dict[str, str] = {}

    for r in rows:
        code = str(r["stock_code"]).strip()
        symbol = str(r["symbol"]).strip()

        if code in codes and _code_from_symbol(symbol) == code:
            cache[code] = symbol

    return cache


def save_symbol_cache(quotes: dict[str, dict[str, Any]]) -> None:
    if not quotes:
        return

    now = _now_iso()

    with get_conn() as conn:
        for code, q in quotes.items():
            symbol = str(q.get("symbol") or "").strip()
            if not symbol:
                continue

            market = _market_from_symbol(symbol)

            if conn.postgres:
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
                    (code, symbol, market, "yahoo", now),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stock_quote_symbols(stock_code, symbol, market, source, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (code, symbol, market, "yahoo", now),
                )


def _quote_to_item(q: dict[str, Any]) -> dict[str, Any] | None:
    symbol = str(q.get("symbol") or "")
    code = _code_from_symbol(symbol)

    if not code:
        return None

    price = _to_float(q.get("regularMarketPrice"))
    if price is None or price <= 0:
        return None

    market_time = q.get("regularMarketTime")
    if market_time:
        try:
            trade_date = datetime.fromtimestamp(int(market_time), tz=TAIPEI_TZ).date().isoformat()
        except Exception:
            trade_date = _today()
    else:
        trade_date = _today()

    volume = _to_float(q.get("regularMarketVolume"))

    item = {
        "stock_code": code,
        "stock_name": q.get("shortName") or q.get("longName") or code,
        "symbol": symbol,
        "price": price,
        "change": _to_float(q.get("regularMarketChange")),
        "change_pct": _to_float(q.get("regularMarketChangePercent")),
        "volume": volume,
        "amount": price * volume if volume is not None else None,
        "open": _to_float(q.get("regularMarketOpen")),
        "high": _to_float(q.get("regularMarketDayHigh")),
        "low": _to_float(q.get("regularMarketDayLow")),
        "market": _market_from_symbol(symbol),
        "trade_date": trade_date,
        "source": "yahoo_intraday",
    }

    return item


def fetch_yahoo_symbols(
    symbols: list[str],
    batch_size: int = 15,
    sleep_sec: float = 3.0,
    max_retries: int = 2,
) -> tuple[dict[str, dict[str, Any]], bool]:
    """
    回傳 (quotes, rate_limited)
    遇到 429 不丟錯，直接停止本輪 Yahoo 更新，保留已抓到資料。
    """
    found: dict[str, dict[str, Any]] = {}
    rate_limited = False

    clean_symbols = []
    seen = set()

    for s in symbols:
        s = str(s or "").strip()
        if not s or s in seen:
            continue
        code = _code_from_symbol(s)
        if not code:
            continue
        seen.add(s)
        clean_symbols.append(s)

    total_batches = (len(clean_symbols) + batch_size - 1) // batch_size

    for idx, batch in enumerate(_chunks(clean_symbols, batch_size), start=1):
        params = {
            "symbols": ",".join(batch),
            "lang": "zh-TW",
            "region": "TW",
            "corsDomain": "finance.yahoo.com",
        }

        ok = False

        for attempt in range(max_retries + 1):
            try:
                print(f"Yahoo batch {idx}/{total_batches}, symbols={len(batch)}, attempt={attempt + 1}", flush=True)

                r = requests.get(YAHOO_QUOTE_URL, params=params, headers=HEADERS, timeout=25)

                if r.status_code == 429:
                    wait = sleep_sec * (attempt + 1) * 5
                    print(f"Yahoo 429 Too Many Requests. wait={wait:.1f}s", flush=True)
                    time.sleep(wait)
                    continue

                if r.status_code != 200:
                    print(f"Yahoo HTTP {r.status_code}. skip this batch.", flush=True)
                    ok = True
                    break

                payload = r.json()
                results = payload.get("quoteResponse", {}).get("result", []) or []

                for q in results:
                    item = _quote_to_item(q)
                    if not item:
                        continue

                    code = item["stock_code"]

                    old = found.get(code)
                    if old is None:
                        found[code] = item
                    else:
                        # 如果 TW / TWO 都回資料，保留成交量較大的。
                        old_vol = _to_float(old.get("volume")) or 0
                        new_vol = _to_float(item.get("volume")) or 0
                        if new_vol > old_vol or (new_vol == old_vol and item.get("market") == "TWSE"):
                            found[code] = item

                ok = True
                break

            except Exception as e:
                print(f"Yahoo exception: {e}", flush=True)
                time.sleep(sleep_sec * (attempt + 1))

        if not ok:
            print("Yahoo appears rate limited. Stop this run and keep partial results.", flush=True)
            rate_limited = True
            break

        time.sleep(sleep_sec)

    return found, rate_limited


def save_stock_quotes(quotes: dict[str, dict[str, Any]], fallback_names: dict[str, str]) -> int:
    now = _now_iso()
    saved = 0

    ensure_quote_tables()

    with get_conn() as conn:
        for code, q in quotes.items():
            name = str(fallback_names.get(code) or q.get("stock_name") or code)

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

    save_symbol_cache(quotes)
    return saved


def update_stock_quotes(
    batch_size: int = 15,
    sleep_sec: float = 3.0,
    max_retries: int = 2,
) -> dict[str, Any]:
    """
    Yahoo-only 版本：
    1. 從 holdings 抓所有 4 碼股票。
    2. 如果已有 symbol cache，就直接查 cache，例如 2330.TW。
    3. 沒 cache 的先查 .TW。
    4. .TW 沒回來的再查 .TWO。
    5. 遇到 429 不讓 Actions 失敗，保留上一筆資料。
    """
    ensure_quote_tables()

    names = get_all_stock_codes_from_holdings()
    codes = sorted(names.keys())

    print(f"Start update_stock_quotes Yahoo-only: holding stock codes={len(codes)}", flush=True)

    if not codes:
        return {
            "updated_at": _now_iso(),
            "codes": 0,
            "quotes_saved": 0,
            "missing_count": 0,
            "rate_limited": False,
        }

    cache = load_symbol_cache(codes)
    cached_codes = sorted(cache.keys())
    uncached_codes = [c for c in codes if c not in cache]

    print(f"Cached symbols={len(cached_codes)}, uncached={len(uncached_codes)}", flush=True)

    quotes: dict[str, dict[str, Any]] = {}
    rate_limited = False

    # 先查已知 symbol，最省 request。
    if cached_codes:
        symbols = [cache[c] for c in cached_codes]
        found, limited = fetch_yahoo_symbols(
            symbols,
            batch_size=batch_size,
            sleep_sec=sleep_sec,
            max_retries=max_retries,
        )
        quotes.update(found)
        rate_limited = rate_limited or limited

    # 若已經 429，就先存部分資料，不繼續硬打。
    if not rate_limited and uncached_codes:
        # 第一輪：假設上市 .TW
        tw_symbols = [f"{c}.TW" for c in uncached_codes]
        found_tw, limited = fetch_yahoo_symbols(
            tw_symbols,
            batch_size=batch_size,
            sleep_sec=sleep_sec,
            max_retries=max_retries,
        )
        quotes.update(found_tw)
        rate_limited = rate_limited or limited

    if not rate_limited and uncached_codes:
        # 第二輪：仍缺的才查上櫃 .TWO
        still_missing = [c for c in uncached_codes if c not in quotes]
        if still_missing:
            two_symbols = [f"{c}.TWO" for c in still_missing]
            found_two, limited = fetch_yahoo_symbols(
                two_symbols,
                batch_size=batch_size,
                sleep_sec=sleep_sec,
                max_retries=max_retries,
            )
            quotes.update(found_two)
            rate_limited = rate_limited or limited

    saved = save_stock_quotes(quotes, names)

    missing = [c for c in codes if c not in quotes]

    print(
        f"Yahoo-only saved={saved}, missing_this_run={len(missing)}, rate_limited={rate_limited}",
        flush=True,
    )

    if missing:
        print("Missing examples: " + ", ".join(missing[:80]), flush=True)

    return {
        "updated_at": _now_iso(),
        "codes": len(codes),
        "cached_symbols": len(cached_codes),
        "uncached_symbols": len(uncached_codes),
        "quotes_saved": saved,
        "missing_count": len(missing),
        "missing": missing[:100],
        "rate_limited": rate_limited,
        "source": "yahoo_only",
    }


if __name__ == "__main__":
    result = update_stock_quotes(
        batch_size=int(os.getenv("YAHOO_BATCH_SIZE", "15")),
        sleep_sec=float(os.getenv("YAHOO_SLEEP_SEC", "3.0")),
        max_retries=int(os.getenv("YAHOO_MAX_RETRIES", "2")),
    )
    print(result)
