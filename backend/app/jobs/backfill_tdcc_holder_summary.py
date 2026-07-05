from __future__ import annotations

import json
import os
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import psycopg
import requests
from psycopg.types.json import Jsonb

from .update_tdcc_holder_summary import (
    CREATE_TABLE_SQL,
    UPSERT_SQL,
    to_float,
    to_int,
)


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

PAGE_URL = os.getenv(
    "TDCC_HISTORY_URL",
    "https://www.tdcc.com.tw/portal/zh/smWeb/qryStock",
).strip()

TARGET_WEEKS = max(
    1,
    int(os.getenv("TARGET_WEEKS", "5")),
)

MAX_CODES = max(
    0,
    int(os.getenv("MAX_CODES", "0")),
)

START_AFTER = os.getenv(
    "START_AFTER",
    "",
).strip().upper()

SLEEP_SEC = max(
    0.3,
    float(os.getenv("SLEEP_SEC", "0.8")),
)

REQUEST_TIMEOUT = max(
    30,
    int(os.getenv("REQUEST_TIMEOUT", "90")),
)

REFRESH_EVERY = max(
    10,
    int(os.getenv("REFRESH_EVERY", "50")),
)

REPORT_PATH = Path(
    os.getenv(
        "REPORT_PATH",
        "tdcc-backfill-report.json",
    )
)


class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.inputs: dict[str, str] = {}
        self.dates: list[str] = []
        self.current_select = ""

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {
            key: value or ""
            for key, value in attrs
        }

        tag = tag.lower()

        if tag == "input":
            name = values.get("name", "")

            if name:
                self.inputs[name] = values.get(
                    "value",
                    "",
                )

        elif tag == "select":
            self.current_select = values.get(
                "name",
                "",
            )

        elif (
            tag == "option"
            and self.current_select == "scaDate"
        ):
            value = values.get("value", "").strip()

            if value:
                self.dates.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "select":
            self.current_select = ""


class TableParser(HTMLParser):
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
            value = " ".join(
                "".join(self.cell_parts).split()
            )

            self.current_row.append(value)
            self.in_cell = False

        elif tag == "tr":
            if self.current_row:
                self.rows.append(self.current_row)

            self.current_row = []


def parse_form(
    html: str,
) -> FormParser:
    parser = FormParser()
    parser.feed(html)
    return parser


def parse_levels(
    html: str,
) -> dict[int, dict[str, Any]]:
    parser = TableParser()
    parser.feed(html)

    levels: dict[int, dict[str, Any]] = {}

    for row in parser.rows:
        cleaned = [
            " ".join(str(cell).split())
            for cell in row
        ]

        level_index = None

        for index, cell in enumerate(cleaned):
            if not re.fullmatch(r"\d{1,2}", cell):
                continue

            level = int(cell)

            if 1 <= level <= 17:
                level_index = index
                break

        if level_index is None:
            continue

        values = cleaned[level_index:]

        if len(values) < 5:
            continue

        level = int(values[0])

        levels[level] = {
            "holder_count": to_int(values[2]),
            "shares": to_int(values[3]),
            "ratio": to_float(values[4]),
        }

    return levels


