from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests

from ..database import get_conn, init_db, normal_stock_condition

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
TWSE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 Chrome Safari",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
}


def now_iso() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def today() -> str:
    return datetime.now(TAIPEI_TZ).date().isoformat()


def date_only(v: Any) -> str:
    s = str(v or "").strip()
    m = re.search(r"(20\d{2})[-/](\d{2})[-/](\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return s[:10]


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


def trade_date(row: dict[str, Any], fallback_date: str | None = None) -> str:
    v = pick(row, ["Date", "TradeDate", "資料日期", "日期", "交易日期"])
    if not v:
        return fallback_date or today()

    s = str(v)
    m = re.search(r"(20\d{2})[-/]?(\d{2})[-/]?(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    m = re.search(r"(\d{3})[-/]?(\d{2})[-/]?(\d{2})", s)
    if m:
        return f"{int(m.group(1)) + 1911:04d}-{m.group(2)}-{m.group(3)}"

    return fallback_date or today()


def row_to_quote(row: dict[str, Any], market: str, fallback_trade_date: str | None = None) -> dict[str, Any] | None:
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
        pick(row, ["Change", "漲跌價差", "漲跌", "漲跌(+/-)", "漲跌(+/-)價差", "ChangeAmount", "PriceChange"])
    )
    pct = to_float(pick(row, ["ChangePercent", "漲跌幅", "漲跌幅(%)", "漲跌幅%", "Change%"]))

    if pct is None and change is not None:
        prev = close - change
        if prev > 0:
            pct = change / prev * 100.0

    volume = to_float(pick(row, ["TradeVolume", "成交股數", "成交股數(股)", "成交量", "Volume", "volume"]))
    amount = to_float(pick(row, ["TradeValue", "成交金額", "成交金額(元)", "成交值", "Amount", "amount"]))
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
        "open": to_float(pick(row, ["OpeningPrice", "Open", "開盤價", "開盤"])),
        "high": to_float(pick(row, ["HighestPrice", "High", "最高價", "最高"])),
        "low": to_float(pick(row, ["LowestPrice", "Low", "最低價", "最低"])),
        "market": market,
        "source": "twse_openapi" if market == "TWSE" else "tpex_openapi",
        "trade_date": trade_date(row, fallback_trade_date),
    }


def ensure_tables() -> None:
    init_db()
    with get_conn() as conn:
        if conn.postgres:
            for col, typ in {
                "change": "DOUBLE PRECISION",
                "volume": "DOUBLE PRECISION",
                "amount": "DOUBLE PRECISION",
                "market": "TEXT",
                "source": "TEXT",
                "trade_date": "TEXT",
            }.items():
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

            for col, typ in {
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
            }.items():
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


def get_latest_holding_scope() -> tuple[str, set[str]]:
    ensure_tables()
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(data_date) AS data_date FROM holdings").fetchone()
        latest_date = date_only(row["data_date"] if row else "")

        if not latest_date:
            return "", set()

        rows = conn.execute(
            f"SELECT DISTINCT h.stock_code FROM holdings h WHERE h.data_date = ? AND {normal_stock_condition('h')}",
            (latest_date,),
        ).fetchall()

    codes = {str(r["stock_code"]).strip() for r in rows if re.fullmatch(r"\d{4}", str(r["stock_code"]).strip())}
    return latest_date, codes


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


def fetch_official_quotes(only_codes: set[str] | None = None, fallback_trade_date: str | None = None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}

    for market, url in [("TWSE", TWSE_URL), ("TPEX", TPEX_URL)]:
        print(f"Fetch {market}: {url}", flush=True)

        try:
            rows = fetch_array(url)
            print(f"{market} rows={len(rows)}", flush=True)
        except Exception as e:
            print(f"{market} fetch error: {e}", flush=True)
            continue

        parsed = kept = 0

        for row in rows:
            q = row_to_quote(row, market, fallback_trade_date=fallback_trade_date)
            if not q:
                continue

            parsed += 1
            code = q["stock_code"]

            if only_codes is not None and code not in only_codes:
                continue

            out[code] = q
            kept += 1

        print(f"{market} parsed={parsed}, kept_for_holdings={kept}", flush=True)

    return out


