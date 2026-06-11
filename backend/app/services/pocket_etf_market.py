from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any

import requests

from ..database import get_conn, init_db

try:
    from ..config import ETF_CODES, ETF_NAMES
except Exception:
    ETF_CODES = []
    ETF_NAMES = {}

API_URL = "https://www.pocket.tw/api/cm/MobileService/ashx/GetDtnoData.ashx"

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
    "cmoneyapi-trace-context": '{"platform":3,"appVersion":"1.0.0","osName":"Windows 10","modelName":null,"manufacturer":null}',
}

def _to_float(x):
    if x is None:
        return None

    try:
        if isinstance(x, str):
            s = x.strip()
            s = s.replace(",", "")
            s = s.replace("％", "%")
            s = s.replace("%", "")
            s = s.replace("億", "")
            if s in {"", "-", "--", "—"}:
                return None
            return float(s)

        return float(x)
    except Exception:
        return None

def _fmt_date(x):
    s = str(x or "").strip()
    if not s:
        return None

    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    m = re.search(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"

    m = re.search(r"(\d{4})/(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"

    return s

def _query(params: dict[str, Any]) -> str:
    from urllib.parse import urlencode
    return urlencode(params)

def _rowdict(obj: dict[str, Any]) -> list[dict[str, Any]]:
    titles = obj.get("Title") or []
    data = obj.get("Data") or []

    rows = []
    for arr in data:
        r = {}
        for i, key in enumerate(titles):
            r[str(key)] = arr[i] if i < len(arr) else ""
        rows.append(r)

    return rows

def fetch_pocket_token(etf_code: str) -> str:
    urls = [
        f"https://www.pocket.tw/etf/tw/{etf_code}/intro?page&parent&source=",
        f"https://www.pocket.tw/etf/tw/{etf_code}/fundholding?page&parent&source",
    ]

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS_BASE, timeout=20)
            if r.status_code != 200:
                continue

            text = r.text
            m = re.search(r'tokens:\{at:"([^"]+)"', text) or re.search(r'accessToken["\']?\s*[:=]\s*["\']([^"\']+)', text)
            if m:
                return m.group(1)
        except Exception:
            continue

    return ""

def fetch_pocket_json(etf_code: str, url: str, referer: str) -> dict[str, Any]:
    token = fetch_pocket_token(etf_code)

    headers = dict(HEADERS_BASE)
    headers["Referer"] = referer
    if token:
        headers["Authorization"] = "Bearer " + token

    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Pocket API HTTP {r.status_code}: {r.text[:300]}")

    return r.json()

def build_quote_url(etf_code: str, dt_range: int = 260) -> str:
    params = {
        "action": "getdtnodata",
        "DtNo": "60465380",
        "ParamStr": f"AssignID={etf_code};DTRange={dt_range}",
        "FilterNo": "0",
    }
    return API_URL + "?" + _query(params)

def build_basic_url(etf_code: str) -> str:
    params = {
        "action": "getdtnodata",
        "DtNo": "59971134",
        "ParamStr": f"AssignID={etf_code};MTPeriod=4;DTMode=0;DTRange=1;DTOrder=1;MajorTable=M326;",
        "AssignSPID": etf_code,
        "FilterNo": "0",
    }
    return API_URL + "?" + _query(params)

def fetch_quote_history(etf_code: str, dt_range: int = 260) -> list[dict[str, Any]]:
    referer = f"https://www.pocket.tw/etf/tw/{etf_code}/intro?page&parent&source="
    obj = fetch_pocket_json(etf_code, build_quote_url(etf_code, dt_range), referer)
    return _rowdict(obj)

def fetch_basic(etf_code: str) -> dict[str, Any]:
    referer = f"https://www.pocket.tw/etf/tw/{etf_code}/intro?page&parent&source="
    obj = fetch_pocket_json(etf_code, build_basic_url(etf_code), referer)
    rows = _rowdict(obj)
    return rows[0] if rows else {}

def _pick(row: dict[str, Any], keys: list[str]):
    for k in keys:
        if k in row and row[k] not in (None, "", "-", "--"):
            return row[k]
    return None

def calc_return(history: list[dict[str, Any]], base_index: int) -> float | None:
    if not history or len(history) < 2:
        return None

    latest = _to_float(_pick(history[0], ["收盤價", "股價", "Close"]))
    if not latest:
        return None

    i = min(base_index, len(history) - 1)
    base = _to_float(_pick(history[i], ["收盤價", "股價", "Close"]))

    if not base:
        return None

    return (latest / base - 1) * 100

def calc_etf_market_row(etf_code: str, history: list[dict[str, Any]], basic: dict[str, Any]) -> dict[str, Any]:
    latest = history[0] if history else {}
    prev = history[1] if len(history) >= 2 else {}

    price = _to_float(_pick(latest, ["收盤價", "股價", "成交價", "Close"]))
    prev_price = _to_float(_pick(prev, ["收盤價", "股價", "成交價", "Close"]))

    api_change = _to_float(_pick(latest, ["漲跌", "漲跌價", "漲跌金額"]))
    api_change_pct = _to_float(_pick(latest, ["漲跌幅", "報酬率"]))

    change = api_change
    change_pct = api_change_pct

    if change is None and price is not None and prev_price is not None:
        change = price - prev_price

    if change_pct is None and price is not None and prev_price:
        change_pct = (price / prev_price - 1) * 100

    volume = _to_float(_pick(latest, ["成交量", "合成交易量", "交易量"]))
    amount = None
    if price is not None and volume is not None:
        amount = price * volume * 1000

    aum = _to_float(_pick(latest, ["資產規模(億)", "資產規模"]) or _pick(basic, ["資產規模(億)", "資產規模"]))

    expense = _to_float(_pick(basic, ["總費用", "內扣費用", "總管理費"]))
    if expense is None:
        management = _to_float(_pick(basic, ["管理費"]))
        custody = _to_float(_pick(basic, ["保管費"]))
        if management is not None or custody is not None:
            expense = (management or 0) + (custody or 0)

    week_return = calc_return(history, 5)
    total_return = calc_return(history, len(history) - 1)

    return {
        "etf_code": etf_code,
        "etf_name": str(
            _pick(latest, ["股票名稱", "基金名稱"])
            or _pick(basic, ["股票名稱", "基金名稱"])
            or ETF_NAMES.get(etf_code)
            or etf_code
        ),
        "price": price,
        "change": change,
        "change_pct": change_pct,
        "volume": volume,
        "amount": amount,
        "aum_billion": aum,
        "expense_ratio": expense,
        "inception_date": _fmt_date(_pick(basic, ["發行日期", "成立時間", "成立日期"]) or _pick(latest, ["成立時間", "成立日期"])),
        "holder_count": _to_float(_pick(basic, ["持股人數", "受益人數"])),
        "dividend_frequency": _pick(basic, ["配息制度", "配息頻率"]),
        "week_return": week_return,
        "total_return": total_return,
        "dividend_yield": _to_float(_pick(basic, ["殖利率", "配息率"])),
        "region": _pick(latest, ["投資區域"]) or _pick(basic, ["投資區域"]),
        "currency": _pick(basic, ["計算幣別"]) or "NTD",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }

def ensure_etf_quote_columns():
    init_db()

    extra_cols = {
        "week_return": "DOUBLE PRECISION",
        "total_return": "DOUBLE PRECISION",
        "dividend_yield": "DOUBLE PRECISION",
        "region": "TEXT",
        "currency": "TEXT",
    }

    with get_conn() as conn:
        for col, typ in extra_cols.items():
            try:
                conn.execute(f"ALTER TABLE etf_quotes ADD COLUMN IF NOT EXISTS {col} {typ}")
            except Exception:
                try:
                    sqlite_type = "REAL" if "DOUBLE" in typ else "TEXT"
                    conn.execute(f"ALTER TABLE etf_quotes ADD COLUMN {col} {sqlite_type}")
                except Exception:
                    pass

def save_etf_market_rows(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0

    ensure_etf_quote_columns()

    with get_conn() as conn:
        for r in rows:
            if conn.postgres:
                conn.execute(
                    """
                    INSERT INTO etf_quotes(
                      etf_code, etf_name, price, change, change_pct, volume, amount,
                      nav, premium_pct, aum_billion, expense_ratio, inception_date,
                      holder_count, dividend_frequency, week_return, total_return,
                      dividend_yield, region, currency, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (etf_code) DO UPDATE SET
                      etf_name=EXCLUDED.etf_name,
                      price=EXCLUDED.price,
                      change=EXCLUDED.change,
                      change_pct=EXCLUDED.change_pct,
                      volume=EXCLUDED.volume,
                      amount=EXCLUDED.amount,
                      aum_billion=EXCLUDED.aum_billion,
                      expense_ratio=EXCLUDED.expense_ratio,
                      inception_date=EXCLUDED.inception_date,
                      holder_count=EXCLUDED.holder_count,
                      dividend_frequency=EXCLUDED.dividend_frequency,
                      week_return=EXCLUDED.week_return,
                      total_return=EXCLUDED.total_return,
                      dividend_yield=EXCLUDED.dividend_yield,
                      region=EXCLUDED.region,
                      currency=EXCLUDED.currency,
                      updated_at=EXCLUDED.updated_at
                    """,
                    (
                        r["etf_code"], r["etf_name"], r["price"], r["change"], r["change_pct"],
                        r["volume"], r["amount"], r["aum_billion"], r["expense_ratio"],
                        r["inception_date"], r["holder_count"], r["dividend_frequency"],
                        r["week_return"], r["total_return"], r["dividend_yield"], r["region"],
                        r["currency"], r["updated_at"],
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO etf_quotes(
                      etf_code, etf_name, price, change, change_pct, volume, amount,
                      nav, premium_pct, aum_billion, expense_ratio, inception_date,
                      holder_count, dividend_frequency, week_return, total_return,
                      dividend_yield, region, currency, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r["etf_code"], r["etf_name"], r["price"], r["change"], r["change_pct"],
                        r["volume"], r["amount"], r["aum_billion"], r["expense_ratio"],
                        r["inception_date"], r["holder_count"], r["dividend_frequency"],
                        r["week_return"], r["total_return"], r["dividend_yield"], r["region"],
                        r["currency"], r["updated_at"],
                    ),
                )

    return len(rows)

def update_pocket_etf_market(dt_range: int = 260, sleep_sec: float = 0.35) -> dict[str, Any]:
    rows = []
    errors = []

    print(f"Start update_pocket_etf_market: total={len(ETF_CODES)}, dt_range={dt_range}", flush=True)

    for i, code in enumerate(ETF_CODES, start=1):
        try:
            print(f"[{i}/{len(ETF_CODES)}] Fetch Pocket ETF market {code}...", flush=True)
            history = fetch_quote_history(code, dt_range=dt_range)
            basic = fetch_basic(code)
            row = calc_etf_market_row(code, history, basic)
            rows.append(row)
            print(
                f"[{i}/{len(ETF_CODES)}] Done {code}: price={row.get('price')}, "
                f"change_pct={row.get('change_pct')}, volume={row.get('volume')}",
                flush=True
            )
        except Exception as e:
            errors.append({"etf_code": code, "error": str(e)})
            print(f"[{i}/{len(ETF_CODES)}] Error {code}: {e}", flush=True)

        time.sleep(sleep_sec)

    saved = save_etf_market_rows(rows)

    return {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "saved": saved,
        "errors": errors,
    }
