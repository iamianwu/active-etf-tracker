'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { rowsOf, stockCode, stockName, fmtFree, fmtPct, priceOf, changePctOf, marketValueBillionOf, sharesLotsOf, sortRows, toneClass, num, type SortDir } from './mobileV89Utils';

type SortKey = 'value' | 'etfs' | 'price' | 'pct' | 'shares' | 'name';
function etfCountOf(r: any) { return num(r?.etf_count ?? r?.holding_etf_count ?? r?.active_etf_count ?? r?.count, 0); }
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
      </div>
      <section className="v89-holding-cards">
        {sorted.map((r, i) => {
          const code = stockCode(r);
          return (
            <Link key={`${code}-${i}`} href={`/stock/${code}?from=holdings`} className="v89-stock-card">
              <div><b>{stockName(r)}</b><span>{code}</span><small>持有 ETF {fmtFree(etfCountOf(r), 0)} 檔</small></div>
              <div><strong>{fmtFree(priceOf(r), 1)}</strong><em className={toneClass(changePctOf(r))}>{fmtPct(changePctOf(r), 2)}</em></div>
              <div><span>持股市值</span><b>{fmtFree(marketValueBillionOf(r), 2)} 億</b></div>
            </Link>
          );
        })}
      </section>
    </main>
  );
}
