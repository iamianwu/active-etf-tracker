'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

type AnyRow = Record<string, any>;
type SortKey = 'inflow' | 'outflow' | 'abs_amount' | 'lots' | 'buy' | 'sell' | 'price' | 'pct';
type Status = '新增' | '刪除' | '加碼' | '減碼';

const STATUSES: Status[] = ['新增', '刪除', '加碼', '減碼'];

function num(v: any, fallback = 0): number {
  if (v === null || v === undefined || v === '') return fallback;
  const x = Number(String(v).replace(/,/g, '').replace(/[^\d.-]/g, ''));
  return Number.isFinite(x) ? x : fallback;
}
function firstNum(row: AnyRow, keys: string[], fallback = 0): number {
  for (const k of keys) {
    if (row && row[k] !== undefined && row[k] !== null && row[k] !== '') {
      const v = num(row[k], NaN);
      if (Number.isFinite(v)) return v;
    }
  }
  return fallback;
}
function rowsOf(data: any): AnyRow[] {
  const src = data?.rows ?? data?.changes ?? data?.aggregate ?? data?.items ?? [];
  return Array.isArray(src) ? src : [];
}
function codeOf(row: AnyRow) { return String(row.stock_code ?? row.code ?? '').trim(); }
function nameOf(row: AnyRow) { return String(row.stock_name ?? row.name ?? row.stockName ?? codeOf(row)).trim(); }
function priceOf(row: AnyRow) {
  const v = firstNum(row, ['price', 'close_price', 'close', 'last_price'], NaN);
  return Number.isFinite(v) ? v : null;
}
function pctOf(row: AnyRow) {
  const v = firstNum(row, ['change_pct', 'pct', 'percent', 'changePercent'], NaN);
  return Number.isFinite(v) ? v : null;
}
function lotsOf(row: AnyRow) {
  return firstNum(row, ['net_lots', 'display_delta_lots', 'change_lots', 'delta_lots', 'lot_change'], 0);
}
function amountOf(row: AnyRow) {
  const direct = firstNum(row, ['net_amount_billion', 'delta_amount_billion', 'flow_billion', 'money_billion', 'amount_billion'], NaN);
  if (Number.isFinite(direct)) return direct;
  const p = priceOf(row);
  return p ? p * lotsOf(row) * 1000 / 100000000 : 0;
}
function statusOf(row: AnyRow): Status {
  const s = String(row.status ?? row.type ?? '').trim();
  if (STATUSES.includes(s as Status)) return s as Status;
  const lots = lotsOf(row);
  if (lots > 0) return '加碼';
  if (lots < 0) return '減碼';
  return '加碼';
}
function buyOf(row: AnyRow) {
  return Math.max(0, Math.round(firstNum(row, ['buy_count', 'buy_etf_count', 'add_etf_count', 'increase_count'], 0)));
}
function sellOf(row: AnyRow) {
  return Math.max(0, Math.round(firstNum(row, ['sell_count', 'sell_etf_count', 'reduce_etf_count', 'decrease_count'], 0)));
}
function mmdd(dateLike: any) {
  const s = String(dateLike ?? '').trim();
  const m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[2]}-${m[3]}`;
  return s;
}
function fmt0(v: any) {
  const x = num(v, NaN);
  if (!Number.isFinite(x)) return '-';
  return Math.round(x).toLocaleString('zh-TW');
}
function fmtPrice(v: number | null) {
  if (v === null || !Number.isFinite(v)) return '-';
  return v.toLocaleString('zh-TW', { maximumFractionDigits: v >= 100 ? 1 : 2 });
}
function fmtPct(v: number | null) {
  if (v === null || !Number.isFinite(v)) return '-';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}%`;
}
function fmtLots(v: number) {
  if (!Number.isFinite(v)) return '-';
  if (Math.abs(v) < 0.01) return '0張';
  const sign = v > 0 ? '+' : '';
  return `${sign}${Math.round(v).toLocaleString('zh-TW')}張`;
}
function fmtBillion(v: number) {
  if (!Number.isFinite(v)) return '-';
  if (Math.abs(v) < 0.005) return '0億';
  const sign = v > 0 ? '+' : '';
  const abs = Math.abs(v);
  const digits = abs >= 100 ? 1 : abs >= 10 ? 1 : 2;
  return `${sign}${v.toLocaleString('zh-TW', { maximumFractionDigits: digits })}億`;
}
function tone(v: number) { return v > 0 ? 'red' : v < 0 ? 'green' : 'muted'; }
function isLimitUp(row: AnyRow) { const p = pctOf(row); return p !== null && p >= 9.7; }
function isLimitDown(row: AnyRow) { const p = pctOf(row); return p !== null && p <= -9.7; }

