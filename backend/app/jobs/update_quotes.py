from pprint import pprint

from ..services.realtime_quotes import update_live_quotes
from ..services.pocket_etf_market import update_pocket_etf_market

def main():
    print("=== Update stock live quotes ===", flush=True)
    stock_result = update_live_quotes()
    pprint(stock_result)

    print("=== Update Pocket ETF market data ===", flush=True)
    etf_result = update_pocket_etf_market()
    pprint(etf_result)

if __name__ == "__main__":
    main()
