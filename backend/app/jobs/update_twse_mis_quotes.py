import os
from pprint import pprint

from ..services.twse_mis_quotes import update_stock_quotes_from_twse_mis


def main():
    result = update_stock_quotes_from_twse_mis(
        batch_codes=int(os.getenv("TWSE_MIS_BATCH_CODES", "40")),
        sleep_sec=float(os.getenv("TWSE_MIS_SLEEP_SEC", "1.0")),
    )
    pprint(result)


if __name__ == "__main__":
    main()
