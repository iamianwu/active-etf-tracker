from __future__ import annotations

import os
import re
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

from ..database import get_conn, normal_stock_condition
from .yahoo_priority_quotes import ensure_quote_tables, load_symbol_cache, save_stock_quotes

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
YAHOO_CHART_HOSTS = [
    "https://query1.finance.yahoo.com/v8/finance/chart",
    "https://query2.finance.yahoo.com/v8/finance/chart",
]

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


def _today() -> str:
    return datetime.now(TAIPEI_TZ).date().isoformat()


def _market_from_symbol(symbol: str) -> str:
    if str(symbol).endswith(".TW"):
        return "TWSE"
    if str(symbol).endswith(".TWO"):
        return "TPEX"
    return ""


def _code_from_symbol(symbol: str) -> str | None:
    m = re.match(r"^(\d{4})\.(TW|TWO)$", str(symbol or ""))
    return m.group(1) if m else None


def _last_non_null(xs: list[Any]) -> Any:
    for x in reversed(xs or []):
        if x is not None:
            return x
    return None


def get_missing_codes(max_codes: int = 50) -> tuple[list[str], dict[str, str], dict[str, int]]:
    ensure_quote_tables()

    with get_conn() as conn:
        all_rows = conn.execute(
            f"""
            SELECT COUNT(*) AS n
            FROM (
              SELECT DISTINCT h.stock_code
              FROM holdings h
              WHERE {normal_stock_condition('h')}
            ) x
            """
        ).fetchall()
        all_count = int(all_rows[0]["n"] if all_rows else 0)

        quoted_rows = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM stock_quotes
            WHERE price IS NOT NULL
            """
        ).fetchall()
        quote_count = int(quoted_rows[0]["n"] if quoted_rows else 0)

        rows = conn.execute(
            f"""
            SELECT h.stock_code, MAX(h.stock_name) AS stock_name
            FROM holdings h
            LEFT JOIN stock_quotes q
              ON q.stock_code = h.stock_code
            WHERE {normal_stock_condition('h')}
              AND (q.stock_code IS NULL OR q.price IS NULL)
            GROUP BY h.stock_code
            ORDER BY h.stock_code
            LIMIT ?
            """,
            (int(max_codes),),
        ).fetchall()

    codes: list[str] = []
    names: dict[str, str] = {}

    for r in rows:
        code = str(r["stock_code"]).strip()
        if _normal_stock_code(code):
            codes.append(code)
            names[code] = str(r["stock_name"] or code).strip()

    return codes, names, {
        "holding_stock_count": all_count,
        "quote_count": quote_count,
        "selected_missing_count": len(codes),
    }


def fetch_chart_symbol(symbol: str, timeout: int = 25) -> tuple[dict[str, Any] | None, bool]:
    for host in YAHOO_CHART_HOSTS:
        url = f"{host}/{symbol}"
        params = {
            "range": "1d",
            "interval": "1m",
            "includePrePost": "false",
            "events": "div,splits",
        }

        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)

            if r.status_code == 429:
                print(f"Yahoo chart 429: {symbol}", flush=True)
                return None, True

            if r.status_code != 200:
                print(f"Yahoo chart HTTP {r.status_code}: {symbol}", flush=True)
                continue

            payload = r.json()
            chart = payload.get("chart", {}) if isinstance(payload, dict) else {}

            if chart.get("error"):
                print(f"Yahoo chart error: {symbol}: {chart.get('error')}", flush=True)
                continue

            result = (chart.get("result") or [None])[0]
            if not result:
                continue

            meta = result.get("meta") or {}
            indicators = result.get("indicators") or {}
            quote0 = (indicators.get("quote") or [{}])[0] or {}

            closes = quote0.get("close") or []
            opens = quote0.get("open") or []
            highs = quote0.get("high") or []
            lows = quote0.get("low") or []
            volumes = quote0.get("volume") or []

            price = _to_float(meta.get("regularMarketPrice"))
            if price is None:
                price = _to_float(_last_non_null(closes))

            if price is None or price <= 0:
                continue

            prev = _to_float(meta.get("previousClose"))
            if prev is None:
                prev = _to_float(meta.get("chartPreviousClose"))

            change = None
            change_pct = None
            if prev is not None and prev > 0:
                change = price - prev
                change_pct = change / prev * 100.0

            volume = _to_float(meta.get("regularMarketVolume"))
            if volume is None:
                nums = [_to_float(v) for v in volumes if v is not None]
                volume = sum(v for v in nums if v is not None) if nums else None

            market_time = meta.get("regularMarketTime")
            if market_time:
                try:
                    trade_date = datetime.fromtimestamp(int(market_time), tz=TAIPEI_TZ).date().isoformat()
                except Exception:
                    trade_date = _today()
            else:
                trade_date = _today()

            code = _code_from_symbol(symbol)
            if not code:
                continue

            clean_highs = [_to_float(v) for v in highs if v is not None]
            clean_lows = [_to_float(v) for v in lows if v is not None]

            return {
                "stock_code": code,
                "stock_name": meta.get("shortName") or meta.get("longName") or code,
                "symbol": symbol,
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "volume": volume,
                "amount": price * volume if volume is not None else None,
                "open": _to_float(_last_non_null(opens)) or _to_float(meta.get("regularMarketOpen")),
                "high": max(clean_highs) if clean_highs else None,
                "low": min(clean_lows) if clean_lows else None,
                "market": _market_from_symbol(symbol),
                "trade_date": trade_date,
                "source": "yahoo_chart_missing",
            }, False

        except Exception as e:
            print(f"Yahoo chart exception {symbol}: {e}", flush=True)
            continue

    return None, False


def fill_missing_quotes(max_codes: int = 50, sleep_sec: float = 3.5) -> dict[str, Any]:
    codes, names, meta = get_missing_codes(max_codes=max_codes)
    cache = load_symbol_cache(codes)

    print(
        f"Start fill_missing_quotes: holding={meta.get('holding_stock_count')}, "
        f"quoted={meta.get('quote_count')}, selected_missing={len(codes)}",
        flush=True,
    )

    quotes: dict[str, dict[str, Any]] = {}
    failed: list[str] = []
    rate_limited = False

    for i, code in enumerate(codes, start=1):
        symbols: list[str] = []

        if code in cache:
            symbols.append(cache[code])

        for s in (f"{code}.TW", f"{code}.TWO"):
            if s not in symbols:
                symbols.append(s)

        print(f"[{i}/{len(codes)}] {code} {names.get(code, '')}: {symbols}", flush=True)

        got = None
        for symbol in symbols:
            item, limited = fetch_chart_symbol(symbol)

            if limited:
                rate_limited = True
                # 遇到 429 先等久一點，但不中斷整個 workflow。
                time.sleep(max(20.0, sleep_sec * 5))
                continue

            if item:
                got = item
                break

            time.sleep(max(1.0, sleep_sec / 2))

        if got:
            # 保留 holdings 內的中文名稱，不被 Yahoo 英文/簡稱覆蓋。
            got["stock_name"] = names.get(code) or got.get("stock_name") or code
            quotes[code] = got
            print(f"saved candidate {code}: {got.get('price')} {got.get('symbol')}", flush=True)
        else:
            failed.append(code)
            print(f"failed {code}", flush=True)

        time.sleep(sleep_sec)

    if quotes:
        saved = save_stock_quotes(quotes, names)
    else:
        saved = 0

    print(f"Finished fill_missing_quotes: saved={saved}, failed={len(failed)}, rate_limited={rate_limited}", flush=True)

    return {
        "source": "yahoo_chart_missing",
        "updated_at": datetime.now(TAIPEI_TZ).isoformat(timespec="seconds"),
        "selected_codes": len(codes),
        "quotes_saved": saved,
        "failed_count": len(failed),
        "failed": failed[:100],
        "rate_limited": rate_limited,
        "meta": meta,
    }
