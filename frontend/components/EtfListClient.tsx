'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { rowsOf, etfCode, etfName, fmtFree, fmtPct, priceOf, changePctOf, amountBillionOf, volumeOf, etfRegion, sortRows, toneClass, latestDateOf, shortDate, num, type SortDir } from './mobileV89Utils';

type Tab = 'live' | 'return' | 'basic';
type EtfTypeFilter = 'all' | 'active' | 'reference';
type SortKey = 'pct' | 'price' | 'amount' | 'volume' | 'aum' | 'return' | 'fee' | 'code';

function aumOf(r: any) { return num(r?.aum_billion ?? r?.fund_size_billion ?? r?.asset_billion ?? r?.scale_billion); }
function returnOf(r: any) { return num(r?.total_return ?? r?.since_inception_return ?? r?.return_since_inception ?? r?.one_week_return ?? r?.return_1w); }
function feeOf(r: any) { return num(r?.expense_ratio ?? r?.fee ?? r?.management_fee ?? r?.total_fee); }

function isReferenceEtfRow(r: any) {
  return String(r?.etf_group ?? r?.etf_type ?? '').toLowerCase() === 'reference';
}

function referenceRoleOf(r: any) {
  return String(r?.reference_role ?? r?.role ?? '參考對照');
}

function referenceMarketOf(r: any) {
  return String(r?.market ?? r?.region ?? etfRegion(r) ?? '台灣');
}

function SortButton({ label, k, sortKey, sortDir, onClick }: any) {
  const active = sortKey === k;
  return <button className={active ? 'active' : ''} onClick={onClick}>{label}<span>{active ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}</span></button>;
}

