from __future__ import annotations

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests


SITE_URL = os.getenv(
    "SITE_URL",
    "https://active-etf-tracker.vercel.app",
).rstrip("/")

REQUESTED_MAX_WORKERS = max(
    1,
    int(os.getenv("MAX_WORKERS", "4")),
)

# 避免錯誤的環境設定同時建立數百條 HTTPS 連線，
# 造成 Too many open files 或遠端 API 壓力。
MAX_WORKERS = min(16, REQUESTED_MAX_WORKERS)
REQUEST_TIMEOUT = max(10, int(os.getenv("REQUEST_TIMEOUT", "90")))
REPORT_PATH = Path(
    os.getenv(
        "REPORT_PATH",
        "signal-operation-sync-report.json",
    )
)

TOLERANCE = 1e-6


def get_json(
    path: str,
    *,
    retries: int = 3,
) -> Any:
    url = f"{SITE_URL}{path}"
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "active-etf-sync-check/1.0",
                },
                timeout=(15, REQUEST_TIMEOUT),
            )
            response.raise_for_status()
            return response.json()

        except (
            requests.RequestException,
            ValueError,
        ) as exc:
            last_error = exc

            if attempt < retries:
                time.sleep(attempt * 2)

    raise RuntimeError(f"{url}: {last_error}")


def number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result
    except (TypeError, ValueError):
        return default


def stock_code_of(row: dict[str, Any]) -> str:
    code = str(
        row.get("stock_code")
        or row.get("code")
        or row.get("symbol")
        or ""
    ).strip()

    return code if re.fullmatch(r"\d{4}", code) else ""


def etf_code_of(row: dict[str, Any]) -> str:
    return str(
        row.get("etf_code")
        or row.get("fund_code")
        or row.get("code")
        or ""
    ).strip().upper()


def operation_date(row: dict[str, Any]) -> str:
    return str(
        row.get("data_date")
        or row.get("date")
        or row.get("trade_date")
        or ""
    )[:10]


def operation_status(row: dict[str, Any]) -> str:
    return str(
        row.get("operation_status")
        or row.get("status")
        or row.get("action")
        or ""
    ).strip()


def operation_delta(row: dict[str, Any]) -> float:
    if row.get("delta_shares") is not None:
        return number(row.get("delta_shares"))

    if row.get("delta_raw_shares") is not None:
        return number(row.get("delta_raw_shares")) / 1000.0

    return 0.0


def collect_signal_rows(
    obj: Any,
    output: dict[str, dict[str, Any]],
) -> None:
    if isinstance(obj, dict):
        code = stock_code_of(obj)

        if code and isinstance(obj.get("changed_etfs"), list):
            output[code] = obj

        for value in obj.values():
            collect_signal_rows(value, output)

    elif isinstance(obj, list):
        for value in obj:
            collect_signal_rows(value, output)


def collect_stock_codes(
    obj: Any,
    output: set[str],
) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in {"stock_code", "code", "symbol"}:
                code = str(value or "").strip()

                if re.fullmatch(r"\d{4}", code):
                    output.add(code)

            collect_stock_codes(value, output)

    elif isinstance(obj, list):
        for value in obj:
            collect_stock_codes(value, output)

    elif isinstance(obj, str):
        value = obj.strip()

        if re.fullmatch(r"\d{4}", value):
            output.add(value)


