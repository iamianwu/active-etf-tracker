#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
COMP = FRONTEND / "components"
APP = FRONTEND / "app"

if not FRONTEND.exists():
    raise SystemExit("❌ 找不到 frontend 目錄，請在 repo 根目錄執行。")
if not COMP.exists():
    raise SystemExit("❌ 找不到 frontend/components 目錄。")

def backup(path: Path, tag="v89"):
    if path.exists():
        bak = path.with_suffix(path.suffix + f".bak_{tag}")
        if not bak.exists():
            bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

def write(path: Path, content: str):
    backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"✅ wrote {path.relative_to(ROOT)}")

utils = r'''
export type SortDir = 'asc' | 'desc';

export function num(v: any, fallback = NaN): number {
  if (v === null || v === undefined || v === '') return fallback;
  const x = Number(String(v).replace(/,/g, ''));
  return Number.isFinite(x) ? x : fallback;
}

export function str(v: any, fallback = ''): string {
  return v === null || v === undefined ? fallback : String(v);
}

export function fmt(v: any, digits = 0): string {
  const x = num(v);
  if (!Number.isFinite(x)) return '-';
  return x.toLocaleString('zh-TW', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

export function fmtFree(v: any, maxDigits = 2): string {
  const x = num(v);
  if (!Number.isFinite(x)) return '-';
  return x.toLocaleString('zh-TW', { maximumFractionDigits: maxDigits });
}

export function fmtPct(v: any, digits = 2): string {
  const x = num(v);
  if (!Number.isFinite(x)) return '-';
  return `${x > 0 ? '+' : ''}${x.toFixed(digits)}%`;
}

export function fmtSigned(v: any, digits = 0, suffix = ''): string {
  const x = num(v);
  if (!Number.isFinite(x)) return '-';
  return `${x > 0 ? '+' : ''}${fmt(x, digits)}${suffix}`;
}

export function tone(v: any): 'red' | 'green' | 'flat' {
  const x = num(v, 0);
  if (x > 0) return 'red';
  if (x < 0) return 'green';
  return 'flat';
}

export function toneClass(v: any): string {
  return `v89-${tone(v)}`;
}

export function rowsOf(input: any): any[] {
  if (Array.isArray(input)) return input;
  const d = input?.data ?? input;
  const candidates = [
    d?.rows, d?.items, d?.list, d?.signals, d?.etfs, d?.holdings,
    d?.currentRows, d?.current_rows, d?.data
  ];
  for (const c of candidates) if (Array.isArray(c)) return c;
  return [];
}

export function quoteOf(input: any): any {
  const d = input?.data ?? input;
  return d?.quote || d?.stock || d?.etf || d?.summary || d || {};
}

export function stockCode(r: any): string {
  return str(r?.stock_code ?? r?.code ?? r?.symbol ?? r?.id);
}

export function stockName(r: any): string {
  return str(r?.stock_name ?? r?.name ?? r?.title ?? r?.stockName);
}

export function etfCode(r: any): string {
  return str(r?.etf_code ?? r?.code ?? r?.symbol ?? r?.id);
}

export function etfName(r: any): string {
  return str(r?.etf_name ?? r?.name ?? r?.title ?? r?.etfName);
}

export function priceOf(r: any): number {
  return num(r?.price ?? r?.close_price ?? r?.close ?? r?.last_price ?? r?.stock_price ?? r?.etf_price);
}

export function changePctOf(r: any): number {
  return num(r?.change_pct ?? r?.changePct ?? r?.pct ?? r?.pct_chg ?? r?.return_pct ?? r?.day_return ?? r?.daily_return);
}

export function volumeOf(r: any): number {
  return num(r?.volume ?? r?.trade_volume ?? r?.trading_volume);
}

export function amountBillionOf(r: any): number {
  const direct = num(r?.amount_billion ?? r?.turnover_billion ?? r?.trading_amount_billion ?? r?.value_billion);
  if (Number.isFinite(direct)) return direct;
  const raw = num(r?.amount ?? r?.turnover ?? r?.trading_amount ?? r?.value);
  return Number.isFinite(raw) ? raw / 100000000 : NaN;
}

export function marketValueBillionOf(r: any): number {
  const direct = num(
    r?.market_value_billion ??
    r?.holding_value_billion ??
    r?.holding_market_value_billion ??
    r?.value_billion ??
    r?.amount_billion
  );
  if (Number.isFinite(direct)) return direct;
  const raw = num(r?.market_value ?? r?.holding_value ?? r?.holding_market_value ?? r?.value ?? r?.amount);
  return Number.isFinite(raw) ? raw / 100000000 : NaN;
}

export function sharesLotsOf(r: any): number {
  const lots = num(r?.shares_lots ?? r?.lots ?? r?.holding_lots ?? r?.share_lots);
  if (Number.isFinite(lots)) return lots;
  const shares = num(r?.shares ?? r?.holding_shares ?? r?.share_count);
  return Number.isFinite(shares) ? shares / 1000 : NaN;
}

export function weightOf(r: any): number {
  return num(r?.weight ?? r?.holding_weight ?? r?.ratio ?? r?.percent);
}

export function latestDateOf(d: any): string {
  return str(d?.data_date ?? d?.latest_date ?? d?.latestDate ?? d?.date ?? d?.updated_date ?? d?.updated_at);
}

export function dateOf(r: any): string {
  return str(r?.data_date ?? r?.trade_date ?? r?.date ?? r?.updated_at ?? r?.created_at);
}

export function shortDate(v: any): string {
  const s = str(v);
  if (!s) return '-';
  if (s.includes('T')) return s.slice(5, 16).replace('T', ' ');
  return s.slice(5, 10) || s;
}

export function isStockCode(c: string): boolean {
  return /^[0-9]{4}$/.test(c);
}

export function directionCompare(a: any, b: any, dir: SortDir): number {
  return dir === 'asc' ? a - b : b - a;
}

export function cmpText(a: string, b: string, dir: SortDir): number {
  return dir === 'asc' ? a.localeCompare(b) : b.localeCompare(a);
}

export function sortRows<T>(rows: T[], getter: (r: T) => any, dir: SortDir): T[] {
  return [...rows].sort((a, b) => {
    const av = getter(a);
    const bv = getter(b);
    const an = num(av);
    const bn = num(bv);
    if (Number.isFinite(an) || Number.isFinite(bn)) {
      if (!Number.isFinite(an)) return 1;
      if (!Number.isFinite(bn)) return -1;
      return directionCompare(an, bn, dir);
    }
    return cmpText(str(av), str(bv), dir);
  });
}

export function statusOf(r: any): '新增' | '刪除' | '加碼' | '減碼' | '異動' {
  const st = str(r?.status ?? r?.action ?? r?.change_type);
  if (st.includes('新增')) return '新增';
  if (st.includes('刪除') || st.includes('刪')) return '刪除';
  if (st.includes('減')) return '減碼';
  if (st.includes('加')) return '加碼';

  const dv = num(r?.delta_shares ?? r?.shares_change ?? r?.delta_lots ?? r?.change_lots, 0);
  if (dv > 0) return '加碼';
  if (dv < 0) return '減碼';
  return '異動';
}

export function flowBillionOf(r: any): number {
  const direct = num(
    r?.flow_billion ??
    r?.amount_billion ??
    r?.capital_flow_billion ??
    r?.delta_amount_billion ??
    r?.net_amount_billion ??
    r?.money_billion
  );
  if (Number.isFinite(direct)) return direct;

  const raw = num(r?.flow_amount ?? r?.delta_amount ?? r?.net_amount ?? r?.market_value_change ?? r?.amount);
  if (Number.isFinite(raw)) return raw / 100000000;

  const lots = num(r?.delta_lots ?? r?.change_lots ?? r?.shares_change ?? r?.delta_shares);
  const px = priceOf(r);
  if (Number.isFinite(lots) && Number.isFinite(px)) return lots * 1000 * px / 100000000;
  return NaN;
}

export function addEtfCount(r: any): number {
  return num(r?.add_etf_count ?? r?.buy_etf_count ?? r?.etf_add_count ?? r?.positive_etf_count ?? r?.add_count ?? r?.buy_count, 0);
}

export function reduceEtfCount(r: any): number {
  return num(r?.reduce_etf_count ?? r?.sell_etf_count ?? r?.etf_reduce_count ?? r?.negative_etf_count ?? r?.reduce_count ?? r?.sell_count, 0);
}

export function etfRegion(r: any): string {
  const c = etfCode(r);
  if (c === '00986A' || c === '00998A') return '全球';
  return str(r?.region ?? r?.investment_region ?? r?.investmentRegion ?? r?.area ?? r?.market_region, '-');
}

export function trendRowsFromAny(input: any): { date: string; value: number }[] {
  const d = input?.data ?? input;
  const arr =
    d?.price_history ||
    d?.priceHistory ||
    d?.chart ||
    d?.chartRows ||
    d?.chart_rows ||
    d?.history ||
    [];
  if (!Array.isArray(arr)) return [];
  return arr
    .map((r: any, idx: number) => ({
      date: dateOf(r) || String(idx),
      value: num(r?.close_price ?? r?.price ?? r?.close ?? r?.value ?? r?.total_lots ?? r?.shares_lots),
    }))
    .filter((x) => Number.isFinite(x.value))
    .slice(-160);
}

export function allHoldingHistory(input: any): any[] {
  const d = input?.data ?? input;
  const arr =
    d?.holding_history ||
    d?.holdingHistory ||
    d?.etf_holding_history ||
    d?.etfHoldingHistory ||
    d?.history ||
    [];
  if (!Array.isArray(arr)) return [];
  return arr.filter((r: any) => etfCode(r) && Number.isFinite(sharesLotsOf(r)) && dateOf(r));
}

export function toggleFavorite(item: { code: string; name: string; type: 'etf' | 'stock' }): boolean {
  if (typeof window === 'undefined') return false;
  const key = 'active_etf_favorites_v89';
  try {
    const old = JSON.parse(window.localStorage.getItem(key) || '[]');
    const has = old.some((x: any) => x.code === item.code && x.type === item.type);
    const next = has
      ? old.filter((x: any) => !(x.code === item.code && x.type === item.type))
      : [item, ...old].slice(0, 100);
    window.localStorage.setItem(key, JSON.stringify(next));
    return !has;
  } catch {
    return false;
  }
}

export function favoriteExists(code: string, type: 'etf' | 'stock'): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const old = JSON.parse(window.localStorage.getItem('active_etf_favorites_v89') || '[]');
    return old.some((x: any) => x.code === code && x.type === type);
  } catch {
    return false;
  }
}
'''
write(COMP / "mobileV89Utils.ts", utils)

