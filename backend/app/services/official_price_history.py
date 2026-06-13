from __future__ import annotations

import os
import re
import time
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

from ..database import get_conn, init_db, normal_stock_condition

TAIPEI_TZ = ZoneInfo("Asia/Taipei")

TWSE_STOCK_DAY_URLS = [
    "https://www.twse.com.tw/exchangeReport/STOCK_DAY",
    "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY",
]

TPEX_TRADING_STOCK_URL = "https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock"
TPEX_ST43_OLD_URL = "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
}


def now_iso() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def to_float(v: Any) -> float | None:
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

    s = (
        s.replace(",", "")
        .replace("%", "")
        .replace("％", "")
        .replace("＋", "+")
        .replace("－", "-")
        .replace("−", "-")
        .replace("▲", "+")
        .replace("△", "+")
        .replace("▼", "-")
        .replace("▽", "-")
    )

    try:
        return float(s)
    except Exception:
        m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
        return float(m.group(0)) if m else None


def normalize_trade_date(v: Any, month_hint: str | None = None) -> str | None:
    if v is None:
        return None

    s = str(v).strip()

    m = re.search(r"(20\d{2})[-/]?(\d{1,2})[-/]?(\d{1,2})", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # 民國年，例如 115/06/12
    m = re.search(r"(\d{3})[-/]?(\d{1,2})[-/]?(\d{1,2})", s)
    if m:
        return f"{int(m.group(1)) + 1911:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # 只有日，例如舊版櫃買資料可能出現 12
    m = re.fullmatch(r"(\d{1,2})", s)
    if m and month_hint:
        y, mo = month_hint.split("-")
        return f"{int(y):04d}-{int(mo):02d}-{int(m.group(1)):02d}"

    return None


def month_list(months: int) -> list[str]:
    today = datetime.now(TAIPEI_TZ).date()
    y = today.year
    m = today.month
    out = []

    for _ in range(max(1, months)):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y -= 1
            m = 12

    return out


def ensure_tables() -> None:
    init_db()

    with get_conn() as conn:
        if conn.postgres:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_price_history(
                  stock_code TEXT NOT NULL,
                  trade_date TEXT NOT NULL,
                  PRIMARY KEY(stock_code, trade_date)
                )
                """
            )

            cols = {
                "stock_name": "TEXT",
                "open": "DOUBLE PRECISION",
                "high": "DOUBLE PRECISION",
                "low": "DOUBLE PRECISION",
                "close": "DOUBLE PRECISION",
                "change": "DOUBLE PRECISION",
                "change_pct": "DOUBLE PRECISION",
                "volume": "DOUBLE PRECISION",
                "amount": "DOUBLE PRECISION",
                "market": "TEXT",
                "source": "TEXT",
                "updated_at": "TEXT",
            }

            for col, typ in cols.items():
                conn.execute(f"ALTER TABLE stock_price_history ADD COLUMN IF NOT EXISTS {col} {typ}")

            conn.execute("ALTER TABLE stock_quotes ADD COLUMN IF NOT EXISTS market TEXT")
            conn.execute("ALTER TABLE stock_quotes ADD COLUMN IF NOT EXISTS source TEXT")
            conn.execute("ALTER TABLE stock_quotes ADD COLUMN IF NOT EXISTS trade_date TEXT")

        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_price_history(
                  stock_code TEXT NOT NULL,
                  trade_date TEXT NOT NULL,
                  PRIMARY KEY(stock_code, trade_date)
                )
                """
            )

            rows = conn.execute("PRAGMA table_info(stock_price_history)").fetchall()
            existing = {r["name"] for r in rows}

            for col, typ in {
                "stock_name": "TEXT",
                "open": "REAL",
                "high": "REAL",
                "low": "REAL",
                "close": "REAL",
                "change": "REAL",
                "change_pct": "REAL",
                "volume": "REAL",
                "amount": "REAL",
                "market": "TEXT",
                "source": "TEXT",
                "updated_at": "TEXT",
            }.items():
                if col not in existing:
                    conn.execute(f"ALTER TABLE stock_price_history ADD COLUMN {col} {typ}")


