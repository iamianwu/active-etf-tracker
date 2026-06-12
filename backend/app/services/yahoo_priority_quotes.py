from __future__ import annotations

import os
import re
import time
from collections import defaultdict
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


def _all_holdings_rows() -> list[dict[str, Any]]:
    ensure_quote_tables()
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT etf_code, data_date, stock_code, stock_name, shares, weight
            FROM holdings h
            WHERE {normal_stock_condition('h')}
            ORDER BY etf_code, data_date DESC, stock_code
            """
        ).fetchall()
    return [dict(r) for r in rows]


def build_priority_codes(max_codes: int = 120, offset: int = 0) -> tuple[list[str], dict[str, str], dict[str, Any]]:
    """
    建立完整排序清單，然後可用 offset + max_codes 分批。
    offset=0, max_codes=120 -> 第 1 批
    offset=120, max_codes=120 -> 第 2 批
    offset=240, max_codes=120 -> 第 3 批
    max_codes<=0 -> 從 offset 之後全部
    """
    rows = _all_holdings_rows()

    names: dict[str, str] = {}
    for r in rows:
        code = str(r.get("stock_code") or "").strip()
        if _normal_stock_code(code):
            names[code] = str(r.get("stock_name") or code).strip()

    by_etf: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_etf[str(r.get("etf_code") or "")].append(r)

    change_score: dict[str, float] = defaultdict(float)
    latest_weight_score: dict[str, float] = defaultdict(float)
    latest_share_score: dict[str, float] = defaultdict(float)
    latest_dates: dict[str, str] = {}

    for etf, items in by_etf.items():
        dates = sorted({str(x.get("data_date") or "") for x in items if x.get("data_date")}, reverse=True)
        if not dates:
            continue

        latest = dates[0]
        prev = dates[1] if len(dates) > 1 else None
        latest_dates[etf] = latest

        latest_map = {str(x.get("stock_code")): x for x in items if str(x.get("data_date")) == latest}
        prev_map = {str(x.get("stock_code")): x for x in items if prev and str(x.get("data_date")) == prev}

        all_codes = set(latest_map.keys()) | set(prev_map.keys())
        for code in all_codes:
            if not _normal_stock_code(code):
                continue
            cur = latest_map.get(code)
            old = prev_map.get(code)
            cur_shares = float(cur.get("shares") or 0) if cur else 0.0
            old_shares = float(old.get("shares") or 0) if old else 0.0
            delta = cur_shares - old_shares
            if abs(delta) > 0:
                change_score[code] += abs(delta)

        for code, cur in latest_map.items():
            if not _normal_stock_code(code):
                continue
            latest_weight_score[code] += abs(float(cur.get("weight") or 0))
            latest_share_score[code] += abs(float(cur.get("shares") or 0))

    changed_sorted = sorted(change_score.keys(), key=lambda c: change_score[c], reverse=True)
    latest_weight_sorted = sorted(latest_weight_score.keys(), key=lambda c: latest_weight_score[c], reverse=True)
    latest_share_sorted = sorted(latest_share_score.keys(), key=lambda c: latest_share_score[c], reverse=True)
    all_sorted = sorted(names.keys())

    ordered: list[str] = []
    seen = set()

    def add_many(xs: list[str]):
        for c in xs:
            if c and c not in seen and _normal_stock_code(c):
                seen.add(c)
                ordered.append(c)

    # 不需要 extra_codes。全都要，但仍維持「異動股 → 大權重 → 大張數 → 其他」排序。
    add_many(changed_sorted)
    add_many(latest_weight_sorted)
    add_many(latest_share_sorted)
    add_many(all_sorted)

    offset = max(0, int(offset or 0))
    if max_codes and max_codes > 0:
        selected = ordered[offset:offset + max_codes]
    else:
        selected = ordered[offset:]

    meta = {
        "all_codes": len(names),
        "ordered_codes": len(ordered),
        "changed_codes": len(changed_sorted),
        "selected_codes": len(selected),
        "offset": offset,
        "max_codes": max_codes,
        "has_more": offset + len(selected) < len(ordered),
        "next_offset": offset + len(selected),
        "latest_data_dates": sorted(set(latest_dates.values()), reverse=True)[:5],
    }

    return selected, names, meta


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
    code_set = set(codes)

    for r in rows:
        code = str(r["stock_code"]).strip()
        symbol = str(r["symbol"]).strip()
        if code in code_set and _code_from_symbol(symbol) == code:
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
                    (code, symbol, market, "yahoo_batches", now),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stock_quote_symbols(stock_code, symbol, market, source, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (code, symbol, market, "yahoo_batches", now),
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

    return {
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
        "source": "yahoo_batches",
    }


def fetch_yahoo_symbols(
    symbols: list[str],
    batch_size: int = 6,
    sleep_sec: float = 8.0,
    max_retries: int = 1,
) -> tuple[dict[str, dict[str, Any]], bool]:
    found: dict[str, dict[str, Any]] = {}
    rate_limited = False

    clean_symbols: list[str] = []
    seen = set()

    for s in symbols:
        s = str(s or "").strip()
        if not s or s in seen:
            continue
        if not _code_from_symbol(s):
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
                print(
                    f"Yahoo batch {idx}/{total_batches}, symbols={len(batch)}, attempt={attempt + 1}, {batch[0]}..",
                    flush=True,
                )
                r = requests.get(YAHOO_QUOTE_URL, params=params, headers=HEADERS, timeout=25)

                if r.status_code == 429:
                    wait = sleep_sec * (attempt + 1) * 4
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
            print("Yahoo appears rate limited. Stop this batch and keep partial results.", flush=True)
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
                        code, name, q.get("price"), q.get("change"), q.get("change_pct"),
                        q.get("volume"), q.get("amount"), q.get("market"), q.get("source"),
                        q.get("trade_date"), now,
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
                        code, q.get("trade_date"), name, q.get("open"), q.get("high"), q.get("low"),
                        q.get("price"), q.get("change"), q.get("change_pct"), q.get("volume"),
                        q.get("amount"), q.get("market"), q.get("source"), now,
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
                        code, name, q.get("price"), q.get("change"), q.get("change_pct"),
                        q.get("volume"), q.get("amount"), q.get("market"), q.get("source"),
                        q.get("trade_date"), now,
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
                        code, q.get("trade_date"), name, q.get("open"), q.get("high"), q.get("low"),
                        q.get("price"), q.get("change"), q.get("change_pct"), q.get("volume"),
                        q.get("amount"), q.get("market"), q.get("source"), now,
                    ),
                )

            saved += 1

    save_symbol_cache(quotes)
    return saved


def update_yahoo_priority_quotes(
    max_codes: int = 120,
    offset: int = 0,
    batch_size: int = 6,
    sleep_sec: float = 8.0,
    max_retries: int = 1,
) -> dict[str, Any]:
    ensure_quote_tables()

    codes, names, meta = build_priority_codes(max_codes=max_codes, offset=offset)

    print(
        f"Start Yahoo batch quotes: selected={len(codes)}, offset={offset}, "
        f"max_codes={max_codes}, all={meta.get('all_codes')}, has_more={meta.get('has_more')}",
        flush=True,
    )

    if not codes:
        return {
            "updated_at": _now_iso(),
            "quotes_saved": 0,
            "selected_codes": 0,
            "offset": offset,
            "rate_limited": False,
            "meta": meta,
        }

    cache = load_symbol_cache(codes)
    cached_codes = [c for c in codes if c in cache]
    uncached_codes = [c for c in codes if c not in cache]

    print(f"Cached selected symbols={len(cached_codes)}, uncached selected={len(uncached_codes)}", flush=True)

    quotes: dict[str, dict[str, Any]] = {}
    rate_limited = False

    if cached_codes:
        found, limited = fetch_yahoo_symbols(
            [cache[c] for c in cached_codes],
            batch_size=batch_size,
            sleep_sec=sleep_sec,
            max_retries=max_retries,
        )
        quotes.update(found)
        rate_limited = rate_limited or limited

    if not rate_limited and uncached_codes:
        found_tw, limited = fetch_yahoo_symbols(
            [f"{c}.TW" for c in uncached_codes],
            batch_size=batch_size,
            sleep_sec=sleep_sec,
            max_retries=max_retries,
        )
        quotes.update(found_tw)
        rate_limited = rate_limited or limited

    if not rate_limited and uncached_codes:
        still_missing = [c for c in uncached_codes if c not in quotes]
        if still_missing:
            found_two, limited = fetch_yahoo_symbols(
                [f"{c}.TWO" for c in still_missing],
                batch_size=batch_size,
                sleep_sec=sleep_sec,
                max_retries=max_retries,
            )
            quotes.update(found_two)
            rate_limited = rate_limited or limited

    saved = save_stock_quotes(quotes, names)
    missing_selected = [c for c in codes if c not in quotes]

    print(
        f"Yahoo batch saved={saved}, missing_selected={len(missing_selected)}, "
        f"rate_limited={rate_limited}, offset={offset}",
        flush=True,
    )

    if missing_selected:
        print("Missing selected examples: " + ", ".join(missing_selected[:80]), flush=True)

    return {
        "updated_at": _now_iso(),
        "source": "yahoo_batches",
        "quotes_saved": saved,
        "selected_codes": len(codes),
        "missing_selected_count": len(missing_selected),
        "missing_selected": missing_selected[:100],
        "rate_limited": rate_limited,
        "offset": offset,
        "max_codes": max_codes,
        "meta": meta,
    }


if __name__ == "__main__":
    result = update_yahoo_priority_quotes(
        max_codes=int(os.getenv("YAHOO_PRIORITY_MAX_CODES", "120")),
        offset=int(os.getenv("YAHOO_PRIORITY_OFFSET", "0")),
        batch_size=int(os.getenv("YAHOO_BATCH_SIZE", "6")),
        sleep_sec=float(os.getenv("YAHOO_SLEEP_SEC", "8.0")),
        max_retries=int(os.getenv("YAHOO_MAX_RETRIES", "1")),
    )
    print(result)
