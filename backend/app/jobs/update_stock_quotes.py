import os
from pprint import pprint

from ..services.stock_quotes_updater import update_stock_quotes


def main():
    result = update_stock_quotes(
        batch_size=int(os.getenv("QUOTE_BATCH_SIZE", "80")),
        sleep_sec=float(os.getenv("QUOTE_SLEEP_SEC", "0.15")),
    )
    pprint(result)


if __name__ == "__main__":
    main()