def signal_operations(
    row: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    for item in row.get("changed_etfs") or []:
        etf = etf_code_of(item)
        delta = operation_delta(item)

        if not etf.endswith("A"):
            continue

        if abs(delta) <= TOLERANCE:
            continue

        result[etf] = {
            "status": operation_status(item),
            "delta": delta,
        }

    return result


def detail_operations(
    payload: dict[str, Any],
    target_date: str,
) -> dict[str, dict[str, Any]]:
    data = payload.get("data") or payload

    raw_rows = (
        data.get("operation_records")
        or data.get("operationRecords")
        or data.get("recent_operations")
        or data.get("recentOperations")
        or []
    )

    result: dict[str, dict[str, Any]] = {}

    for item in raw_rows:
        if operation_date(item) != target_date:
            continue

        etf = etf_code_of(item)
        delta = operation_delta(item)

        # 與個股頁「主動式」頁籤採用相同條件。
        if not etf.endswith("A"):
            continue

        if abs(delta) <= TOLERANCE:
            continue

        result[etf] = {
            "status": operation_status(item),
            "delta": delta,
        }

    return result


def fetch_stock_detail(
    code: str,
) -> tuple[str, dict[str, Any]]:
    cache_buster = time.time_ns()

    payload = get_json(
        f"/api/stock-detail"
        f"?code={code}"
        f"&cb={cache_buster}"
    )

    return code, payload


def main() -> None:
    cache_buster = time.time_ns()

    # 此同步檢查需要 changed_etfs 的 ETF 明細，
    # 因此必須使用 full payload；一般網頁仍使用 compact payload。
    signals_payload = get_json(
        f"/api/signals"
        f"?days=1"
        f"&universe=active"
        f"&full=1"
        f"&cb={cache_buster}"
    )

    signal_rows: dict[str, dict[str, Any]] = {}
    collect_signal_rows(signals_payload, signal_rows)

    # 防止 compact payload 或 API schema 改變時，
    # 將空訊號誤判成數百筆同步錯誤。
    if signals_payload.get("compact_payload"):
        raise RuntimeError(
            "同步檢查收到 compact signals payload；"
            "此檢查需要 full=1 的 changed_etfs 明細"
        )

    if not signal_rows:
        top_level_rows = signals_payload.get("rows")
        top_level_row_count = (
            len(top_level_rows)
            if isinstance(top_level_rows, list)
            else 0
        )

        raise RuntimeError(
            "今日訊號 API 未取得任何含 changed_etfs 的股票列；"
            f"top_level_rows={top_level_row_count}，"
            "停止同步比較以避免產生大量假陽性"
        )

    target_date = str(
        signals_payload.get("target_data_date")
        or signals_payload.get("data_date")
        or ""
    )[:10]

    if not target_date and signal_rows:
        first_row = next(iter(signal_rows.values()))
        target_date = str(
            first_row.get("target_data_date")
            or first_row.get("data_date")
            or ""
        )[:10]

    if not target_date:
        raise RuntimeError("無法取得今日訊號資料日期")

    codes_payload = get_json(
        f"/api/stock-cache-codes?cb={cache_buster}"
    )

    all_codes: set[str] = set()
    collect_stock_codes(codes_payload, all_codes)
    all_codes.update(signal_rows.keys())

    print(f"資料日：{target_date}")
    print(f"今日訊號股票數：{len(signal_rows)}")
    print(f"待檢查股票數：{len(all_codes)}")
    print(f"並行數：{MAX_WORKERS}")
    print()

    detail_payloads: dict[str, dict[str, Any]] = {}
    fetch_errors: list[dict[str, Any]] = []

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS,
    ) as executor:
        futures = {
            executor.submit(fetch_stock_detail, code): code
            for code in sorted(all_codes)
        }

        completed = 0

        for future in as_completed(futures):
            code = futures[future]

            try:
                fetched_code, payload = future.result()
                detail_payloads[fetched_code] = payload

            except Exception as exc:
                fetch_errors.append({
                    "stock_code": code,
                    "error": str(exc),
                })

            completed += 1

            if completed % 50 == 0 or completed == len(futures):
                print(
                    f"已檢查 API："
                    f"{completed}/{len(futures)}"
                )

    mismatches: list[dict[str, Any]] = []

    for code in sorted(all_codes):
        signal_row = signal_rows.get(code) or {}
        signal_ops = signal_operations(signal_row)

        detail_payload = detail_payloads.get(code)

        if detail_payload is None:
            continue

        detail_ops = detail_operations(
            detail_payload,
            target_date,
        )

        signal_etfs = set(signal_ops)
        detail_etfs = set(detail_ops)

        missing_in_detail = sorted(
            signal_etfs - detail_etfs
        )
        extra_in_detail = sorted(
            detail_etfs - signal_etfs
        )

        value_mismatches: list[dict[str, Any]] = []

        for etf in sorted(signal_etfs & detail_etfs):
            signal_item = signal_ops[etf]
            detail_item = detail_ops[etf]

            delta_diff = abs(
                signal_item["delta"]
                - detail_item["delta"]
            )

            status_diff = (
                signal_item["status"]
                != detail_item["status"]
            )

            if delta_diff > TOLERANCE or status_diff:
                value_mismatches.append({
                    "etf_code": etf,
                    "signals": signal_item,
                    "recent_operations": detail_item,
                })

        signal_delta = sum(
            item["delta"]
            for item in signal_ops.values()
        )
        detail_delta = sum(
            item["delta"]
            for item in detail_ops.values()
        )

        signal_buy = sum(
            1
            for item in signal_ops.values()
            if item["status"] in {"新增", "加碼"}
        )
        signal_sell = sum(
            1
            for item in signal_ops.values()
            if item["status"] in {"刪除", "減碼"}
        )

        detail_buy = sum(
            1
            for item in detail_ops.values()
            if item["status"] in {"新增", "加碼"}
        )
        detail_sell = sum(
            1
            for item in detail_ops.values()
            if item["status"] in {"刪除", "減碼"}
        )

        aggregates_match = (
            abs(signal_delta - detail_delta)
            <= TOLERANCE
            and signal_buy == detail_buy
            and signal_sell == detail_sell
        )

        if (
            missing_in_detail
            or extra_in_detail
            or value_mismatches
            or not aggregates_match
        ):
            mismatches.append({
                "stock_code": code,
                "missing_in_recent_operations":
                    missing_in_detail,
                "extra_in_recent_operations":
                    extra_in_detail,
                "value_mismatches":
                    value_mismatches,
                "signals_summary": {
                    "delta_shares": signal_delta,
                    "buy": signal_buy,
                    "sell": signal_sell,
                    "etf_count": len(signal_ops),
                },
                "recent_operations_summary": {
                    "delta_shares": detail_delta,
                    "buy": detail_buy,
                    "sell": detail_sell,
                    "etf_count": len(detail_ops),
                },
            })

    report = {
        "site_url": SITE_URL,
        "target_date": target_date,
        "signal_stock_count": len(signal_rows),
        "audited_stock_count": len(all_codes),
        "fetch_error_count": len(fetch_errors),
        "mismatch_count": len(mismatches),
        "fetch_errors": fetch_errors,
        "mismatches": mismatches,
    }

    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_PATH.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print("=" * 65)
    print("今日訊號與近期操作記錄同步檢查")
    print("=" * 65)
    print(f"資料日：{target_date}")
    print(f"檢查股票：{len(all_codes)}")
    print(f"API 錯誤：{len(fetch_errors)}")
    print(f"資料不一致：{len(mismatches)}")

    for item in fetch_errors[:20]:
        print()
        print(
            f"[API ERROR] "
            f"{item['stock_code']}: "
            f"{item['error']}"
        )

    for item in mismatches[:20]:
        print()
        print("-" * 65)
        print(f"股票：{item['stock_code']}")
        print(
            f"今日訊號："
            f"{item['signals_summary']}"
        )
        print(
            f"近期記錄："
            f"{item['recent_operations_summary']}"
        )

        if item["missing_in_recent_operations"]:
            print(
                "近期記錄缺少：",
                item["missing_in_recent_operations"],
            )

        if item["extra_in_recent_operations"]:
            print(
                "近期記錄多出：",
                item["extra_in_recent_operations"],
            )

        if item["value_mismatches"]:
            print(
                "數值或狀態不符：",
                item["value_mismatches"],
            )

    print()
    print(f"完整報告：{REPORT_PATH}")

    if fetch_errors or mismatches:
        raise SystemExit(
            "FAIL：今日訊號與近期操作記錄不同步"
        )

    print(
        "PASS：今日訊號與近期操作記錄完全同步。"
    )


if __name__ == "__main__":
    main()
