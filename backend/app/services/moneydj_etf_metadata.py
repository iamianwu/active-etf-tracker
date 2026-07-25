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
MONEYDJ_CUMULATIVE_RETURN_URL = (
    "https://www.moneydj.com/ETF/X/Rank/Rank0006.xdjhtm"
)
MONEYDJ_ANNUALIZED_RETURN_URL = (
    "https://www.moneydj.com/ETF/X/Rank/Rank0007.xdjhtm"
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


class _TableRowsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._table_depth = 0
        self._in_row = False
        self._cell_depth = 0
        self._buffer: list[str] = []
        self._row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized == "table":
            self._table_depth += 1
        elif normalized == "tr" and self._table_depth:
            self._in_row = True
            self._row = []
        elif normalized in {"td", "th"} and self._in_row:
            self._cell_depth += 1
            if self._cell_depth == 1:
                self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"td", "th"} and self._cell_depth:
            self._cell_depth -= 1
            if self._cell_depth == 0:
                value = re.sub(r"\s+", " ", "".join(self._buffer)).strip()
                self._row.append(value)
        elif normalized == "tr" and self._in_row:
            if self._row:
                self.rows.append(self._row)
            self._in_row = False
            self._row = []
        elif normalized == "table" and self._table_depth:
            self._table_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._cell_depth:
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
        "aum_billion": (
            (_number(_cell_after(cells, "ETF規模")) or 0) / 100
            if _number(_cell_after(cells, "ETF規模")) is not None
            else None
        ),
        "nav": _number(_cell_after(cells, "ETF淨值")),
        "premium_pct": _number(_cell_after(cells, "折溢價(%)")),
        "currency": (
            _cell_after(cells, "淨值幣別").strip()
            or _cell_after(cells, "計價幣別").strip()
            or None
        ),
        "manager": _cell_after(cells, "經理人").strip() or None,
        "company": _cell_after(cells, "發行公司").strip() or None,
        "custodian": _cell_after(cells, "保管機構").strip() or None,
    }


def parse_moneydj_return_rank(
    raw_html: str,
    return_label: str,
) -> dict[str, dict[str, float | None]]:
    parser = _TableRowsParser()
    parser.feed(raw_html)

    header: list[str] | None = None
    code_index = -1
    return_index = -1
    week_index = -1
    result: dict[str, dict[str, float | None]] = {}
    normalized_return_label = re.sub(r"\s+", "", return_label)

    for row in parser.rows:
        normalized_row = [
            re.sub(r"\s+", "", cell)
            for cell in row
        ]
        if "代碼" in normalized_row and normalized_return_label in normalized_row:
            header = row
            code_index = normalized_row.index("代碼")
            return_index = normalized_row.index(normalized_return_label)
            week_index = (
                normalized_row.index("一週")
                if "一週" in normalized_row
                else -1
            )
            continue

        if not header or max(code_index, return_index) >= len(row):
            continue

        code = str(row[code_index] or "").strip().upper()
        if not re.fullmatch(r"[0-9]{4,6}A?", code):
            continue

        result[code] = {
            "return": _number(row[return_index]),
            "week_return": (
                _number(row[week_index])
                if 0 <= week_index < len(row)
                else None
            ),
        }

    return result


