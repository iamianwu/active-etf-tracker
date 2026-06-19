'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { ResponsiveContainer, AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { rowsOf, quoteOf, stockCode, stockName, etfCode, etfName, fmtFree, fmtPct, fmtSigned, priceOf, changePctOf, marketValueBillionOf, sharesLotsOf, allHoldingHistory, trendRowsFromAny, dateOf, shortDate, sortRows, toneClass, num, toggleFavorite, favoriteExists, type SortDir } from './mobileV89Utils';

type Tab = 'overview' | 'whale' | 'rank' | 'detail';
type SortKey = 'lots' | 'value' | 'delta5' | 'delta20' | 'weight' | 'code';

function useBack() { return () => { if (typeof window !== 'undefined' && window.history.length > 1) window.history.back(); else window.location.href = '/holdings'; }; }

function Header({ code, name }: any) {
  const back = useBack();
  const [fav, setFav] = useState(false);
  return <header className="v89-detail-header"><button onClick={back} className="back">‹</button><div><b>{code}</b><span>{name}</span></div><button className="star" onClick={() => setFav(toggleFavorite({ code, name, type: 'stock' }))}>{fav || favoriteExists(code, 'stock') ? '★' : '☆'}</button></header>;
}

function Tabs({ tab, setTab }: any) {
  const tabs: [Tab, string][] = [['overview', '總覽'], ['whale', 'ETF持股變化'], ['rank', '加減碼排行'], ['detail', '持股明細']];
  return <nav className="v89-detail-tabs">{tabs.map(([k, label]) => <button key={k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)}>{label}</button>)}</nav>;
}

function MiniArea({ rows, color = 'red', height = 190 }: any) {
  if (!Array.isArray(rows) || rows.length < 2) return <div className="v89-empty-box">目前沒有足夠的歷史資料</div>;
  return <div className="v89-chart-box"><ResponsiveContainer width="100%" height={height}><AreaChart data={rows}><CartesianGrid strokeDasharray="4 4" vertical={false} /><XAxis dataKey="date" tickFormatter={(v) => shortDate(v)} minTickGap={20} /><YAxis width={38} domain={['auto', 'auto']} /><Tooltip /><Area type="monotone" dataKey="value" stroke={color === 'red' ? '#df555d' : '#27a575'} fill={color === 'red' ? '#fff1f2' : '#ecfdf5'} strokeWidth={2.2} /></AreaChart></ResponsiveContainer></div>;
}

function buildEtfRows(data: any, currentRows: any[]) {
  const hist = allHoldingHistory(data);
  const currentMap: Record<string, any> = {};
  currentRows.forEach((r) => { if (etfCode(r)) currentMap[etfCode(r)] = r; });
  if (!hist.length) return currentRows.map((r) => ({ raw: r, code: etfCode(r), name: etfName(r), lots: sharesLotsOf(r), value: marketValueBillionOf(r), weight: num(r?.weight), delta5: NaN, delta20: NaN, latestDate: dateOf(r) })).filter((x) => x.code);
  const groups: Record<string, any[]> = {};
  hist.forEach((r) => { const c = etfCode(r); if (!groups[c]) groups[c] = []; groups[c].push(r); });
  return Object.entries(groups).map(([code, list]) => {
    const sorted = [...list].sort((a, b) => dateOf(a).localeCompare(dateOf(b)));
    const latest = sorted[sorted.length - 1];
    const prev5 = sorted[Math.max(0, sorted.length - 6)];
    const prev20 = sorted[Math.max(0, sorted.length - 21)];
    const lots = sharesLotsOf(latest);
    const cur = currentMap[code] || latest;
    return { raw: cur, code, name: etfName(cur) || etfName(latest), lots, value: marketValueBillionOf(cur), weight: num(cur?.weight ?? latest?.weight), delta5: sorted.length >= 2 ? lots - sharesLotsOf(prev5) : NaN, delta20: sorted.length >= 2 ? lots - sharesLotsOf(prev20) : NaN, latestDate: dateOf(latest) };
  });
}

function totalHoldingTrend(data: any) {
  const hist = allHoldingHistory(data);
  if (!hist.length) return [];
  const map: Record<string, number> = {};
  hist.forEach((r) => { const d = dateOf(r); if (d) map[d] = (map[d] || 0) + (Number.isFinite(sharesLotsOf(r)) ? sharesLotsOf(r) : 0); });
  return Object.entries(map).sort(([a], [b]) => a.localeCompare(b)).map(([date, value]) => ({ date, value })).slice(-160);
}

function SortButton({ label, k, sortKey, sortDir, onClick }: any) { const active = sortKey === k; return <button className={active ? 'active' : ''} onClick={onClick}>{label}<span>{active ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}</span></button>; }

