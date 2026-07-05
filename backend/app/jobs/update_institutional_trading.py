from __future__ import annotations

import html
import os
import re
from datetime import date, timedelta
from html.parser import HTMLParser
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
import requests


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

TWSE_URL = os.getenv(
    "TWSE_INSTITUTIONAL_URL",
    "https://www.twse.com.tw/rwd/zh/fund/T86",
).strip()

TPEX_URL = os.getenv(
    "TPEX_INSTITUTIONAL_URL",
    "https://www.tpex.org.tw/web/stock/3insti/daily_trade/"
    "3itrade_hedge_result.php",
).strip()

LOOKBACK_DAYS = max(
    3,
    int(os.getenv("INSTITUTIONAL_LOOKBACK_DAYS", "10")),
)

REQUEST_TIMEOUT = max(
    30,
    int(os.getenv("REQUEST_TIMEOUT", "90")),
)

TAIPEI = ZoneInfo("Asia/Taipei")


UPSERT_SQL = """
INSERT INTO institutional_trading_daily (
    security_code,
    trade_date,
    market,
    security_name,

    foreign_buy,
    foreign_sell,
    foreign_net,

    trust_buy,
    trust_sell,
    trust_net,

    dealer_self_buy,
    dealer_self_sell,
    dealer_self_net,

    dealer_hedge_buy,
    dealer_hedge_sell,
    dealer_hedge_net,

    dealer_net,
    institutional_net,

    source,
    updated_at
)
VALUES (
    %s, %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s,
    %s, NOW()
)
ON CONFLICT (
    security_code,
    trade_date,
    market
)
DO UPDATE SET
    security_name = EXCLUDED.security_name,

    foreign_buy = EXCLUDED.foreign_buy,
    foreign_sell = EXCLUDED.foreign_sell,
    foreign_net = EXCLUDED.foreign_net,

    trust_buy = EXCLUDED.trust_buy,
    trust_sell = EXCLUDED.trust_sell,
    trust_net = EXCLUDED.trust_net,

    dealer_self_buy = EXCLUDED.dealer_self_buy,
    dealer_self_sell = EXCLUDED.dealer_self_sell,
    dealer_self_net = EXCLUDED.dealer_self_net,

    dealer_hedge_buy = EXCLUDED.dealer_hedge_buy,
    dealer_hedge_sell = EXCLUDED.dealer_hedge_sell,
    dealer_hedge_net = EXCLUDED.dealer_hedge_net,

    dealer_net = EXCLUDED.dealer_net,
    institutional_net = EXCLUDED.institutional_net,

    source = EXCLUDED.source,
    updated_at = NOW()
"""


def to_int(value: Any) -> int:
    text = str(value or "").strip()

    if not text or text in {"--", "---", "N/A"}:
        return 0

    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace(",", "").replace("+", "").strip()

    try:
        return int(float(text))
    except (TypeError, ValueError):
        return 0


def clean_text(value: Any) -> str:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    return " ".join(html.unescape(text).split()).strip()


def normalize_field(value: Any) -> str:
    return re.sub(
        r"[\s\u3000（）()]",
        "",
        clean_text(value),
    )


def find_field(
    fields: list[str],
    *tokens: str,
) -> int:
    normalized_tokens = [
        normalize_field(token)
        for token in tokens
    ]

    for index, field in enumerate(fields):
        normalized = normalize_field(field)

        if all(
            token in normalized
            for token in normalized_tokens
        ):
            return index

    raise KeyError(
        f"找不到欄位：{tokens}; fields={fields}"
    )


def row_value(
    row: list[Any],
    index: int,
) -> int:
    if index < 0 or index >= len(row):
        return 0

    return to_int(row[index])


