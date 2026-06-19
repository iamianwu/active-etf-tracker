'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import {
  rowsOf, latestDateOf, shortDate, stockCode, stockName, fmt, fmtPct, fmtSigned,
  priceOf, changePctOf, flowBillionOf, addEtfCount, reduceEtfCount,
  statusOf, sortRows, toneClass, isStockCode, num, type SortDir
} from './mobileV89Utils';

type Status = '新增' | '刪除' | '加碼' | '減碼' | '異動';
type SortKey = 'flow' | 'price' | 'pct' | 'status' | 'name';

const statusOrder: Record<string, number> = { 新增: 4, 加碼: 3, 減碼: 2, 刪除: 1, 異動: 0 };

function usable(r: any) {
  return isStockCode(stockCode(r)) && !!stockName(r);
}

function lotsDelta(r: any) {
  return num(r?.delta_lots ?? r?.change_lots ?? r?.shares_change ?? r?.delta_shares ?? r?.deltaShares ?? r?.changeShares, 0);
}

function SortButton({ label, k, sortKey, sortDir, onClick }: any) {
  const active = sortKey === k;
  return <button className={active ? 'active' : ''} onClick={onClick}>{label}<span>{active ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}</span></button>;
}

function RangeTabs({ current }: { current: string }) {
  const tabs = [
    ['1', '今日', '/signals'],
    ['5', '5日', '/signals?days=5'],
    ['10', '10日', '/signals?days=10'],
    ['20', '20日', '/signals?days=20'],
  ];
  return (
    <section className="v89-range-card">
      <div className="v89-range-title">訊號區間</div>
      <div className="v89-segment four">
        {tabs.map(([v, label, href]) => <Link key={v} href={href} className={String(current) === v ? 'active' : ''}>{label}</Link>)}
      </div>
    </section>
  );
}

function FocusCard({ title, item, tone }: { title: string; item: any; tone: 'red' | 'green' }) {
  if (!item) return <div className={`v89-focus ${tone}`}><h3>{title}</h3><div className="v89-empty">尚無有效訊號</div></div>;
  const code = stockCode(item);
  const flow = flowBillionOf(item);
  const add = addEtfCount(item);
  const reduce = reduceEtfCount(item);
  const delta = lotsDelta(item);
  const consensus = add || reduce ? `${add}:${reduce}` : (delta ? `張數 ${fmtSigned(delta, 0)}` : '0:0');

  return (
    <Link href={`/stock/${code}?from=signals`} className={`v89-focus ${tone}`}>
      <h3>{title}</h3>
      <div className="v89-focus-grid">
        <div>
          <div className="v89-focus-name">{stockName(item)} <span>{code}</span></div>
          <div className={toneClass(changePctOf(item)) + ' v89-focus-price'}>{fmt(priceOf(item), 1)} <small>{fmtPct(changePctOf(item), 2)}</small></div>
        </div>
        <div className="v89-focus-info">
          <span>資金動向</span><b className={flow >= 0 ? 'v89-red' : 'v89-green'}>{Number.isFinite(flow) ? fmtSigned(flow, 1, ' 億') : '-'}</b>
          <span>多空共識</span><b>{consensus}</b>
        </div>
      </div>
    </Link>
  );
}

function StatusPill({ status, count, active, onClick }: any) {
  return <button className={`v89-status-pill ${status} ${active ? 'active' : ''}`} onClick={onClick}><span>{status}</span><b>{count}</b></button>;
}