export default function StockDetailClient(props: any) {
  const data = props?.data || props;
  const quote = quoteOf(data);
  const code = stockCode(quote) || data?.stock_code || data?.code;
  const name = stockName(quote) || data?.stock_name || data?.name;
  const [tab, setTab] = useState<Tab>('overview');
  const [sortKey, setSortKey] = useState<SortKey>('value');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const currentRows = rowsOf(data);
  const etfRows = useMemo(() => buildEtfRows(data, currentRows), [data, currentRows]);
  const totalLots = etfRows.reduce((a, r) => a + (Number.isFinite(r.lots) ? r.lots : 0), 0);
  const totalValue = etfRows.reduce((a, r) => a + (Number.isFinite(r.value) ? r.value : 0), 0);
  const delta5 = etfRows.reduce((a, r) => a + (Number.isFinite(r.delta5) ? r.delta5 : 0), 0);
  const delta20 = etfRows.reduce((a, r) => a + (Number.isFinite(r.delta20) ? r.delta20 : 0), 0);
  const holdingTrend = useMemo(() => totalHoldingTrend(data), [data]);
  const priceTrend = trendRowsFromAny(data);

  const sortedEtfRows = useMemo(() => sortRows(etfRows, (r: any) => {
    if (sortKey === 'lots') return r.lots;
    if (sortKey === 'delta5') return r.delta5;
    if (sortKey === 'delta20') return r.delta20;
    if (sortKey === 'weight') return r.weight;
    if (sortKey === 'code') return r.code;
    return r.value;
  }, sortDir), [etfRows, sortKey, sortDir]);

  function toggleSort(k: SortKey) { if (sortKey === k) setSortDir((d) => d === 'desc' ? 'asc' : 'desc'); else { setSortKey(k); setSortDir('desc'); } }

  const addRank = [...etfRows].filter((r) => Number.isFinite(r.delta20) && r.delta20 > 0).sort((a, b) => b.delta20 - a.delta20).slice(0, 5);
  const reduceRank = [...etfRows].filter((r) => Number.isFinite(r.delta20) && r.delta20 < 0).sort((a, b) => a.delta20 - b.delta20).slice(0, 5);

  return (
    <main className="v89-detail-page">
      <Header code={code} name={name} />
      <Tabs tab={tab} setTab={setTab} />
      {tab === 'overview' && <section className="v89-section">
        <div className="v89-stock-quote"><div><span>股價</span><b className={toneClass(changePctOf(quote))}>{fmtFree(priceOf(quote), 1)}</b><small>{fmtPct(changePctOf(quote), 2)}</small></div><div><span>主動 ETF 持股熱度</span><b>{fmtFree(etfRows.length, 0)} 檔</b><small>總市值 {fmtFree(totalValue, 2)} 億</small></div></div>
        <div className="v89-kpi-grid four"><div><span>持有 ETF</span><b>{fmtFree(etfRows.length, 0)}</b><small>檔</small></div><div><span>總持股張數</span><b>{fmtFree(totalLots, 0)}</b><small>張</small></div><div><span>近5日變化</span><b className={toneClass(delta5)}>{fmtSigned(delta5, 0)}</b><small>張</small></div><div><span>近20日變化</span><b className={toneClass(delta20)}>{fmtSigned(delta20, 0)}</b><small>張</small></div></div>
        <div className={`v89-insight ${delta20 >= 0 ? 'red' : 'green'}`}><b>🎯 主動 ETF 近期{delta20 >= 0 ? '偏加碼' : '偏減碼'}</b><span>近20日淨變化 {fmtSigned(delta20, 0, ' 張')}</span></div>
        <h2>主動 ETF 總持股趨勢</h2><MiniArea rows={holdingTrend.length ? holdingTrend : priceTrend} color={delta20 >= 0 ? 'red' : 'green'} />
        <h2>持有 ETF 明細</h2><EtfHoldingList rows={sortedEtfRows.slice(0, 8)} />
      </section>}
      {tab === 'whale' && <section className="v89-section"><h1>ETF 大戶持股總覽</h1><div className="v89-kpi-grid four"><div><span>持有 ETF 檔數</span><b>{fmtFree(etfRows.length, 0)}</b></div><div><span>總持股張數</span><b>{fmtFree(totalLots, 0)}</b></div><div><span>總持股市值</span><b>{fmtFree(totalValue, 2)}</b><small>億</small></div><div><span>近20日變化</span><b className={toneClass(delta20)}>{fmtSigned(delta20, 0)}</b><small>張</small></div></div><h2>總持股趨勢</h2><MiniArea rows={holdingTrend} color={delta20 >= 0 ? 'red' : 'green'} /></section>}
      {tab === 'rank' && <section className="v89-section"><RankCard title="近20日加碼 TOP5" rows={addRank} positive /><RankCard title="近20日減碼 TOP5" rows={reduceRank} positive={false} /></section>}
      {tab === 'detail' && <section className="v89-section"><div className="v89-sort-row sticky"><SortButton label="市值" k="value" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('value')} /><SortButton label="張數" k="lots" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('lots')} /><SortButton label="近5日" k="delta5" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('delta5')} /><SortButton label="近20日" k="delta20" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('delta20')} /></div><EtfHoldingList rows={sortedEtfRows} /></section>}
    </main>
  );
}

function RankCard({ title, rows, positive }: any) {
  return <section className={`v89-rank-card ${positive ? 'red' : 'green'}`}><h2>{title}</h2>{rows.length === 0 && <div className="v89-empty-box small">目前缺少近20日變動資料</div>}{rows.map((r: any, i: number) => <Link href={`/etf/${r.code}?from=stock`} className="v89-rank-item" key={r.code}><span>{i + 1}</span><div><b>{r.code}</b><small>{r.name}</small></div><strong>{fmtSigned(r.delta20, 0, ' 張')}</strong></Link>)}</section>;
}

function EtfHoldingList({ rows }: { rows: any[] }) {
  if (!rows.length) return <div className="v89-empty-box">目前沒有 ETF 持股資料</div>;
  return <div className="v89-etf-holding-list">{rows.map((r) => <Link key={r.code} href={`/etf/${r.code}?from=stock`} className="v89-etf-holding-row"><div><b>{r.code}</b><span>{r.name}</span></div><div><b>{fmtFree(r.lots, 0)} 張</b><span>{fmtFree(r.value, 2)} 億</span></div><div><b className={toneClass(r.delta5)}>{Number.isFinite(r.delta5) ? fmtSigned(r.delta5, 0) : '-'}</b><span>近5日</span></div><div><b className={toneClass(r.delta20)}>{Number.isFinite(r.delta20) ? fmtSigned(r.delta20, 0) : '-'}</b><span>近20日</span></div></Link>)}</div>;
}