# For size, place component file strings stored in separate simple files from precomposed text chunks.
# We'll keep the implementation intentionally conservative and sort-preserving.

signals = r'''
'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import {
  rowsOf, latestDateOf, shortDate, stockCode, stockName, fmt, fmtPct, fmtSigned,
  priceOf, changePctOf, flowBillionOf, addEtfCount, reduceEtfCount,
  statusOf, sortRows, toneClass, isStockCode, type SortDir
} from './mobileV89Utils';

type Status = '新增' | '刪除' | '加碼' | '減碼' | '異動';
type SortKey = 'flow' | 'price' | 'pct' | 'status' | 'name';

const statusOrder: Record<string, number> = { 新增: 4, 加碼: 3, 減碼: 2, 刪除: 1, 異動: 0 };

function usable(r: any) {
  return isStockCode(stockCode(r)) && !!stockName(r);
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
          <span>多空共識</span><b>{addEtfCount(item)}:{reduceEtfCount(item)}</b>
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
    const withFlow = rows.map((r) => ({ r, flow: flowBillionOf(r), add: addEtfCount(r), reduce: reduceEtfCount(r) })).filter((x) => Number.isFinite(x.flow));
    return {
      summary,
      focus: {
        inflow: [...withFlow].filter((x) => x.flow > 0).sort((a, b) => b.flow - a.flow)[0]?.r || null,
        outflow: [...withFlow].filter((x) => x.flow < 0).sort((a, b) => a.flow - b.flow)[0]?.r || null,
        mostAdd: [...withFlow].filter((x) => x.add > 0).sort((a, b) => b.add - a.add || b.flow - a.flow)[0]?.r || null,
        mostReduce: [...withFlow].filter((x) => x.reduce > 0).sort((a, b) => b.reduce - a.reduce || a.flow - b.flow)[0]?.r || null,
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
        {sorted.slice(0, 160).map((r, i) => {
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
'''
write(COMP / "SignalsClient.tsx", signals)

