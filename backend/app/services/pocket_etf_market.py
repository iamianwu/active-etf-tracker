from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any

import requests

from ..database import get_conn, init_db

try:
    from ..config import (
        ETF_CODES,
        ETF_NAMES,
        REFERENCE_ETF_CODES,
        REFERENCE_ETF_NAMES,
    )
except Exception:
    ETF_CODES = []
    ETF_NAMES = {}
    REFERENCE_ETF_CODES = []
    REFERENCE_ETF_NAMES = {}

ALL_ETF_CODES = list(dict.fromkeys([
    *ETF_CODES,
    *REFERENCE_ETF_CODES,
]))
ALL_ETF_NAMES = {
    **REFERENCE_ETF_NAMES,
    **ETF_NAMES,
}

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
            s = x.strip().replace(",", "").replace("％", "%").replace("%", "").replace("億", "")
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

def _pick(row: dict[str, Any], keys: list[str]):
    for k in keys:
        if k in row and row[k] not in (None, "", "-", "--"):
            return row[k]
    return None

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

def ensure_etf_tables():
    init_db()
    with get_conn() as conn:
        if conn.postgres:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS etf_price_history(
              etf_code TEXT NOT NULL,
              trade_date TEXT NOT NULL,
              close DOUBLE PRECISION,
              change DOUBLE PRECISION,
              change_pct DOUBLE PRECISION,
              volume DOUBLE PRECISION,
              amount DOUBLE PRECISION,
              PRIMARY KEY(etf_code, trade_date)
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS etf_nav_history(
              etf_code TEXT NOT NULL,
              trade_date TEXT NOT NULL,
              price DOUBLE PRECISION,
              nav DOUBLE PRECISION,
              premium_pct DOUBLE PRECISION,
              PRIMARY KEY(etf_code, trade_date)
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS etf_basic_info(
              etf_code TEXT PRIMARY KEY,
              etf_name TEXT,
              full_name TEXT,
              aum_billion DOUBLE PRECISION,
              expense_ratio DOUBLE PRECISION,
              inception_date TEXT,
              holder_count INTEGER,
              dividend_frequency TEXT,
              manager TEXT,
              company TEXT,
              custodian TEXT,
              region TEXT,
              updated_at TEXT
            )
            """)
            extra_cols = {
                "week_return": "DOUBLE PRECISION",
                "total_return": "DOUBLE PRECISION",
                "annualized_return": "DOUBLE PRECISION",
                "dividend_yield": "DOUBLE PRECISION",
                "region": "TEXT",
                "currency": "TEXT",
                "manager": "TEXT",
                "company": "TEXT",
                "custodian": "TEXT",
            }
            for col, typ in extra_cols.items():
                try:
                    conn.execute(f"ALTER TABLE etf_quotes ADD COLUMN IF NOT EXISTS {col} {typ}")
                except Exception:
                    pass
        else:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS etf_price_history(
              etf_code TEXT NOT NULL,
              trade_date TEXT NOT NULL,
              close REAL,
              change REAL,
              change_pct REAL,
              volume REAL,
              amount REAL,
              PRIMARY KEY(etf_code, trade_date)
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS etf_nav_history(
              etf_code TEXT NOT NULL,
              trade_date TEXT NOT NULL,
              price REAL,
              nav REAL,
              premium_pct REAL,
              PRIMARY KEY(etf_code, trade_date)
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS etf_basic_info(
              etf_code TEXT PRIMARY KEY,
              etf_name TEXT,
              full_name TEXT,
              aum_billion REAL,
              expense_ratio REAL,
              inception_date TEXT,
              holder_count INTEGER,
              dividend_frequency TEXT,
              manager TEXT,
              company TEXT,
              custodian TEXT,
              region TEXT,
              updated_at TEXT
            )
            """)
            existing_quote_columns = {
                str(row[1])
                for row in conn.execute(
                    "PRAGMA table_info(etf_quotes)"
                ).fetchall()
            }
            sqlite_quote_columns = {
                "week_return": "REAL",
                "total_return": "REAL",
                "annualized_return": "REAL",
                "dividend_yield": "REAL",
                "region": "TEXT",
                "currency": "TEXT",
                "manager": "TEXT",
                "company": "TEXT",
                "custodian": "TEXT",
            }
            for col, typ in sqlite_quote_columns.items():
                if col not in existing_quote_columns:
                    conn.execute(
                        f"ALTER TABLE etf_quotes ADD COLUMN {col} {typ}"
                    )

def calc_etf_market_row(etf_code: str, history: list[dict[str, Any]], basic: dict[str, Any]) -> dict[str, Any]:
    latest = history[0] if history else {}
    prev = history[1] if len(history) >= 2 else {}

    price = _to_float(_pick(latest, ["收盤價", "股價", "成交價", "Close"]))
    prev_price = _to_float(_pick(prev, ["收盤價", "股價", "成交價", "Close"]))

    change = _to_float(_pick(latest, ["漲跌", "漲跌價", "漲跌金額"]))
    change_pct = _to_float(_pick(latest, ["漲跌幅", "報酬率"]))

    if change is None and price is not None and prev_price is not None:
        change = price - prev_price
    if change_pct is None and price is not None and prev_price:
        change_pct = (price / prev_price - 1) * 100

    volume = _to_float(_pick(latest, ["成交量", "合成交易量", "交易量"]))
    amount = price * volume * 1000 if price is not None and volume is not None else None
    nav = _to_float(_pick(latest, ["淨值", "NAV"]))
    premium_pct = _to_float(_pick(latest, ["折溢價", "折溢價(%)", "折溢價率"]))

    management = _to_float(_pick(basic, ["管理費"]))
    custody = _to_float(_pick(basic, ["保管費"]))
    expense = _to_float(_pick(basic, ["總費用", "內扣費用", "總管理費"]))
    if expense is None and (management is not None or custody is not None):
        expense = (management or 0) + (custody or 0)

    return {
        "etf_code": etf_code,
        "etf_name": str(_pick(latest, ["股票名稱", "基金名稱"]) or _pick(basic, ["股票名稱", "基金名稱"]) or ALL_ETF_NAMES.get(etf_code) or etf_code),
        "full_name": str(_pick(basic, ["基金全名", "基金名稱"]) or ""),
        "price": price,
        "change": change,
        "change_pct": change_pct,
        "volume": volume,
        "amount": amount,
        "nav": nav,
        "premium_pct": premium_pct,
        "aum_billion": _to_float(_pick(latest, ["資產規模(億)", "資產規模"]) or _pick(basic, ["資產規模(億)", "資產規模"])),
        "expense_ratio": expense,
        "inception_date": _fmt_date(_pick(basic, ["發行日期", "成立時間", "成立日期"]) or _pick(latest, ["成立時間", "成立日期"])),
        "holder_count": _to_float(_pick(basic, ["持股人數", "受益人數"])),
        "dividend_frequency": _pick(basic, ["配息制度", "配息頻率"]),
        "week_return": calc_return(history, 5),
        "total_return": calc_return(history, len(history) - 1),
        "annualized_return": None,
        "dividend_yield": _to_float(_pick(basic, ["殖利率", "配息率"])),
        "region": _pick(latest, ["投資區域"]) or _pick(basic, ["投資區域"]),
        "currency": _pick(basic, ["計算幣別"]) or "NTD",
        "manager": _pick(basic, ["經理人", "基金經理人"]),
        "company": _pick(basic, ["投信公司", "發行公司", "發行商"]),
        "custodian": _pick(basic, ["保管銀行"]),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }

def history_rows(etf_code: str, history: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    price_rows = []
    nav_rows = []

    for r in history:
        d = _fmt_date(_pick(r, ["日期", "年月日", "Date", "資料日期"]))
        if not d:
            continue

        close = _to_float(_pick(r, ["收盤價", "股價", "成交價", "Close"]))
        change = _to_float(_pick(r, ["漲跌", "漲跌價", "漲跌金額"]))
        change_pct = _to_float(_pick(r, ["漲跌幅", "報酬率"]))
        volume = _to_float(_pick(r, ["成交量", "合成交易量", "交易量"]))
        amount = close * volume * 1000 if close is not None and volume is not None else None
        nav = _to_float(_pick(r, ["淨值", "NAV"]))
        premium_pct = _to_float(_pick(r, ["折溢價", "折溢價(%)", "折溢價率"]))

        if close is not None:
            price_rows.append({
                "etf_code": etf_code,
                "trade_date": d,
                "close": close,
                "change": change,
                "change_pct": change_pct,
                "volume": volume,
                "amount": amount,
            })

        if nav is not None or premium_pct is not None:
            nav_rows.append({
                "etf_code": etf_code,
                "trade_date": d,
                "price": close,
                "nav": nav,
                "premium_pct": premium_pct,
            })

    return price_rows, nav_rows

def save_all(rows: list[dict[str, Any]], price_history: list[dict[str, Any]], nav_history: list[dict[str, Any]]) -> int:
    ensure_etf_tables()
    with get_conn() as conn:
        for r in rows:
            if conn.postgres:
                conn.execute(
                    """
                    INSERT INTO etf_quotes(
                      etf_code, etf_name, price, change, change_pct, volume, amount,
                      nav, premium_pct, aum_billion, expense_ratio, inception_date,
                      holder_count, dividend_frequency, week_return, total_return,
                      annualized_return, dividend_yield, region, currency, manager,
                      company, custodian, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (etf_code) DO UPDATE SET
                      etf_name=EXCLUDED.etf_name,
                      price=EXCLUDED.price,
                      change=EXCLUDED.change,
                      change_pct=EXCLUDED.change_pct,
                      volume=EXCLUDED.volume,
                      amount=EXCLUDED.amount,
                      nav=EXCLUDED.nav,
                      premium_pct=EXCLUDED.premium_pct,
                      aum_billion=EXCLUDED.aum_billion,
                      expense_ratio=COALESCE(EXCLUDED.expense_ratio, etf_quotes.expense_ratio),
                      inception_date=COALESCE(EXCLUDED.inception_date, etf_quotes.inception_date),
                      holder_count=COALESCE(EXCLUDED.holder_count, etf_quotes.holder_count),
                      dividend_frequency=COALESCE(NULLIF(EXCLUDED.dividend_frequency, ''), etf_quotes.dividend_frequency),
                      week_return=COALESCE(EXCLUDED.week_return, etf_quotes.week_return),
                      total_return=COALESCE(EXCLUDED.total_return, etf_quotes.total_return),
                      annualized_return=COALESCE(EXCLUDED.annualized_return, etf_quotes.annualized_return),
                      dividend_yield=COALESCE(EXCLUDED.dividend_yield, etf_quotes.dividend_yield),
                      region=COALESCE(NULLIF(EXCLUDED.region, ''), etf_quotes.region),
                      currency=COALESCE(NULLIF(EXCLUDED.currency, ''), etf_quotes.currency),
                      manager=COALESCE(NULLIF(EXCLUDED.manager, ''), etf_quotes.manager),
                      company=COALESCE(NULLIF(EXCLUDED.company, ''), etf_quotes.company),
                      custodian=COALESCE(NULLIF(EXCLUDED.custodian, ''), etf_quotes.custodian),
                      updated_at=EXCLUDED.updated_at
                    """,
                    (
                        r["etf_code"], r["etf_name"], r["price"], r["change"], r["change_pct"],
                        r["volume"], r["amount"], r["nav"], r["premium_pct"], r["aum_billion"],
                        r["expense_ratio"], r["inception_date"], r["holder_count"],
                        r["dividend_frequency"], r["week_return"], r["total_return"],
                        r["annualized_return"], r["dividend_yield"], r["region"],
                        r["currency"], r["manager"], r["company"], r["custodian"],
                        r["updated_at"],
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO etf_quotes(
                      etf_code, etf_name, price, change, change_pct, volume, amount,
                      nav, premium_pct, aum_billion, expense_ratio, inception_date,
                      holder_count, dividend_frequency, week_return, total_return,
                      annualized_return, dividend_yield, region, currency, manager,
                      company, custodian, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r["etf_code"], r["etf_name"], r["price"], r["change"], r["change_pct"],
                        r["volume"], r["amount"], r["nav"], r["premium_pct"], r["aum_billion"],
                        r["expense_ratio"], r["inception_date"], r["holder_count"],
                        r["dividend_frequency"], r["week_return"], r["total_return"],
                        r["annualized_return"], r["dividend_yield"], r["region"],
                        r["currency"], r["manager"], r["company"], r["custodian"],
                        r["updated_at"],
                    ),
                )

            conn.execute(
                """
                INSERT INTO etf_basic_info(
                  etf_code, etf_name, full_name, aum_billion, expense_ratio,
                  inception_date, holder_count, dividend_frequency, manager, company,
                  custodian, region, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (etf_code) DO UPDATE SET
                  etf_name=EXCLUDED.etf_name,
                  full_name=EXCLUDED.full_name,
                  aum_billion=EXCLUDED.aum_billion,
                  expense_ratio=COALESCE(EXCLUDED.expense_ratio, etf_basic_info.expense_ratio),
                  inception_date=COALESCE(EXCLUDED.inception_date, etf_basic_info.inception_date),
                  holder_count=COALESCE(EXCLUDED.holder_count, etf_basic_info.holder_count),
                  dividend_frequency=COALESCE(NULLIF(EXCLUDED.dividend_frequency, ''), etf_basic_info.dividend_frequency),
                  manager=COALESCE(NULLIF(EXCLUDED.manager, ''), etf_basic_info.manager),
                  company=COALESCE(NULLIF(EXCLUDED.company, ''), etf_basic_info.company),
                  custodian=COALESCE(NULLIF(EXCLUDED.custodian, ''), etf_basic_info.custodian),
                  region=COALESCE(NULLIF(EXCLUDED.region, ''), etf_basic_info.region),
                  updated_at=EXCLUDED.updated_at
                """ if conn.postgres else """
                INSERT OR REPLACE INTO etf_basic_info(
                  etf_code, etf_name, full_name, aum_billion, expense_ratio,
                  inception_date, holder_count, dividend_frequency, manager, company,
                  custodian, region, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r["etf_code"], r["etf_name"], r["full_name"], r["aum_billion"],
                    r["expense_ratio"], r["inception_date"], r["holder_count"],
                    r["dividend_frequency"], r["manager"], r["company"],
                    r["custodian"], r["region"], r["updated_at"],
                ),
            )

        for h in price_history:
            if conn.postgres:
                conn.execute(
                    """
                    INSERT INTO etf_price_history(etf_code, trade_date, close, change, change_pct, volume, amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (etf_code, trade_date) DO UPDATE SET
                      close=EXCLUDED.close,
                      change=EXCLUDED.change,
                      change_pct=EXCLUDED.change_pct,
                      volume=EXCLUDED.volume,
                      amount=EXCLUDED.amount
                    """,
                    (h["etf_code"], h["trade_date"], h["close"], h["change"], h["change_pct"], h["volume"], h["amount"]),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO etf_price_history(etf_code, trade_date, close, change, change_pct, volume, amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (h["etf_code"], h["trade_date"], h["close"], h["change"], h["change_pct"], h["volume"], h["amount"]),
                )

        for h in nav_history:
            if conn.postgres:
                conn.execute(
                    """
                    INSERT INTO etf_nav_history(etf_code, trade_date, price, nav, premium_pct)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (etf_code, trade_date) DO UPDATE SET
                      price=EXCLUDED.price,
                      nav=EXCLUDED.nav,
                      premium_pct=EXCLUDED.premium_pct
                    """,
                    (h["etf_code"], h["trade_date"], h["price"], h["nav"], h["premium_pct"]),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO etf_nav_history(etf_code, trade_date, price, nav, premium_pct)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (h["etf_code"], h["trade_date"], h["price"], h["nav"], h["premium_pct"]),
                )

    return len(rows)

def update_pocket_etf_market(
    dt_range: int = 260,
    sleep_sec: float = 0.35,
    codes: list[str] | None = None,
) -> dict[str, Any]:
    selected_codes = list(dict.fromkeys(
        str(code or "").strip().upper()
        for code in (codes if codes is not None else ALL_ETF_CODES)
        if str(code or "").strip()
    ))
    rows = []
    ph = []
    nh = []
    errors = []

    print(
        f"Start update_pocket_etf_market: total={len(selected_codes)}, "
        f"dt_range={dt_range}",
        flush=True,
    )

    for i, code in enumerate(selected_codes, start=1):
        try:
            print(
                f"[{i}/{len(selected_codes)}] Fetch Pocket ETF market {code}...",
                flush=True,
            )
            history = fetch_quote_history(code, dt_range=dt_range)
            basic = fetch_basic(code)
            row = calc_etf_market_row(code, history, basic)
            p_rows, n_rows = history_rows(code, history)

            rows.append(row)
            ph.extend(p_rows)
            nh.extend(n_rows)

            print(
                f"[{i}/{len(selected_codes)}] Done {code}: price={row.get('price')}, "
                f"change_pct={row.get('change_pct')}, hist={len(p_rows)}, nav={len(n_rows)}",
                flush=True
            )
        except Exception as e:
            errors.append({"etf_code": code, "error": str(e)})
            print(f"[{i}/{len(selected_codes)}] Error {code}: {e}", flush=True)

        time.sleep(sleep_sec)

    saved = save_all(rows, ph, nh)

    return {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "saved": saved,
        "price_history_rows": len(ph),
        "nav_history_rows": len(nh),
        "errors": errors,
    }
