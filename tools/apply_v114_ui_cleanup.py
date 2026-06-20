#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import textwrap

ROOT = Path.cwd()
if not (ROOT / 'frontend').exists():
    # allow running from tools folder or one level deeper
    for p in [Path.cwd().parent, Path.cwd().parent.parent]:
        if (p / 'frontend').exists():
            ROOT = p
            break

FRONTEND = ROOT / 'frontend'
if not FRONTEND.exists():
    raise SystemExit('❌ 找不到 frontend 資料夾。請先 cd 到 active-etf-tracker-fix 專案根目錄再執行。')

signals_page = FRONTEND / 'app' / 'signals' / 'page.tsx'
signals_client = FRONTEND / 'components' / 'SignalsClient.tsx'
globals_css = FRONTEND / 'app' / 'globals.css'

for path in [signals_page, signals_client, globals_css]:
    if not path.exists():
        raise SystemExit(f'❌ 找不到 {path.relative_to(ROOT)}')


def backup(path: Path):
    bak = path.with_suffix(path.suffix + '.bak_v114')
    shutil.copy2(path, bak)
    return bak

for p in [signals_page, signals_client, globals_css]:
    backup(p)

signals_page.write_text(r"""
export const revalidate = 60;

import Link from 'next/link';
import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

const VALID_SIGNAL_DAYS = [1, 5, 10, 20] as const;
type SignalDays = typeof VALID_SIGNAL_DAYS[number];

type SearchParams = {
  days?: string | string[];
  rangeDays?: string | string[];
  signalRangeDays?: string | string[];
};

function one(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}

function normalizeSignalDays(searchParams?: SearchParams): SignalDays {
  const raw = one(searchParams?.days) || one(searchParams?.rangeDays) || one(searchParams?.signalRangeDays) || '1';
  const n = Number(raw);
  return (VALID_SIGNAL_DAYS as readonly number[]).includes(n) ? (n as SignalDays) : 1;
}

export default async function SignalsPage({ searchParams }: { searchParams?: SearchParams }) {
  const days = normalizeSignalDays(searchParams);
  const data = await apiGet(`/signals?days=${days}`);

  return (
    <main className="signals-page-v114">
      <section className="signals-range-card-v114" aria-label="訊號區間">
        <div className="signals-range-label-v114">訊號區間</div>
        <div className="signals-segment-v114">
          {VALID_SIGNAL_DAYS.map((d) => (
            <Link
              key={d}
              href={d === 1 ? '/signals' : `/signals?days=${d}`}
              className={days === d ? 'active' : ''}
              prefetch
            >
              {d === 1 ? '今日' : `${d}日`}
            </Link>
          ))}
        </div>
      </section>

      <SignalsClient data={data} activeDays={days} />
    </main>
  );
}
""".strip() + "\n", encoding='utf-8')

