from pprint import pprint

from ..services.moneydj_etf_metadata import update_moneydj_etf_metadata
from ..services.pocket_etf_market import update_pocket_etf_market

def main():
    pocket_result = update_pocket_etf_market()
    moneydj_result = update_moneydj_etf_metadata()
    result = {
        "pocket": pocket_result,
        "moneydj": moneydj_result,
    }
    pprint(result)

    if not moneydj_result.get("saved"):
        raise RuntimeError("MoneyDJ ETF metadata update saved zero rows")

if __name__ == "__main__":
    main()
