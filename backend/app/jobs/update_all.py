import os
from pprint import pprint
from ..database import init_db
from ..services.fetcher import update_all_etfs
from ..services.market_data import update_market_data_from_latest_holdings

def main():
    init_db()
    dt_range=int(os.getenv('DT_RANGE','1'))
    sleep_sec=float(os.getenv('SLEEP_SEC','0.8'))
    stock_days=int(os.getenv('STOCK_HISTORY_DAYS','120'))
    stock_limit_raw=os.getenv('STOCK_LIMIT','').strip()
    stock_limit=int(stock_limit_raw) if stock_limit_raw else None
    print(f"DATABASE_URL: {'set' if os.getenv('DATABASE_URL') else 'not set'}", flush=True)
    print(f"DT_RANGE: {dt_range}", flush=True)
    pprint(update_all_etfs(dt_range=dt_range,sleep_sec=sleep_sec))
    print('Start market data update...',flush=True)
    pprint(update_market_data_from_latest_holdings(stock_days=stock_days,stock_limit=stock_limit))
    print('Update all finished.',flush=True)
if __name__=='__main__': main()
