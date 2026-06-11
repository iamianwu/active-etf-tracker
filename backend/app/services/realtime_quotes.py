from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import requests

from ..database import get_conn, init_db, normal_stock_condition

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
    回傳 key 是 4 碼股票代號。
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

                out[code] = {
                    "stock_code": code,
                    "stock_name": item.get("longName") or item.get("shortName") or code,
                    "price": price,
                    "change": _to_float(item.get("regularMarketChange")),
                    "change_pct": _to_float(item.get("regularMarketChangePercent")),
                    "volume": _to_float(item.get("regularMarketVolume")),
                    "market": suffix,
                }
        except Exception:
            continue

        time.sleep(0.1)

    return out

def save_quotes(quotes: dict[str, dict[str, Any]], name_map: dict[str, str]) -> int:
    if not quotes:
        return 0

    now = datetime.now().isoformat(timespec="seconds")
    init_db()

    with get_conn() as conn:
        for code, q in quotes.items():
            stock_name = name_map.get(code) or q.get("stock_name") or code
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
                    (
                        code,
                        stock_name,
                        q.get("price"),
                        q.get("change"),
                        q.get("change_pct"),
                        q.get("volume"),
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stock_quotes(stock_code, stock_name, price, change, change_pct, volume, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code,
                        stock_name,
                        q.get("price"),
                        q.get("change"),
                        q.get("change_pct"),
                        q.get("volume"),
                        now,
                    ),
                )

    return len(quotes)

def update_live_quotes(chunk_size: int = 80) -> dict[str, Any]:
    stocks = get_latest_stock_universe()
    codes = [x["stock_code"] for x in stocks]
    name_map = {x["stock_code"]: x["stock_name"] for x in stocks}

    all_quotes: dict[str, dict[str, Any]] = {}

    print(f"Start update_live_quotes: stocks={len(codes)}", flush=True)

    for i, chunk in enumerate(_chunks(codes, chunk_size), start=1):
        print(f"[quote chunk {i}] fetching {len(chunk)} symbols", flush=True)
        q = fetch_yahoo_quote_batch(chunk)
        all_quotes.update(q)
        print(f"[quote chunk {i}] got {len(q)} quotes", flush=True)
        time.sleep(0.2)

    saved = save_quotes(all_quotes, name_map)
    missing = [c for c in codes if c not in all_quotes]

    print(f"Finished update_live_quotes: saved={saved}, missing={len(missing)}", flush=True)

    return {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "total_codes": len(codes),
        "saved": saved,
        "missing_count": len(missing),
        "missing_sample": missing[:30],
    }
