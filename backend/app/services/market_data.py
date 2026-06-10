import time
from datetime import date, datetime, timedelta
from typing import Any
import requests
from ..database import get_conn, init_db, normal_stock_condition, upsert_stock_quote

HEADERS={"User-Agent":"Mozilla/5.0","Accept-Language":"zh-TW,zh;q=0.9,en-US;q=0.8"}

def _to_float(x):
    if x is None: return None
    try:
        if isinstance(x,str):
            x=x.replace(',','').replace('--','').strip()
            if x=='': return None
        return float(x)
    except Exception:
        return None

def _num_tw(x): return _to_float(str(x or '').replace(',','')) or 0.0

def is_normal_stock_code(code:str)->bool:
    c=str(code or '').strip()
    return c.isdigit() and len(c)==4

def _upsert_stock_price_history(conn,row):
    if conn.postgres:
        conn.execute('''insert into stock_price_history
        (stock_code,trade_date,open,high,low,close,volume,change_pct,market,updated_at)
        values (?,?,?,?,?,?,?,?,?,?)
        on conflict (stock_code,trade_date) do update set
          open=excluded.open, high=excluded.high, low=excluded.low, close=excluded.close,
          volume=excluded.volume, change_pct=excluded.change_pct, market=excluded.market, updated_at=excluded.updated_at''',row)
    else:
        conn.execute('''insert or replace into stock_price_history
        (stock_code,trade_date,open,high,low,close,volume,change_pct,market,updated_at)
        values (?,?,?,?,?,?,?,?,?,?)''',row)

def _upsert_institutional_flow(conn,row):
    if conn.postgres:
        conn.execute('''insert into institutional_flows
        (stock_code,trade_date,foreign_net,investment_trust_net,dealer_net,total_net,source,updated_at)
        values (?,?,?,?,?,?,?,?)
        on conflict (stock_code,trade_date,source) do update set
          foreign_net=excluded.foreign_net, investment_trust_net=excluded.investment_trust_net,
          dealer_net=excluded.dealer_net, total_net=excluded.total_net, updated_at=excluded.updated_at''',row)
    else:
        conn.execute('''insert or replace into institutional_flows
        (stock_code,trade_date,foreign_net,investment_trust_net,dealer_net,total_net,source,updated_at)
        values (?,?,?,?,?,?,?,?)''',row)

def get_latest_stock_universe(limit:int|None=None):
    init_db()
    with get_conn() as conn:
        rows=conn.execute(f'''select h.stock_code, max(h.stock_name) as stock_name,
                   count(distinct h.etf_code) as etf_count, sum(h.weight) as total_weight
            from holdings h
            where {normal_stock_condition('h')}
              and h.data_date=(select max(h2.data_date) from holdings h2 where h2.etf_code=h.etf_code)
            group by h.stock_code order by etf_count desc, total_weight desc''').fetchall()
    out=[{"stock_code":r["stock_code"],"stock_name":r["stock_name"]} for r in rows]
    return out[:limit] if limit else out

def fetch_yahoo_history(stock_code:str,days:int=120):
    p1=int((datetime.now()-timedelta(days=days+20)).timestamp())
    p2=int((datetime.now()+timedelta(days=1)).timestamp())
    for suffix in ('TW','TWO'):
        url=f'https://query1.finance.yahoo.com/v8/finance/chart/{stock_code}.{suffix}'
        try:
            r=requests.get(url,params={"period1":p1,"period2":p2,"interval":"1d","events":"history"},headers=HEADERS,timeout=20)
            if r.status_code!=200: continue
            res=((r.json().get('chart') or {}).get('result') or [])
            if not res: continue
            item=res[0]; ts=item.get('timestamp') or []
            q=((item.get('indicators') or {}).get('quote') or [{}])[0]
            opens,highs,lows=q.get('open') or [],q.get('high') or [],q.get('low') or []
            closes,vols=q.get('close') or [],q.get('volume') or []
            rows=[]; prev=None
            for i,t in enumerate(ts):
                close=_to_float(closes[i] if i<len(closes) else None)
                if close is None: continue
                d=datetime.fromtimestamp(t).strftime('%Y-%m-%d')
                cp=(close-prev)/prev*100 if prev else None
                rows.append({"trade_date":d,"open":_to_float(opens[i] if i<len(opens) else None),"high":_to_float(highs[i] if i<len(highs) else None),"low":_to_float(lows[i] if i<len(lows) else None),"close":close,"volume":_to_float(vols[i] if i<len(vols) else None),"change_pct":cp,"market":suffix})
                prev=close
            if rows: return suffix, rows[-days:]
        except Exception:
            continue
    return None, []

