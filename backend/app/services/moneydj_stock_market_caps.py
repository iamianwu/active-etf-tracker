from __future__ import annotations

import html
import re
import time
from datetime import datetime
from typing import Any, Iterable
from urllib.parse import urlencode

import requests

from ..database import get_conn, init_db, is_postgres, rows_to_dicts


MONEYDJ_URLS = (
    "https://www.moneydj.com/Z/ZC/ZCA/ZCA.djhtm?{query}",
    "https://5850web.moneydj.com/z/zc/zca/zca_{code}.djhtm",
)
TWSE_COMPANY_URL = (
    "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
)
TPEX_COMPANY_URL = (
    "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
)

INDUSTRY_NAMES = {
    "01": "水泥工業",
    "02": "食品工業",
    "03": "塑膠工業",
    "04": "紡織纖維",
    "05": "電機機械",
    "06": "電器電纜",
    "08": "玻璃陶瓷",
    "09": "造紙工業",
    "10": "鋼鐵工業",
    "11": "橡膠工業",
    "12": "汽車工業",
    "14": "建材營造",
    "15": "航運業",
    "16": "觀光餐旅",
    "17": "金融保險",
    "18": "貿易百貨",
    "20": "其他",
    "21": "化學工業",
    "22": "生技醫療",
    "23": "油電燃氣",
    "24": "半導體業",
    "25": "電腦及週邊設備",
    "26": "光電業",
    "27": "通信網路業",
    "28": "電子零組件業",
    "29": "電子通路業",
    "30": "資訊服務業",
    "31": "其他電子業",
    "32": "文化創意業",
    "33": "農業科技業",
    "34": "電子商務",
    "35": "綠能環保",
    "36": "數位雲端",
    "37": "運動休閒",
    "38": "居家生活",
}

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.7",
    "Referer": "https://www.moneydj.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
}