function DataQuality({ data }: { data: any }) {
  const total = Number(data?.total_etf_count ?? data?.totalEtfCount ?? 0);
  const today = Number(data?.today_etf_count ?? data?.fetched_etf_count ?? data?.includedEtfCount ?? 0);
  const missing = Number(data?.non_today_etf_count ?? Math.max(0, total - today));
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';
  return (
    <div className="v112-quality">
      <div className="v112-quality-main">資料日 {date ? mmdd(date) : '-'}</div>
      <div className="v112-quality-sub">
        已取得今日資料：<b>{today}</b> / <b>{total || today}</b> 檔 ETF
        {missing > 0 ? <span className="v112-warn">未更新 {missing} 檔，本頁不混入前一日資料</span> : <span>資料完整</span>}
      </div>
    </div>
  );
}

function FocusCard({ title, row, kind }: { title: string; row?: AnyRow | null; kind: 'red' | 'green' }) {
  if (!row) {
    return <div className={`v112-focus-card ${kind}`}><div className="v112-focus-title">{title}</div><div className="v112-empty">尚無有效訊號</div></div>;
  }
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const price = priceOf(row);
  const pct = pctOf(row);
  return (
    <Link href={`/stock/${codeOf(row)}`} className={`v112-focus-card ${kind}`}>
      <div className="v112-focus-title">{title}</div>
      <div className="v112-focus-name"><span>{nameOf(row)}</span><em>{codeOf(row)}</em></div>
      <div className="v112-focus-price"><span>{fmtPrice(price)}</span><b className={tone(pct ?? 0)}>{fmtPct(pct)}</b></div>
      <div className="v112-focus-meta"><span>淨額 <b className={tone(amount)}>{fmtBillion(amount)}</b></span><span>張數 <b className={tone(lots)}>{fmtLots(lots)}</b></span><span>買賣 {buyOf(row)}:{sellOf(row)}</span></div>
    </Link>
  );
}

function SortPill({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`v112-sort-pill ${active ? 'active' : ''}`}>{label}</button>;
}
function StatusPill({ label, count, active, onClick }: { label: Status; count: number; active: boolean; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`v112-status-pill s-${label} ${active ? 'active' : ''}`}>{label} {count}</button>;
}

function SignalRow({ row }: { row: AnyRow }) {
  const code = codeOf(row);
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const pct = pctOf(row);
  const status = statusOf(row);
  return (
    <Link href={`/stock/${code}`} className="v112-row">
      <div className="v112-r-main">
        <div className="v112-r-name">{nameOf(row)}<span>{code}</span></div>
        <div className="v112-r-price"><span className={isLimitUp(row) ? 'limit-up' : isLimitDown(row) ? 'limit-down' : ''}>{fmtPrice(priceOf(row))}</span><b className={tone(pct ?? 0)}>{fmtPct(pct)}</b></div>
        <div className="v112-r-amount"><b className={tone(amount)}>{fmtBillion(amount)}</b><span className={tone(lots)}>{fmtLots(lots)}</span></div>
      </div>
      <div className="v112-r-sub">
        <span className={`v112-status s-${status}`}>{status}</span>
        <span>買賣 {buyOf(row)}:{sellOf(row)}</span>
        {isLimitUp(row) && <span className="v112-limit up">漲停</span>}
        {isLimitDown(row) && <span className="v112-limit down">跌停</span>}
      </div>
    </Link>
  );
}

