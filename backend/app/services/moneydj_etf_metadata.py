from __future__ import annotations

import re
import time
from datetime import datetime
from html.parser import HTMLParser
from typing import Any, Iterable

import requests

from ..config import (
    ETF_CODES,
    ETF_NAMES,
    REFERENCE_ETF_CODES,
    REFERENCE_ETF_NAMES,
)
from ..database import get_conn
from .pocket_etf_market import ensure_etf_tables


MONEYDJ_BASIC_URL = (
    "https://www.moneydj.com/ETF/X/Basic/Basic0004.xdjhtm"
)

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.7",
    "Referer": "https://www.moneydj.com/ETF/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
}


class _TableCellParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._depth = 0
        self._buffer: list[str] = []
        self.cells: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() not in {"td", "th"}:
            return
        self._depth += 1
        if self._depth == 1:
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() not in {"td", "th"} or self._depth == 0:
            return
        self._depth -= 1
        if self._depth == 0:
            value = re.sub(r"\s+", " ", "".join(self._buffer)).strip()
            self.cells.append(value)

    def handle_data(self, data: str) -> None:
        if self._depth:
            self._buffer.append(data)


def _cell_after(cells: list[str], label: str) -> str:
    for index, cell in enumerate(cells):
        if cell == label:
            return cells[index + 1] if index + 1 < len(cells) else ""
    return ""


