from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import requests

from .update_institutional_trading import (
    DATABASE_URL,
    REQUEST_TIMEOUT,
    TAIPEI,
    UPSERT_SQL,
    fetch_tpex,
    fetch_twse,
)


BACKFILL_DAYS = max(
    1,
    int(os.getenv("BACKFILL_DAYS", "90")),
)

SLEEP_SEC = max(
    0.1,
    float(os.getenv("SLEEP_SEC", "0.5")),
)

REPORT_PATH = Path(
    os.getenv(
        "REPORT_PATH",
        "institutional-backfill-report.json",
    )
)


def load_existing_dates(
    conn: psycopg.Connection,
) -> set[tuple[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                market,
                TO_CHAR(trade_date, 'YYYY-MM-DD')
            FROM institutional_trading_daily
            GROUP BY market, trade_date
            """
        )

        return {
            (
                str(row[0]),
                str(row[1]),
            )
            for row in cur.fetchall()
        }


def upsert_rows(
    conn: psycopg.Connection,
    rows: list[tuple[Any, ...]],
) -> None:
    if not rows:
        return

    with conn.cursor() as cur:
        cur.executemany(
            UPSERT_SQL,
            rows,
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

    today = datetime.now(TAIPEI).date()

    targets = [
        today - timedelta(days=offset)
        for offset in range(BACKFILL_DAYS)
    ]

    inserted_rows = 0
    skipped_existing = 0
    no_data: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []

    with psycopg.connect(DATABASE_URL) as conn:
        existing = load_existing_dates(conn)

        total_tasks = len(targets) * 2
        completed = 0

        print(
            f"Backfill calendar days: {BACKFILL_DAYS}",
            flush=True,
        )
        print(
            f"Market/date tasks: {total_tasks}",
            flush=True,
        )
        print(
            f"Existing market dates: {len(existing)}",
            flush=True,
        )

        for target in targets:
            for market in ("TWSE", "TPEX"):
                completed += 1
                date_key = target.isoformat()

                if (market, date_key) in existing:
                    skipped_existing += 1

                    print(
                        f"[SKIP] {market} {date_key} already exists",
                        flush=True,
                    )
                    continue

                try:
                    if market == "TWSE":
                        actual_date, rows = fetch_twse(
                            session,
                            target,
                        )
                    else:
                        actual_date, rows = fetch_tpex(
                            session,
                            target,
                        )

                    print(
                        f"{market} {date_key}: "
                        f"{len(rows):,} rows",
                        flush=True,
                    )

                    if not rows:
                        no_data.append({
                            "market": market,
                            "requested_date": date_key,
                        })
                    else:
                        upsert_rows(
                            conn,
                            rows,
                        )
                        conn.commit()

                        inserted_rows += len(rows)

                        actual_iso = (
                            f"{actual_date[:4]}-"
                            f"{actual_date[4:6]}-"
                            f"{actual_date[6:8]}"
                        )

                        existing.add(
                            (market, actual_iso)
                        )

                except Exception as exc:
                    conn.rollback()

                    failures.append({
                        "market": market,
                        "requested_date": date_key,
                        "error": str(exc),
                    })

                    print(
                        f"[ERROR] {market} {date_key}: {exc}",
                        flush=True,
                    )

                if (
                    completed % 10 == 0
                    or completed == total_tasks
                ):
                    print(
                        f"Progress {completed}/{total_tasks}; "
                        f"inserted_rows={inserted_rows:,}; "
                        f"no_data={len(no_data)}; "
                        f"failures={len(failures)}",
                        flush=True,
                    )

                time.sleep(SLEEP_SEC)

    report = {
        "backfill_days": BACKFILL_DAYS,
        "inserted_rows": inserted_rows,
        "skipped_existing": skipped_existing,
        "no_data_count": len(no_data),
        "failure_count": len(failures),
        "no_data": no_data,
        "failures": failures,
    }

    REPORT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        json.dumps(
            {
                "inserted_rows": inserted_rows,
                "skipped_existing": skipped_existing,
                "no_data": len(no_data),
                "failures": len(failures),
                "report": str(REPORT_PATH),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    if failures:
        raise SystemExit(
            "Institutional trading backfill completed "
            "with failures"
        )

    print(
        "Institutional trading backfill completed.",
        flush=True,
    )


if __name__ == "__main__":
    main()