# Use shorter but complete list/holdings/detail components
etf_list = r'''
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
'''
write(COMP / "EtfListClient.tsx", etf_list)

holdings = r'''
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
'''
write(COMP / "HoldingsClient.tsx", holdings)

# Stock and ETF detail are too long but critical; keep robust and sorting. 
stock_detail = r'''
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
'''
write(COMP / "StockDetailClient.tsx", stock_detail)

# EtfDetail simpler, sorting retained.
etf_detail = r'''
'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { rowsOf, quoteOf, etfCode, etfName, stockCode, stockName, fmtFree, fmtPct, priceOf, changePctOf, amountBillionOf, volumeOf, marketValueBillionOf, sharesLotsOf, weightOf, trendRowsFromAny, latestDateOf, shortDate, sortRows, toneClass, statusOf, fmtSigned, num, toggleFavorite, favoriteExists, type SortDir } from './mobileV89Utils';

type Tab = 'overview' | 'live' | 'operation' | 'holdings' | 'basic';
type SortKey = 'weight' | 'value' | 'shares' | 'price' | 'pct' | 'code';
function useBack() { return () => { if (typeof window !== 'undefined' && window.history.length > 1) window.history.back(); else window.location.href = '/etfs'; }; }
function SortButton({ label, k, sortKey, sortDir, onClick }: any) { const active = sortKey === k; return <button className={active ? 'active' : ''} onClick={onClick}>{label}<span>{active ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}</span></button>; }

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
      {tab === 'operation' && <section className="v89-section"><h1>操作日報</h1><div className="v89-dense-list">{(Array.isArray(changes) ? changes : []).map((r: any, i: number) => { const s=statusOf(r); const delta=num(r?.delta_lots ?? r?.change_lots ?? r?.shares_change ?? r?.delta_shares); return <Link href={`/stock/${stockCode(r)}?from=etf`} key={`${stockCode(r)}-${i}`} className="v89-signal-row"><div className="v89-name-cell"><b>{stockName(r)}</b><span>{stockCode(r)}</span></div><div className={`v89-pill ${s}`}>{s}</div><div className={delta>=0?'v89-red':'v89-green'}>{Number.isFinite(delta)?fmtSigned(delta,0,' 張'):'-'}</div><div>{fmtFree(weightOf(r),2)}%</div></Link>; })}</div></section>}
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
'''
write(COMP / "EtfDetailClient.tsx", etf_detail)

