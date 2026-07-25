from pprint import pprint

from ..services.moneydj_stock_market_caps import (
    update_moneydj_stock_market_caps,
)


def main() -> None:
    result = update_moneydj_stock_market_caps()
    pprint(result)

    if not result.get("saved"):
        raise RuntimeError("MoneyDJ stock market cap update saved zero rows")


if __name__ == "__main__":
    main()