signals_client.write_text(r"""
'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

type AnyRow = Record<string, any>;
type Status = '新增' | '刪除' | '加碼' | '減碼';
type SortKey = 'inflow' | 'outflow' | 'absAmount' | 'lots' | 'consensus' | 'price' | 'pct';

const TOTAL_ACTIVE_ETFS = 27;
const STATUSES: Status[] = ['新增', '刪除', '加碼', '減碼'];

function num(v: any, fallback = 0): number {
  if (v === null || v === undefined || v === '') return fallback;
  const x = Number(String(v).replace(/,/g, '').replace(/[^
\d.-]/g, ''));
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

function codeOf(row: AnyRow): string {
  return String(row.stock_code ?? row.code ?? row.stockCode ?? '').trim();
}

function nameOf(row: AnyRow): string {
  return String(row.stock_name ?? row.name ?? row.stockName ?? codeOf(row)).trim();
}

function priceOf(row: AnyRow): number | null {
  const v = firstNum(row, ['price', 'close_price', 'close', 'last_price'], NaN);
  return Number.isFinite(v) ? v : null;
}

function pctOf(row: AnyRow): number | null {
  const v = firstNum(row, ['change_pct', 'pct', 'percent', 'changePercent'], NaN);
  return Number.isFinite(v) ? v : null;
}

function lotsOf(row: AnyRow): number {
  let v = firstNum(row, [
    'net_lots',
    'display_delta_lots',
    'change_lots',
    'delta_lots',
    'lot_change',
    'shares_lots_change',
    'delta_shares_lots',
    'shares_change',
    'delta_shares',
  ], 0);
  // 有些舊資料欄位是「股」，若數值過大，轉成「張」顯示。
  if (Math.abs(v) >= 100000) v = v / 1000;
  return v;
}

function amountOf(row: AnyRow): number {
  const direct = firstNum(row, [
    'net_amount_billion',
    'delta_amount_billion',
    'flow_billion',
    'money_billion',
    'amount_billion',
    'delta_value_billion',
    'trade_amount_billion',
  ], NaN);
  if (Number.isFinite(direct)) return direct;
  const p = priceOf(row);
  const lots = lotsOf(row);
  if (p !== null && Number.isFinite(lots)) return p * lots * 1000 / 100000000;
  return 0;
}

function statusOf(row: AnyRow): Status | null {
  const s = String(row.status ?? row.type ?? '').trim();
  if (STATUSES.includes(s as Status)) return s as Status;
  const lots = lotsOf(row);
  if (lots > 0) return '加碼';
  if (lots < 0) return '減碼';
  return null;
}

function buyOf(row: AnyRow): number {
  const direct = firstNum(row, ['buy_count', 'buy_etf_count', 'add_etf_count', 'increase_count'], NaN);
  if (Number.isFinite(direct)) return Math.max(0, Math.round(direct));
  const s = statusOf(row);
  return s === '新增' || s === '加碼' ? 1 : 0;
}

function sellOf(row: AnyRow): number {
  const direct = firstNum(row, ['sell_count', 'sell_etf_count', 'reduce_etf_count', 'decrease_count'], NaN);
  if (Number.isFinite(direct)) return Math.max(0, Math.round(direct));
  const s = statusOf(row);
  return s === '刪除' || s === '減碼' ? 1 : 0;
}

function consensusScore(row: AnyRow): number {
  return buyOf(row) - sellOf(row);
}

function mmdd(dateLike: any): string {
  const s = String(dateLike ?? '').trim();
  const m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[2]}-${m[3]}`;
  return s || '-';
}

function fmtPrice(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return '-';
  return v.toLocaleString('zh-TW', { maximumFractionDigits: v >= 100 ? 1 : 2 });
}

function fmtPct(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return '-';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}%`;
}

function fmt0(v: any): string {
  const x = num(v, NaN);
  if (!Number.isFinite(x)) return '-';
  return Math.round(x).toLocaleString('zh-TW');
}

function fmtLots(v: number): string {
  if (!Number.isFinite(v)) return '-';
  if (Math.abs(v) < 0.01) return '0張';
  const sign = v > 0 ? '+' : '';
  return `${sign}${Math.round(v).toLocaleString('zh-TW')}張`;
}

function fmtBillion(v: number): string {
  if (!Number.isFinite(v)) return '-';
  if (Math.abs(v) < 0.005) return '0億';
  const sign = v > 0 ? '+' : '';
  const abs = Math.abs(v);
  const digits = abs >= 100 ? 1 : abs >= 10 ? 1 : 2;
  return `${sign}${v.toLocaleString('zh-TW', { maximumFractionDigits: digits })}億`;
}

function toneClass(v: number): string {
  if (v > 0) return 'is-red';
  if (v < 0) return 'is-green';
  return 'is-muted';
}

function isLimitUp(row: AnyRow): boolean {
  const p = pctOf(row);
  return p !== null && p >= 9.7;
}

function isLimitDown(row: AnyRow): boolean {
  const p = pctOf(row);
  return p !== null && p <= -9.7;
}

function getTotalEtfs(data: any): number {
  const v = firstNum(data, ['total_etf_count', 'totalEtfCount', 'total_etfs', 'totalEtfs'], NaN);
  if (Number.isFinite(v) && v > 0) return Math.max(TOTAL_ACTIVE_ETFS, Math.round(v));
  return TOTAL_ACTIVE_ETFS;
}

function getTodayEtfs(data: any, total: number): number {
  const direct = firstNum(data, ['today_etf_count', 'todayEtfCount', 'today_etfs', 'todayEtfs', 'fetched_etf_count', 'includedEtfCount'], NaN);
  if (Number.isFinite(direct) && direct >= 0) return Math.min(total, Math.round(direct));
  const missing = firstNum(data, ['non_today_etf_count', 'nonTodayEtfCount', 'missing_etf_count'], NaN);
  if (Number.isFinite(missing) && missing >= 0) return Math.max(0, total - Math.round(missing));
  return total;
}

function DataQuality({ data, activeDays }: { data: any; activeDays: number }) {
  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';

  if (activeDays !== 1) {
    return (
      <div className="signals-quality-v114">
        <div>資料區間：近 {activeDays} 日</div>
        <div>資料日 {mmdd(date)}</div>
      </div>
    );
  }

  return (
    <div className="signals-quality-v114">
      <div>資料日 {mmdd(date)}</div>
      <div>已取得今日資料：<b>{today}</b> / {total} 檔 ETF</div>
      {missing > 0 && <div className="signals-warning-v114">未更新 {missing} 檔，本頁不混入前一日資料</div>}
    </div>
  );
}

function FocusCard({ title, row, kind }: { title: string; row?: AnyRow | null; kind: 'red' | 'green' }) {
  if (!row) {
    return (
      <div className={`focus-card-v114 ${kind}`}>
        <div className="focus-title-v114">{title}</div>
        <div className="focus-empty-v114">尚無有效訊號</div>
      </div>
    );
  }
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const price = priceOf(row);
  const pct = pctOf(row);
  return (
    <Link href={`/stock/${encodeURIComponent(codeOf(row))}`} className={`focus-card-v114 ${kind}`} prefetch>
      <div className="focus-title-v114">{title}</div>
      <div className="focus-name-v114"><span>{nameOf(row)}</span><em>{codeOf(row)}</em></div>
      <div className="focus-price-v114">
        <span>{fmtPrice(price)}</span>
        <small className={toneClass(pct ?? 0)}>{fmtPct(pct)}</small>
      </div>
      <div className="focus-meta-v114">
        <span>淨額 <b className={toneClass(amount)}>{fmtBillion(amount)}</b></span>
        <span>張數 <b className={toneClass(lots)}>{fmtLots(lots)}</b></span>
        <span>買賣 <b>{buyOf(row)}:{sellOf(row)}</b></span>
      </div>
    </Link>
  );
}

function StatusPill({ label, count, active, onClick }: { label: Status; count: number; active: boolean; onClick: () => void }) {
  return <button type="button" className={`status-pill-v114 ${active ? 'active' : ''} status-${label}`} onClick={onClick}>{label} {count}</button>;
}

function SortPill({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return <button type="button" className={`sort-pill-v114 ${active ? 'active' : ''}`} onClick={onClick}>{label}</button>;
}

function SignalRow({ row }: { row: AnyRow }) {
  const code = codeOf(row);
  const price = priceOf(row);
  const pct = pctOf(row);
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const status = statusOf(row) || '加碼';
  const limitUp = isLimitUp(row);
  const limitDown = isLimitDown(row);
  return (
    <Link href={`/stock/${encodeURIComponent(code)}`} className="signal-row-v114" prefetch>
      <div className="signal-stock-v114">
        <strong>{nameOf(row)}</strong>
        <span>{code}</span>
      </div>
      <div className="signal-price-v114">
        <strong className={limitUp ? 'limit-up-v114' : limitDown ? 'limit-down-v114' : ''}>{fmtPrice(price)}</strong>
        <span className={toneClass(pct ?? 0)}>{fmtPct(pct)}</span>
      </div>
      <div className="signal-flow-v114">
        <strong className={toneClass(amount)}>{fmtBillion(amount)}</strong>
        <span className={toneClass(lots)}>{fmtLots(lots)}</span>
      </div>
      <div className="signal-action-v114">
        <span className={`status-badge-v114 status-${status}`}>{status}</span>
        <small>買賣 {buyOf(row)}:{sellOf(row)}</small>
      </div>
    </Link>
  );
}

export default function SignalsClient(props: any) {
  const data = props?.data ?? props ?? {};
  const activeDays = Number(props?.activeDays ?? data?.days ?? 1) || 1;
  const sourceRows = rowsOf(data).filter((r) => codeOf(r) && statusOf(r));

  const [selectedStatuses, setSelectedStatuses] = useState<Status[]>(['新增', '刪除', '加碼', '減碼']);
  const [sortKey, setSortKey] = useState<SortKey>('inflow');

  const statusCount = useMemo(() => {
    const out: Record<Status, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0 };
    for (const r of sourceRows) {
      const s = statusOf(r);
      if (s) out[s] += 1;
    }
    return out;
  }, [sourceRows]);

  const rows = useMemo(() => {
    const filtered = sourceRows.filter((r) => {
      const s = statusOf(r);
      return s && selectedStatuses.includes(s);
    });
    const value = (r: AnyRow) => {
      const amount = amountOf(r);
      const lots = lotsOf(r);
      if (sortKey === 'inflow') return amount > 0 ? amount : -999999999 + amount;
      if (sortKey === 'outflow') return amount < 0 ? Math.abs(amount) : -999999999 - amount;
      if (sortKey === 'absAmount') return Math.abs(amount);
      if (sortKey === 'lots') return Math.abs(lots);
      if (sortKey === 'consensus') return Math.abs(consensusScore(r)) * 1000000 + Math.abs(lots);
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
      mostAdd: max(sourceRows.filter((r) => buyOf(r) > 0 && lotsOf(r) > 0), (r) => buyOf(r) * 1000000 + Math.max(0, lotsOf(r))),
      mostReduce: max(sourceRows.filter((r) => sellOf(r) > 0 && lotsOf(r) < 0), (r) => sellOf(r) * 1000000 + Math.abs(Math.min(0, lotsOf(r)))),
    };
  }, [sourceRows]);

  function toggleStatus(s: Status) {
    setSelectedStatuses((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]);
  }

  const title = activeDays === 1 ? '今日訊號' : `近${activeDays}日訊號`;

  return (
    <section className="signals-client-v114">
      <h1>{title}</h1>
      <DataQuality data={data} activeDays={activeDays} />

      <div className="focus-grid-v114">
        <FocusCard title="淨資金流入最多" row={focus.inflow} kind="red" />
        <FocusCard title="淨資金流出最多" row={focus.outflow} kind="green" />
        <FocusCard title="最多 ETF 加碼" row={focus.mostAdd} kind="red" />
        <FocusCard title="最多 ETF 減碼" row={focus.mostReduce} kind="green" />
      </div>

      <div className="signal-list-head-v114">
        <h2>資金交易明細：共 {fmt0(rows.length)} 檔</h2>
        <div className="status-row-v114">
          {STATUSES.map((s) => (
            <StatusPill key={s} label={s} count={statusCount[s]} active={selectedStatuses.includes(s)} onClick={() => toggleStatus(s)} />
          ))}
        </div>
        <div className="sort-row-v114" aria-label="排序">
          <SortPill label="淨流入" active={sortKey === 'inflow'} onClick={() => setSortKey('inflow')} />
          <SortPill label="淨流出" active={sortKey === 'outflow'} onClick={() => setSortKey('outflow')} />
          <SortPill label="絕對金額" active={sortKey === 'absAmount'} onClick={() => setSortKey('absAmount')} />
          <SortPill label="張數" active={sortKey === 'lots'} onClick={() => setSortKey('lots')} />
          <SortPill label="共識" active={sortKey === 'consensus'} onClick={() => setSortKey('consensus')} />
          <SortPill label="股價" active={sortKey === 'price'} onClick={() => setSortKey('price')} />
          <SortPill label="漲跌幅" active={sortKey === 'pct'} onClick={() => setSortKey('pct')} />
        </div>
      </div>

      <div className="signal-table-v114">
        <div className="signal-table-header-v114">
          <span>標的</span><span>股價</span><span>淨額 / 張數</span><span>狀態 / 共識</span>
        </div>
        {rows.length ? rows.map((row, idx) => <SignalRow key={`${codeOf(row)}-${idx}`} row={row} />) : (
          <div className="signal-empty-v114">目前沒有符合篩選的訊號。</div>
        )}
      </div>
    </section>
  );
}
""".strip() + "\n", encoding='utf-8')

