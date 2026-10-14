"""Cloud-only cache retention and verified GitHub Release holdings archives.

Run on GitHub Actions; temporary files live only on its hosted runner.
Historical holdings are deleted only after a verified remote backup and a
second, locked comparison with the rows actually being deleted.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


def gh(*args: str) -> None:
    subprocess.run(["gh", *args], check=True)


def encoded(row: dict) -> bytes:
    return (json.dumps(row, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), default=str) + "\n").encode()


def cleanup_caches(conn) -> None:
    for table, partition in (
        ("signals_cache", "days, signal_type"),
        ("app_cache", "regexp_replace(cache_key, ':date=.*$|:holdings=.*$', '')"),
    ):
        total = 0
        while True:
            with conn.transaction():
                conn.execute("SET TRANSACTION READ WRITE")
                result = conn.execute(f"""
                    WITH ranked AS (
                        SELECT cache_key, row_number() OVER (
                            PARTITION BY {partition}
                            ORDER BY data_date DESC NULLS LAST,
                                     updated_at DESC NULLS LAST, cache_key DESC
                        ) AS rn FROM public.{table}
                    ), targets AS (
                        SELECT cache_key FROM ranked WHERE rn > 1 LIMIT 25
                    ), removed AS (
                        DELETE FROM public.{table} c USING targets t
                        WHERE c.cache_key = t.cache_key RETURNING c.cache_key
                    ) SELECT count(*) AS count FROM removed
                """).fetchone()
                count = result["count"]
            total += count
            if count == 0:
                break
        print(f"{table}: removed {total} obsolete cache versions", flush=True)


def archive_holdings(conn) -> None:
    latest = conn.execute("SELECT max(data_date) AS latest FROM public.holdings").fetchone()["latest"]
    if not latest:
        return
    cutoff = (date.fromisoformat(str(latest)[:10]) - timedelta(days=90)).isoformat()
    query = "SELECT * FROM public.holdings WHERE data_date < %s ORDER BY etf_code, data_date, stock_code"
    repo = os.environ["GITHUB_REPOSITORY"]
    run_id = os.environ["GITHUB_RUN_ID"]
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    tag = "data-archive-holdings-" + cutoff[:7]
    asset_name = f"holdings-before-{cutoff}-{run_id}-{attempt}.jsonl.gz"

    with tempfile.TemporaryDirectory(prefix="etf-cloud-archive-") as directory:
        path = Path(directory) / asset_name
        digest = hashlib.sha256()
        count = 0
        with gzip.open(path, "wb") as output:
            with conn.cursor(name="archive_holdings", row_factory=dict_row) as cursor:
                cursor.execute(query, (cutoff,))
                for row in cursor:
                    line = encoded(row)
                    output.write(line)
                    digest.update(line)
                    count += 1
        # Named cursors require a transaction; close it before cloud uploads.
        conn.commit()
        if count == 0:
            print("No holdings older than retention cutoff", flush=True)
            return

        manifest = path.with_suffix(path.suffix + ".manifest.json")
        manifest.write_text(json.dumps({
            "table": "public.holdings", "cutoff_exclusive": cutoff,
            "rows": count, "uncompressed_sha256": digest.hexdigest(),
            "compressed_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }, indent=2))
        exists = subprocess.run(["gh", "release", "view", tag, "--repo", repo],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if exists.returncode:
            gh("release", "create", tag, "--repo", repo, "--target", os.environ["GITHUB_SHA"],
               "--title", f"ETF holdings cloud archive {cutoff[:7]}",
               "--notes", "Compressed historical holdings and integrity manifests. Retain these assets.")
        gh("release", "upload", tag, str(path), str(manifest), "--repo", repo)
        verified = Path(directory) / "verified"
        verified.mkdir()
        gh("release", "download", tag, "--repo", repo, "--pattern", asset_name,
           "--dir", str(verified))
        if hashlib.sha256((verified / asset_name).read_bytes()).digest() != hashlib.sha256(path.read_bytes()).digest():
            raise RuntimeError("Remote archive verification failed; holdings were not deleted")

        with conn.transaction():
            conn.execute("SET TRANSACTION READ WRITE")
            conn.execute("SET LOCAL lock_timeout = '10s'")
            conn.execute("LOCK TABLE public.holdings IN SHARE ROW EXCLUSIVE MODE")
            current_digest = hashlib.sha256()
            current_count = 0
            with conn.cursor(name="verify_holdings", row_factory=dict_row) as cursor:
                cursor.execute(query, (cutoff,))
                for row in cursor:
                    current_digest.update(encoded(row))
                    current_count += 1
            if current_count != count or current_digest.digest() != digest.digest():
                raise RuntimeError("Holdings changed during archive; no historical rows deleted")
            result = conn.execute("DELETE FROM public.holdings WHERE data_date < %s", (cutoff,))
            if result.rowcount != count:
                raise RuntimeError("Unexpected delete count; transaction rolled back")
        print(f"Archived and verified {count} holdings rows in GitHub Release {tag}", flush=True)


def main() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("This job runs only on hosted GitHub Actions; no local backups")
    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url, row_factory=dict_row, connect_timeout=15) as conn:
        cleanup_caches(conn)
        if os.environ.get("ARCHIVE_HOLDINGS", "false") == "true":
            archive_holdings(conn)
        conn.commit()
        conn.autocommit = True
        # Override only this cleanup connection, not the project-wide guard.
        conn.execute("SET default_transaction_read_only = off")
        for table in ("signals_cache", "app_cache"):
            # FULL returns obsolete cache storage to the filesystem.
            # Run off-hours: it briefly locks each cache table.
            conn.execute(f"VACUUM (FULL, ANALYZE) public.{table}")
        if os.environ.get("ARCHIVE_HOLDINGS", "false") == "true":
            conn.execute("VACUUM (FULL, ANALYZE) public.holdings")
        row = conn.execute("SELECT pg_size_pretty(pg_database_size(current_database())) AS size, current_setting('default_transaction_read_only') AS read_only").fetchone()
        print(dict(row), flush=True)


if __name__ == "__main__":
    main()