def fetch_yahoo_chart_quote(code: str, target_date: str) -> dict[str, Any] | None:
    try:
        target = datetime.fromisoformat(target_date).date()
    except Exception:
        return None

    start = target - timedelta(days=7)
    end = target + timedelta(days=2)

    period1 = int(datetime(start.year, start.month, start.day, tzinfo=TAIPEI_TZ).timestamp())
    period2 = int(datetime(end.year, end.month, end.day, tzinfo=TAIPEI_TZ).timestamp())

    for suffix, market in [(".TW", "TWSE"), (".TWO", "TPEX")]:
        symbol = f"{code}{suffix}"
        url = YAHOO_URL.format(symbol=symbol)

        try:
            r = requests.get(
                url,
                headers=HEADERS,
                params={
                    "period1": period1,
                    "period2": period2,
                    "interval": "1d",
                    "events": "history",
                },
                timeout=25,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"Yahoo fallback error {symbol}: {e}", flush=True)
            continue

        result = ((data.get("chart") or {}).get("result") or [None])[0]
        if not result:
            continue

        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        meta = result.get("meta") or {}

        closes = quote.get("close") or []
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        volumes = quote.get("volume") or []

        idx = None
        for i, ts in enumerate(timestamps):
            d = datetime.fromtimestamp(int(ts), tz=TAIPEI_TZ).date().isoformat()
            close = to_float(closes[i] if i < len(closes) else None)
            if d == target_date and close is not None and close > 0:
                idx = i
                break

        if idx is None:
            continue

        close = to_float(closes[idx])
        if close is None or close <= 0:
            continue

        prev_close = None
        for j in range(idx - 1, -1, -1):
            x = to_float(closes[j] if j < len(closes) else None)
            if x is not None and x > 0:
                prev_close = x
                break

        change = close - prev_close if prev_close else None
        change_pct = (change / prev_close * 100.0) if prev_close and change is not None else None
        volume = to_float(volumes[idx] if idx < len(volumes) else None)
        amount = close * volume if volume is not None else None

        name = str(meta.get("shortName") or meta.get("longName") or code)

        return {
            "stock_code": code,
            "stock_name": name,
            "price": close,
            "change": change,
            "change_pct": change_pct,
            "volume": volume,
            "amount": amount,
            "open": to_float(opens[idx] if idx < len(opens) else None),
            "high": to_float(highs[idx] if idx < len(highs) else None),
            "low": to_float(lows[idx] if idx < len(lows) else None),
            "market": market,
            "source": "yahoo_chart_fallback",
            "trade_date": target_date,
        }

    return None


def fetch_yahoo_missing_exact_quotes(missing_codes: set[str], target_date: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}

    if not missing_codes or not target_date:
        return out

    print(f"Yahoo fallback exact target_date={target_date}, codes={len(missing_codes)}", flush=True)

    for i, code in enumerate(sorted(missing_codes), 1):
        q = fetch_yahoo_chart_quote(code, target_date)
        if q:
            out[code] = q
            print(f"Yahoo fallback ok {i}/{len(missing_codes)} {code} price={q.get('price')}", flush=True)
        else:
            print(f"Yahoo fallback missing {i}/{len(missing_codes)} {code}", flush=True)

    return out


def save_quotes(quotes: dict[str, dict[str, Any]]) -> int:
    ensure_tables()

    if not quotes:
        return 0

    now = now_iso()
    saved = 0

    with get_conn() as conn:
        for code, q in quotes.items():
            if conn.postgres:
                conn.execute(
                    """
                    INSERT INTO stock_quotes(stock_code, stock_name, price, change, change_pct, volume, amount, market, source, trade_date, updated_at)
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
                    INSERT INTO stock_price_history(stock_code, trade_date, stock_name, open, high, low, close, change, change_pct, volume, amount, market, source, updated_at)
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
                    INSERT OR REPLACE INTO stock_quotes(stock_code, stock_name, price, change, change_pct, volume, amount, market, source, trade_date, updated_at)
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
                    INSERT OR REPLACE INTO stock_price_history(stock_code, trade_date, stock_name, open, high, low, close, change, change_pct, volume, amount, market, source, updated_at)
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
            if saved % 50 == 0:
                print(f"Saved quotes: {saved}/{len(quotes)}", flush=True)

    return saved


def update_official_close_quotes() -> dict[str, Any]:
    ensure_tables()

    holding_date, holding_codes = get_latest_holding_scope()

    print(f"Latest holding date={holding_date}", flush=True)
    print(f"Latest holding stock codes={len(holding_codes)}", flush=True)

    official_quotes = fetch_official_quotes(only_codes=holding_codes, fallback_trade_date=holding_date or None)
    official_exact_codes = {
        code for code, q in official_quotes.items()
        if date_only(q.get("trade_date")) == holding_date
    }

    print(f"Official quotes kept for latest holdings={len(official_quotes)}", flush=True)
    print(f"Official exact-date quotes={len(official_exact_codes)}", flush=True)

    missing_exact = holding_codes - official_exact_codes
    yahoo_quotes = fetch_yahoo_missing_exact_quotes(missing_exact, holding_date)

    quotes = dict(official_quotes)
    quotes.update(yahoo_quotes)

    exact_codes_final = {
        code for code, q in quotes.items()
        if date_only(q.get("trade_date")) == holding_date
    }

    saved = save_quotes(quotes)
    missing_final = sorted(holding_codes - exact_codes_final)

    print(f"Official+Yahoo quotes saved={saved}, missing_exact_latest_holdings={len(missing_final)}", flush=True)
    if missing_final:
        print("Missing exact examples: " + ", ".join(missing_final[:80]), flush=True)

    return {
        "updated_at": now_iso(),
        "holding_date": holding_date,
        "holding_codes": len(holding_codes),
        "official_quotes": len(official_quotes),
        "official_exact_quotes": len(official_exact_codes),
        "yahoo_fallback_quotes": len(yahoo_quotes),
        "quotes_saved": saved,
        "missing_exact_holdings": len(missing_final),
        "missing_examples": missing_final[:80],
        "source": "official_openapi_close_plus_yahoo_exact_fallback",
    }


if __name__ == "__main__":
    print(update_official_close_quotes())