export default function SignalsClient(props: any) {
  const data = props?.data ?? props ?? {};
  const sourceRows = rowsOf(data).filter((r) => STATUSES.includes(statusOf(r)) && codeOf(r));
  const [period, setPeriod] = useState<'today' | '5' | '10' | '20'>('today');
  const [selectedStatuses, setSelectedStatuses] = useState<Status[]>(['新增', '刪除', '加碼', '減碼']);
  const [sortKey, setSortKey] = useState<SortKey>('inflow');

  const statusCount = useMemo(() => {
    const out: Record<Status, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0 };
    for (const r of sourceRows) out[statusOf(r)] += 1;
    return out;
  }, [sourceRows]);

  const rows = useMemo(() => {
    const filtered = sourceRows.filter((r) => selectedStatuses.includes(statusOf(r)));
    const value = (r: AnyRow) => {
      if (sortKey === 'inflow') return amountOf(r);
      if (sortKey === 'outflow') return -amountOf(r);
      if (sortKey === 'abs_amount') return Math.abs(amountOf(r));
      if (sortKey === 'lots') return Math.abs(lotsOf(r));
      if (sortKey === 'buy') return buyOf(r);
      if (sortKey === 'sell') return sellOf(r);
      if (sortKey === 'price') return priceOf(r) ?? -Infinity;
      if (sortKey === 'pct') return pctOf(r) ?? -Infinity;
      return 0;
    };
    return [...filtered].sort((a, b) => value(b) - value(a));
  }, [sourceRows, selectedStatuses, sortKey]);

  const focus = useMemo(() => {
    const pos = sourceRows.filter((r) => amountOf(r) > 0);
    const neg = sourceRows.filter((r) => amountOf(r) < 0);
    const max = (arr: AnyRow[], fn: (r: AnyRow) => number) => arr.length ? [...arr].sort((a, b) => fn(b) - fn(a))[0] : null;
    return {
      inflow: max(pos, amountOf),
      outflow: max(neg, (r) => Math.abs(amountOf(r))),
      mostAdd: max(sourceRows.filter((r) => buyOf(r) > 0), (r) => buyOf(r) * 1000000 + Math.max(0, lotsOf(r))),
      mostReduce: max(sourceRows.filter((r) => sellOf(r) > 0), (r) => sellOf(r) * 1000000 + Math.abs(Math.min(0, lotsOf(r)))),
    };
  }, [sourceRows]);

  function toggleStatus(s: Status) {
    setSelectedStatuses((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]);
  }

  return (
    <main className="v112-signals-page">
      <section className="v112-section">
        <div className="v112-label">訊號區間</div>
        <div className="v112-segment">
          {(['today', '5', '10', '20'] as const).map((p) => (
            <button key={p} type="button" className={period === p ? 'active' : ''} onClick={() => setPeriod(p)} disabled={p !== 'today'}>
              {p === 'today' ? '今日' : `${p}日`}
            </button>
          ))}
        </div>
      </section>

      <section className="v112-section">
        <h1>今日訊號</h1>
        <DataQuality data={data} />
        <div className="v112-focus-grid">
          <FocusCard title="淨資金流入最多" row={focus.inflow} kind="red" />
          <FocusCard title="淨資金流出最多" row={focus.outflow} kind="green" />
          <FocusCard title="最多 ETF 加碼" row={focus.mostAdd} kind="red" />
          <FocusCard title="最多 ETF 減碼" row={focus.mostReduce} kind="green" />
        </div>
      </section>

      <section className="v112-section v112-list-section">
        <h2>資金交易明細：共 {fmt0(rows.length)} 檔</h2>
        <div className="v112-status-row">
          {STATUSES.map((s) => <StatusPill key={s} label={s} count={statusCount[s]} active={selectedStatuses.includes(s)} onClick={() => toggleStatus(s)} />)}
        </div>
        <div className="v112-sort-row" aria-label="排序">
          <SortPill label="淨流入" active={sortKey === 'inflow'} onClick={() => setSortKey('inflow')} />
          <SortPill label="淨流出" active={sortKey === 'outflow'} onClick={() => setSortKey('outflow')} />
          <SortPill label="絕對金額" active={sortKey === 'abs_amount'} onClick={() => setSortKey('abs_amount')} />
          <SortPill label="張數" active={sortKey === 'lots'} onClick={() => setSortKey('lots')} />
          <SortPill label="買進ETF" active={sortKey === 'buy'} onClick={() => setSortKey('buy')} />
          <SortPill label="賣出ETF" active={sortKey === 'sell'} onClick={() => setSortKey('sell')} />
          <SortPill label="股價" active={sortKey === 'price'} onClick={() => setSortKey('price')} />
          <SortPill label="漲跌幅" active={sortKey === 'pct'} onClick={() => setSortKey('pct')} />
        </div>
        <div className="v112-table-head"><span>標的</span><span>股價</span><span>淨額 / 張數</span><span>狀態 / 共識</span></div>
        <div className="v112-rows">
          {rows.length ? rows.map((row, idx) => <SignalRow row={row} key={`${codeOf(row)}-${idx}`} />) : <div className="v112-no-data">目前沒有符合篩選的今日訊號。</div>}
        </div>
      </section>
    </main>
  );
}
