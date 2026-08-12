from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode

import psycopg
import requests

from .warm_signals_cache_from_api import (
    init_table,
    merge_signal_payloads,
    warm_cdn,
    write_cache,
)


REFERENCE_ETF_CODES = [
    "0050", "0051", "0052", "0053", "0055", "0056", "0057",
    "006201", "006203", "006204", "006208", "00690", "00692",
    "00701", "00713", "00728", "00730", "00731", "00733", "00850",
    "00878", "00881", "00888", "00891", "00892", "00894", "00896",
    "00900", "00901", "00904", "00905", "00907", "00912", "00913",
    "00915", "00918", "00919", "00921", "00922", "00923", "00927",
    "00928", "00929", "00930", "00932", "00934", "00935", "00936",
    "00938", "00939", "00940", "00943", "00944", "00946", "00947",
    "00952", "00961", "00962", "009802", "009803", "009804", "009808",
    "00735", "009809", "009816",
]


def chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


def fetch_chunk(site_url: str, days: int, codes: list[str]) -> dict:
    url = f"{site_url.rstrip('/')}/api/signals-reference-chunk?" + urlencode({
        "days": str(days),
        "codes": ",".join(codes),
    })
    last_error: Exception | None = None

    for attempt in range(1, 4):
        try:
            print({
                "stage": "fetch_reference_chunk",
                "days": days,
                "codes": codes,
                "attempt": attempt,
            }, flush=True)
            response = requests.get(url, timeout=(20, 240))
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(str(payload["error"]))
            return payload
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            last_error = exc
            print({
                "ok": False,
                "stage": "fetch_reference_chunk",
                "days": days,
                "codes": codes,
                "attempt": attempt,
                "error": str(exc),
            }, flush=True)

    raise RuntimeError(
        f"reference chunk failed days={days} codes={','.join(codes)}"
    ) from last_error


def read_latest_active_cache(conn, days: int) -> dict:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT payload
            FROM signals_cache
            WHERE days = %s AND signal_type = 'active::'
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (days,),
        )
        row = cursor.fetchone()

    if not row or not isinstance(row[0], dict):
        raise RuntimeError(f"missing active signals cache days={days}")

    return row[0]


def main() -> None:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    site_url = os.environ.get(
        "SITE_URL",
        "https://active-etf-tracker.vercel.app",
    ).strip()
    days_values = [
        int(value.strip())
        for value in os.environ.get("SIGNAL_DAYS", "1,5,10,20").split(",")
        if value.strip()
    ]
    chunk_size = max(1, min(10, int(os.environ.get("REFERENCE_CHUNK_SIZE", "8"))))
    workers = max(1, min(4, int(os.environ.get("REFERENCE_CHUNK_WORKERS", "3"))))

    if not database_url:
        raise RuntimeError("Missing DATABASE_URL")

    code_chunks = chunks(REFERENCE_ETF_CODES, chunk_size)

    with psycopg.connect(database_url) as conn:
        init_table(conn)

        for days in days_values:
            payloads: list[dict] = []

            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(fetch_chunk, site_url, days, codes): codes
                    for codes in code_chunks
                }
                for future in as_completed(futures):
                    payloads.append(future.result())

            if len(payloads) != len(code_chunks):
                raise RuntimeError(
                    f"incomplete reference chunks days={days}: "
                    f"{len(payloads)}/{len(code_chunks)}"
                )

            reference = payloads[0]
            for payload in payloads[1:]:
                reference = merge_signal_payloads(reference, payload, days)

            reference["universe"] = "reference"
            reference["etf_universe"] = "reference"
            reference["source"] = "github_action_merged_reference_chunks"
            reference["total_etf_count"] = len(REFERENCE_ETF_CODES)
            reference["all_etf_codes"] = REFERENCE_ETF_CODES

            reference_meta = write_cache(conn, "reference", days, reference)
            active = read_latest_active_cache(conn, days)
            combined = merge_signal_payloads(active, reference, days)
            all_meta = write_cache(conn, "all", days, combined)

            print({
                "ok": True,
                "stage": "reference_chunks_complete",
                "days": days,
                "chunks": len(payloads),
                "reference": reference_meta,
                "all": all_meta,
            }, flush=True)

            warm_cdn(site_url, "reference", days)
            warm_cdn(site_url, "all", days)


if __name__ == "__main__":
    main()
