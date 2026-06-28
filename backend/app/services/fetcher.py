import re
import time
from datetime import datetime
from typing import Any

import requests

from ..config import API_URL, ETF_CODES, ETF_NAMES, REFERENCE_ETF_CODES, REFERENCE_ETF_NAMES
from ..database import get_conn, init_db, upsert_holding, upsert_etf_quote, upsert_stock_quote

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
}

def format_pocket_date(raw: str) -> str:
    s = str(raw).strip()
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s

def _get_access_token(etf_code: str) -> str:
    page_url = f"https://www.pocket.tw/etf/tw/{etf_code}/fundholding?page&parent&source"
    r = requests.get(page_url, headers=HEADERS_BASE, timeout=20)
    r.raise_for_status()
    m = re.search(r'tokens:\{at:"([^"]+)"', r.text)
    if not m:
        raise RuntimeError(f"access token not found for {etf_code}")
    return m.group(1)

def fetch_holdings(etf_code: str, dt_range: int = 1, include_all_dates: bool = False) -> list[dict[str, Any]]:
    token = _get_access_token(etf_code)
    page_url = f"https://www.pocket.tw/etf/tw/{etf_code}/fundholding?page&parent&source"
    params = {
        "action": "getdtnodata",
        "DtNo": "59449513",
        "ParamStr": f"AssignID={etf_code};MTPeriod=0;DTMode=0;DTRange={dt_range};DTOrder=1;MajorTable=M722;",
        "FilterNo": "0",
    }
    headers = {
        **HEADERS_BASE,
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token}",
        "Referer": page_url,
        "cmoneyapi-trace-context": '{"platform":3,"appVersion":"1.0.0","osName":"Mac OS","modelName":null,"manufacturer":null}',
    }
    r = requests.get(API_URL, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    js = r.json()
    data = js.get("Data") or []
    rows = []
    for x in data:
        rows.append({
            "etf_code": etf_code,
            "data_date": format_pocket_date(str(x[0])),
            "stock_code": str(x[1]),
            "stock_name": str(x[2]),
            "weight": float(x[3] or 0),
            "shares": float(x[4] or 0),
            "unit": str(x[5]) if len(x) > 5 else "",
        })
    if include_all_dates or not rows:
        return rows
    latest = max(r["data_date"] for r in rows)
    return [r for r in rows if r["data_date"] == latest]

def save_holdings(rows: list[dict[str, Any]]) -> int:
    init_db()
    with get_conn() as conn:
        n = 0
        for r in rows:
            upsert_holding(conn, r)
            n += 1
        return n

def update_one_etf(etf_code: str, dt_range: int = 1) -> dict[str, Any]:
    rows = fetch_holdings(etf_code, dt_range=dt_range, include_all_dates=dt_range > 1)
    saved = save_holdings(rows)
    return {"etf_code": etf_code, "rows": saved, "dates": sorted({r["data_date"] for r in rows})}

def update_all_etfs(dt_range: int = 1, sleep_sec: float = 0.5) -> dict[str, Any]:
    out = []
    print(f"Start update_all_etfs: dt_range={dt_range}, total={len(ETF_CODES)}", flush=True)

    for i, code in enumerate(ETF_CODES, start=1):
        print(f"[{i}/{len(ETF_CODES)}] Fetching {code}...", flush=True)

        try:
            result = update_one_etf(code, dt_range=dt_range)
            out.append(result)
            print(
                f"[{i}/{len(ETF_CODES)}] Done {code}: rows={result.get('rows')}, dates={result.get('dates')}",
                flush=True
            )
        except Exception as e:
            out.append({"etf_code": code, "error": str(e)})
            print(f"[{i}/{len(ETF_CODES)}] Error {code}: {e}", flush=True)

        time.sleep(sleep_sec)

    print("All ETF update finished.", flush=True)
    return {"updated_at": datetime.now().isoformat(timespec="seconds"), "results": out}


def update_reference_etfs(dt_range: int = 2, sleep_sec: float = 0.5) -> dict[str, Any]:
    out = []
    print(f"Start update_reference_etfs: dt_range={dt_range}, total={len(REFERENCE_ETF_CODES)}", flush=True)

    for i, code in enumerate(REFERENCE_ETF_CODES, start=1):
        print(f"[reference {i}/{len(REFERENCE_ETF_CODES)}] Fetching {code}...", flush=True)

        try:
            result = update_one_etf(code, dt_range=dt_range)
            result["etf_name"] = REFERENCE_ETF_NAMES.get(code, code)
            result["etf_group"] = "reference"
            out.append(result)
            print(
                f"[reference {i}/{len(REFERENCE_ETF_CODES)}] Done {code}: rows={result.get('rows')}, dates={result.get('dates')}",
                flush=True
            )
        except Exception as e:
            out.append({"etf_code": code, "etf_group": "reference", "error": str(e)})
            print(f"[reference {i}/{len(REFERENCE_ETF_CODES)}] Error {code}: {e}", flush=True)

        time.sleep(sleep_sec)

    print("Reference ETF update finished.", flush=True)
    return {"updated_at": datetime.now().isoformat(timespec="seconds"), "results": out}

def seed_demo_data():
    """讓前端先能點頁面；之後按 Update 就會換成真資料。"""
    init_db()
    demo = [
        ("00403A", "2026-05-28", "2330", "台積電", 17.06, 1420000, "股"),
        ("00403A", "2026-05-28", "C_NTD", "CASH", 6.55, 0, ""),
        ("00403A", "2026-05-28", "2303", "聯電", 5.92, 7970000, "股"),
        ("00403A", "2026-05-28", "3037", "欣興", 4.81, 896000, "股"),
        ("00403A", "2026-05-27", "2330", "台積電", 16.70, 1400000, "股"),
        ("00403A", "2026-05-27", "2303", "聯電", 6.10, 8200000, "股"),
        ("00994A", "2026-06-08", "3653", "健策", 0.36, 5000, "股"),
        ("00994A", "2026-06-08", "3081", "聯亞", 0.0, 0, "股"),
        ("00994A", "2026-06-08", "2368", "金像電", 2.53, 13000, "股"),
        ("00994A", "2026-06-07", "3081", "聯亞", 1.06, 22000, "股"),
        ("00994A", "2026-06-07", "2368", "金像電", 2.08, 0, "股"),
        ("00981A", "2026-06-08", "2330", "台積電", 12.4, 200000, "股"),
        ("00980A", "2026-06-08", "3211", "順達", 1.1, 1000, "股"),
    ]
    with get_conn() as conn:
        for code in ETF_CODES:
            upsert_etf_quote(conn, (code, ETF_NAMES.get(code, code), None, None, datetime.now().isoformat(timespec="seconds")))
        for row in demo:
            upsert_holding(conn, {
                "etf_code": row[0], "data_date": row[1], "stock_code": row[2],
                "stock_name": row[3], "weight": row[4], "shares": row[5], "unit": row[6]
            })
        stock_quotes = [
            ("2330", "台積電", 2355, 2.61), ("2303", "聯電", 144.5, 1.76),
            ("3037", "欣興", 1055, 2.93), ("3211", "順達", 469, 9.96),
            ("2368", "金像電", 1320, 1.45), ("3653", "健策", None, None),
        ]
        for c, n, p, pct in stock_quotes:
            upsert_stock_quote(conn, (c, n, p, pct, datetime.now().isoformat(timespec="seconds")))