def update_stock_price_history_for_universe(days:int=120,limit:int|None=None,sleep_sec:float=0.05):
    stocks=get_latest_stock_universe(limit)
    print(f'Start stock price update: total={len(stocks)}',flush=True)
    now=datetime.now().isoformat(timespec='seconds')
    results=[]
    for i,s in enumerate(stocks,1):
        code,name=s['stock_code'],s.get('stock_name')
        print(f'[price {i}/{len(stocks)}] {code} {name or ""}',flush=True)
        try:
            market,rows=fetch_yahoo_history(code,days)
            init_db()
            with get_conn() as conn:
                for r in rows:
                    _upsert_stock_price_history(conn,(code,r['trade_date'],r.get('open'),r.get('high'),r.get('low'),r.get('close'),r.get('volume'),r.get('change_pct'),r.get('market'),now))
                if rows:
                    latest=rows[-1]
                    upsert_stock_quote(conn,(code,name or code,latest.get('close'),latest.get('change_pct'),now))
            results.append({"stock_code":code,"market":market,"rows":len(rows)})
        except Exception as e:
            results.append({"stock_code":code,"error":str(e)})
        time.sleep(sleep_sec)
    return {"updated_at":now,"results":results}

def fetch_twse_t86(day:date):
    url='https://www.twse.com.tw/rwd/zh/fund/T86'
    r=requests.get(url,params={"date":day.strftime('%Y%m%d'),"selectType":"ALLBUT0999","response":"json"},headers=HEADERS,timeout=20)
    if r.status_code!=200: return []
    rows=[]
    for x in (r.json().get('data') or []):
        if len(x)<19: continue
        code=str(x[0]).strip()
        if not is_normal_stock_code(code): continue
        rows.append({"stock_code":code,"trade_date":day.strftime('%Y-%m-%d'),"foreign_net":_num_tw(x[4]),"investment_trust_net":_num_tw(x[10]),"dealer_net":_num_tw(x[16]),"total_net":_num_tw(x[18]),"source":"TWSE"})
    return rows

def fetch_tpex_institutional(day:date):
    # TPEx 欄位格式有時會變，失敗時略過，不影響主要資料。
    ymd=day.strftime('%Y/%m/%d')
    url='https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php'
    out=[]
    for se in ('EW','AL'):
        try:
            r=requests.get(url,params={"l":"zh-tw","d":ymd,"se":se,"t":"D"},headers=HEADERS,timeout=20)
            if r.status_code!=200: continue
            for x in (r.json().get('aaData') or r.json().get('data') or []):
                if len(x)<8: continue
                code=str(x[0]).strip()
                if not is_normal_stock_code(code): continue
                foreign=_num_tw(x[4]) if len(x)>4 else 0
                trust=_num_tw(x[7]) if len(x)>7 else 0
                dealer=_num_tw(x[10]) if len(x)>10 else 0
                out.append({"stock_code":code,"trade_date":day.strftime('%Y-%m-%d'),"foreign_net":foreign,"investment_trust_net":trust,"dealer_net":dealer,"total_net":foreign+trust+dealer,"source":"TPEx"})
            if out: return out
        except Exception:
            continue
    return out

def update_institutional_flows(days_back:int=35):
    now=datetime.now().isoformat(timespec='seconds')
    results=[]
    for offset in range(days_back):
        d=date.today()-timedelta(days=offset)
        if d.weekday()>=5: continue
        allrows=[]
        try: allrows+=fetch_twse_t86(d)
        except Exception as e: print(f'[inst] TWSE {d}: {e}',flush=True)
        try: allrows+=fetch_tpex_institutional(d)
        except Exception as e: print(f'[inst] TPEx {d}: {e}',flush=True)
        init_db()
        with get_conn() as conn:
            for r in allrows:
                _upsert_institutional_flow(conn,(r['stock_code'],r['trade_date'],r['foreign_net'],r['investment_trust_net'],r['dealer_net'],r['total_net'],r['source'],now))
        print(f'[inst] {d} rows={len(allrows)}',flush=True)
        results.append({"date":d.isoformat(),"rows":len(allrows)})
        time.sleep(0.1)
    return {"updated_at":now,"results":results}

def update_market_data_from_latest_holdings(stock_days:int=120,stock_limit:int|None=None):
    return {"price":update_stock_price_history_for_universe(stock_days,stock_limit),"institutional":update_institutional_flows(35)}
