'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { rowsOf, quoteOf, etfCode, etfName, stockCode, stockName, fmtFree, fmtPct, priceOf, changePctOf, amountBillionOf, volumeOf, marketValueBillionOf, sharesLotsOf, weightOf, trendRowsFromAny, latestDateOf, shortDate, sortRows, toneClass, statusOf, fmtSigned, num, toggleFavorite, favoriteExists, type SortDir } from './mobileV89Utils';

type Tab = 'overview' | 'live' | 'operation' | 'holdings' | 'basic';
type SortKey = 'weight' | 'value' | 'shares' | 'price' | 'pct' | 'code';
function useBack() { return () => { if (typeof window !== 'undefined' && window.history.length > 1) window.history.back(); else window.location.href = '/etfs'; }; }
function SortButton({ label, k, sortKey, sortDir, onClick }: any) { const active = sortKey === k; return <button className={active ? 'active' : ''} onClick={onClick}>{label}<span>{active ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}</span></button>; }


function opDeltaLots(r: any): number {
  const directLots = num(r?.delta_lots ?? r?.change_lots ?? r?.deltaLots ?? r?.changeLots);
  if (Number.isFinite(directLots)) {
    // 有些舊資料欄位名稱雖叫 lots，但實際塞的是股數；數字太大時自動換成張
    return Math.abs(directLots) >= 100000 ? directLots / 1000 : directLots;
  }

  const shares = num(
    r?.shares_change ??
    r?.delta_shares ??
    r?.sharesChange ??
    r?.deltaShares ??
    r?.change_shares ??
    r?.changeShares
  );
  if (Number.isFinite(shares)) return shares / 1000;

  return NaN;
}

function opAmountBillion(r: any, lots: number): number {
  const direct = num(
    r?.amount_billion ??
    r?.flow_billion ??
    r?.money_billion ??
    r?.delta_amount_billion ??
    r?.net_amount_billion ??
    r?.value_change_billion ??
    r?.market_value_change_billion
  );
  if (Number.isFinite(direct)) return direct;

  const raw = num(
    r?.amount ??
    r?.flow_amount ??
    r?.delta_amount ??
    r?.net_amount ??
    r?.value_change ??
    r?.market_value_change
  );
  if (Number.isFinite(raw)) return raw / 100000000;

  const px = priceOf(r);
  if (Number.isFinite(lots) && Number.isFinite(px)) return lots * 1000 * px / 100000000;

  return NaN;
}