def build_summary(
    code: str,
    date_text: str,
    levels: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    retail_ratio = sum(
        to_float(
            levels.get(level, {}).get("ratio")
        )
        for level in (1, 2)
    )

    major_ratio = sum(
        to_float(
            levels.get(level, {}).get("ratio")
        )
        for level in (12, 13, 14)
    )

    thousand = levels.get(15, {})
    total = levels.get(17, {})

    total_holder_count = to_int(
        total.get("holder_count")
    )
    total_shares = to_int(
        total.get("shares")
    )

    if not total_holder_count:
        total_holder_count = sum(
            to_int(
                levels.get(level, {}).get(
                    "holder_count"
                )
            )
            for level in range(1, 16)
        )

    if not total_shares:
        total_shares = sum(
            to_int(
                levels.get(level, {}).get(
                    "shares"
                )
            )
            for level in range(1, 16)
        )

    return {
        "security_code": code,
        "data_date": (
            f"{date_text[:4]}-"
            f"{date_text[4:6]}-"
            f"{date_text[6:8]}"
        ),
        "retail_ratio": round(
            retail_ratio,
            4,
        ),
        "major_ratio": round(
            major_ratio,
            4,
        ),
        "thousand_holder_count": to_int(
            thousand.get("holder_count")
        ),
        "thousand_holder_ratio": round(
            to_float(thousand.get("ratio")),
            4,
        ),
        "total_holder_count": total_holder_count,
        "total_shares": total_shares,
        "levels": {
            str(level): values
            for level, values in sorted(
                levels.items()
            )
        },
    }


class TdccHistoryClient:
    def __init__(self) -> None:
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 "
                "(Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 "
                "Chrome/149 Safari/537.36"
            ),
            "Accept-Language": "zh-TW,zh;q=0.9",
        })

        self.token = ""
        self.uri = "/portal/zh/smWeb/qryStock"
        self.first_date = ""
        self.available_dates: list[str] = []
        self.request_count = 0

    def refresh_form(self) -> None:
        response = self.session.get(
            PAGE_URL,
            timeout=(20, REQUEST_TIMEOUT),
        )
        response.raise_for_status()

        parser = parse_form(response.text)

        self.token = parser.inputs.get(
            "SYNCHRONIZER_TOKEN",
            "",
        )

        self.uri = parser.inputs.get(
            "SYNCHRONIZER_URI",
            "/portal/zh/smWeb/qryStock",
        )

        self.first_date = parser.inputs.get(
            "firDate",
            "",
        )

        self.available_dates = list(
            dict.fromkeys(parser.dates)
        )

        if not self.token:
            raise RuntimeError(
                "TDCC page missing SYNCHRONIZER_TOKEN"
            )

    def fetch_levels(
        self,
        code: str,
        date_text: str,
    ) -> dict[int, dict[str, Any]] | None:
        for attempt in range(1, 4):
            if (
                not self.token
                or self.request_count % REFRESH_EVERY == 0
            ):
                self.refresh_form()

            payload = {
                "SYNCHRONIZER_TOKEN": self.token,
                "SYNCHRONIZER_URI": self.uri,
                "method": "submit",
                "firDate": self.first_date,
                "scaDate": date_text,
                "sqlMethod": "StockNo",
                "stockNo": code,
                "stockName": "",
            }

            try:
                response = self.session.post(
                    PAGE_URL,
                    data=payload,
                    headers={
                        "Referer": PAGE_URL,
                        "Origin":
                            "https://www.tdcc.com.tw",
                    },
                    timeout=(20, REQUEST_TIMEOUT),
                )
                response.raise_for_status()
                self.request_count += 1

                response_form = parse_form(
                    response.text
                )

                next_token = response_form.inputs.get(
                    "SYNCHRONIZER_TOKEN",
                    "",
                )

                if next_token:
                    self.token = next_token

                levels = parse_levels(
                    response.text
                )

                if len(levels) >= 15:
                    return levels

                if (
                    "查無資料" in response.text
                    or "無符合" in response.text
                ):
                    return None

                raise RuntimeError(
                    f"only {len(levels)} level rows"
                )

            except (
                requests.RequestException,
                RuntimeError,
            ) as exc:
                if attempt >= 3:
                    raise RuntimeError(
                        f"{code}/{date_text}: {exc}"
                    ) from exc

                self.token = ""
                time.sleep(attempt * 2)

        return None


def load_codes(
    conn: psycopg.Connection,
) -> list[str]:
    sql = """
    WITH website_codes AS (
        SELECT DISTINCT
            TRIM(stock_code) AS security_code
        FROM holdings

        UNION

        SELECT DISTINCT
            TRIM(etf_code) AS security_code
        FROM holdings

        UNION

        SELECT DISTINCT
            TRIM(stock_code) AS security_code
        FROM stock_quotes

        UNION

        SELECT DISTINCT
            TRIM(etf_code) AS security_code
        FROM etf_quotes
    )
    SELECT security_code
    FROM website_codes
    WHERE security_code ~ '^[0-9A-Z]{4,6}$'
    ORDER BY security_code
    """

    with conn.cursor() as cur:
        cur.execute(sql)

        codes = [
            str(row[0]).strip().upper()
            for row in cur.fetchall()
            if row and row[0]
        ]

    if START_AFTER:
        codes = [
            code
            for code in codes
            if code > START_AFTER
        ]

    if MAX_CODES > 0:
        codes = codes[:MAX_CODES]

    return codes


