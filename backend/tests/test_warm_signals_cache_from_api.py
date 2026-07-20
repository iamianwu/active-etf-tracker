import sys
import unittest
from unittest.mock import MagicMock

try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:
    sys.modules["psycopg"] = MagicMock()

from app.jobs.warm_signals_cache_from_api import (
    merge_signal_payloads,
)


def signal_row(
    code: str,
    delta_raw_shares: int,
    *,
    etf_code: str,
    price: float = 100,
) -> dict:
    buying = delta_raw_shares > 0

    return {
        "stock_code": code,
        "stock_name": f"Stock {code}",
        "price": price,
        "curr_raw_shares": max(
            delta_raw_shares,
            0,
        ),
        "prev_raw_shares": max(
            -delta_raw_shares,
            0,
        ),
        "delta_raw_shares": delta_raw_shares,
        "curr_weight": 1 if buying else 0,
        "prev_weight": 0 if buying else 1,
        "delta_weight": 1 if buying else -1,
        "buy_etf_count": 1 if buying else 0,
        "sell_etf_count": 0 if buying else 1,
        "add_count": 1 if buying else 0,
        "delete_count": 0 if buying else 1,
        "increase_count": 0,
        "decrease_count": 0,
        "etf_change_count": 1,
        "changed_etfs": [
            {
                "etf_code": etf_code,
                "stock_code": code,
                "status": "新增" if buying else "刪除",
                "data_date": "2026-07-20",
                "prev_date": "2026-07-17",
                "delta_raw_shares": delta_raw_shares,
            }
        ],
    }


def payload(
    universe: str,
    rows: list[dict],
    *,
    etf_codes: list[str],
) -> dict:
    return {
        "data_date": "2026-07-20",
        "universe": universe,
        "rows": rows,
        "allRows": rows,
        "all_etf_codes": etf_codes,
        "today_etf_codes": etf_codes,
        "fetched_etf_count": len(etf_codes),
        "total_etf_count": len(etf_codes),
        "includedEtfCount": len(etf_codes),
        "today_holding_rows": len(rows) * 10,
        "included_holding_rows": len(rows) * 20,
        "missing_today_etf_codes": [],
        "no_compare_etf_codes": [],
        "non_today_etfs": [],
    }


class MergeSignalPayloadsTests(unittest.TestCase):
    def test_merges_duplicate_stocks_and_recomputes_net_status(self):
        active = payload(
            "active",
            [
                signal_row(
                    "2330",
                    100_000,
                    etf_code="00981A",
                ),
                signal_row(
                    "2317",
                    -25_000,
                    etf_code="00982A",
                ),
            ],
            etf_codes=["00981A", "00982A"],
        )
        reference = payload(
            "reference",
            [
                signal_row(
                    "2330",
                    -40_000,
                    etf_code="0050",
                ),
            ],
            etf_codes=["0050"],
        )

        merged = merge_signal_payloads(
            active,
            reference,
            1,
        )

        self.assertEqual(
            merged["data_date"],
            "2026-07-20",
        )
        self.assertEqual(
            merged["universe"],
            "all",
        )
        self.assertEqual(
            merged["total_etf_count"],
            3,
        )
        self.assertEqual(
            merged["today_holding_rows"],
            30,
        )
        self.assertEqual(
            merged["signal_count"],
            2,
        )

        row_2330 = next(
            row
            for row in merged["rows"]
            if row["stock_code"] == "2330"
        )
        self.assertEqual(
            row_2330["delta_raw_shares"],
            60_000,
        )
        self.assertEqual(
            row_2330["delta_shares"],
            60,
        )
        self.assertEqual(
            row_2330["status"],
            "加碼",
        )
        self.assertEqual(
            row_2330["buy_count"],
            1,
        )
        self.assertEqual(
            row_2330["sell_count"],
            1,
        )
        self.assertEqual(
            len(
                row_2330[
                    "changed_etfs"
                ]
            ),
            2,
        )

    def test_rejects_payloads_from_different_dates(self):
        active = payload(
            "active",
            [],
            etf_codes=["00981A"],
        )
        reference = payload(
            "reference",
            [],
            etf_codes=["0050"],
        )
        reference["data_date"] = (
            "2026-07-17"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "different data dates",
        ):
            merge_signal_payloads(
                active,
                reference,
                1,
            )


if __name__ == "__main__":
    unittest.main()