export default function EtfListClient(props: any) {
  const rows = rowsOf(props);
  const [tab, setTab] = useState<Tab>('live');
  const [typeFilter, setTypeFilter] = useState<EtfTypeFilter>('all');
  const [sortKey, setSortKey] = useState<SortKey>('pct');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [q, setQ] = useState('');

  const activeCount = rows.filter((r: any) => !isReferenceEtfRow(r)).length;
  const referenceCount = rows.filter((r: any) => isReferenceEtfRow(r)).length;

  const typeFiltered = rows.filter((r: any) => {
    if (typeFilter === 'active') return !isReferenceEtfRow(r);
    if (typeFilter === 'reference') return isReferenceEtfRow(r);
    return true;
  });

  const filtered = typeFiltered.filter((r: any) => {
    const keyword = `${etfCode(r)} ${etfName(r)} ${referenceRoleOf(r)} ${referenceMarketOf(r)}`.toLowerCase();
    return keyword.includes(q.trim().toLowerCase());
  });

  const sorted = useMemo(() => sortRows(filtered, (r: any) => {
    if (sortKey === 'price') return isReferenceEtfRow(r) ? -Infinity : priceOf(r);
    if (sortKey === 'amount') return isReferenceEtfRow(r) ? -Infinity : amountBillionOf(r);
    if (sortKey === 'volume') return isReferenceEtfRow(r) ? -Infinity : volumeOf(r);
    if (sortKey === 'aum') return isReferenceEtfRow(r) ? -Infinity : aumOf(r);
    if (sortKey === 'return') return isReferenceEtfRow(r) ? -Infinity : returnOf(r);
    if (sortKey === 'fee') return isReferenceEtfRow(r) ? -Infinity : feeOf(r);
    if (sortKey === 'code') return etfCode(r);
    return isReferenceEtfRow(r) ? -Infinity : changePctOf(r);
  }, sortDir), [filtered, sortKey, sortDir]);

  function toggleSort(k: SortKey) {
    if (sortKey === k) setSortDir((d) => d === 'desc' ? 'asc' : 'desc');
    else { setSortKey(k); setSortDir('desc'); }
  }

  function switchTypeFilter(next: EtfTypeFilter) {
    setTypeFilter(next);
    if (next === 'reference') {
      setSortKey('code');
      setSortDir('asc');
    }
  }

  return (
    <main className="page v89-page">
      <section className="v89-list-title-row">
        <div>
          <h1>ETF 列表</h1>
          <p>共 {sorted.length} 檔，主動式 ETF 可點進詳情；一般 ETF 作為參考對照。</p>
        </div>
        <div className="v89-segment compact">
          <button className={tab === 'live' ? 'active' : ''} onClick={() => { setTab('live'); setSortKey('pct'); }}>即時</button>
          <button className={tab === 'return' ? 'active' : ''} onClick={() => { setTab('return'); setSortKey('return'); }}>報酬</button>
          <button className={tab === 'basic' ? 'active' : ''} onClick={() => { setTab('basic'); setSortKey('aum'); }}>基本</button>
        </div>
      </section>

      <div className="v89-segment compact v89-etf-type-filter">
        <button className={typeFilter === 'all' ? 'active' : ''} onClick={() => switchTypeFilter('all')}>全部 {activeCount + referenceCount}</button>
        <button className={typeFilter === 'active' ? 'active' : ''} onClick={() => switchTypeFilter('active')}>主動式 ETF {activeCount}</button>
        <button className={typeFilter === 'reference' ? 'active' : ''} onClick={() => switchTypeFilter('reference')}>一般 ETF {referenceCount}</button>
      </div>

      <div className="v89-search-filter">
        <button>篩選</button>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜尋 ETF、代號或參考用途" />
      </div>

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
        {sorted.map((r: any, i: number) => {
          const code = etfCode(r);
          const isRef = isReferenceEtfRow(r);
          const href = isRef ? '/reference-etfs' : `/etf/${code}?from=etfs`;

          return (
            <Link key={`${code}-${i}`} href={href} className="v89-etf-card">
              <div className={`v89-side-line ${isRef ? 'ref' : (changePctOf(r) >= 0 ? 'red' : 'green')}`} />
              <div className="v89-etf-main">
                <div className="v89-etf-top">
                  <div>
                    <b>{code}</b>
                    <span>{etfName(r)}</span>
                  </div>

                  {isRef ? (
                    <div>
                      <strong>一般 ETF</strong>
                      <em>參考</em>
                    </div>
                  ) : (
                    <div>
                      <strong>{fmtFree(priceOf(r), 2)}</strong>
                      <em className={toneClass(changePctOf(r))}>{fmtPct(changePctOf(r), 2)}</em>
                    </div>
                  )}
                </div>

                {isRef && (
                  <div className="v89-etf-meta three">
                    <span>市場<b>{referenceMarketOf(r)}</b></span>
                    <span>參考用途<b>{referenceRoleOf(r)}</b></span>
                    <span>今日訊號<b>不納入</b></span>
                  </div>
                )}

                {!isRef && tab === 'live' && <div className="v89-etf-meta three"><span>成交量<b>{fmtFree(volumeOf(r), 0)}</b></span><span>成交金額<b>{fmtFree(amountBillionOf(r), 1)} 億</b></span><span>報價更新<b>{shortDate(latestDateOf(r))}</b></span></div>}
                {!isRef && tab === 'return' && <div className="v89-etf-meta three"><span>報酬<b className={toneClass(returnOf(r))}>{fmtPct(returnOf(r), 1)}</b></span><span>成交額<b>{fmtFree(amountBillionOf(r), 1)} 億</b></span><span>區域<b>{etfRegion(r)}</b></span></div>}
                {!isRef && tab === 'basic' && <div className="v89-etf-meta three"><span>資產規模<b>{fmtFree(aumOf(r), 0)} 億</b></span><span>內扣費用<b>{Number.isFinite(feeOf(r)) ? fmtFree(feeOf(r), 2) + '%' : '-'}</b></span><span>投資區域<b>{etfRegion(r)}</b></span></div>}

                {isRef ? (
                  <div className="v89-data-badges">
                    <span className="ok">一般 ETF ✓</span>
                    <span className="miss">持股待接入</span>
                  </div>
                ) : (
                  <div className="v89-data-badges">
                    <span className={Number.isFinite(priceOf(r)) ? 'ok' : 'miss'}>股價 {Number.isFinite(priceOf(r)) ? '✓' : '-'}</span>
                    <span className="ok">成分股 ✓</span>
                  </div>
                )}
              </div>
            </Link>
          );
        })}
      </section>
    </main>
  );
}
