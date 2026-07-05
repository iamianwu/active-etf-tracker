from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
from typing import Any

import psycopg
import requests
from psycopg.types.json import Jsonb


TDCC_URL = os.getenv(
    "TDCC_URL",
    "https://openapi-t.tdcc.com.tw/v1/opendata/1-5",
).strip()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

REQUEST_TIMEOUT = int(
    os.getenv("TDCC_REQUEST_TIMEOUT", "240")
)


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key).lstrip("\ufeff").strip(): value
        for key, value in row.items()
    }


def to_int(value: Any) -> int:
    text = str(value or "0").replace(",", "").strip()

    try:
        return int(float(text))
    except (TypeError, ValueError):
        return 0


def to_float(value: Any) -> float:
    text = str(value or "0").replace(",", "").strip()

    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def parse_date(value: Any):
    text = str(value or "").strip()

    if len(text) != 8 or not text.isdigit():
        raise ValueError(f"Invalid TDCC data date: {text!r}")

    return datetime.strptime(text, "%Y%m%d").date()


def fetch_tdcc_rows() -> list[dict[str, Any]]:
    print(f"Downloading TDCC data: {TDCC_URL}", flush=True)

    response = requests.get(
        TDCC_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "active-etf-tracker/1.0",
        },
        timeout=(20, REQUEST_TIMEOUT),
    )
    response.raise_for_status()

    payload = response.json()

    if not isinstance(payload, list):
        raise RuntimeError(
            f"Unexpected TDCC payload type: {type(payload).__name__}"
        )

    print(
        f"Downloaded {len(payload):,} TDCC level rows",
        flush=True,
    )

    return [
        normalize_row(row)
        for row in payload
        if isinstance(row, dict)
    ]


