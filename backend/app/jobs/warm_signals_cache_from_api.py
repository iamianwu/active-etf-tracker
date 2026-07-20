from __future__ import annotations

import copy
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
        "full": "1",
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



ROW_ALIASES = (
    "rows",
    "items",
    "allRows",
    "changes",
    "signals",
    "rawChanges",
    "all_changes",
)


def signal_number(value):
    if value is None or value == "":
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).replace(",", "")
    cleaned = "".join(
        char
        for char in text
        if char.isdigit()
        or char in ".-"
    )

    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def first_number(row: dict, keys: list[str]):
    for key in keys:
        value = signal_number(
            row.get(key)
        )

        if value is not None:
            return value

    return None


def first_text(row: dict, keys: list[str]) -> str:
    for key in keys:
        value = str(
            row.get(key) or ""
        ).strip()

        if value:
            return value

    return ""


def source_delta(source: dict):
    lots = first_number(
        source,
        [
            "delta_shares",
            "delta_shares_lots",
            "shares_change",
            "change_lots",
            "delta_lots",
            "display_delta_lots",
        ],
    )

    if lots is not None:
        return lots

    return first_number(
        source,
        [
            "delta_raw_shares",
            "deltaRawShares",
            "raw_delta_shares",
        ],
    )


def changed_etf_counts(sources):
    if not isinstance(sources, list):
        return None

    add_etfs: set[str] = set()
    reduce_etfs: set[str] = set()

    for source in sources:
        if not isinstance(source, dict):
            continue

        etf_code = first_text(
            source,
            [
                "etf_code",
                "etfCode",
                "fund_code",
                "fundCode",
                "etf",
            ],
        )

        if not etf_code:
            continue

        delta = source_delta(source)

        if (
            delta is None
            or abs(delta) < 0.001
        ):
            continue

        if delta > 0:
            add_etfs.add(etf_code)

        if delta < 0:
            reduce_etfs.add(etf_code)

    return {
        "buy": len(add_etfs),
        "sell": len(reduce_etfs),
    }


def compact_node(value):
    if isinstance(value, list):
        return [
            compact_node(item)
            for item in value
        ]

    if not isinstance(value, dict):
        return value

    changed_etfs = (
        value.get("changed_etfs")
        if isinstance(
            value.get("changed_etfs"),
            list,
        )
        else value.get("changedEtfs")
        if isinstance(
            value.get("changedEtfs"),
            list,
        )
        else None
    )

    counts = changed_etf_counts(
        changed_etfs
    )

    output = {}

    for key, child in value.items():
        if key in {
            "changed_etfs",
            "changedEtfs",
        }:
            continue

        output[key] = compact_node(
            child
        )

    if counts is not None:
        existing_buy = first_number(
            value,
            [
                "buy_count",
                "buyCount",
            ],
        )

        existing_sell = first_number(
            value,
            [
                "sell_count",
                "sellCount",
            ],
        )

        output["buy_count"] = (
            int(existing_buy)
            if existing_buy is not None
            else counts["buy"]
        )

        output["sell_count"] = (
            int(existing_sell)
            if existing_sell is not None
            else counts["sell"]
        )

    return output


def compact_signals_payload(data):
    if not isinstance(data, dict):
        return data

    source_rows = []

    for key in ROW_ALIASES:
        value = data.get(key)

        if isinstance(value, list):
            source_rows = value
            break

    if (
        not source_rows
        and isinstance(
            data.get("aggregate"),
            list,
        )
    ):
        source_rows = data["aggregate"]

    output = {}

    for key, value in data.items():
        if key in ROW_ALIASES:
            continue

        output[key] = compact_node(
            value
        )

    output["rows"] = [
        compact_node(row)
        for row in source_rows
    ]

    output["compact_payload"] = True
    output["compact_version"] = 1

    return output


def payload_rows(payload: dict) -> list[dict]:
    for key in (
        "allRows",
        "all_changes",
        *ROW_ALIASES,
    ):
        value = payload.get(key)

        if isinstance(value, list):
            return [
                row
                for row in value
                if isinstance(row, dict)
            ]

    return []