css = globals_css.read_text(encoding='utf-8')
css = re.sub(r"/\* V114_UI_CLEANUP_START \*/.*?/\* V114_UI_CLEANUP_END \*/\s*", "", css, flags=re.S)
css += r"""

/* V114_UI_CLEANUP_START */
.signals-page-v114,
.signals-client-v114 {
  width: min(100%, 860px);
  margin: 0 auto;
  padding: 0 16px 36px;
  box-sizing: border-box;
}

.signals-range-card-v114 {
  margin-top: 18px;
  margin-bottom: 32px;
}

.signals-range-label-v114 {
  color: #748094;
  font-weight: 900;
  font-size: 20px;
  margin-bottom: 10px;
}

.signals-segment-v114 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  background: #edf3fa;
  border: 1px solid #d9e2ee;
  border-radius: 999px;
  padding: 6px;
  gap: 4px;
}

.signals-segment-v114 a {
  text-decoration: none;
  text-align: center;
  border-radius: 999px;
  padding: 12px 0;
  color: #66758a;
  font-weight: 900;
  font-size: 18px;
}

.signals-segment-v114 a.active {
  background: #fff;
  color: #2f6fc6;
  box-shadow: 0 2px 8px rgba(29, 59, 104, .12);
}

.signals-client-v114 h1 {
  font-size: clamp(38px, 8vw, 56px);
  line-height: 1.05;
  margin: 0 0 10px;
  color: #101828;
  letter-spacing: -0.04em;
}

.signals-quality-v114 {
  color: #758197;
  font-weight: 900;
  font-size: 18px;
  line-height: 1.45;
  margin-bottom: 18px;
}

.signals-warning-v114 {
  color: #ad7820;
}

.focus-grid-v114 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0 28px;
}

.focus-card-v114 {
  display: block;
  text-decoration: none;
  min-height: 176px;
  border-radius: 22px;
  padding: 18px 18px 16px;
  border: 1.5px solid #e9edf4;
  background: #fff;
  box-sizing: border-box;
}

.focus-card-v114.red { background: #fff8f9; border-color: #f6cbd1; }
.focus-card-v114.green { background: #f3fffa; border-color: #bfeedd; }

.focus-title-v114 {
  font-size: 21px;
  font-weight: 950;
  line-height: 1.15;
  margin-bottom: 12px;
}
.focus-card-v114.red .focus-title-v114 { color: #dc5663; }
.focus-card-v114.green .focus-title-v114 { color: #2ca678; }
.focus-name-v114 { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.focus-name-v114 span { color: #142033; font-size: 22px; font-weight: 950; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.focus-name-v114 em { color: #8a96a8; font-size: 15px; font-style: normal; font-weight: 900; }
.focus-price-v114 { margin-top: 6px; display: flex; align-items: baseline; gap: 8px; }
.focus-price-v114 span { color: #dc5663; font-size: 32px; line-height: 1; font-weight: 950; letter-spacing: -0.03em; }
.focus-price-v114 small { font-size: 17px; font-weight: 950; }
.focus-meta-v114 { margin-top: 10px; display: grid; gap: 2px; color: #748094; font-size: 15px; line-height: 1.25; font-weight: 900; }
.focus-empty-v114 { color: #7d8797; font-size: 16px; font-weight: 900; margin-top: 16px; }

.signal-list-head-v114 h2 {
  margin: 0 0 12px;
  color: #101828;
  font-size: clamp(30px, 7vw, 44px);
  line-height: 1.06;
  letter-spacing: -0.04em;
}

.status-row-v114,
.sort-row-v114 {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  padding: 2px 0 10px;
  scrollbar-width: none;
}
.status-row-v114::-webkit-scrollbar,
.sort-row-v114::-webkit-scrollbar { display: none; }

.status-pill-v114,
.sort-pill-v114 {
  white-space: nowrap;
  border: 2px solid #c8d1dd;
  color: #687589;
  background: #fff;
  border-radius: 999px;
  padding: 9px 16px;
  font-size: 17px;
  line-height: 1;
  font-weight: 950;
}
.status-pill-v114.active.status-新增 { color: #b89b00; border-color: #c8b100; background: #fffdf0; }
.status-pill-v114.active.status-刪除 { color: #697586; border-color: #aab4c2; background: #f8fafc; }
.status-pill-v114.active.status-加碼 { color: #d6515d; border-color: #df6a74; background: #fff8f9; }
.status-pill-v114.active.status-減碼 { color: #28a372; border-color: #28a372; background: #f2fff9; }
.sort-pill-v114.active { color: #2f6fc6; border-color: #c7dcff; background: #f0f6ff; }

.signal-table-v114 {
  margin-top: 8px;
  border-top: 1px solid #e4ebf3;
}

.signal-table-header-v114,
.signal-row-v114 {
  display: grid;
  grid-template-columns: 30% 20% 28% 22%;
  column-gap: 8px;
  align-items: center;
}

.signal-table-header-v114 {
  background: #f2f5f9;
  color: #617085;
  font-size: 15px;
  font-weight: 950;
  padding: 12px 14px;
  border-radius: 12px 12px 0 0;
}

.signal-row-v114 {
  min-height: 90px;
  padding: 14px;
  border-bottom: 1px solid #e4ebf3;
  text-decoration: none;
  color: inherit;
  box-sizing: border-box;
}
.signal-row-v114:active { background: #f7fbff; }

.signal-stock-v114,
.signal-price-v114,
.signal-flow-v114,
.signal-action-v114 {
  min-width: 0;
}
.signal-stock-v114 strong {
  display: block;
  color: #142033;
  font-size: 21px;
  line-height: 1.15;
  font-weight: 950;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.signal-stock-v114 span,
.signal-price-v114 span,
.signal-flow-v114 span,
.signal-action-v114 small {
  display: block;
  color: #8995a7;
  font-size: 15px;
  font-weight: 900;
  line-height: 1.25;
}
.signal-price-v114 strong,
.signal-flow-v114 strong {
  display: inline-block;
  color: #142033;
  font-size: 20px;
  line-height: 1.15;
  font-weight: 950;
  letter-spacing: -0.02em;
}
.signal-flow-v114 { text-align: right; }
.signal-action-v114 { text-align: right; }
.status-badge-v114 {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 6px 10px;
  min-width: 48px;
  font-weight: 950;
  font-size: 15px;
  line-height: 1;
  margin-bottom: 4px;
}
.status-badge-v114.status-新增 { color: #b89b00; background: #fff4b8; }
.status-badge-v114.status-刪除 { color: #697586; background: #eef2f6; }
.status-badge-v114.status-加碼 { color: #d6515d; background: #fde9ec; }
.status-badge-v114.status-減碼 { color: #28a372; background: #e4f8ef; }

.is-red { color: #dc5663 !important; }
.is-green { color: #28a372 !important; }
.is-muted { color: #8995a7 !important; }
.limit-up-v114,
.limit-down-v114 {
  color: #fff !important;
  border-radius: 8px;
  padding: 2px 7px;
}
.limit-up-v114 { background: #df5664; }
.limit-down-v114 { background: #2ca678; }
.signal-empty-v114 {
  padding: 28px 16px;
  text-align: center;
  color: #7d8797;
  font-weight: 900;
}

@media (max-width: 520px) {
  .signals-page-v114,
  .signals-client-v114 { padding-left: 16px; padding-right: 16px; }
  .signals-range-card-v114 { margin-bottom: 30px; }
  .signals-segment-v114 a { font-size: 17px; padding: 11px 0; }
  .focus-grid-v114 { gap: 10px; }
  .focus-card-v114 { min-height: 162px; padding: 14px 14px 12px; border-radius: 20px; }
  .focus-title-v114 { font-size: 19px; }
  .focus-name-v114 span { font-size: 20px; }
  .focus-price-v114 span { font-size: 30px; }
  .focus-meta-v114 { font-size: 14px; }
  .signal-table-header-v114,
  .signal-row-v114 { grid-template-columns: 29% 20% 29% 22%; column-gap: 6px; }
  .signal-table-header-v114 { font-size: 14px; padding: 10px 10px; }
  .signal-row-v114 { padding: 13px 10px; min-height: 86px; }
  .signal-stock-v114 strong { font-size: 19px; }
  .signal-price-v114 strong,
  .signal-flow-v114 strong { font-size: 18px; }
  .signal-stock-v114 span,
  .signal-price-v114 span,
  .signal-flow-v114 span,
  .signal-action-v114 small { font-size: 14px; }
  .status-badge-v114 { min-width: 44px; font-size: 14px; padding: 6px 8px; }
}
/* V114_UI_CLEANUP_END */
""" + "\n"
globals_css.write_text(css, encoding='utf-8')

