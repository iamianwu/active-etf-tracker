from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import psycopg
import requests


def getenv(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def split_csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def init_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS signals_cache (
                cache_key TEXT PRIMARY KEY,
                data_date TEXT,
                holdings_row_count INTEGER,
                days INTEGER,
                signal_type TEXT,
                payload JSONB NOT NULL,
                updated_at TEXT
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_cache_data_date
            ON signals_cache(data_date)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_cache_signal_days_updated
            ON signals_cache(signal_type, days, updated_at DESC)
        """)
    conn.commit()


def fetch_signals(site_url: str, universe: str, days: int) -> dict:
    qs = urlencode({
        "days": str(days),
        "universe": universe,
        "fresh": "1",
    })
    url = f"{site_url.rstrip('/')}/api/signals?{qs}"

    if universe == "all":
        timeout_sec = int(getenv("SIGNALS_ALL_FETCH_TIMEOUT_SEC", "180"))
        retries = max(1, int(getenv("SIGNALS_ALL_FETCH_RETRIES", "1")))
    else:
        timeout_sec = int(getenv("SIGNALS_FETCH_TIMEOUT_SEC", "300"))
        retries = max(1, int(getenv("SIGNALS_FETCH_RETRIES", "2")))

    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        print(
            f"fetch {url} attempt={attempt}/{retries} timeout={timeout_sec}s",
            flush=True,
        )

        try:
            res = requests.get(
                url,
                timeout=(20, timeout_sec),
            )
            res.raise_for_status()
            return res.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            print({
                "ok": False,
                "stage": "fetch_signals",
                "universe": universe,
                "days": days,
                "attempt": attempt,
                "error": str(exc),
            }, flush=True)

            if attempt < retries:
                time.sleep(min(15, attempt * 5))

    raise RuntimeError(
        f"signals fetch failed universe={universe} days={days}"
    ) from last_error


def write_cache(conn, universe: str, days: int, payload: dict) -> dict:
    data_date = str(payload.get("data_date") or payload.get("target_data_date") or "")
    holdings_row_count = int(
        payload.get("today_holding_rows")
        or payload.get("included_holding_rows")
        or payload.get("holdings_row_count")
        or 0
    )

    signal_type = f"{universe}::"
    cache_key = f"signals:v2:{universe}:all:days={days}:date={data_date}:rows={holdings_row_count}"
    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    payload = dict(payload)
    payload["universe"] = universe
    payload["etf_universe"] = universe
    payload["cache_written_by"] = "github_action"
    payload["cache_key"] = cache_key
    payload["cache_updated_at"] = updated_at

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO signals_cache (
                cache_key, data_date, holdings_row_count, days, signal_type, payload, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (cache_key) DO UPDATE SET
                data_date = EXCLUDED.data_date,
                holdings_row_count = EXCLUDED.holdings_row_count,
                days = EXCLUDED.days,
                signal_type = EXCLUDED.signal_type,
                payload = EXCLUDED.payload,
                updated_at = EXCLUDED.updated_at
            """,
            (
                cache_key,
                data_date,
                holdings_row_count,
                days,
                signal_type,
                json.dumps(payload, ensure_ascii=False),
                updated_at,
            ),
        )
    conn.commit()

    return {
        "cache_key": cache_key,
        "signal_type": signal_type,
        "data_date": data_date,
        "holdings_row_count": holdings_row_count,
        "updated_at": updated_at,
    }


def warm_cdn(site_url: str, universe: str, days: int) -> None:
    url = f"{site_url.rstrip()}/api/signals?days={days}&universe={universe}"

    for i in range(2):
        try:
            res = requests.get(url, timeout=120)
            res.raise_for_status()
            data = res.json()
            print(
                f"cdn warm {i + 1}/2 universe={universe} days={days} "
                f"cache_hit={data.get('cache_hit')} "
                f"cache_mode={data.get('cache_mode')} "
                f"signals={data.get('signal_count')}"
            )
        except requests.exceptions.RequestException as e:
            print({
                "ok": False,
                "stage": "cdn_warm",
                "universe": universe,
                "days": days,
                "url": url,
                "error": str(e),
            })
            return

def main() -> None:
    database_url = getenv("DATABASE_URL")
    site_url = getenv("SITE_URL", "https://active-etf-tracker.vercel.app")
    days_list = [int(x) for x in split_csv(getenv("SIGNAL_DAYS", "1,5,10,20"))]
    universes = split_csv(getenv("SIGNAL_UNIVERSES", "active,reference,all"))
    sleep_sec = float(getenv("SIGNALS_CACHE_SLEEP_SEC", "0.5"))

    if not database_url:
        raise RuntimeError("Missing DATABASE_URL")

    print({
        "site_url": site_url,
        "days_list": days_list,
        "universes": universes,
        "sleep_sec": sleep_sec,
    }, flush=True)

    with psycopg.connect(database_url) as conn:
        init_table(conn)

        failures: list[dict] = []

        # 先完成所有 universe 的 1 日資料，再處理 5、10、20 日。
        for days in days_list:
            for universe in universes:
                try:
                    payload = fetch_signals(site_url, universe, days)

                    fetched = int(payload.get("fetched_etf_count") or 0)
                    total = int(payload.get("total_etf_count") or 0)

                    # all 曾出現 13/93 半成品；低於 80% 時拒絕覆蓋正常快取。
                    if (
                        universe == "all"
                        and total > 0
                        and fetched / total < 0.80
                    ):
                        raise RuntimeError(
                            "refusing incomplete all cache: "
                            f"fetched={fetched} total={total}"
                        )

                    meta = write_cache(conn, universe, days, payload)

                    print({
                        "ok": True,
                        "universe": universe,
                        "days": days,
                        "signal_count": payload.get("signal_count"),
                        "total_etf_count": total,
                        "fetched_etf_count": fetched,
                        **meta,
                    }, flush=True)

                    warm_cdn(site_url, universe, days)

                except Exception as exc:
                    failure = {
                        "ok": False,
                        "stage": "signals_cache_task",
                        "universe": universe,
                        "days": days,
                        "error": str(exc),
                    }
                    failures.append(failure)
                    print(failure, flush=True)

                time.sleep(sleep_sec)

        print({
            "ok": not failures,
            "stage": "signals_cache_summary",
            "failure_count": len(failures),
            "failures": failures,
        }, flush=True)

        critical_failures = [
            item
            for item in failures
            if item["universe"] in {"active", "reference"}
        ]

        if critical_failures:
            raise RuntimeError(
                f"{len(critical_failures)} critical signals cache tasks failed"
            )


if __name__ == "__main__":
    main()