function OperationRows({ changes }: { changes: any[] }) {
  if (!Array.isArray(changes) || changes.length === 0) {
    return <div className="v89-empty-box">目前沒有操作日報資料</div>;
  }

  return (
    <div className="v93-op-list">
      {changes.map((r: any, i: number) => {
        const s = statusOf(r);
        const code = stockCode(r);
        const lots = opDeltaLots(r);
        const amount = opAmountBillion(r, lots);
        const weight = weightOf(r);
        const positive = Number.isFinite(lots) ? lots >= 0 : s === '新增' || s === '加碼';

        return (
          <Link href={`/stock/${code}?from=etf`} key={`${code}-${i}`} className="v93-op-row">
            <div className="v93-op-main">
              <div className="v93-op-name">
                <b>{stockName(r)}</b>
                <span>{code}</span>
              </div>
              <div className={`v89-pill ${s}`}>{s}</div>
            </div>

            <div className="v93-op-metrics">
              <div>
                <span>持股變動</span>
                <b className={positive ? 'v89-red' : 'v89-green'}>
                  {Number.isFinite(lots) ? fmtSigned(lots, 0, ' 張') : '-'}
                </b>
              </div>
              <div>
                <span>估算金額</span>
                <b className={Number.isFinite(amount) ? (amount >= 0 ? 'v89-red' : 'v89-green') : ''}>
                  {Number.isFinite(amount) ? fmtSigned(amount, 2, ' 億') : '-'}
                </b>
              </div>
              <div>
                <span>目前權重</span>
                <b>{Number.isFinite(weight) ? `${fmtFree(weight, 2)}%` : '-'}</b>
              </div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}

export default function EtfDetailClient(props: any) {
  const data = props?.data || props;
  const quote = quoteOf(data);
  const code = etfCode(quote) || data?.etf_code || data?.code;
  const name = etfName(quote) || data?.etf_name || data?.name;
  const back = useBack();
  const [fav, setFav] = useState(false);
  const [tab, setTab] = useState<Tab>('overview');
  const [sortKey, setSortKey] = useState<SortKey>('weight');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const holdings = rowsOf(data);
  const changes = data?.changes || data?.operationRows || data?.operation_rows || data?.changeRows || [];
  const chartRows = trendRowsFromAny(data);
  const sortedHoldings = useMemo(() => sortRows(holdings, (r: any) => {
    if (sortKey === 'value') return marketValueBillionOf(r);
    if (sortKey === 'shares') return sharesLotsOf(r);
    if (sortKey === 'price') return priceOf(r);
    if (sortKey === 'pct') return changePctOf(r);
    if (sortKey === 'code') return stockCode(r);
    return weightOf(r);
  }, sortDir), [holdings, sortKey, sortDir]);
  function toggleSort(k: SortKey) { if (sortKey === k) setSortDir((d) => d === 'desc' ? 'asc' : 'desc'); else { setSortKey(k); setSortDir('desc'); } }

  return (
    <main className="v89-detail-page">
      <header className="v89-detail-header"><button onClick={back} className="back">‹</button><div><b>{code}</b><span>{name}</span></div><button className="star" onClick={() => setFav(toggleFavorite({ code, name, type: 'etf' }))}>{fav || favoriteExists(code, 'etf') ? '★' : '☆'}</button></header>
      <nav className="v89-detail-tabs five">{([['overview','總覽'],['live','即時'],['operation','操作日報'],['holdings','成分股'],['basic','基本']] as any).map(([k,l]: any) => <button key={k} className={tab===k?'active':''} onClick={() => setTab(k)}>{l}</button>)}</nav>
      {tab === 'overview' && <section className="v89-section"><div className="v89-kpi-grid four"><div><span>股價</span><b className={toneClass(changePctOf(quote))}>{fmtFree(priceOf(quote), 2)}</b><small>{fmtPct(changePctOf(quote), 2)}</small></div><div><span>成交金額</span><b>{fmtFree(amountBillionOf(quote), 1)}</b><small>億</small></div><div><span>持股異動</span><b>{Array.isArray(changes) ? changes.length : 0}</b><small>檔</small></div><div><span>資料狀態</span><b className={holdings.length ? 'v89-green' : 'v89-red'}>{holdings.length ? '完整' : '待補'}</b><small>股價 / 成分股 / 歷史</small></div></div><h2>淨值 / 股價走勢</h2><Chart rows={chartRows} color={changePctOf(quote) >= 0 ? 'red' : 'green'} /><h2>前五大持股</h2><HoldingRows rows={sortedHoldings.slice(0, 5)} /></section>}
      {tab === 'live' && <section className="v89-section"><div className="v89-stock-quote"><div><span>股價</span><b className={toneClass(changePctOf(quote))}>{fmtFree(priceOf(quote), 2)}</b><small>{fmtPct(changePctOf(quote), 2)}</small></div><div><span>成交量</span><b>{fmtFree(volumeOf(quote), 0)}</b><small>{fmtFree(amountBillionOf(quote), 1)} 億</small></div></div></section>}
      {tab === 'operation' && <section className="v89-section"><h1>操作日報</h1><OperationRows changes={Array.isArray(changes) ? changes : []} /></section>}
      {tab === 'holdings' && <section className="v89-section"><div className="v89-sort-row sticky"><SortButton label="權重" k="weight" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('weight')} /><SortButton label="市值" k="value" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('value')} /><SortButton label="張數" k="shares" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('shares')} /><SortButton label="漲跌幅" k="pct" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('pct')} /></div><HoldingRows rows={sortedHoldings} /></section>}
      {tab === 'basic' && <section className="v89-section"><div className="v89-info-card"><p><span>資產規模</span><b>{fmtFree(quote?.aum_billion ?? quote?.fund_size_billion, 1)} 億</b></p><p><span>內扣費用</span><b>{Number.isFinite(num(quote?.expense_ratio)) ? fmtFree(quote?.expense_ratio, 2) + '%' : '-'}</b></p><p><span>成立日</span><b>{quote?.inception_date || quote?.listing_date || '-'}</b></p><p><span>更新時間</span><b>{shortDate(latestDateOf(quote))}</b></p></div></section>}
    </main>
  );
}

function Chart({ rows, color }: any) {
  if (!Array.isArray(rows) || rows.length < 2) return <div className="v89-empty-box">目前沒有足夠的歷史資料</div>;
  return <div className="v89-chart-box"><ResponsiveContainer width="100%" height={190}><AreaChart data={rows}><CartesianGrid strokeDasharray="4 4" vertical={false} /><XAxis dataKey="date" tickFormatter={(v) => shortDate(v)} minTickGap={20} /><YAxis width={38} domain={['auto','auto']} /><Tooltip /><Area type="monotone" dataKey="value" stroke={color==='red'?'#df555d':'#27a575'} fill={color==='red'?'#fff1f2':'#ecfdf5'} strokeWidth={2.2} /></AreaChart></ResponsiveContainer></div>;
}

function HoldingRows({ rows }: { rows: any[] }) {
  return <div className="v89-etf-holding-list">{rows.map((r) => <Link key={stockCode(r)} href={`/stock/${stockCode(r)}?from=etf`} className="v89-etf-holding-row"><div><b>{stockName(r)}</b><span>{stockCode(r)}</span></div><div><b>{fmtFree(marketValueBillionOf(r), 1)} 億</b><span>{fmtFree(sharesLotsOf(r), 0)} 張</span></div><div><b>{fmtFree(weightOf(r), 2)}%</b><span>權重</span></div><div><b>{fmtFree(priceOf(r), 1)}</b><span className={toneClass(changePctOf(r))}>{fmtPct(changePctOf(r), 2)}</span></div></Link>)}</div>;
}