css = r'''
/* ===== V89 app-like UI with sorting ===== */
:root{--v89-blue:#2f6ecb;--v89-navy:#182032;--v89-gray:#748094;--v89-line:#e3eaf3;--v89-soft:#f5f8fc;--v89-red:#df555d;--v89-green:#27a575;--v89-yellow:#b99a00}
.v89-page,.v89-detail-page{max-width:460px;margin:0 auto;padding:14px 14px 92px;color:var(--v89-navy);background:#fff}.v89-detail-page{padding-top:0}
.v89-title h1,.v89-list-title-row h1,.v89-section h1{margin:22px 0 8px;font-size:30px;line-height:1.12;font-weight:950;letter-spacing:-.5px}.v89-title p,.v89-list-title-row p{margin:0;color:var(--v89-gray);font-size:15px;font-weight:850}
.v89-range-card{margin:18px 0}.v89-range-title{color:var(--v89-gray);font-weight:950;margin-bottom:8px;font-size:16px}.v89-segment{display:grid;background:#edf2f8;border:1px solid #dfe7f2;border-radius:999px;padding:4px}.v89-segment.four{grid-template-columns:repeat(4,1fr)}.v89-segment.compact{grid-template-columns:repeat(3,1fr);min-width:160px}.v89-segment a,.v89-segment button{display:grid;place-items:center;height:42px;border:0;border-radius:999px;background:transparent;color:#64748b;font-size:16px;font-weight:950;text-decoration:none}.v89-segment .active,.v89-segment button.active{background:#fff;color:var(--v89-blue);box-shadow:0 6px 16px rgba(30,64,120,.12)}
.v89-focus-wrap{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:14px}.v89-focus{display:block;text-decoration:none;color:inherit;border-radius:14px;border:1px solid var(--v89-line);padding:11px 12px;min-height:156px}.v89-focus.red{background:#fff8f8;border-color:#f4d0d5}.v89-focus.green{background:#f5fffb;border-color:#ccefe2}.v89-focus h3{margin:0 0 9px;font-size:16px;font-weight:950}.v89-focus.red h3{color:var(--v89-red)}.v89-focus.green h3{color:var(--v89-green)}.v89-focus-grid{display:grid;gap:7px}.v89-focus-name{font-size:17px;font-weight:950;line-height:1.15}.v89-focus-name span{margin-left:5px;color:#8994a6;font-size:13px}.v89-focus-price{margin-top:3px;font-size:25px;line-height:1.05;font-weight:950}.v89-focus-price small{font-size:13px}.v89-focus-info{display:grid;grid-template-columns:auto 1fr;gap:1px 6px;font-size:12px;font-weight:900;color:#8490a2}.v89-focus-info b{font-size:12.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.v89-empty{color:#8a95a6;font-weight:900}
.v89-table-head h2{margin:18px 0 8px;font-size:20px;font-weight:950}.v89-status-row,.v89-sort-row,.v89-range-mini{display:flex;gap:8px;overflow-x:auto;padding:0 0 8px;scrollbar-width:none}.v89-status-pill,.v89-sort-row button,.v89-range-mini button{border-radius:999px;border:2px solid #c9d2df;background:#fff;color:#657386;padding:8px 12px;font-size:15px;font-weight:950;white-space:nowrap}.v89-sort-row button span{margin-left:4px;color:#9aa5b4}.v89-sort-row button.active,.v89-range-mini button.active{color:var(--v89-blue);border-color:#c9dcff;background:#edf5ff}.v89-status-pill.新增.active{color:#b19700;border-color:#c7a900;background:#fffdf1}.v89-status-pill.刪除.active{color:#667386;border-color:#aab3bf;background:#f8fafc}.v89-status-pill.加碼.active{color:var(--v89-red);border-color:var(--v89-red);background:#fff5f6}.v89-status-pill.減碼.active{color:var(--v89-green);border-color:var(--v89-green);background:#f2fff9}
.v89-dense-list{display:grid;gap:0}.v89-signal-row{display:grid;grid-template-columns:minmax(86px,1fr) 76px 58px 82px;align-items:center;gap:6px;min-height:66px;padding:9px 4px;color:inherit;text-decoration:none;border-bottom:1px solid var(--v89-line)}.v89-name-cell b{display:block;font-size:17px;line-height:1.15;font-weight:950}.v89-name-cell span,.v89-num-cell span{display:block;color:#8a95a6;font-size:13px;font-weight:850}.v89-num-cell b{display:block;font-size:18px;font-weight:950}.v89-pill{justify-self:center;padding:4px 9px;border-radius:999px;font-size:13px;font-weight:950;background:#eef2f7}.v89-pill.新增{color:#b19700;background:#fff6c8}.v89-pill.加碼{color:var(--v89-red);background:#ffecee}.v89-pill.減碼{color:var(--v89-green);background:#e9fbf4}.v89-pill.刪除{color:#4b5563;background:#eef2f7}.v89-flow{text-align:right;font-size:13px;font-weight:950}
.v89-red{color:var(--v89-red)!important}.v89-green{color:var(--v89-green)!important}.v89-flat{color:#6f7a89!important}
.v89-list-title-row{display:flex;align-items:flex-end;justify-content:space-between;gap:10px}.v89-search-filter{display:flex;gap:8px;margin:12px 0 10px}.v89-search-filter button{border:1px solid var(--v89-line);background:#fff;border-radius:12px;padding:0 12px;font-weight:950;color:var(--v89-blue)}.v89-search-filter input{min-width:0;flex:1;height:44px;border:0;border-radius:14px;background:#f0f4f9;padding:0 14px;color:var(--v89-navy);font-size:15px;font-weight:850;outline:none}.v89-etf-cards,.v89-holding-cards{display:grid;gap:10px}
.v89-etf-card{display:grid;grid-template-columns:6px 1fr;gap:10px;padding:11px 12px;border:1px solid var(--v89-line);border-radius:14px;text-decoration:none;color:inherit;box-shadow:0 2px 10px rgba(15,23,42,.04)}.v89-side-line{border-radius:999px}.v89-side-line.red{background:var(--v89-red)}.v89-side-line.green{background:var(--v89-green)}.v89-etf-top{display:grid;grid-template-columns:minmax(0,1fr) 84px;gap:10px}.v89-etf-top b{display:block;font-size:21px;line-height:1.05;font-weight:950}.v89-etf-top span{display:block;margin-top:4px;color:#5e6878;font-size:13px;font-weight:850}.v89-etf-top strong{display:block;color:var(--v89-blue);text-align:right;font-size:20px;font-weight:950}.v89-etf-top em{display:block;margin-top:2px;text-align:right;font-style:normal;font-size:13px;font-weight:950}.v89-etf-meta{display:grid;gap:6px;margin-top:10px}.v89-etf-meta.three{grid-template-columns:repeat(3,1fr)}.v89-etf-meta span{color:#7d8796;font-size:12px;font-weight:850}.v89-etf-meta b{display:block;margin-top:2px;color:var(--v89-navy);font-size:13px;font-weight:950}.v89-data-badges{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}.v89-data-badges span{padding:4px 8px;border-radius:999px;font-size:12px;font-weight:950}.v89-data-badges .ok{color:var(--v89-blue);background:#edf5ff}.v89-data-badges .miss{color:#8994a6;background:#f1f5f9}
.v89-stock-card{display:grid;grid-template-columns:minmax(0,1fr) 82px 104px;gap:8px;align-items:center;padding:13px 14px;border:1px solid var(--v89-line);border-radius:14px;color:inherit;text-decoration:none}.v89-stock-card b{display:block;font-size:20px;line-height:1.1;font-weight:950}.v89-stock-card span,.v89-stock-card small{display:block;color:#6f7a89;font-size:13px;font-weight:850}.v89-stock-card strong{display:block;text-align:right;font-size:21px;font-weight:950}.v89-stock-card em{display:block;font-style:normal;text-align:right;font-size:13px;font-weight:950}.v89-stock-card div:last-child{text-align:right}
.v89-detail-header{position:sticky;top:0;z-index:30;display:grid;grid-template-columns:48px 1fr 48px;align-items:center;min-height:74px;background:rgba(255,255,255,.97);backdrop-filter:blur(10px);border-bottom:1px solid var(--v89-line)}.v89-detail-header button{border:0;background:transparent;color:#0085ff;font-size:38px;line-height:1;font-weight:900}.v89-detail-header .star{font-size:34px;color:#0a84ff}.v89-detail-header div{text-align:center;min-width:0}.v89-detail-header b{display:block;font-size:26px;font-weight:950;line-height:1.05}.v89-detail-header span{display:block;color:#6f7a89;font-size:16px;font-weight:900;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}.v89-detail-tabs{position:sticky;top:74px;z-index:29;display:grid;grid-template-columns:repeat(4,1fr);margin:0 -14px 18px;background:rgba(255,255,255,.97);border-bottom:1px solid var(--v89-line)}.v89-detail-tabs.five{grid-template-columns:repeat(5,1fr)}.v89-detail-tabs button{height:48px;border:0;border-bottom:3px solid transparent;background:transparent;color:#5f6978;font-size:14px;font-weight:950}.v89-detail-tabs button.active{color:var(--v89-blue);border-bottom-color:var(--v89-blue)}
.v89-section h1{font-size:29px;margin-top:20px}.v89-section h2{margin:22px 0 10px;font-size:24px;line-height:1.15;font-weight:950}.v89-stock-quote{display:grid;grid-template-columns:1fr 1fr;gap:12px}.v89-stock-quote>div,.v89-kpi-grid>div,.v89-info-card,.v89-chart-box,.v89-insight,.v89-rank-card{border:1px solid var(--v89-line);border-radius:14px;background:#fff;padding:14px;box-shadow:0 2px 10px rgba(15,23,42,.03)}.v89-stock-quote span,.v89-kpi-grid span,.v89-info-card span{display:block;color:#6f7a89;font-size:13px;font-weight:950}.v89-stock-quote b,.v89-kpi-grid b{display:block;margin-top:8px;font-size:25px;line-height:1.05;font-weight:950}.v89-stock-quote small,.v89-kpi-grid small{display:block;margin-top:4px;color:#7d8796;font-size:12px;font-weight:850}.v89-kpi-grid{display:grid;gap:10px}.v89-kpi-grid.four{grid-template-columns:repeat(2,1fr)}.v89-insight{margin-top:12px;background:#fff8f8;border-color:#f4d0d5}.v89-insight.green{background:#f5fffb;border-color:#ccefe2}.v89-insight b{display:block;color:var(--v89-red);font-size:17px;font-weight:950}.v89-insight.green b{color:var(--v89-green)}.v89-insight span{display:block;margin-top:5px;color:#6f7a89;font-size:14px;font-weight:900}.v89-chart-box{padding:10px}.v89-empty-box{padding:24px 12px;text-align:center;border:1px dashed #d2dbe8;border-radius:14px;background:#f8fafc;color:#7d8796;font-weight:900}.v89-empty-box.small{padding:12px}
.v89-etf-holding-list{display:grid}.v89-etf-holding-row{display:grid;grid-template-columns:minmax(84px,1fr) 98px 66px 66px;gap:7px;align-items:center;min-height:70px;padding:10px 0;color:inherit;text-decoration:none;border-bottom:1px solid var(--v89-line)}.v89-etf-holding-row b{display:block;font-size:16.5px;line-height:1.15;font-weight:950}.v89-etf-holding-row span{display:block;color:#8a95a6;font-size:12.5px;font-weight:850}.v89-rank-card{margin-bottom:14px}.v89-rank-card h2{margin:0 0 12px;color:var(--v89-red);font-size:22px}.v89-rank-card.green h2{color:var(--v89-green)}.v89-rank-item{display:grid;grid-template-columns:28px 1fr 82px;gap:8px;align-items:center;min-height:42px;color:inherit;text-decoration:none;border-bottom:1px solid var(--v89-line)}.v89-rank-item:last-child{border-bottom:0}.v89-rank-item>span{width:22px;height:22px;display:grid;place-items:center;border-radius:999px;background:#f1f5f9;color:var(--v89-red);font-size:13px;font-weight:950}.v89-rank-card.green .v89-rank-item>span{color:var(--v89-green)}.v89-rank-item b{font-size:15px;font-weight:950}.v89-rank-item small{margin-left:5px;color:#7d8796;font-size:13px;font-weight:850}.v89-rank-item strong{text-align:right;color:var(--v89-red);font-size:14px;font-weight:950}.v89-rank-card.green .v89-rank-item strong{color:var(--v89-green)}.v89-info-card{display:grid;gap:0}.v89-info-card p{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:0;padding:12px 0;border-bottom:1px solid var(--v89-line)}.v89-info-card p:last-child{border-bottom:0}.v89-info-card b{text-align:right;font-weight:950}.v89-sort-row.sticky{position:sticky;top:122px;z-index:20;background:#fff;padding-top:6px}
@media(max-width:390px){.v89-focus-wrap{grid-template-columns:1fr}.v89-signal-row{grid-template-columns:minmax(78px,1fr) 72px 56px 72px}.v89-etf-holding-row{grid-template-columns:minmax(76px,1fr) 86px 58px 58px}}
'''