def _number(value: Any) -> float | None:
    text = str(value or "").replace(",", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def _date(value: Any) -> str | None:
    match = re.search(
        r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
        str(value or ""),
    )
    if not match:
        return None
    return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"


def parse_moneydj_etf_basic(raw_html: str, expected_code: str = "") -> dict[str, Any]:
    parser = _TableCellParser()
    parser.feed(raw_html)
    cells = parser.cells

    code = _cell_after(cells, "交易所代碼").strip().upper()
    if expected_code and code != expected_code.strip().upper():
        raise ValueError(
            f"MoneyDJ ETF code mismatch: expected={expected_code}, actual={code or '-'}"
        )

    total_expense_text = _cell_after(cells, "總管理費用(%)")
    management_fee_text = _cell_after(cells, "經理費(%)")
    total_expense = _number(total_expense_text)
    management_fee = _number(management_fee_text)

    # MoneyDJ 對新成立 ETF 可能尚未公布總費用率；此時先以已公告的
    # 經理費作為可用值，待總費用率出現後由下一次更新自動取代。
    expense_ratio = total_expense
    expense_basis = "total_expense"
    if expense_ratio is None:
        expense_ratio = management_fee
        expense_basis = "management_fee_fallback"

    region = _cell_after(cells, "投資區域").strip()
    if not region:
        raise ValueError(f"MoneyDJ investment region missing: {code or expected_code}")

    return {
        "etf_code": code or expected_code.strip().upper(),
        "etf_name": _cell_after(cells, "ETF名稱").strip(),
        "expense_ratio": expense_ratio,
        "expense_ratio_basis": expense_basis,
        "management_fee": management_fee,
        "region": region,
        "dividend_frequency": _cell_after(cells, "配息頻率").strip() or None,
        "dividend_yield": _number(_cell_after(cells, "殖利率(%)")),
        "inception_date": _date(_cell_after(cells, "成立日期")),
    }


def fetch_moneydj_etf_basic(
    etf_code: str,
    *,
    session: requests.Session | None = None,
    timeout: int = 25,
) -> dict[str, Any]:
    code = str(etf_code or "").strip().upper()
    client = session or requests.Session()
    response = client.get(
        MONEYDJ_BASIC_URL,
        params={"etfid": f"{code}.TW"},
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() in {"ascii", "iso-8859-1"}:
        response.encoding = response.apparent_encoding or "utf-8"

    result = parse_moneydj_etf_basic(response.text, expected_code=code)
    result["source_url"] = response.url
    return result


def save_moneydj_etf_metadata(rows: Iterable[dict[str, Any]]) -> int:
    normalized_rows = list(rows)
    if not normalized_rows:
        return 0

    ensure_etf_tables()
    now = datetime.now().isoformat(timespec="seconds")

    with get_conn() as conn:
        for row in normalized_rows:
            values = (
                row["etf_code"],
                row.get("etf_name") or row["etf_code"],
                row.get("expense_ratio"),
                row.get("inception_date"),
                row.get("dividend_frequency"),
                row.get("dividend_yield"),
                row.get("region"),
                now,
            )
            conn.execute(
                """
                INSERT INTO etf_quotes(
                  etf_code, etf_name, expense_ratio, inception_date,
                  dividend_frequency, dividend_yield, region, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (etf_code) DO UPDATE SET
                  etf_name=COALESCE(NULLIF(EXCLUDED.etf_name, ''), etf_quotes.etf_name),
                  expense_ratio=COALESCE(EXCLUDED.expense_ratio, etf_quotes.expense_ratio),
                  inception_date=COALESCE(EXCLUDED.inception_date, etf_quotes.inception_date),
                  dividend_frequency=COALESCE(EXCLUDED.dividend_frequency, etf_quotes.dividend_frequency),
                  dividend_yield=COALESCE(EXCLUDED.dividend_yield, etf_quotes.dividend_yield),
                  region=COALESCE(EXCLUDED.region, etf_quotes.region),
                  updated_at=EXCLUDED.updated_at
                """,
                values,
            )

            conn.execute(
                """
                INSERT INTO etf_basic_info(
                  etf_code, etf_name, expense_ratio, inception_date,
                  dividend_frequency, region, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (etf_code) DO UPDATE SET
                  etf_name=COALESCE(NULLIF(EXCLUDED.etf_name, ''), etf_basic_info.etf_name),
                  expense_ratio=COALESCE(EXCLUDED.expense_ratio, etf_basic_info.expense_ratio),
                  inception_date=COALESCE(EXCLUDED.inception_date, etf_basic_info.inception_date),
                  dividend_frequency=COALESCE(EXCLUDED.dividend_frequency, etf_basic_info.dividend_frequency),
                  region=COALESCE(EXCLUDED.region, etf_basic_info.region),
                  updated_at=EXCLUDED.updated_at
                """,
                (
                    row["etf_code"],
                    row.get("etf_name") or row["etf_code"],
                    row.get("expense_ratio"),
                    row.get("inception_date"),
                    row.get("dividend_frequency"),
                    row.get("region"),
                    now,
                ),
            )

    return len(normalized_rows)


def update_moneydj_etf_metadata(
    *,
    codes: Iterable[str] | None = None,
    sleep_sec: float = 0.12,
) -> dict[str, Any]:
    default_codes = list(ETF_CODES) + list(REFERENCE_ETF_CODES)
    selected_codes = list(dict.fromkeys(
        str(code or "").strip().upper()
        for code in (codes if codes is not None else default_codes)
        if str(code or "").strip()
    ))
    names = {**REFERENCE_ETF_NAMES, **ETF_NAMES}
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    session = requests.Session()

    print(
        f"Start MoneyDJ ETF metadata update: total={len(selected_codes)}",
        flush=True,
    )

    for index, code in enumerate(selected_codes, start=1):
        try:
            row = fetch_moneydj_etf_basic(code, session=session)
            if not row.get("etf_name"):
                row["etf_name"] = names.get(code, code)
            rows.append(row)
            print(
                f"[{index}/{len(selected_codes)}] {code}: "
                f"fee={row.get('expense_ratio')} "
                f"basis={row.get('expense_ratio_basis')} "
                f"region={row.get('region')}",
                flush=True,
            )
        except Exception as exc:
            errors.append({"etf_code": code, "error": str(exc)})
            print(
                f"[{index}/{len(selected_codes)}] {code}: ERROR {exc}",
                flush=True,
            )
        time.sleep(max(0.0, sleep_sec))

    saved = save_moneydj_etf_metadata(rows)
    return {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "requested": len(selected_codes),
        "saved": saved,
        "errors": errors,
    }