def get_holding_codes_with_market() -> list[dict[str, str]]:
    ensure_tables()

    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT
              h.stock_code,
              MAX(h.stock_name) AS stock_name,
              MAX(q.market) AS market
            FROM holdings h
            LEFT JOIN stock_quotes q ON q.stock_code = h.stock_code
            WHERE {normal_stock_condition('h')}
            GROUP BY h.stock_code
            ORDER BY h.stock_code
            """
        ).fetchall()

    out = []

    for r in rows:
        code = str(r["stock_code"]).strip()

        if not re.fullmatch(r"\d{4}", code):
            continue

        out.append(
            {
                "stock_code": code,
                "stock_name": str(r["stock_name"] or code).strip(),
                "market": str(r["market"] or "").strip().upper(),
            }
        )

    return out


def fetch_twse_month(code: str, stock_name: str, yyyy_mm: str) -> list[dict[str, Any]]:
    yyyymm01 = yyyy_mm.replace("-", "") + "01"
    rows_out: list[dict[str, Any]] = []

    for url in TWSE_STOCK_DAY_URLS:
        params = {"response": "json", "date": yyyymm01, "stockNo": code}

        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if r.status_code != 200:
                continue

            payload = r.json()
        except Exception:
            continue

        data = payload.get("data") if isinstance(payload, dict) else None

        if not isinstance(data, list) or not data:
            continue

        for item in data:
            if not isinstance(item, list) or len(item) < 7:
                continue

            trade_date = normalize_trade_date(item[0], month_hint=yyyy_mm)
            close = to_float(item[6])

            if not trade_date or close is None or close <= 0:
                continue

            change = to_float(item[7]) if len(item) > 7 else None
            pct = None

            if change is not None:
                prev = close - change
                if prev > 0:
                    pct = change / prev * 100.0

            rows_out.append(
                {
                    "stock_code": code,
                    "trade_date": trade_date,
                    "stock_name": stock_name,
                    "open": to_float(item[3]) if len(item) > 3 else None,
                    "high": to_float(item[4]) if len(item) > 4 else None,
                    "low": to_float(item[5]) if len(item) > 5 else None,
                    "close": close,
                    "change": change,
                    "change_pct": pct,
                    "volume": to_float(item[1]) if len(item) > 1 else None,
                    "amount": to_float(item[2]) if len(item) > 2 else None,
                    "market": "TWSE",
                    "source": "twse_stock_day",
                }
            )

        if rows_out:
            break

    return rows_out


def _extract_table_rows(payload: Any) -> list[Any]:
    if isinstance(payload, dict):
        for key in ["tables", "table"]:
            if isinstance(payload.get(key), list):
                out = []
                for tb in payload[key]:
                    if isinstance(tb, dict):
                        data = tb.get("data") or tb.get("aaData")
                        if isinstance(data, list):
                            out.extend(data)
                if out:
                    return out

        for key in ["data", "aaData", "items", "rows"]:
            if isinstance(payload.get(key), list):
                return payload[key]

    if isinstance(payload, list):
        return payload

    return []


def _parse_tpex_list_row(item: list[Any], code: str, stock_name: str, yyyy_mm: str) -> dict[str, Any] | None:
    # 舊版 st43_result 常見欄位：
    # 日期, 成交仟股, 成交仟元, 開盤, 最高, 最低, 收盤, 漲跌, 筆數
    if len(item) < 7:
        return None

    trade_date = normalize_trade_date(item[0], month_hint=yyyy_mm)

    close = to_float(item[6])

    # 新版欄位偶爾位置不同，嘗試找最後幾個數值中較像收盤價者
    if close is None:
        for idx in [5, 6, 4, 3]:
            if idx < len(item):
                v = to_float(item[idx])
                if v is not None and v > 0:
                    close = v
                    break

    if not trade_date or close is None or close <= 0:
        return None

    change = to_float(item[7]) if len(item) > 7 else None
    pct = None

    if change is not None:
        prev = close - change
        if prev > 0:
            pct = change / prev * 100.0

    volume = to_float(item[1]) if len(item) > 1 else None
    amount = to_float(item[2]) if len(item) > 2 else None

    # 舊版櫃買常用「仟股 / 仟元」，轉成股 / 元，避免金額太小。
    if volume is not None and volume < 10_000_000:
        volume = volume * 1000.0

    if amount is not None and amount < 10_000_000_000:
        amount = amount * 1000.0

    return {
        "stock_code": code,
        "trade_date": trade_date,
        "stock_name": stock_name,
        "open": to_float(item[3]) if len(item) > 3 else None,
        "high": to_float(item[4]) if len(item) > 4 else None,
        "low": to_float(item[5]) if len(item) > 5 else None,
        "close": close,
        "change": change,
        "change_pct": pct,
        "volume": volume,
        "amount": amount,
        "market": "TPEX",
        "source": "tpex_trading_stock",
    }


def _parse_tpex_dict_row(row: dict[str, Any], code: str, stock_name: str, yyyy_mm: str) -> dict[str, Any] | None:
    def pick_any(keys: list[str]) -> Any:
        for k in keys:
            if k in row and row[k] not in (None, ""):
                return row[k]
        norm = {str(k).replace(" ", "").replace("　", ""): k for k in row.keys()}
        for k in keys:
            kk = k.replace(" ", "").replace("　", "")
            if kk in norm and row[norm[kk]] not in (None, ""):
                return row[norm[kk]]
        return None

    trade_date = normalize_trade_date(pick_any(["Date", "日期", "資料日期", "交易日期"]), month_hint=yyyy_mm)
    close = to_float(pick_any(["Close", "收盤", "收盤價", "ClosingPrice"]))

    if not trade_date or close is None or close <= 0:
        return None

    change = to_float(pick_any(["Change", "漲跌", "漲跌價差"]))
    pct = None

    if change is not None:
        prev = close - change
        if prev > 0:
            pct = change / prev * 100.0

    volume = to_float(pick_any(["成交股數", "成交量", "TradeVolume", "Volume"]))
    amount = to_float(pick_any(["成交金額", "成交值", "TradeValue", "Amount"]))

    return {
        "stock_code": code,
        "trade_date": trade_date,
        "stock_name": stock_name,
        "open": to_float(pick_any(["Open", "開盤", "開盤價"])),
        "high": to_float(pick_any(["High", "最高", "最高價"])),
        "low": to_float(pick_any(["Low", "最低", "最低價"])),
        "close": close,
        "change": change,
        "change_pct": pct,
        "volume": volume,
        "amount": amount,
        "market": "TPEX",
        "source": "tpex_trading_stock",
    }


def fetch_tpex_month(code: str, stock_name: str, yyyy_mm: str) -> list[dict[str, Any]]:
    rows_out: list[dict[str, Any]] = []
    y, m = yyyy_mm.split("-")
    roc_y = int(y) - 1911

    attempts = [
        (
            TPEX_TRADING_STOCK_URL,
            {
                "code": code,
                "date": f"{y}/{m}/01",
                "id": "",
                "response": "json",
            },
        ),
        (
            TPEX_ST43_OLD_URL,
            {
                "l": "zh-tw",
                "d": f"{roc_y}/{m}",
                "stkno": code,
            },
        ),
    ]

    for url, params in attempts:
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if r.status_code != 200:
                continue

            payload = r.json()
        except Exception:
            continue

        table_rows = _extract_table_rows(payload)

        if not table_rows:
            continue

        for item in table_rows:
            parsed = None

            if isinstance(item, list):
                parsed = _parse_tpex_list_row(item, code, stock_name, yyyy_mm)
            elif isinstance(item, dict):
                parsed = _parse_tpex_dict_row(item, code, stock_name, yyyy_mm)

            if parsed:
                rows_out.append(parsed)

        if rows_out:
            break

    return rows_out


def save_history_rows(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0

    ensure_tables()
    now = now_iso()
    saved = 0

    with get_conn() as conn:
        for r in rows:
            if conn.postgres:
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
                        r.get("stock_code"),
                        r.get("trade_date"),
                        r.get("stock_name"),
                        r.get("open"),
                        r.get("high"),
                        r.get("low"),
                        r.get("close"),
                        r.get("change"),
                        r.get("change_pct"),
                        r.get("volume"),
                        r.get("amount"),
                        r.get("market"),
                        r.get("source"),
                        now,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stock_price_history(
                      stock_code, trade_date, stock_name, open, high, low, close,
                      change, change_pct, volume, amount, market, source, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r.get("stock_code"),
                        r.get("trade_date"),
                        r.get("stock_name"),
                        r.get("open"),
                        r.get("high"),
                        r.get("low"),
                        r.get("close"),
                        r.get("change"),
                        r.get("change_pct"),
                        r.get("volume"),
                        r.get("amount"),
                        r.get("market"),
                        r.get("source"),
                        now,
                    ),
                )

            saved += 1

    return saved


def backfill_official_price_history(
    months: int = 4,
    batch_total: int = 1,
    batch_index: int = 0,
    sleep_sec: float = 0.15,
) -> dict[str, Any]:
    ensure_tables()

    all_codes = get_holding_codes_with_market()

    selected = [
        x
        for i, x in enumerate(all_codes)
        if batch_total <= 1 or (i % batch_total) == batch_index
    ]

    months_list = month_list(months)

    print(
        f"Start official history backfill: total_codes={len(all_codes)}, selected={len(selected)}, "
        f"batch={batch_index + 1}/{batch_total}, months={months_list}",
        flush=True,
    )

    total_rows = 0
    total_saved = 0
    failures: list[str] = []

    for idx, item in enumerate(selected, start=1):
        code = item["stock_code"]
        name = item["stock_name"]
        market = item["market"]

        print(f"[{idx}/{len(selected)}] {code} {name} market={market or '-'}", flush=True)

        code_rows: list[dict[str, Any]] = []

        for ym in months_list:
            rows: list[dict[str, Any]] = []

            if market == "TWSE":
                rows = fetch_twse_month(code, name, ym)
            elif market == "TPEX":
                rows = fetch_tpex_month(code, name, ym)
            else:
                # 若 market 不明，先上市再上櫃。
                rows = fetch_twse_month(code, name, ym)
                if not rows:
                    rows = fetch_tpex_month(code, name, ym)

            if rows:
                code_rows.extend(rows)

            time.sleep(sleep_sec)

        if code_rows:
            saved = save_history_rows(code_rows)
            total_rows += len(code_rows)
            total_saved += saved
            print(f"  rows={len(code_rows)}, saved={saved}", flush=True)
        else:
            failures.append(code)
            print(f"  no history rows", flush=True)

    print(
        f"Official history backfill done: rows={total_rows}, saved={total_saved}, failures={len(failures)}",
        flush=True,
    )

    if failures:
        print("Failure examples: " + ", ".join(failures[:80]), flush=True)

    return {
        "updated_at": now_iso(),
        "total_codes": len(all_codes),
        "selected_codes": len(selected),
        "batch_total": batch_total,
        "batch_index": batch_index,
        "months": months,
        "rows": total_rows,
        "saved": total_saved,
        "failures": failures[:80],
    }


if __name__ == "__main__":
    print(
        backfill_official_price_history(
            months=int(os.getenv("HISTORY_MONTHS", "4")),
            batch_total=int(os.getenv("BATCH_TOTAL", "1")),
            batch_index=int(os.getenv("BATCH_INDEX", "0")),
            sleep_sec=float(os.getenv("HISTORY_SLEEP_SEC", "0.15")),
        )
    )
