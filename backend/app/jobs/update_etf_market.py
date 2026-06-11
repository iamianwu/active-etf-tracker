from pprint import pprint

from ..services.pocket_etf_market import update_pocket_etf_market

def main():
    result = update_pocket_etf_market()
    pprint(result)

if __name__ == "__main__":
    main()