def build_summary_rows(
    raw_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[
        tuple[str, Any],
        dict[int, dict[str, Any]],
    ] = defaultdict(dict)

    for row in raw_rows:
        code = str(row.get("證券代號") or "").strip()
        date_text = row.get("資料日期")
        level = to_int(row.get("持股分級"))

        if not code or not date_text:
            continue

        if level < 1 or level > 17:
            continue

        data_date = parse_date(date_text)

        grouped[(code, data_date)][level] = {
            "holder_count": to_int(row.get("人數")),
            "shares": to_int(row.get("股數")),
            "ratio": to_float(
                row.get("占集保庫存數比例%")
            ),
        }

    summaries: list[dict[str, Any]] = []

    for (code, data_date), levels in grouped.items():
        retail_ratio = sum(
            float(levels.get(level, {}).get("ratio", 0))
            for level in (1, 2)
        )

        major_ratio = sum(
            float(levels.get(level, {}).get("ratio", 0))
            for level in (12, 13, 14)
        )

        thousand_level = levels.get(15, {})
        total_level = levels.get(17, {})

        total_holder_count = to_int(
            total_level.get("holder_count")
        )
        total_shares = to_int(
            total_level.get("shares")
        )

        if not total_holder_count:
            total_holder_count = sum(
                to_int(levels.get(level, {}).get("holder_count"))
                for level in range(1, 16)
            )

        if not total_shares:
            total_shares = sum(
                to_int(levels.get(level, {}).get("shares"))
                for level in range(1, 16)
            )

        summaries.append({
            "security_code": code,
            "data_date": data_date,
            "retail_ratio": round(retail_ratio, 4),
            "major_ratio": round(major_ratio, 4),
            "thousand_holder_count": to_int(
                thousand_level.get("holder_count")
            ),
            "thousand_holder_ratio": round(
                to_float(thousand_level.get("ratio")),
                4,
            ),
            "total_holder_count": total_holder_count,
            "total_shares": total_shares,
            "levels": {
                str(level): values
                for level, values in sorted(levels.items())
            },
        })

    summaries.sort(
        key=lambda row: (
            row["data_date"],
            row["security_code"],
        )
    )

    return summaries


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tdcc_holder_summary (
    security_code TEXT NOT NULL,
    data_date DATE NOT NULL,

    retail_ratio NUMERIC(8, 4) NOT NULL DEFAULT 0,
    major_ratio NUMERIC(8, 4) NOT NULL DEFAULT 0,

    thousand_holder_count INTEGER NOT NULL DEFAULT 0,
    thousand_holder_ratio NUMERIC(8, 4) NOT NULL DEFAULT 0,

    total_holder_count BIGINT NOT NULL DEFAULT 0,
    total_shares BIGINT NOT NULL DEFAULT 0,

    levels JSONB NOT NULL DEFAULT '{}'::jsonb,

    source TEXT NOT NULL DEFAULT 'TDCC_OD_1-5',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (security_code, data_date)
);

CREATE INDEX IF NOT EXISTS
    idx_tdcc_holder_summary_code_date
ON tdcc_holder_summary (
    security_code,
    data_date DESC
);

CREATE INDEX IF NOT EXISTS
    idx_tdcc_holder_summary_date
ON tdcc_holder_summary (
    data_date DESC
);
"""


UPSERT_SQL = """
INSERT INTO tdcc_holder_summary (
    security_code,
    data_date,
    retail_ratio,
    major_ratio,
    thousand_holder_count,
    thousand_holder_ratio,
    total_holder_count,
    total_shares,
    levels,
    source,
    updated_at
)
VALUES (
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    'TDCC_OD_1-5',
    NOW()
)
ON CONFLICT (
    security_code,
    data_date
)
DO UPDATE SET
    retail_ratio = EXCLUDED.retail_ratio,
    major_ratio = EXCLUDED.major_ratio,
    thousand_holder_count =
        EXCLUDED.thousand_holder_count,
    thousand_holder_ratio =
        EXCLUDED.thousand_holder_ratio,
    total_holder_count =
        EXCLUDED.total_holder_count,
    total_shares = EXCLUDED.total_shares,
    levels = EXCLUDED.levels,
    source = EXCLUDED.source,
    updated_at = NOW()
"""


def write_summaries(
    summaries: list[dict[str, Any]],
) -> None:
    if not DATABASE_URL:
        raise RuntimeError("Missing DATABASE_URL")

    values = [
        (
            row["security_code"],
            row["data_date"],
            row["retail_ratio"],
            row["major_ratio"],
            row["thousand_holder_count"],
            row["thousand_holder_ratio"],
            row["total_holder_count"],
            row["total_shares"],
            Jsonb(row["levels"]),
        )
        for row in summaries
    ]

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)

            batch_size = 500

            for start in range(0, len(values), batch_size):
                batch = values[start:start + batch_size]
                cur.executemany(UPSERT_SQL, batch)

                print(
                    f"Upserted "
                    f"{min(start + batch_size, len(values)):,}"
                    f"/{len(values):,}",
                    flush=True,
                )

        conn.commit()


def main() -> None:
    raw_rows = fetch_tdcc_rows()
    summaries = build_summary_rows(raw_rows)

    if not summaries:
        raise RuntimeError("No TDCC summary rows generated")

    dates = sorted({
        row["data_date"]
        for row in summaries
    })

    print(
        f"Generated {len(summaries):,} security summaries",
        flush=True,
    )
    print(
        f"TDCC dates: {dates[0]} to {dates[-1]}",
        flush=True,
    )

    write_summaries(summaries)

    sample = next(
        (
            row for row in summaries
            if row["security_code"] == "3037"
        ),
        None,
    )

    if sample:
        print(
            {
                "security_code": sample["security_code"],
                "data_date": str(sample["data_date"]),
                "retail_ratio": sample["retail_ratio"],
                "major_ratio": sample["major_ratio"],
                "thousand_holder_count":
                    sample["thousand_holder_count"],
                "thousand_holder_ratio":
                    sample["thousand_holder_ratio"],
            },
            flush=True,
        )

    print("TDCC holder summary update completed.", flush=True)


if __name__ == "__main__":
    main()