export default function SignalsClient(props: any) {
  const data = props?.data || props;
  const rows = rowsOf(data).filter(usable);
  const [enabled, setEnabled] = useState<Status[]>(['新增', '刪除', '加碼', '減碼', '異動']);
  const [sortKey, setSortKey] = useState<SortKey>('flow');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const range = String(data?.range_days || data?.signalRangeDays || data?.days || 1);

  const { summary, focus } = useMemo(() => {
    const summary: Record<Status, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0, 異動: 0 };
    rows.forEach((r) => { summary[statusOf(r) as Status] += 1; });

    const withFlow = rows.map((r) => ({
      r,
      flow: flowBillionOf(r),
      add: addEtfCount(r),
      reduce: reduceEtfCount(r),
      status: statusOf(r),
      delta: lotsDelta(r),
    }));

    const validFlow = withFlow.filter((x) => Number.isFinite(x.flow));
    const addPoolByCount = withFlow.filter((x) => x.add > 0);
    const reducePoolByCount = withFlow.filter((x) => x.reduce > 0);
    const addPoolFallback = withFlow.filter((x) => x.status === '加碼' || x.delta > 0);
    const reducePoolFallback = withFlow.filter((x) => x.status === '減碼' || x.delta < 0);

    const mostAdd =
      [...addPoolByCount].sort((a, b) => b.add - a.add || Math.abs(b.flow || 0) - Math.abs(a.flow || 0))[0]?.r ||
      [...addPoolFallback].sort((a, b) => Math.abs(b.flow || 0) - Math.abs(a.flow || 0) || Math.abs(b.delta) - Math.abs(a.delta))[0]?.r ||
      null;

    const mostReduce =
      [...reducePoolByCount].sort((a, b) => b.reduce - a.reduce || Math.abs(b.flow || 0) - Math.abs(a.flow || 0))[0]?.r ||
      [...reducePoolFallback].sort((a, b) => Math.abs(b.flow || 0) - Math.abs(a.flow || 0) || Math.abs(b.delta) - Math.abs(a.delta))[0]?.r ||
      null;

    return {
      summary,
      focus: {
        inflow: [...validFlow].filter((x) => x.flow > 0).sort((a, b) => b.flow - a.flow)[0]?.r || null,
        outflow: [...validFlow].filter((x) => x.flow < 0).sort((a, b) => a.flow - b.flow)[0]?.r || null,
        mostAdd,
        mostReduce,
      }
    };
  }, [rows]);

  const filtered = rows.filter((r) => enabled.includes(statusOf(r) as Status));
  const sorted = useMemo(() => {
    return sortRows(filtered, (r: any) => {
      if (sortKey === 'flow') return flowBillionOf(r);
      if (sortKey === 'price') return priceOf(r);
      if (sortKey === 'pct') return changePctOf(r);
      if (sortKey === 'status') return statusOrder[statusOf(r)] || 0;
      return stockName(r);
    }, sortDir);
  }, [filtered, sortKey, sortDir]);

  function toggleSort(k: SortKey) {
    if (sortKey === k) setSortDir((d) => d === 'desc' ? 'asc' : 'desc');
    else { setSortKey(k); setSortDir('desc'); }
  }

  const fetched = data?.fetched_etf_count ?? data?.fetchedEtfCount ?? data?.complete_etf_count ?? 0;
  const total = data?.total_etf_count ?? data?.totalEtfCount ?? 0;

  return (
    <main className="page v89-page">
      <RangeTabs current={range} />

      <section className="v89-title">
        <h1>{range === '1' ? '今日訊號' : `${range}日訊號`}</h1>
        <p>已抓取 {fetched || total || 0} / {total || fetched || 0} 檔 ETF，資料日期 {shortDate(latestDateOf(data))}</p>
      </section>

      <section className="v89-focus-wrap">
        <FocusCard title="資金流入最多" item={focus.inflow} tone="red" />
        <FocusCard title="資金流出最多" item={focus.outflow} tone="green" />
        <FocusCard title="最多 ETF 加碼" item={focus.mostAdd} tone="red" />
        <FocusCard title="最多 ETF 減碼" item={focus.mostReduce} tone="green" />
      </section>

      <section className="v89-table-head"><h2>資金交易明細：共 {sorted.length} 檔</h2></section>
      <div className="v89-status-row">
        {(['新增', '刪除', '加碼', '減碼'] as Status[]).map((s) => (
          <StatusPill key={s} status={s} count={summary[s]} active={enabled.includes(s)} onClick={() => setEnabled((old) => old.includes(s) ? old.filter((x) => x !== s) : [...old, s])} />
        ))}
      </div>
      <div className="v89-sort-row">
        <SortButton label="金額" k="flow" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('flow')} />
        <SortButton label="股價" k="price" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('price')} />
        <SortButton label="漲跌幅" k="pct" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('pct')} />
        <SortButton label="狀態" k="status" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('status')} />
      </div>

      <section className="v89-dense-list">
        {sorted.slice(0, 180).map((r, i) => {
          const s = statusOf(r);
          const code = stockCode(r);
          const flow = flowBillionOf(r);
          return (
            <Link href={`/stock/${code}?from=signals`} className="v89-signal-row" key={`${code}-${i}`}>
              <div className="v89-name-cell"><b>{stockName(r)}</b><span>{code}</span></div>
              <div className="v89-num-cell"><b>{fmt(priceOf(r), 1)}</b><span className={toneClass(changePctOf(r))}>{fmtPct(changePctOf(r), 2)}</span></div>
              <div className={`v89-pill ${s}`}>{s}</div>
              <div className={flow >= 0 ? 'v89-red v89-flow' : 'v89-green v89-flow'}>{Number.isFinite(flow) ? fmtSigned(flow, 2, ' 億') : '-'}</div>
            </Link>
          );
        })}
      </section>
    </main>
  );
}
