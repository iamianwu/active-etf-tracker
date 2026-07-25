'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { rowsOf, stockCode, stockName, fmtFree, fmtPct, priceOf, changePctOf, marketValueBillionOf, sharesLotsOf, sortRows, toneClass, num, type SortDir } from './mobileV89Utils';
import styles from './HoldingsClient.module.css';

type SortKey = 'value' | 'etfs' | 'price' | 'pct' | 'shares' | 'ratio' | 'name';
function etfCountOf(r: any) { return num(r?.etf_count ?? r?.holding_etf_count ?? r?.active_etf_count ?? r?.count, 0); }
function estimatedHoldingPctOf(r: any) { return num(r?.estimated_holding_pct ?? r?.estimatedHoldingPct); }
function SortButton({ label, k, sortKey, sortDir, onClick }: any) { const active = sortKey === k; return <button className={active ? 'active' : ''} onClick={onClick}>{label}<span>{active ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}</span></button>; }

export default function HoldingsClient(props: any) {
  const rows = rowsOf(props);
  const [q, setQ] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('value');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const filtered = rows.filter((r) => (`${stockCode(r)} ${stockName(r)}`).toLowerCase().includes(q.trim().toLowerCase()));
  const sorted = useMemo(() => sortRows(filtered, (r: any) => {
    if (sortKey === 'etfs') return etfCountOf(r);
    if (sortKey === 'price') return priceOf(r);
    if (sortKey === 'pct') return changePctOf(r);
    if (sortKey === 'shares') return sharesLotsOf(r);
    if (sortKey === 'ratio') return estimatedHoldingPctOf(r);
    if (sortKey === 'name') return stockName(r);
    return marketValueBillionOf(r);
  }, sortDir), [filtered, sortKey, sortDir]);

  function toggleSort(k: SortKey) {
    if (sortKey === k) setSortDir((d) => d === 'desc' ? 'asc' : 'desc');
    else { setSortKey(k); setSortDir('desc'); }
  }

  return (
    <main className="page v89-page">
      <section className="v89-title"><h1>資金持股</h1><p>共 {sorted.length} 檔，可點股票進個股詳情。</p></section>
      <div className="v89-search-filter"><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜尋個股或代號" /></div>
      <div className="v89-sort-row">
        <SortButton label="市值" k="value" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('value')} />
        <SortButton label="ETF檔數" k="etfs" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('etfs')} />
        <SortButton label="股價" k="price" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('price')} />
        <SortButton label="漲跌幅" k="pct" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('pct')} />
        <SortButton label="持股張數" k="shares" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('shares')} />
        <SortButton label="估個股比重" k="ratio" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('ratio')} />
      </div>
      <section className={styles.cards}>
        {sorted.map((r, i) => {
          const code = stockCode(r);
          const estimatedPct = estimatedHoldingPctOf(r);
          return (
            <Link key={`${code}-${i}`} href={`/stock/${code}?from=holdings`} className={styles.card}>
              <div className={styles.identity}><b>{stockName(r)}</b><span>{code}</span></div>
              <div className={styles.quote}><strong>{fmtFree(priceOf(r), 1)}</strong><em className={toneClass(changePctOf(r))}>{fmtPct(changePctOf(r), 2)}</em></div>
              <div className={styles.metric}><span>持股市值</span><b>{fmtFree(marketValueBillionOf(r), 2)} 億</b><small>{fmtFree(sharesLotsOf(r), 0)} 張</small></div>
              <div className={styles.metric}><span>主動式檔數</span><b>{fmtFree(etfCountOf(r), 0)} 檔</b><small>估比重 {Number.isFinite(estimatedPct) ? `${fmtFree(estimatedPct, 2)}%` : '-'}</small></div>
            </Link>
          );
        })}
      </section>
    </main>
  );
}
