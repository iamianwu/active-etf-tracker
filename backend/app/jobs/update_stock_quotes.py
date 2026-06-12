import os
from pprint import pprint

from ..services.stock_quotes_updater import update_stock_quotes


def main():
    result = update_stock_quotes(
        batch_size=int(os.getenv("YAHOO_BATCH_SIZE", "15")),
        sleep_sec=float(os.getenv("YAHOO_SLEEP_SEC", "3.0")),
        max_retries=int(os.getenv("YAHOO_MAX_RETRIES", "2")),
    )
    pprint(result)


if __name__ == "__main__":
    main()