def unique_texts(*values) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()

    for value in values:
        if not isinstance(value, list):
            continue

        for item in value:
            text = str(item or "").strip()

            if not text or text in seen:
                continue

            seen.add(text)
            output.append(text)

    return output


def unique_dicts(
    *values,
    keys: tuple[str, ...],
) -> list[dict]:
    output: list[dict] = []
    seen: set[tuple[str, ...]] = set()

    for value in values:
        if not isinstance(value, list):
            continue

        for item in value:
            if not isinstance(item, dict):
                continue

            identity = tuple(
                str(item.get(key) or "").strip()
                for key in keys
            )

            if not any(identity):
                identity = (
                    json.dumps(
                        item,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                )

            if identity in seen:
                continue

            seen.add(identity)
            output.append(copy.deepcopy(item))

    return output


def finite_number(value, default=0.0) -> float:
    number = signal_number(value)
    return number if number is not None else float(default)


def merged_signal_row(rows: list[dict]) -> dict | None:
    if not rows:
        return None

    base = copy.deepcopy(rows[0])
    stock_code = first_text(
        base,
        ["stock_code", "code", "symbol"],
    )

    sum_fields = (
        "curr_raw_shares",
        "prev_raw_shares",
        "delta_raw_shares",
        "curr_weight",
        "prev_weight",
        "delta_weight",
        "buy_etf_count",
        "sell_etf_count",
        "add_count",
        "delete_count",
        "increase_count",
        "decrease_count",
        "etf_change_count",
    )

    for field in sum_fields:
        base[field] = sum(
            finite_number(row.get(field))
            for row in rows
        )

    changed_etfs = unique_dicts(
        *[
            row.get("changed_etfs")
            for row in rows
        ],
        keys=(
            "etf_code",
            "stock_code",
            "status",
            "data_date",
            "prev_date",
        ),
    )
    base["changed_etfs"] = changed_etfs

    curr_lots = (
        finite_number(
            base.get("curr_raw_shares")
        )
        / 1000
    )
    prev_lots = (
        finite_number(
            base.get("prev_raw_shares")
        )
        / 1000
    )
    delta_lots = (
        finite_number(
            base.get("delta_raw_shares")
        )
        / 1000
    )
    delta_weight = finite_number(
        base.get("delta_weight")
    )

    if abs(delta_lots) < 0.001:
        return None

    if prev_lots <= 0 < curr_lots:
        status = "新增"
    elif curr_lots <= 0 < prev_lots:
        status = "刪除"
    elif delta_lots > 0:
        status = "加碼"
    elif delta_lots < 0:
        status = "減碼"
    elif delta_weight > 0:
        status = "加碼"
    elif delta_weight < 0:
        status = "減碼"
    else:
        return None

    price = finite_number(
        base.get("price")
    )
    net_amount_billion = (
        finite_number(
            base.get("delta_raw_shares")
        )
        * price
        / 100000000
    )
    buy_count = int(
        finite_number(
            base.get("buy_etf_count")
        )
    )
    sell_count = int(
        finite_number(
            base.get("sell_etf_count")
        )
    )

    base.update({
        "stock_code": stock_code,
        "code": stock_code,
        "symbol": stock_code,
        "status": status,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "add_etf_count": buy_count,
        "reduce_etf_count": sell_count,
        "increase_etf_count": int(
            finite_number(
                base.get("increase_count")
            )
        ),
        "decrease_etf_count": int(
            finite_number(
                base.get("decrease_count")
            )
        ),
        "etf_count": int(
            finite_number(
                base.get("etf_change_count")
            )
        ),
        "delta_shares": delta_lots,
        "delta_shares_lots": delta_lots,
        "shares_change": delta_lots,
        "curr_shares": curr_lots,
        "prev_shares": prev_lots,
        "current_shares": curr_lots,
        "net_delta_shares": delta_lots,
        "net_amount_billion": net_amount_billion,
        "amount_billion": net_amount_billion,
        "delta_amount_billion": net_amount_billion,
        "amount": net_amount_billion,
        "abs_amount_billion": abs(
            net_amount_billion
        ),
        "consensus": (
            f"買賣檔數 {buy_count}:{sell_count}"
        ),
        "long_short_consensus": (
            f"買賣檔數 {buy_count}:{sell_count}"
        ),
        "buySellText": (
            f"買賣檔數 {buy_count}:{sell_count}"
        ),
    })

    return base


def signal_counts(rows: list[dict]) -> dict:
    return {
        "total": len(rows),
        "all": len(rows),
        "add": sum(
            row.get("status") == "新增"
            for row in rows
        ),
        "remove": sum(
            row.get("status") == "刪除"
            for row in rows
        ),
        "increase": sum(
            row.get("status") == "加碼"
            for row in rows
        ),
        "decrease": sum(
            row.get("status") == "減碼"
            for row in rows
        ),
    }


def top_signal_rows(rows: list[dict]) -> dict:
    positive = sorted(
        (
            row
            for row in rows
            if finite_number(
                row.get("net_amount_billion")
            ) > 0
        ),
        key=lambda row: finite_number(
            row.get("net_amount_billion")
        ),
        reverse=True,
    )
    negative = sorted(
        (
            row
            for row in rows
            if finite_number(
                row.get("net_amount_billion")
            ) < 0
        ),
        key=lambda row: finite_number(
            row.get("net_amount_billion")
        ),
    )
    buy = sorted(
        (
            row
            for row in rows
            if finite_number(
                row.get("buy_etf_count")
            ) > 0
        ),
        key=lambda row: (
            finite_number(
                row.get("buy_etf_count")
            ),
            finite_number(
                row.get("net_amount_billion")
            ),
        ),
        reverse=True,
    )
    sell = sorted(
        (
            row
            for row in rows
            if finite_number(
                row.get("sell_etf_count")
            ) > 0
        ),
        key=lambda row: (
            -finite_number(
                row.get("sell_etf_count")
            ),
            finite_number(
                row.get("net_amount_billion")
            ),
        ),
    )

    return {
        "topInflow": (
            positive[0]
            if positive
            else None
        ),
        "topOutflow": (
            negative[0]
            if negative
            else None
        ),
        "topIncreaseEtf": (
            buy[0]
            if buy
            else None
        ),
        "topDecreaseEtf": (
            sell[0]
            if sell
            else None
        ),
    }


def merge_signal_payloads(
    active: dict,
    reference: dict,
    days: int,
) -> dict:
    data_dates = {
        str(
            payload.get("data_date")
            or payload.get(
                "target_data_date"
            )
            or ""
        )
        for payload in (
            active,
            reference,
        )
    }
    data_dates.discard("")

    if len(data_dates) != 1:
        raise RuntimeError(
            "cannot merge signals with "
            f"different data dates: "
            f"{sorted(data_dates)}"
        )

    rows_by_code: dict[
        str,
        list[dict],
    ] = {}

    for payload in (
        active,
        reference,
    ):
        for row in payload_rows(
            payload
        ):
            code = first_text(
                row,
                [
                    "stock_code",
                    "code",
                    "symbol",
                ],
            )

            if not code:
                continue

            rows_by_code.setdefault(
                code,
                [],
            ).append(row)

    rows = [
        merged
        for grouped in rows_by_code.values()
        if (
            merged := merged_signal_row(
                grouped
            )
        ) is not None
    ]
    rows.sort(
        key=lambda row: abs(
            finite_number(
                row.get(
                    "net_amount_billion"
                )
            )
        ),
        reverse=True,
    )

    counts = signal_counts(rows)
    focus = top_signal_rows(rows)
    data_date = next(iter(data_dates))
    all_etf_codes = unique_texts(
        active.get("all_etf_codes"),
        reference.get(
            "all_etf_codes"
        ),
    )
    today_etf_codes = unique_texts(
        active.get(
            "today_etf_codes"
        ),
        reference.get(
            "today_etf_codes"
        ),
    )
    missing_today_etf_codes = (
        unique_texts(
            active.get(
                "missing_today_etf_codes"
            ),
            reference.get(
                "missing_today_etf_codes"
            ),
        )
    )
    no_compare_etf_codes = (
        unique_texts(
            active.get(
                "no_compare_etf_codes"
            ),
            reference.get(
                "no_compare_etf_codes"
            ),
        )
    )
    non_today_etfs = unique_dicts(
        active.get("non_today_etfs"),
        reference.get(
            "non_today_etfs"
        ),
        keys=("etf_code",),
    )
    total = int(
        finite_number(
            active.get(
                "total_etf_count"
            )
        )
        + finite_number(
            reference.get(
                "total_etf_count"
            )
        )
    )
    fetched = int(
        finite_number(
            active.get(
                "fetched_etf_count"
            )
        )
        + finite_number(
            reference.get(
                "fetched_etf_count"
            )
        )
    )
    included = int(
        finite_number(
            active.get(
                "includedEtfCount"
            )
        )
        + finite_number(
            reference.get(
                "includedEtfCount"
            )
        )
    )

    meta = {
        "data_date": data_date,
        "target_data_date": data_date,
        "rangeDays": days,
        "signalRangeDays": days,
        "range_days": days,
        "rangeLabel": (
            "今日"
            if days == 1
            else f"{days}日"
        ),
        "comparisonMode": (
            "前一交易日"
            if days == 1
            else f"{days}個交易日前"
        ),
        "includedEtfCount": included,
        "comparable_etf_count": included,
        "signal_etf_count": included,
        "fetched_etf_count": fetched,
        "total_etf_count": total,
        "all_etf_codes": all_etf_codes,
        "today_etf_codes": today_etf_codes,
        "today_etf_count": fetched,
        "missing_today_etf_count": len(
            missing_today_etf_codes
        ),
        "missing_today_etf_codes": (
            missing_today_etf_codes
        ),
        "missing_today_etf_codes_text": ",".join(
            missing_today_etf_codes
        ),
        "non_today_etf_codes_text": ",".join(
            missing_today_etf_codes
        ),
        "no_compare_etf_count": len(
            no_compare_etf_codes
        ),
        "excluded_compare_etf_count": max(
            0,
            total - included,
        ),
        "non_today_etf_count": len(
            missing_today_etf_codes
        ),
        "non_today_etfs": non_today_etfs,
        "missing_etfs": non_today_etfs,
        "no_compare_etf_codes": (
            no_compare_etf_codes
        ),
        "today_holding_rows": int(
            finite_number(
                active.get(
                    "today_holding_rows"
                )
            )
            + finite_number(
                reference.get(
                    "today_holding_rows"
                )
            )
        ),
        "included_holding_rows": int(
            finite_number(
                active.get(
                    "included_holding_rows"
                )
            )
            + finite_number(
                reference.get(
                    "included_holding_rows"
                )
            )
        ),
        "signal_count": len(rows),
        "today_change_count": len(rows),
        "source": (
            "github_action_merged_active_reference"
        ),
        "universe": "all",
        "etf_universe": "all",
        "data_note": (
            f"今日有資料 {fetched}/{total} 檔 ETF；"
            f"可計算訊號 {included} 檔；"
            f"未納入 {max(0, total - included)} 檔"
            f"（{len(missing_today_etf_codes)} 檔非今日資料、"
            f"{len(no_compare_etf_codes)} 檔缺前日比較）。"
        ),
    }

    return {
        **meta,
        "rows": rows,
        "changes": rows,
        "rawChanges": rows,
        "items": rows,
        "signals": rows,
        "allRows": rows,
        "all_changes": rows,
        "counts": counts,
        "status_counts": counts,
        "summary": {
            **meta,
            "counts": counts,
            **focus,
        },
        "focus": focus,
        "focusCards": focus,
        "top_cards": focus,
        **focus,
    }


def write_cache(
    conn,
    universe: str,
    days: int,
    payload: dict,
) -> dict:
    if payload.get("compact_payload"):
        raise RuntimeError(
            "Expected full payload, received compact payload"
        )

    data_date = str(
        payload.get("data_date")
        or payload.get("target_data_date")
        or ""
    )

    holdings_row_count = int(
        payload.get("today_holding_rows")
        or payload.get("included_holding_rows")
        or payload.get("holdings_row_count")
        or 0
    )

    full_signal_type = (
        f"{universe}::"
    )

    compact_signal_type = (
        f"compact::{universe}::"
    )

    full_cache_key = (
        f"signals:v2:{universe}:all"
        f":days={days}"
        f":date={data_date}"
        f":rows={holdings_row_count}"
    )

    compact_cache_key = (
        f"signals:v3:compact:{universe}:all"
        f":days={days}"
        f":date={data_date}"
        f":rows={holdings_row_count}"
    )

    updated_at = (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
    )

    full_payload = dict(payload)

    full_payload["universe"] = universe
    full_payload["etf_universe"] = universe
    full_payload["cache_written_by"] = (
        "github_action"
    )
    full_payload["cache_key"] = (
        full_cache_key
    )
    full_payload["cache_updated_at"] = (
        updated_at
    )

    compact_payload = (
        compact_signals_payload(
            full_payload
        )
    )

    compact_payload["cache_written_by"] = (
        "github_action_compact"
    )
    compact_payload["cache_key"] = (
        compact_cache_key
    )
    compact_payload["cache_updated_at"] = (
        updated_at
    )

    rows = [
        (
            full_cache_key,
            data_date,
            holdings_row_count,
            days,
            full_signal_type,
            full_payload,
            updated_at,
        ),
        (
            compact_cache_key,
            data_date,
            holdings_row_count,
            days,
            compact_signal_type,
            compact_payload,
            updated_at,
        ),
    ]

    with conn.cursor() as cur:
        for (
            cache_key,
            row_data_date,
            row_count,
            row_days,
            signal_type,
            row_payload,
            row_updated_at,
        ) in rows:
            cur.execute(
                """
                INSERT INTO signals_cache (
                    cache_key,
                    data_date,
                    holdings_row_count,
                    days,
                    signal_type,
                    payload,
                    updated_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s::jsonb,
                    %s
                )
                ON CONFLICT (cache_key)
                DO UPDATE SET
                    data_date =
                        EXCLUDED.data_date,
                    holdings_row_count =
                        EXCLUDED.holdings_row_count,
                    days =
                        EXCLUDED.days,
                    signal_type =
                        EXCLUDED.signal_type,
                    payload =
                        EXCLUDED.payload,
                    updated_at =
                        EXCLUDED.updated_at
                """,
                (
                    cache_key,
                    row_data_date,
                    row_count,
                    row_days,
                    signal_type,
                    json.dumps(
                        row_payload,
                        ensure_ascii=False,
                    ),
                    row_updated_at,
                ),
            )

    conn.commit()

    return {
        "cache_key":
            full_cache_key,
        "signal_type":
            full_signal_type,
        "compact_cache_key":
            compact_cache_key,
        "compact_signal_type":
            compact_signal_type,
        "data_date":
            data_date,
        "holdings_row_count":
            holdings_row_count,
        "updated_at":
            updated_at,
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
            payloads_by_universe: dict[
                str,
                dict,
            ] = {}

            for universe in universes:
                try:
                    if (
                        universe == "all"
                        and "active" in payloads_by_universe
                        and "reference" in payloads_by_universe
                    ):
                        payload = merge_signal_payloads(
                            payloads_by_universe["active"],
                            payloads_by_universe["reference"],
                            days,
                        )
                        print({
                            "ok": True,
                            "stage": "merge_all_signals",
                            "days": days,
                            "data_date": payload.get("data_date"),
                            "signal_count": payload.get("signal_count"),
                        }, flush=True)
                    else:
                        payload = fetch_signals(
                            site_url,
                            universe,
                            days,
                        )

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

                    payloads_by_universe[
                        universe
                    ] = payload

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

        if failures:
            raise RuntimeError(
                f"{len(failures)} signals cache tasks failed"
            )


if __name__ == "__main__":
    main()