readme = ROOT / 'README_V114_UI_CLEANUP.md'
readme.write_text("""# V114 UI Cleanup

本次修改：

1. 今日訊號只保留一組「訊號區間」。
2. 今日資料完整度固定顯示 27 檔總數，避免 18/18、23/23 造成誤解。
3. 未更新 ETF 會明確提示，而且今日訊號不混入前一日資料。
4. 今日訊號四張重點卡改成摘要格式。
5. 資金交易明細改成更穩定的表格列，並保留排序與狀態篩選。
6. 排序名稱改成「淨流入 / 淨流出 / 絕對金額 / 張數 / 共識 / 股價 / 漲跌幅」。
7. 每列可點擊進入個股頁。
8. 漲停 / 跌停會在股價上用色塊標示。

套用後請執行：

```bash
cd frontend
npm run build
cd ..
git add frontend/app/signals/page.tsx frontend/components/SignalsClient.tsx frontend/app/globals.css README_V114_UI_CLEANUP.md tools/apply_v114_ui_cleanup.py
git commit -m "Polish signals UI and sorting v114"
git push origin main
```
""", encoding='utf-8')

print('✅ V114 已完成：今日訊號 UI、資料完整度、排序與明細排版已重新整理')
print('接著執行：cd frontend && npm run build')
