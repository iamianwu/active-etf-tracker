'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { rowsOf, etfCode, etfName, fmtFree, fmtPct, priceOf, changePctOf, amountBillionOf, volumeOf, etfRegion, sortRows, toneClass, latestDateOf, shortDate, num, type SortDir } from './mobileV89Utils';

type Tab = 'live' | 'return' | 'basic';
type SortKey = 'pct' | 'price' | 'amount' | 'volume' | 'aum' | 'return' | 'fee' | 'code';

function aumOf(r: any) { return num(r?.aum_billion ?? r?.fund_size_billion ?? r?.asset_billion ?? r?.scale_billion); }
function returnOf(r: any) { return num(r?.total_return ?? r?.since_inception_return ?? r?.return_since_inception ?? r?.one_week_return ?? r?.return_1w); }
function feeOf(r: any) { return num(r?.expense_ratio ?? r?.fee ?? r?.management_fee ?? r?.total_fee); }
function SortButton({ label, k, sortKey, sortDir, onClick }: any) { const active = sortKey === k; return <button className={active ? 'active' : ''} onClick={onClick}>{label}<span>{active ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}</span></button>; }

export default function EtfListClient(props: any) {
  const rows = rowsOf(props);
  const [tab, setTab] = useState<Tab>('live');
  const [sortKey, setSortKey] = useState<SortKey>('pct');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [q, setQ] = useState('');

  const filtered = rows.filter((r) => (`${etfCode(r)} ${etfName(r)}`).toLowerCase().includes(q.trim().toLowerCase()));
  const sorted = useMemo(() => sortRows(filtered, (r: any) => {
    if (sortKey === 'price') return priceOf(r);
    if (sortKey === 'amount') return amountBillionOf(r);
    if (sortKey === 'volume') return volumeOf(r);
    if (sortKey === 'aum') return aumOf(r);
    if (sortKey === 'return') return returnOf(r);
    if (sortKey === 'fee') return feeOf(r);
    if (sortKey === 'code') return etfCode(r);
    return changePctOf(r);
  }, sortDir), [filtered, sortKey, sortDir]);

  function toggleSort(k: SortKey) {
    if (sortKey === k) setSortDir((d) => d === 'desc' ? 'asc' : 'desc');
    else { setSortKey(k); setSortDir('desc'); }
  }

  return (
    <main className="page v89-page">
      <section className="v89-list-title-row">
        <div><h1>ETF 列表</h1><p>共 {sorted.length} 檔，每檔 ETF 可點進詳情。</p></div>
        <div className="v89-segment compact">
          <button className={tab === 'live' ? 'active' : ''} onClick={() => { setTab('live'); setSortKey('pct'); }}>即時</button>
          <button className={tab === 'return' ? 'active' : ''} onClick={() => { setTab('return'); setSortKey('return'); }}>報酬</button>
          <button className={tab === 'basic' ? 'active' : ''} onClick={() => { setTab('basic'); setSortKey('aum'); }}>基本</button>
        </div>
      </section>

      <div className="v89-search-filter"><button>篩選</button><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜尋 ETF 或代號" /></div>

      <div className="v89-sort-row">
        {tab === 'live' && <>
          <SortButton label="漲跌幅" k="pct" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('pct')} />
          <SortButton label="股價" k="price" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('price')} />
          <SortButton label="成交額" k="amount" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('amount')} />
          <SortButton label="成交量" k="volume" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('volume')} />
        </>}
        {tab === 'return' && <>
          <SortButton label="報酬" k="return" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('return')} />
          <SortButton label="股價" k="price" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('price')} />
          <SortButton label="漲跌幅" k="pct" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('pct')} />
        </>}
        {tab === 'basic' && <>
          <SortButton label="規模" k="aum" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('aum')} />
          <SortButton label="費用" k="fee" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('fee')} />
          <SortButton label="代號" k="code" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('code')} />
        </>}
      </div>

      <section className="v89-etf-cards">
        {sorted.map((r, i) => {
          const code = etfCode(r);
          return (
            <Link key={`${code}-${i}`} href={`/etf/${code}?from=etfs`} className="v89-etf-card">
              <div className={`v89-side-line ${changePctOf(r) >= 0 ? 'red' : 'green'}`} />
              <div className="v89-etf-main">
                <div className="v89-etf-top">
                  <div><b>{code}</b><span>{etfName(r)}</span></div>
                  <div><strong>{fmtFree(priceOf(r), 2)}</strong><em className={toneClass(changePctOf(r))}>{fmtPct(changePctOf(r), 2)}</em></div>
                </div>
                {tab === 'live' && <div className="v89-etf-meta three"><span>成交量<b>{fmtFree(volumeOf(r), 0)}</b></span><span>成交金額<b>{fmtFree(amountBillionOf(r), 1)} 億</b></span><span>更新<b>{shortDate(latestDateOf(r))}</b></span></div>}
                {tab === 'return' && <div className="v89-etf-meta three"><span>報酬<b className={toneClass(returnOf(r))}>{fmtPct(returnOf(r), 1)}</b></span><span>成交額<b>{fmtFree(amountBillionOf(r), 1)} 億</b></span><span>區域<b>{etfRegion(r)}</b></span></div>}
                {tab === 'basic' && <div className="v89-etf-meta three"><span>資產規模<b>{fmtFree(aumOf(r), 0)} 億</b></span><span>內扣費用<b>{Number.isFinite(feeOf(r)) ? fmtFree(feeOf(r), 2) + '%' : '-'}</b></span><span>投資區域<b>{etfRegion(r)}</b></span></div>}
                <div className="v89-data-badges"><span className={Number.isFinite(priceOf(r)) ? 'ok' : 'miss'}>股價 {Number.isFinite(priceOf(r)) ? '✓' : '-'}</span><span className="ok">成分股 ✓</span><span className="miss">歷史 -</span></div>
              </div>
            </Link>
          );
        })}
      </section>
    </main>
  );
}