css_path = APP / "globals.css"
old = css_path.read_text(encoding="utf-8")
if "V89 app-like UI with sorting" not in old:
    backup(css_path)
    css_path.write_text(old + "\n\n" + css, encoding="utf-8")
    print("✅ appended V89 CSS")
else:
    print("ℹ️ V89 CSS already exists")

readme = r'''
# V89 App-like UI with Sorting

這版目標是更接近設計稿，但保留排序能力：

- 今日訊號：單一區間切換、四張摘要卡、狀態篩選、排序列
- ETF 列表：卡片式，但保留排序：漲跌幅 / 股價 / 成交額 / 規模 / 報酬 / 費用
- 資金持股：卡片式，但保留排序：市值 / ETF檔數 / 股價 / 漲跌幅
- ETF 詳情：總覽 / 即時 / 操作日報 / 成分股 / 基本，成分股可排序
- 個股詳情：ETF大戶持股追蹤，含總覽、ETF持股變化、加減碼排行、持股明細排序

注意：需要後端提供 holding_history 才能完整呈現「各 ETF 持股張數變化」。
'''
write(ROOT / "README_APP_LIKE_SORTING_V89.md", readme)

print("\n✅ V89 已套用。請執行：")
print("cd frontend")
print("[ -d node_modules ] || npm install")
print("npm run build")