def fetch_twse(
    session: requests.Session,
    target: date,
) -> tuple[str, list[tuple[Any, ...]]]:
    date_text = target.strftime("%Y%m%d")

    response = session.get(
        TWSE_URL,
        params={
            "date": date_text,
            "selectType": "ALLBUT0999",
            "response": "json",
        },
        timeout=(20, REQUEST_TIMEOUT),
    )
    response.raise_for_status()

    payload = response.json()

    if payload.get("stat") != "OK":
        return date_text, []

    fields = [
        clean_text(value)
        for value in payload.get("fields", [])
    ]

    raw_rows = payload.get("data", [])

    if not fields or not raw_rows:
        return date_text, []

    code_i = find_field(fields, "證券代號")
    name_i = find_field(fields, "證券名稱")

    foreign_buy_i = find_field(
        fields,
        "買進股數",
        "不含外資自營商",
    )
    foreign_sell_i = find_field(
        fields,
        "賣出股數",
        "不含外資自營商",
    )
    foreign_net_i = find_field(
        fields,
        "買賣超股數",
        "不含外資自營商",
    )

    trust_buy_i = find_field(
        fields,
        "投信",
        "買進股數",
    )
    trust_sell_i = find_field(
        fields,
        "投信",
        "賣出股數",
    )
    trust_net_i = find_field(
        fields,
        "投信",
        "買賣超股數",
    )

    dealer_self_buy_i = find_field(
        fields,
        "自營商",
        "買進股數",
        "自行買賣",
    )
    dealer_self_sell_i = find_field(
        fields,
        "自營商",
        "賣出股數",
        "自行買賣",
    )
    dealer_self_net_i = find_field(
        fields,
        "自營商",
        "買賣超股數",
        "自行買賣",
    )

    dealer_hedge_buy_i = find_field(
        fields,
        "自營商",
        "買進股數",
        "避險",
    )
    dealer_hedge_sell_i = find_field(
        fields,
        "自營商",
        "賣出股數",
        "避險",
    )
    dealer_hedge_net_i = find_field(
        fields,
        "自營商",
        "買賣超股數",
        "避險",
    )

    institutional_net_i = find_field(
        fields,
        "三大法人",
        "買賣超股數",
    )

    actual_date = str(
        payload.get("date") or date_text
    ).replace("/", "").replace("-", "")[:8]

    rows: list[tuple[Any, ...]] = []

    for raw_row in raw_rows:
        if not isinstance(raw_row, list):
            continue

        code = clean_text(raw_row[code_i]).upper()
        name = clean_text(raw_row[name_i])

        if not re.fullmatch(r"[0-9A-Z]{4,6}", code):
            continue

        dealer_self_buy = row_value(
            raw_row,
            dealer_self_buy_i,
        )
        dealer_self_sell = row_value(
            raw_row,
            dealer_self_sell_i,
        )
        dealer_self_net = row_value(
            raw_row,
            dealer_self_net_i,
        )

        dealer_hedge_buy = row_value(
            raw_row,
            dealer_hedge_buy_i,
        )
        dealer_hedge_sell = row_value(
            raw_row,
            dealer_hedge_sell_i,
        )
        dealer_hedge_net = row_value(
            raw_row,
            dealer_hedge_net_i,
        )

        rows.append((
            code,
            (
                f"{actual_date[:4]}-"
                f"{actual_date[4:6]}-"
                f"{actual_date[6:8]}"
            ),
            "TWSE",
            name,

            row_value(raw_row, foreign_buy_i),
            row_value(raw_row, foreign_sell_i),
            row_value(raw_row, foreign_net_i),

            row_value(raw_row, trust_buy_i),
            row_value(raw_row, trust_sell_i),
            row_value(raw_row, trust_net_i),

            dealer_self_buy,
            dealer_self_sell,
            dealer_self_net,

            dealer_hedge_buy,
            dealer_hedge_sell,
            dealer_hedge_net,

            dealer_self_net + dealer_hedge_net,
            row_value(raw_row, institutional_net_i),

            "TWSE_T86",
        ))

    return actual_date, rows


def roc_date_text(target: date) -> str:
    return (
        f"{target.year - 1911}/"
        f"{target.month:02d}/"
        f"{target.day:02d}"
    )


class TpexTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() in {"td", "th"}:
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag in {"td", "th"} and self.in_cell:
            self.current_row.append(
                clean_text("".join(self.cell_parts))
            )
            self.in_cell = False

        elif tag == "tr":
            if self.current_row:
                self.rows.append(self.current_row)

            self.current_row = []


