from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import requests

from ..database import get_conn, init_db, normal_stock_condition

try:
    from ..config import ETF_CODES, ETF_NAMES
except Exception:
    ETF_CODES = []
    ETF_NAMES = {}

HEADERS = {
    "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}

def _to_float(x):
    if x is None:
        return None
    try:
        if isinstance(x, str):
            x = x.replace(",", "").strip()
            if x in {"", "-", "--"}:
                return None
        return float(x)
    except Exception:
        return None

def _chunks(xs: list[str], n: int):
    for i in range(0, len(xs), n):
        yield xs[i:i+n]

def get_latest_stock_universe() -> list[dict[str, str]]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT h.stock_code, MAX(h.stock_name) AS stock_name
            FROM holdings h
            WHERE {normal_stock_condition("h")}
              AND h.data_date = (
                SELECT MAX(h2.data_date)
                FROM holdings h2
                WHERE h2.etf_code = h.etf_code
              )
            GROUP BY h.stock_code
            ORDER BY h.stock_code
            """
        ).fetchall()

    return [{"stock_code": r["stock_code"], "stock_name": r["stock_name"]} for r in rows]

def fetch_yahoo_quote_batch(codes: list[str]) -> dict[str, dict[str, Any]]:
    """
    先查 .TW，再查 .TWO。
    回傳 key 是代號。
    """
    out: dict[str, dict[str, Any]] = {}

    for suffix in ("TW", "TWO"):
        missing = [c for c in codes if c not in out]
        if not missing:
            break

        symbols = ",".join([f"{c}.{suffix}" for c in missing])
        url = "https://query1.finance.yahoo.com/v7/finance/quote"

        try:
            r = requests.get(url, params={"symbols": symbols}, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                continue

            js = r.json()
            results = ((js.get("quoteResponse") or {}).get("result") or [])

            for item in results:
                symbol = str(item.get("symbol") or "")
                code = symbol.split(".")[0]
                if not code or code in out:
                    continue

                price = _to_float(item.get("regularMarketPrice"))
                if price is None:
                    continue

                volume = _to_float(item.get("regularMarketVolume"))
                amount = price * volume if price is not None and volume is not None else None

                out[code] = {
                    "code": code,
                    "name": item.get("longName") or item.get("shortName") or code,
                    "price": price,
                    "change": _to_float(item.get("regularMarketChange")),
                    "change_pct": _to_float(item.get("regularMarketChangePercent")),
                    "volume": volume,
                    "amount": amount,
                    "market": suffix,
                }
        except Exception:
            continue

        time.sleep(0.1)

    return out

def save_stock_quotes(quotes: dict[str, dict[str, Any]], name_map: dict[str, str]) -> int:
    if not quotes:
        return 0

    now = datetime.now().isoformat(timespec="seconds")
    init_db()

    with get_conn() as conn:
        for code, q in quotes.items():
            stock_name = name_map.get(code) or q.get("name") or code
            if conn.postgres:
                conn.execute(
                    """
                    INSERT INTO stock_quotes(stock_code, stock_name, price, change, change_pct, volume, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (stock_code) DO UPDATE SET
                      stock_name=EXCLUDED.stock_name,
                      price=EXCLUDED.price,
                      change=EXCLUDED.change,
                      change_pct=EXCLUDED.change_pct,
                      volume=EXCLUDED.volume,
                      updated_at=EXCLUDED.updated_at
                    """,
                    (code, stock_name, q.get("price"), q.get("change"), q.get("change_pct"), q.get("volume"), now),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stock_quotes(stock_code, stock_name, price, change, change_pct, volume, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (code, stock_name, q.get("price"), q.get("change"), q.get("change_pct"), q.get("volume"), now),
                )

    return len(quotes)

def save_etf_quotes(quotes: dict[str, dict[str, Any]]) -> int:
    if not quotes:
        return 0

    now = datetime.now().isoformat(timespec="seconds")
    init_db()

    with get_conn() as conn:
        for code, q in quotes.items():
            etf_name = ETF_NAMES.get(code) or q.get("name") or code
            if conn.postgres:
                conn.execute(
                    """
                    INSERT INTO etf_quotes(etf_code, etf_name, price, change, change_pct, volume, amount, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (etf_code) DO UPDATE SET
                      etf_name=EXCLUDED.etf_name,
                      price=EXCLUDED.price,
                      change=EXCLUDED.change,
                      change_pct=EXCLUDED.change_pct,
                      volume=EXCLUDED.volume,
                      amount=EXCLUDED.amount,
                      updated_at=EXCLUDED.updated_at
                    """,
                    (
                        code,
                        etf_name,
                        q.get("price"),
                        q.get("change"),
                        q.get("change_pct"),
                        q.get("volume"),
                        q.get("amount"),
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO etf_quotes(etf_code, etf_name, price, change, change_pct, volume, amount, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code,
                        etf_name,
                        q.get("price"),
                        q.get("change"),
                        q.get("change_pct"),
                        q.get("volume"),
                        q.get("amount"),
                        now,
                    ),
                )

    return len(quotes)

def update_live_quotes(chunk_size: int = 80) -> dict[str, Any]:
    stocks = get_latest_stock_universe()
    stock_codes = [x["stock_code"] for x in stocks]
    stock_name_map = {x["stock_code"]: x["stock_name"] for x in stocks}

    all_stock_quotes: dict[str, dict[str, Any]] = {}
    all_etf_quotes: dict[str, dict[str, Any]] = {}

    print(f"Start update_live_quotes: stocks={len(stock_codes)}, etfs={len(ETF_CODES)}", flush=True)

    for i, chunk in enumerate(_chunks(stock_codes, chunk_size), start=1):
        print(f"[stock quote chunk {i}] fetching {len(chunk)} symbols", flush=True)
        q = fetch_yahoo_quote_batch(chunk)
        all_stock_quotes.update(q)
        print(f"[stock quote chunk {i}] got {len(q)} quotes", flush=True)
        time.sleep(0.2)

    etf_codes = list(dict.fromkeys([str(x) for x in ETF_CODES if x]))
    for i, chunk in enumerate(_chunks(etf_codes, chunk_size), start=1):
        print(f"[ETF quote chunk {i}] fetching {len(chunk)} symbols", flush=True)
        q = fetch_yahoo_quote_batch(chunk)
        all_etf_quotes.update(q)
        print(f"[ETF quote chunk {i}] got {len(q)} quotes", flush=True)
        time.sleep(0.2)

    saved_stocks = save_stock_quotes(all_stock_quotes, stock_name_map)
    saved_etfs = save_etf_quotes(all_etf_quotes)

    missing_stocks = [c for c in stock_codes if c not in all_stock_quotes]
    missing_etfs = [c for c in etf_codes if c not in all_etf_quotes]

    print(
        f"Finished update_live_quotes: saved_stocks={saved_stocks}, saved_etfs={saved_etfs}, "
        f"missing_stocks={len(missing_stocks)}, missing_etfs={len(missing_etfs)}",
        flush=True,
    )

    return {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "total_stock_codes": len(stock_codes),
        "saved_stocks": saved_stocks,
        "missing_stock_count": len(missing_stocks),
        "missing_stock_sample": missing_stocks[:30],
        "total_etf_codes": len(etf_codes),
        "saved_etfs": saved_etfs,
        "missing_etf_count": len(missing_etfs),
        "missing_etf_sample": missing_etfs[:30],
    }