def _html_tokens(raw_html: str) -> list[str]:
    text = html.unescape(raw_html)
    text = re.sub(r"<script[\s\S]*?</script>", "\n", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return [
        line
        for line in (item.strip() for item in text.split("\n"))
        if line
    ]


def parse_moneydj_market_cap(raw_html: str) -> dict[str, Any]:
    tokens = _html_tokens(raw_html)
    market_cap_million: float | None = None
    trade_date_text = ""

    for token in tokens:
        if "最近交易日" in token:
            match = re.search(
                r"最近交易日[:：]\s*([0-9]{1,2}/[0-9]{1,2})",
                token,
            )
            if match:
                trade_date_text = match.group(1)

    for index, token in enumerate(tokens):
        if token != "總市值" and not token.endswith("總市值"):
            continue

        for candidate in tokens[index + 1:index + 10]:
            if re.fullmatch(r"[0-9,]+(?:\.\d+)?", candidate):
                market_cap_million = float(candidate.replace(",", ""))
                break

        if market_cap_million is not None:
            break

    if market_cap_million is None:
        raise ValueError("MoneyDJ market cap not found")

    return {
        "market_cap_million": market_cap_million,
        # 前端既有 market_value_billion 實際以「億元」為單位，
        # 因此這裡同樣換算成億元，兩者才能直接計算持股占比。
        "market_cap_billion": market_cap_million / 100.0,
        "trade_date_text": trade_date_text,
    }


def fetch_moneydj_market_cap(
    stock_code: str,
    *,
    session: requests.Session | None = None,
    timeout: int = 25,
) -> dict[str, Any]:
    code = str(stock_code or "").strip()
    if not re.fullmatch(r"\d{4}", code):
        raise ValueError(f"Invalid stock code: {stock_code}")

    client = session or requests.Session()
    errors: list[str] = []

    for template in MONEYDJ_URLS:
        url = template.format(
            code=code,
            query=urlencode({"a": code}),
        )
        try:
            response = client.get(
                url,
                headers=HEADERS,
                timeout=timeout,
            )
            response.raise_for_status()
            if (
                not response.encoding
                or response.encoding.lower() in {"ascii", "iso-8859-1"}
            ):
                response.encoding = response.apparent_encoding or "big5"

            result = parse_moneydj_market_cap(response.text)
            result["source_url"] = response.url
            return result
        except Exception as exc:
            errors.append(f"{url}: {exc}")

    raise RuntimeError(" | ".join(errors))


def fetch_official_industry_map(
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> dict[str, dict[str, str]]:
    client = session or requests.Session()
    result: dict[str, dict[str, str]] = {}

    sources = (
        (
            TWSE_COMPANY_URL,
            "公司代號",
            "產業別",
        ),
        (
            TPEX_COMPANY_URL,
            "SecuritiesCompanyCode",
            "SecuritiesIndustryCode",
        ),
    )

    for url, code_key, industry_key in sources:
        response = client.get(
            url,
            headers=HEADERS,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()

        for row in payload if isinstance(payload, list) else []:
            code = str(row.get(code_key) or "").strip()
            industry_code = str(row.get(industry_key) or "").strip().zfill(2)
            if not re.fullmatch(r"\d{4}", code):
                continue

            result[code] = {
                "industry_code": industry_code,
                "industry_name": (
                    INDUSTRY_NAMES.get(industry_code)
                    or f"產業 {industry_code}"
                ),
            }

    return result


def ensure_market_cap_columns() -> None:
    init_db()
    with get_conn() as conn:
        if conn.postgres:
            conn.execute(
                "ALTER TABLE stock_quotes "
                "ADD COLUMN IF NOT EXISTS market_cap_billion DOUBLE PRECISION"
            )
            conn.execute(
                "ALTER TABLE stock_quotes "
                "ADD COLUMN IF NOT EXISTS market_cap_source TEXT"
            )
            conn.execute(
                "ALTER TABLE stock_quotes "
                "ADD COLUMN IF NOT EXISTS market_cap_updated_at TEXT"
            )
            conn.execute(
                "ALTER TABLE stock_quotes "
                "ADD COLUMN IF NOT EXISTS industry_code TEXT"
            )
            conn.execute(
                "ALTER TABLE stock_quotes "
                "ADD COLUMN IF NOT EXISTS industry_name TEXT"
            )
            return

        existing = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(stock_quotes)").fetchall()
        }
        columns = {
            "market_cap_billion": "REAL",
            "market_cap_source": "TEXT",
            "market_cap_updated_at": "TEXT",
            "industry_code": "TEXT",
            "industry_name": "TEXT",
        }
        for column, column_type in columns.items():
            if column not in existing:
                conn.execute(
                    f"ALTER TABLE stock_quotes "
                    f"ADD COLUMN {column} {column_type}"
                )


def get_stock_universe() -> list[dict[str, str]]:
    condition = (
        "stock_code ~ '^[0-9]{4}$'"
        if is_postgres()
        else "stock_code GLOB '[0-9][0-9][0-9][0-9]'"
    )
    with get_conn() as conn:
        rows = rows_to_dicts(
            conn.execute(
                f"""
                SELECT stock_code, MAX(stock_name) AS stock_name
                FROM holdings
                WHERE {condition}
                GROUP BY stock_code
                ORDER BY stock_code
                """
            ).fetchall()
        )
    return [
        {
            "stock_code": str(row.get("stock_code") or ""),
            "stock_name": str(row.get("stock_name") or ""),
        }
        for row in rows
    ]


def save_market_caps(rows: Iterable[dict[str, Any]]) -> int:
    normalized_rows = list(rows)
    if not normalized_rows:
        return 0

    ensure_market_cap_columns()
    now = datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        for row in normalized_rows:
            conn.execute(
                """
                INSERT INTO stock_quotes(
                  stock_code, stock_name, market_cap_billion,
                  market_cap_source, market_cap_updated_at,
                  industry_code, industry_name
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (stock_code) DO UPDATE SET
                  stock_name=COALESCE(
                    NULLIF(EXCLUDED.stock_name, ''),
                    stock_quotes.stock_name
                  ),
                  market_cap_billion=COALESCE(
                    EXCLUDED.market_cap_billion,
                    stock_quotes.market_cap_billion
                  ),
                  market_cap_source=COALESCE(
                    EXCLUDED.market_cap_source,
                    stock_quotes.market_cap_source
                  ),
                  market_cap_updated_at=COALESCE(
                    EXCLUDED.market_cap_updated_at,
                    stock_quotes.market_cap_updated_at
                  ),
                  industry_code=COALESCE(
                    EXCLUDED.industry_code,
                    stock_quotes.industry_code
                  ),
                  industry_name=COALESCE(
                    EXCLUDED.industry_name,
                    stock_quotes.industry_name
                  )
                """,
                (
                    row["stock_code"],
                    row.get("stock_name") or row["stock_code"],
                    row.get("market_cap_billion"),
                    row.get("source_url"),
                    now if row.get("market_cap_billion") is not None else None,
                    row.get("industry_code"),
                    row.get("industry_name"),
                ),
            )

    return len(normalized_rows)


def update_moneydj_stock_market_caps(
    *,
    stocks: Iterable[dict[str, str]] | None = None,
    sleep_sec: float = 0.15,
) -> dict[str, Any]:
    selected = list(stocks if stocks is not None else get_stock_universe())
    session = requests.Session()
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    industry_map: dict[str, dict[str, str]] = {}

    try:
        industry_map = fetch_official_industry_map(session=session)
        print(
            f"Official stock industry rows={len(industry_map)}",
            flush=True,
        )
    except Exception as exc:
        print(f"Official stock industries: ERROR {exc}", flush=True)

    print(
        f"Start MoneyDJ stock market cap update: total={len(selected)}",
        flush=True,
    )

    for index, stock in enumerate(selected, start=1):
        code = str(stock.get("stock_code") or "").strip()
        name = str(stock.get("stock_name") or "").strip()
        industry = industry_map.get(code) or {}
        try:
            row = fetch_moneydj_market_cap(code, session=session)
            row.update({
                "stock_code": code,
                "stock_name": name or code,
                **industry,
            })
            rows.append(row)
            print(
                f"[{index}/{len(selected)}] {code}: "
                f"market_cap={row['market_cap_billion']:.2f} 億",
                flush=True,
            )
        except Exception as exc:
            if industry:
                rows.append({
                    "stock_code": code,
                    "stock_name": name or code,
                    **industry,
                })
            errors.append({
                "stock_code": code,
                "error": str(exc),
            })
            print(
                f"[{index}/{len(selected)}] {code}: ERROR {exc}",
                flush=True,
            )

        time.sleep(max(0.0, sleep_sec))

    saved = save_market_caps(rows)
    return {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "requested": len(selected),
        "saved": saved,
        "errors": errors,
    }
