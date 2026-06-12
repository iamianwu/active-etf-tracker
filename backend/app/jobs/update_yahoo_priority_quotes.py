import os
from pprint import pprint

from ..services.yahoo_priority_quotes import update_yahoo_priority_quotes


def main():
    result = update_yahoo_priority_quotes(
        max_codes=int(os.getenv("YAHOO_PRIORITY_MAX_CODES", "80")),
        batch_size=int(os.getenv("YAHOO_BATCH_SIZE", "6")),
        sleep_sec=float(os.getenv("YAHOO_SLEEP_SEC", "8.0")),
        max_retries=int(os.getenv("YAHOO_MAX_RETRIES", "1")),
    )
    pprint(result)


if __name__ == "__main__":
    main()
