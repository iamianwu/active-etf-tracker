from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

from ..database import get_conn, init_db

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
TWSE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"

HEADERS = {
    "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 Chrome Safari",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
}


def now_iso() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def today() -> str:
    return datetime.now(TAIPEI_TZ).date().isoformat()


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


def pick(row: dict[str, Any], keys: list[str]) -> Any:
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]

    norm = {str(k).replace(" ", "").replace("　", ""): k for k in row.keys()}

    for k in keys:
        kk = k.replace(" ", "").replace("　", "")
        if kk in norm and row[norm[kk]] not in (None, ""):
            return row[norm[kk]]

    return None


def find_code(row: dict[str, Any]) -> str | None:
    v = pick(
        row,
        [
            "Code",
            "證券代號",
            "有價證券代號",
            "股票代號",
            "代號",
            "SecuritiesCompanyCode",
            "SecuritiesCode",
            "CompanyCode",
            "stock_id",
        ],
    )

    if v is not None:
        m = re.search(r"\b(\d{4})\b", str(v))
        if m:
            return m.group(1)

    for x in row.values():
        s = str(x or "").strip()
        if re.fullmatch(r"\d{4}", s):
            return s

    return None


def trade_date(row: dict[str, Any]) -> str:
    v = pick(row, ["Date", "TradeDate", "資料日期", "日期", "交易日期"])

    if not v:
        return today()

    s = str(v)

    m = re.search(r"(20\d{2})[-/]?(\d{2})[-/]?(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    m = re.search(r"(\d{3})[-/]?(\d{2})[-/]?(\d{2})", s)
    if m:
        return f"{int(m.group(1)) + 1911:04d}-{m.group(2)}-{m.group(3)}"

    return today()


def row_to_quote(row: dict[str, Any], market: str) -> dict[str, Any] | None:
    code = find_code(row)

    if not code or not re.fullmatch(r"\d{4}", code):
        return None

    name = str(
        pick(
            row,
            [
                "Name",
                "證券名稱",
                "有價證券名稱",
                "股票名稱",
                "名稱",
                "CompanyName",
                "SecuritiesCompanyName",
                "stock_name",
            ],
        )
        or code
    ).strip()

    close = to_float(pick(row, ["ClosingPrice", "收盤價", "收盤", "Close", "close"]))

    if close is None or close <= 0:
        return None

    change = to_float(
        pick(
            row,
            [
                "Change",
                "漲跌價差",
                "漲跌",
                "漲跌(+/-)",
                "漲跌(+/-)價差",
                "ChangeAmount",
                "PriceChange",
            ],
        )
    )

    pct = to_float(pick(row, ["ChangePercent", "漲跌幅", "漲跌幅(%)", "漲跌幅%", "Change%"]))

    if pct is None and change is not None:
        prev = close - change
        if prev > 0:
            pct = change / prev * 100.0

    volume = to_float(
        pick(
            row,
            [
                "TradeVolume",
                "成交股數",
                "成交股數(股)",
                "成交量",
                "Volume",
                "volume",
            ],
        )
    )

    amount = to_float(
        pick(
            row,
            [
                "TradeValue",
                "成交金額",
                "成交金額(元)",
                "成交值",
                "Amount",
                "amount",
            ],
        )
    )

    if amount is None and volume is not None:
        amount = close * volume

    return {
        "stock_code": code,
        "stock_name": name,
        "price": close,
        "change": change,
        "change_pct": pct,
        "volume": volume,
        "amount": amount,
        "open": to_float(pick(row, ["Open", "開盤價", "開盤"])),
        "high": to_float(pick(row, ["High", "最高價", "最高"])),
        "low": to_float(pick(row, ["Low", "最低價", "最低"])),
        "market": market,
        "source": "twse_openapi" if market == "TWSE" else "tpex_openapi",
        "trade_date": trade_date(row),
    }


def ensure_tables() -> None:
    """
    V27 fix:
    你的 Supabase 內 stock_price_history 已經存在，但舊版 schema 沒有 stock_name 欄位。
    CREATE TABLE IF NOT EXISTS 不會自動幫既有表補欄位，所以這裡要 ALTER TABLE 補齊全部欄位。
    """
    init_db()

    with get_conn() as conn:
        if conn.postgres:
            stock_quotes_cols = {
                "change": "DOUBLE PRECISION",
                "volume": "DOUBLE PRECISION",
                "amount": "DOUBLE PRECISION",
                "market": "TEXT",
                "source": "TEXT",
                "trade_date": "TEXT",
            }

            for col, typ in stock_quotes_cols.items():
                conn.execute(f"ALTER TABLE stock_quotes ADD COLUMN IF NOT EXISTS {col} {typ}")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_price_history(
                  stock_code TEXT NOT NULL,
                  trade_date TEXT NOT NULL,
                  PRIMARY KEY(stock_code, trade_date)
                )
                """
            )

            stock_price_history_cols = {
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

            for col, typ in stock_price_history_cols.items():
                conn.execute(f"ALTER TABLE stock_price_history ADD COLUMN IF NOT EXISTS {col} {typ}")

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
            cols = {r["name"] for r in rows}

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
                if col not in cols:
                    conn.execute(f"ALTER TABLE stock_price_history ADD COLUMN {col} {typ}")


def fetch_array(url: str) -> list[dict[str, Any]]:
    r = requests.get(url, headers=HEADERS, timeout=45)
    r.raise_for_status()

    data = r.json()

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if isinstance(data, dict):
        for k in ["data", "result", "items", "rows"]:
            if isinstance(data.get(k), list):
                return [x for x in data[k] if isinstance(x, dict)]

    return []


def fetch_official_quotes() -> dict[str, dict[str, Any]]:
    out = {}

    for market, url in [("TWSE", TWSE_URL), ("TPEX", TPEX_URL)]:
        print(f"Fetch {market}: {url}", flush=True)

        try:
            rows = fetch_array(url)
            print(f"{market} rows={len(rows)}", flush=True)
        except Exception as e:
            print(f"{market} fetch error: {e}", flush=True)
            continue

        parsed = 0

        for row in rows:
            q = row_to_quote(row, market)

            if q:
                out[q["stock_code"]] = q
                parsed += 1

        print(f"{market} parsed={parsed}", flush=True)

    return out


def save_quotes(quotes: dict[str, dict[str, Any]]) -> int:
    ensure_tables()

    now = now_iso()
    saved = 0

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

            saved += 1

    return saved


def update_official_close_quotes() -> dict[str, Any]:
    ensure_tables()

    quotes = fetch_official_quotes()
    saved = save_quotes(quotes)

    print(f"Official close quotes saved={saved}", flush=True)

    return {
        "updated_at": now_iso(),
        "quotes_fetched": len(quotes),
        "quotes_saved": saved,
        "source": "official_openapi_close",
    }


if __name__ == "__main__":
    print(update_official_close_quotes())
