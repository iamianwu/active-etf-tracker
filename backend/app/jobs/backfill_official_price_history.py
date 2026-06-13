import os
from pprint import pprint

from ..services.official_price_history import backfill_official_price_history


def main():
    result = backfill_official_price_history(
        months=int(os.getenv("HISTORY_MONTHS", "4")),
        batch_total=int(os.getenv("BATCH_TOTAL", "1")),
        batch_index=int(os.getenv("BATCH_INDEX", "0")),
        sleep_sec=float(os.getenv("HISTORY_SLEEP_SEC", "0.15")),
    )
    pprint(result)


if __name__ == "__main__":
    main()
