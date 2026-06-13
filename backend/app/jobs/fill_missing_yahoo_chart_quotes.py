import os
from pprint import pprint

from ..services.yahoo_chart_missing_quotes import fill_missing_quotes


def main():
    result = fill_missing_quotes(
        max_codes=int(os.getenv("YAHOO_MISSING_MAX_CODES", "50")),
        sleep_sec=float(os.getenv("YAHOO_MISSING_SLEEP_SEC", "3.5")),
    )
    pprint(result)


if __name__ == "__main__":
    main()