def load_existing(
    conn: psycopg.Connection,
    target_dates: list[str],
) -> set[tuple[str, str]]:
    sql = """
    SELECT
        security_code,
        TO_CHAR(data_date, 'YYYYMMDD')
    FROM tdcc_holder_summary
    WHERE data_date = ANY(%s::date[])
    """

    iso_dates = [
        (
            f"{date_text[:4]}-"
            f"{date_text[4:6]}-"
            f"{date_text[6:8]}"
        )
        for date_text in target_dates
    ]

    with conn.cursor() as cur:
        cur.execute(sql, (iso_dates,))

        return {
            (
                str(row[0]).strip().upper(),
                str(row[1]),
            )
            for row in cur.fetchall()
        }


def upsert_summary(
    conn: psycopg.Connection,
    summary: dict[str, Any],
) -> None:
    values = (
        summary["security_code"],
        summary["data_date"],
        summary["retail_ratio"],
        summary["major_ratio"],
        summary["thousand_holder_count"],
        summary["thousand_holder_ratio"],
        summary["total_holder_count"],
        summary["total_shares"],
        Jsonb(summary["levels"]),
    )

    with conn.cursor() as cur:
        cur.execute(
            UPSERT_SQL,
            values,
        )


def main() -> None:
    if not DATABASE_URL:
        raise RuntimeError("Missing DATABASE_URL")

    client = TdccHistoryClient()
    client.refresh_form()

    target_dates = client.available_dates[
        :TARGET_WEEKS
    ]

    if len(target_dates) < TARGET_WEEKS:
        raise RuntimeError(
            "TDCC returned only "
            f"{len(target_dates)} available dates"
        )

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)

        conn.commit()

        codes = load_codes(conn)
        existing = load_existing(
            conn,
            target_dates,
        )

        pending = [
            (code, date_text)
            for code in codes
            for date_text in target_dates
            if (code, date_text) not in existing
        ]

        print(
            f"Website security codes: {len(codes):,}",
            flush=True,
        )
        print(
            f"Target dates: {target_dates}",
            flush=True,
        )
        print(
            f"Existing rows: {len(existing):,}",
            flush=True,
        )
        print(
            f"Pending requests: {len(pending):,}",
            flush=True,
        )
        print(
            f"Sleep between requests: "
            f"{SLEEP_SEC:.2f}s",
            flush=True,
        )

        completed = 0
        inserted = 0
        unavailable: list[dict[str, str]] = []
        failures: list[dict[str, str]] = []

        for code, date_text in pending:
            completed += 1

            try:
                levels = client.fetch_levels(
                    code,
                    date_text,
                )

                if not levels:
                    unavailable.append({
                        "security_code": code,
                        "data_date": date_text,
                    })
                else:
                    summary = build_summary(
                        code,
                        date_text,
                        levels,
                    )

                    upsert_summary(
                        conn,
                        summary,
                    )

                    inserted += 1

                conn.commit()

            except Exception as exc:
                conn.rollback()

                failures.append({
                    "security_code": code,
                    "data_date": date_text,
                    "error": str(exc),
                })

                print(
                    f"[ERROR] {code}/{date_text}: "
                    f"{exc}",
                    flush=True,
                )

            if (
                completed % 25 == 0
                or completed == len(pending)
            ):
                print(
                    f"Progress {completed:,}/"
                    f"{len(pending):,}; "
                    f"inserted={inserted:,}; "
                    f"unavailable={len(unavailable):,}; "
                    f"failures={len(failures):,}",
                    flush=True,
                )

            time.sleep(SLEEP_SEC)

    report = {
        "target_dates": target_dates,
        "website_code_count": len(codes),
        "pending_request_count": len(pending),
        "inserted_count": inserted,
        "unavailable_count": len(unavailable),
        "failure_count": len(failures),
        "unavailable": unavailable,
        "failures": failures,
    }

    REPORT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print(
        json.dumps(
            {
                "target_dates": target_dates,
                "inserted": inserted,
                "unavailable": len(unavailable),
                "failures": len(failures),
                "report": str(REPORT_PATH),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    if failures:
        raise SystemExit(
            "TDCC history backfill completed "
            "with request failures"
        )

    print(
        "TDCC five-week history backfill completed.",
        flush=True,
    )


if __name__ == "__main__":
    main()