def fetch_moneydj_return_rank(
    url: str,
    *,
    return_label: str,
    session: requests.Session | None = None,
    timeout: int = 40,
) -> dict[str, dict[str, float | None]]:
    client = session or requests.Session()
    response = client.get(
        url,
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() in {"ascii", "iso-8859-1"}:
        response.encoding = response.apparent_encoding or "utf-8"
    return parse_moneydj_return_rank(response.text, return_label)


def fetch_moneydj_etf_basic(
    etf_code: str,
    *,
    session: requests.Session | None = None,
    timeout: int = 25,
    retries: int = 3,
) -> dict[str, Any]:
    code = str(etf_code or "").strip().upper()
    client = session or requests.Session()
    last_error: Exception | None = None

    for attempt in range(1, max(1, retries) + 1):
        try:
            response = client.get(
                MONEYDJ_BASIC_URL,
                params={"etfid": f"{code}.TW"},
                headers=HEADERS,
                timeout=timeout,
            )
            response.raise_for_status()
            if (
                not response.encoding
                or response.encoding.lower() in {"ascii", "iso-8859-1"}
            ):
                response.encoding = response.apparent_encoding or "utf-8"

            result = parse_moneydj_etf_basic(
                response.text,
                expected_code=code,
            )
            result["source_url"] = response.url
            return result
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < max(1, retries):
                time.sleep(attempt)

    raise RuntimeError(
        f"MoneyDJ ETF basic failed after {max(1, retries)} attempts: "
        f"{code}: {last_error}"
    )


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
                row.get("nav"),
                row.get("premium_pct"),
                row.get("aum_billion"),
                row.get("expense_ratio"),
                row.get("inception_date"),
                row.get("dividend_frequency"),
                row.get("dividend_yield"),
                row.get("week_return"),
                row.get("total_return"),
                row.get("annualized_return"),
                row.get("region"),
                row.get("currency"),
                row.get("manager"),
                row.get("company"),
                row.get("custodian"),
                now,
            )
            conn.execute(
                """
                INSERT INTO etf_quotes(
                  etf_code, etf_name, nav, premium_pct, aum_billion,
                  expense_ratio, inception_date, dividend_frequency,
                  dividend_yield, week_return, total_return, annualized_return,
                  region, currency, manager, company, custodian, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (etf_code) DO UPDATE SET
                  etf_name=COALESCE(NULLIF(EXCLUDED.etf_name, ''), etf_quotes.etf_name),
                  nav=COALESCE(EXCLUDED.nav, etf_quotes.nav),
                  premium_pct=COALESCE(EXCLUDED.premium_pct, etf_quotes.premium_pct),
                  aum_billion=COALESCE(EXCLUDED.aum_billion, etf_quotes.aum_billion),
                  expense_ratio=COALESCE(EXCLUDED.expense_ratio, etf_quotes.expense_ratio),
                  inception_date=COALESCE(EXCLUDED.inception_date, etf_quotes.inception_date),
                  dividend_frequency=COALESCE(EXCLUDED.dividend_frequency, etf_quotes.dividend_frequency),
                  dividend_yield=COALESCE(EXCLUDED.dividend_yield, etf_quotes.dividend_yield),
                  week_return=COALESCE(EXCLUDED.week_return, etf_quotes.week_return),
                  total_return=COALESCE(EXCLUDED.total_return, etf_quotes.total_return),
                  annualized_return=COALESCE(EXCLUDED.annualized_return, etf_quotes.annualized_return),
                  region=COALESCE(EXCLUDED.region, etf_quotes.region),
                  currency=COALESCE(EXCLUDED.currency, etf_quotes.currency),
                  manager=COALESCE(EXCLUDED.manager, etf_quotes.manager),
                  company=COALESCE(EXCLUDED.company, etf_quotes.company),
                  custodian=COALESCE(EXCLUDED.custodian, etf_quotes.custodian),
                  updated_at=EXCLUDED.updated_at
                """,
                values,
            )

            conn.execute(
                """
                INSERT INTO etf_basic_info(
                  etf_code, etf_name, aum_billion, expense_ratio,
                  inception_date, dividend_frequency, manager, company,
                  custodian, region, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (etf_code) DO UPDATE SET
                  etf_name=COALESCE(NULLIF(EXCLUDED.etf_name, ''), etf_basic_info.etf_name),
                  aum_billion=COALESCE(EXCLUDED.aum_billion, etf_basic_info.aum_billion),
                  expense_ratio=COALESCE(EXCLUDED.expense_ratio, etf_basic_info.expense_ratio),
                  inception_date=COALESCE(EXCLUDED.inception_date, etf_basic_info.inception_date),
                  dividend_frequency=COALESCE(EXCLUDED.dividend_frequency, etf_basic_info.dividend_frequency),
                  manager=COALESCE(EXCLUDED.manager, etf_basic_info.manager),
                  company=COALESCE(EXCLUDED.company, etf_basic_info.company),
                  custodian=COALESCE(EXCLUDED.custodian, etf_basic_info.custodian),
                  region=COALESCE(EXCLUDED.region, etf_basic_info.region),
                  updated_at=EXCLUDED.updated_at
                """,
                (
                    row["etf_code"],
                    row.get("etf_name") or row["etf_code"],
                    row.get("aum_billion"),
                    row.get("expense_ratio"),
                    row.get("inception_date"),
                    row.get("dividend_frequency"),
                    row.get("manager"),
                    row.get("company"),
                    row.get("custodian"),
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
    cumulative_returns: dict[str, dict[str, float | None]] = {}
    annualized_returns: dict[str, dict[str, float | None]] = {}

    try:
        cumulative_returns = fetch_moneydj_return_rank(
            MONEYDJ_CUMULATIVE_RETURN_URL,
            return_label="成立以來",
            session=session,
        )
        print(
            f"MoneyDJ cumulative return rows={len(cumulative_returns)}",
            flush=True,
        )
    except Exception as exc:
        print(f"MoneyDJ cumulative return rank: ERROR {exc}", flush=True)

    try:
        annualized_returns = fetch_moneydj_return_rank(
            MONEYDJ_ANNUALIZED_RETURN_URL,
            return_label="成立以來 年化報酬",
            session=session,
        )
        print(
            f"MoneyDJ annualized return rows={len(annualized_returns)}",
            flush=True,
        )
    except Exception as exc:
        print(f"MoneyDJ annualized return rank: ERROR {exc}", flush=True)

    print(
        f"Start MoneyDJ ETF metadata update: total={len(selected_codes)}",
        flush=True,
    )

    for index, code in enumerate(selected_codes, start=1):
        try:
            row = fetch_moneydj_etf_basic(code, session=session)
            if not row.get("etf_name"):
                row["etf_name"] = names.get(code, code)

            cumulative = cumulative_returns.get(code) or {}
            annualized = annualized_returns.get(code) or {}
            row["week_return"] = (
                cumulative.get("week_return")
                if cumulative.get("week_return") is not None
                else annualized.get("week_return")
            )
            row["total_return"] = cumulative.get("return")
            row["annualized_return"] = annualized.get("return")
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