def fetch_tpex(
    session: requests.Session,
    target: date,
) -> tuple[str, list[tuple[Any, ...]]]:
    response = session.get(
        TPEX_URL,
        params={
            "l": "zh-tw",
            "o": "htm",
            "se": "EW",
            "t": "D",
            "d": roc_date_text(target),
            "s": "0,asc",
        },
        headers={
            "Referer": (
                "https://www.tpex.org.tw/zh-tw/"
                "mainboard/trading/major-institutional/"
                "detail/day.html"
            ),
        },
        timeout=(20, REQUEST_TIMEOUT),
    )
    response.raise_for_status()

    encoding = response.encoding or ""

    if (
        not encoding
        or encoding.lower() in {
            "iso-8859-1",
            "latin-1",
        }
    ):
        encoding = "utf-8"

    page_text = response.content.decode(
        encoding,
        errors="replace",
    )

    parser = TpexTableParser()
    parser.feed(page_text)

    actual_target = target

    date_match = re.search(
        r"(\d{3})年(\d{2})月(\d{2})日",
        page_text,
    )

    if date_match:
        actual_target = date(
            int(date_match.group(1)) + 1911,
            int(date_match.group(2)),
            int(date_match.group(3)),
        )

    rows: list[tuple[Any, ...]] = []

    for raw_row in parser.rows:
        cleaned = [
            clean_text(value)
            for value in raw_row
        ]

        code_index = None

        for index, value in enumerate(cleaned):
            if re.fullmatch(
                r"[0-9A-Z]{4,6}",
                value.upper(),
            ):
                code_index = index
                break

        if code_index is None:
            continue

        values = cleaned[code_index:]

        # 代號、名稱，加上 22 個法人數值欄位。
        if len(values) < 24:
            continue

        code = values[0].upper()
        name = values[1]

        foreign_buy = to_int(values[2])
        foreign_sell = to_int(values[3])
        foreign_net = to_int(values[4])

        # values[5:8] 是外資自營商。
        # 資料表的 foreign_* 使用不含外資自營商欄位。
        trust_buy = to_int(values[11])
        trust_sell = to_int(values[12])
        trust_net = to_int(values[13])

        dealer_self_buy = to_int(values[14])
        dealer_self_sell = to_int(values[15])
        dealer_self_net = to_int(values[16])

        dealer_hedge_buy = to_int(values[17])
        dealer_hedge_sell = to_int(values[18])
        dealer_hedge_net = to_int(values[19])

        dealer_net = to_int(values[22])
        institutional_net = to_int(values[23])

        rows.append((
            code,
            actual_target.isoformat(),
            "TPEX",
            name,

            foreign_buy,
            foreign_sell,
            foreign_net,

            trust_buy,
            trust_sell,
            trust_net,

            dealer_self_buy,
            dealer_self_sell,
            dealer_self_net,

            dealer_hedge_buy,
            dealer_hedge_sell,
            dealer_hedge_net,

            dealer_net,
            institutional_net,

            "TPEX_3INSTI_HTML",
        ))

    return actual_target.strftime("%Y%m%d"), rows

def find_latest_rows(
    session: requests.Session,
    market: str,
) -> tuple[str, list[tuple[Any, ...]]]:
    today = date.today()

    for offset in range(LOOKBACK_DAYS):
        target = today - timedelta(days=offset)

        try:
            if market == "TWSE":
                date_text, rows = fetch_twse(
                    session,
                    target,
                )
            else:
                date_text, rows = fetch_tpex(
                    session,
                    target,
                )

            print(
                f"{market} {target.isoformat()}: "
                f"{len(rows):,} rows",
                flush=True,
            )

            if rows:
                return date_text, rows

        except Exception as exc:
            print(
                f"{market} {target.isoformat()} failed: "
                f"{exc}",
                flush=True,
            )

    raise RuntimeError(
        f"No {market} institutional data found "
        f"within {LOOKBACK_DAYS} days"
    )


def main() -> None:
    if not DATABASE_URL:
        raise RuntimeError("Missing DATABASE_URL")

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 "
            "(Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/149 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "zh-TW,zh;q=0.9",
    })

    twse_date, twse_rows = find_latest_rows(
        session,
        "TWSE",
    )
    tpex_date, tpex_rows = find_latest_rows(
        session,
        "TPEX",
    )

    all_rows = twse_rows + tpex_rows

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                UPSERT_SQL,
                all_rows,
            )

        conn.commit()

    print()
    print(
        f"TWSE date={twse_date}, "
        f"rows={len(twse_rows):,}",
        flush=True,
    )
    print(
        f"TPEX date={tpex_date}, "
        f"rows={len(tpex_rows):,}",
        flush=True,
    )
    print(
        f"Upserted total={len(all_rows):,}",
        flush=True,
    )

    for code in ("2330", "3037", "00981A"):
        samples = [
            row
            for row in all_rows
            if row[0] == code
        ]

        for row in samples:
            print({
                "security_code": row[0],
                "trade_date": row[1],
                "market": row[2],
                "foreign_net": row[6],
                "trust_net": row[9],
                "dealer_self_net": row[12],
                "dealer_hedge_net": row[15],
                "dealer_net": row[16],
                "institutional_net": row[17],
            })

    print(
        "Institutional trading update completed.",
        flush=True,
    )


if __name__ == "__main__":
    main()
