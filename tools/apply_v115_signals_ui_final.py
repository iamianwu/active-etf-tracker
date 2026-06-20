#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
FRONTEND = ROOT / 'frontend'
SIGNALS_PAGE = FRONTEND / 'app' / 'signals' / 'page.tsx'
SIGNALS_CLIENT = FRONTEND / 'components' / 'SignalsClient.tsx'
GLOBALS = FRONTEND / 'app' / 'globals.css'

def backup(path: Path, tag: str = 'v115'):
    if path.exists():
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        b = path.with_name(path.name + f'.bak_{tag}_{stamp}')
        b.write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
        return b
    return None

if not FRONTEND.exists():
    raise SystemExit('❌ 找不到 frontend，請先 cd 到 active-etf-tracker-fix 專案根目錄再執行。')

backup(SIGNALS_PAGE)
backup(SIGNALS_CLIENT)
backup(GLOBALS)

SIGNALS_PAGE.write_text(r"""
import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

type SearchParams = {
  days?: string | string[];
  rangeDays?: string | string[];
  signalRangeDays?: string | string[];
};

function one(v?: string | string[]) {
  return Array.isArray(v) ? v[0] : v;
}

function normalizeSignalDays(searchParams?: SearchParams): number {
  const raw = one(searchParams?.days) || one(searchParams?.rangeDays) || one(searchParams?.signalRangeDays) || '1';
  const n = Number(raw);
  return [1, 5, 10, 20].includes(n) ? n : 1;
}

export default async function SignalsPage({ searchParams }: { searchParams?: SearchParams }) {
  const days = normalizeSignalDays(searchParams);
  const data = await apiGet(`/signals?days=${days}`);
  return <SignalsClient data={data} activeDays={days} />;
}
""".strip() + "\n", encoding='utf-8')

SIGNALS_CLIENT.write_text(r"""
'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

type AnyRow = Record<string, any>;
type Status = '新增' | '刪除' | '加碼' | '減碼';
type StatusFilter = Status | '全部';
type SortKey = 'netIn' | 'netOut' | 'absAmount' | 'lots' | 'consensus' | 'price' | 'pct';
type SortDir = 'desc' | 'asc';

const TOTAL_ACTIVE_ETFS = 27;
const STATUSES: Status[] = ['新增', '刪除', '加碼', '減碼'];
const RANGE_DAYS = [1, 5, 10, 20];

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

function firstStr(row: AnyRow, keys: string[], fallback = ''): string {
  for (const k of keys) {
    if (row && row[k] !== undefined && row[k] !== null && String(row[k]).trim() !== '') {
      return String(row[k]).trim();
    }
  }
  return fallback;
}

function rowsOf(data: any): AnyRow[] {
  const src = data?.rows ?? data?.changes ?? data?.aggregate ?? data?.items ?? [];
  return Array.isArray(src) ? src : [];
}

function codeOf(row: AnyRow): string {
  return firstStr(row, ['stock_code', 'code', 'stockCode', 'symbol']);
}

function nameOf(row: AnyRow): string {
  return firstStr(row, ['stock_name', 'name', 'stockName'], codeOf(row));
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
    'shares_change_lots',
    'shares_change',
    'delta_shares',
  ], 0);
  // 後端若給的是「股」，轉為「張」。台股 1 張 = 1000 股。
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
    'estimated_amount_billion',
  ], NaN);
  if (Number.isFinite(direct)) return direct;
  const p = priceOf(row);
  const lots = lotsOf(row);
  if (p !== null && Number.isFinite(lots)) return p * lots / 100000;
  return 0;
}

function statusOf(row: AnyRow): Status | null {
  const s = firstStr(row, ['status', 'type', 'signal_type']);
  if (STATUSES.includes(s as Status)) return s as Status;
  const lots = lotsOf(row);
  if (lots > 0) return '加碼';
  if (lots < 0) return '減碼';
  return null;
}

function buyOf(row: AnyRow): number {
  const direct = firstNum(row, ['buy_count', 'buy_etf_count', 'add_etf_count', 'increase_count', 'bull_count'], NaN);
  if (Number.isFinite(direct)) return Math.max(0, Math.round(direct));
  const s = statusOf(row);
  return s === '新增' || s === '加碼' ? 1 : 0;
}

function sellOf(row: AnyRow): number {
  const direct = firstNum(row, ['sell_count', 'sell_etf_count', 'reduce_etf_count', 'decrease_count', 'bear_count'], NaN);
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
  const missing = firstNum(data, ['non_today_etf_count', 'nonTodayEtfCount', 'missing_etf_count', 'missingEtfCount'], NaN);
  if (Number.isFinite(missing) && missing >= 0) return Math.max(0, total - Math.round(missing));
  return total;
}

function missingEtfsOf(data: any): AnyRow[] {
  const candidates = [
    data?.non_today_etfs,
    data?.nonTodayEtfs,
    data?.missing_etfs,
    data?.missingEtfs,
    data?.stale_etfs,
    data?.staleEtfs,
    data?.etf_status,
    data?.etfStatus,
  ];
  for (const c of candidates) {
    if (Array.isArray(c)) return c;
    if (c && typeof c === 'object') return Object.values(c) as AnyRow[];
  }
  return [];
}

function RangePicker({ activeDays }: { activeDays: number }) {
  return (
    <section className="signals-range-v115" aria-label="訊號區間">
      <div className="signals-range-label-v115">訊號區間</div>
      <div className="signals-range-pill-v115">
        {RANGE_DAYS.map((d) => (
          <Link key={d} href={d === 1 ? '/signals' : `/signals?days=${d}`} className={activeDays === d ? 'active' : ''}>
            {d === 1 ? '今日' : `${d}日`}
          </Link>
        ))}
      </div>
    </section>
  );
}

function DataQuality({ data, activeDays }: { data: any; activeDays: number }) {
  const [open, setOpen] = useState(false);
  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';
  const missingList = missingEtfsOf(data);

  if (activeDays !== 1) {
    return (
      <div className="signals-quality-v115">
        <div><span>資料區間</span><b>近 {activeDays} 日</b></div>
        <div><span>資料日</span><b>{mmdd(date)}</b></div>
      </div>
    );
  }

  return (
    <div className="signals-quality-v115">
      <div><span>資料日</span><b>{mmdd(date)}</b></div>
      <div><span>已取得今日資料</span><b>{today} / {total} 檔 ETF</b></div>
      {missing > 0 && (
        <button type="button" className="signals-warning-v115" onClick={() => setOpen(true)}>
          未更新 {missing} 檔，本頁不混入前一日資料 〉
        </button>
      )}
      {open && (
        <div className="signals-modal-mask-v115" onClick={() => setOpen(false)} role="presentation">
          <div className="signals-modal-v115" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <div className="signals-modal-title-v115">未更新 ETF 清單</div>
            <p className="signals-modal-desc-v115">這些 ETF 今日尚未更新，所以今日訊號不會混入它們的前一日資料。</p>
            {missingList.length > 0 ? (
              <div className="signals-missing-list-v115">
                {missingList.map((e, i) => {
                  const code = firstStr(e, ['etf_code', 'code', 'symbol'], `ETF ${i + 1}`);
                  const name = firstStr(e, ['etf_name', 'name', 'fund_name'], '');
                  const d = firstStr(e, ['latest_date', 'data_date', 'date'], '');
                  return (
                    <div className="signals-missing-row-v115" key={`${code}-${i}`}>
                      <div><b>{code}</b>{name && <span>{name}</span>}</div>
                      <em>{d ? `最新 ${mmdd(d)}` : '尚無日期'}</em>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="signals-missing-empty-v115">目前後端尚未回傳未更新 ETF 名單，只能顯示未更新檔數。</div>
            )}
            <button type="button" className="signals-modal-close-v115" onClick={() => setOpen(false)}>我知道了</button>
          </div>
        </div>
      )}
    </div>
  );
}

function FocusCard({ title, row, kind }: { title: string; row?: AnyRow | null; kind: 'red' | 'green' }) {
  if (!row) {
    return (
      <div className={`focus-card-v115 ${kind}`}>
        <div className="focus-title-v115">{title}</div>
        <div className="focus-empty-v115">尚無有效訊號</div>
      </div>
    );
  }
  const code = codeOf(row);
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const price = priceOf(row);
  const pct = pctOf(row);
  return (
    <Link href={code ? `/stock/${code}` : '#'} className={`focus-card-v115 ${kind}`}>
      <div className="focus-title-v115">{title}</div>
      <div className="focus-name-v115"><span>{nameOf(row)}</span><em>{code}</em></div>
      <div className="focus-price-v115">
        <b className={toneClass(pct ?? 0)}>{fmtPrice(price)}</b>
        <span className={toneClass(pct ?? 0)}>{fmtPct(pct)}</span>
      </div>
      <div className="focus-meta-v115">
        <span>淨額 <b className={toneClass(amount)}>{fmtBillion(amount)}</b></span>
        <span>張數 <b className={toneClass(lots)}>{fmtLots(lots)}</b></span>
        <span>買賣 <b>{buyOf(row)}:{sellOf(row)}</b></span>
      </div>
    </Link>
  );
}

function StatusChip({ label, count, active, onClick }: { label: StatusFilter; count: number; active: boolean; onClick: () => void }) {
  const cls = label === '新增' ? 'new' : label === '刪除' ? 'delete' : label === '加碼' ? 'add' : label === '減碼' ? 'reduce' : 'all';
  return (
    <button type="button" onClick={onClick} className={`status-chip-v115 ${cls} ${active ? 'active' : ''}`}>
      {label === '全部' ? '全部' : label}<b>{count}</b>
    </button>
  );
}

function SortChip({ label, sortKey, currentKey, dir, onClick }: { label: string; sortKey: SortKey; currentKey: SortKey; dir: SortDir; onClick: () => void }) {
  const active = sortKey === currentKey;
  return (
    <button type="button" onClick={onClick} className={`sort-chip-v115 ${active ? 'active' : ''}`}>
      {label}<span>{active ? (dir === 'desc' ? '▼' : '▲') : '↕'}</span>
    </button>
  );
}

function rowSortValue(row: AnyRow, key: SortKey): number {
  const amount = amountOf(row);
  if (key === 'netIn') return amount;
  if (key === 'netOut') return -amount;
  if (key === 'absAmount') return Math.abs(amount);
  if (key === 'lots') return lotsOf(row);
  if (key === 'consensus') return consensusScore(row);
  if (key === 'price') return priceOf(row) ?? -Infinity;
  if (key === 'pct') return pctOf(row) ?? -Infinity;
  return 0;
}

function SignalRow({ row }: { row: AnyRow }) {
  const code = codeOf(row);
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const price = priceOf(row);
  const pct = pctOf(row);
  const status = statusOf(row);
  const limitClass = isLimitUp(row) ? 'limit-up' : isLimitDown(row) ? 'limit-down' : '';
  return (
    <Link href={code ? `/stock/${code}` : '#'} className="signal-row-v115">
      <div className="signal-stock-v115">
        <b>{nameOf(row)}</b>
        <span>{code}</span>
      </div>
      <div className="signal-price-v115">
        <b className={limitClass}>{fmtPrice(price)}</b>
        <span className={toneClass(pct ?? 0)}>{fmtPct(pct)}</span>
      </div>
      <div className="signal-money-v115">
        <b className={toneClass(amount)}>{fmtBillion(amount)}</b>
        <span className={toneClass(lots)}>{fmtLots(lots)}</span>
      </div>
      <div className="signal-status-v115">
        {status && <b className={`status-badge-v115 ${status}`}>{status}</b>}
        <span>買賣 {buyOf(row)}:{sellOf(row)}</span>
      </div>
    </Link>
  );
}

export default function SignalsClient(props: { data: any; activeDays?: number }) {
  const data = props?.data ?? {};
  const activeDays = Number(props?.activeDays ?? data?.days ?? 1) || 1;
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('全部');
  const [sortKey, setSortKey] = useState<SortKey>('netIn');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const rawRows = useMemo(() => rowsOf(data).filter((r) => codeOf(r)), [data]);

  const counts = useMemo(() => {
    const out: Record<Status | '全部', number> = { 全部: rawRows.length, 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0 };
    rawRows.forEach((r) => {
      const s = statusOf(r);
      if (s) out[s] += 1;
    });
    return out;
  }, [rawRows]);

  const rows = useMemo(() => {
    let arr = rawRows;
    if (statusFilter !== '全部') arr = arr.filter((r) => statusOf(r) === statusFilter);
    const m = sortDir === 'desc' ? -1 : 1;
    return [...arr].sort((a, b) => {
      const av = rowSortValue(a, sortKey);
      const bv = rowSortValue(b, sortKey);
      if (av === bv) return Math.abs(amountOf(b)) - Math.abs(amountOf(a));
      return av > bv ? m : -m;
    });
  }, [rawRows, statusFilter, sortKey, sortDir]);

  const focus = useMemo(() => {
    const valid = rawRows.filter((r) => Number.isFinite(amountOf(r)) && codeOf(r));
    const inflow = valid.filter((r) => amountOf(r) > 0).sort((a, b) => amountOf(b) - amountOf(a))[0] ?? null;
    const outflow = valid.filter((r) => amountOf(r) < 0).sort((a, b) => amountOf(a) - amountOf(b))[0] ?? null;
    const add = valid.filter((r) => buyOf(r) > sellOf(r)).sort((a, b) => buyOf(b) - buyOf(a) || amountOf(b) - amountOf(a))[0] ?? null;
    const reduce = valid.filter((r) => sellOf(r) > buyOf(r)).sort((a, b) => sellOf(b) - sellOf(a) || amountOf(a) - amountOf(b))[0] ?? null;
    return { inflow, outflow, add, reduce };
  }, [rawRows]);

  function changeSort(k: SortKey) {
    if (k === sortKey) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    else {
      setSortKey(k);
      setSortDir('desc');
    }
  }

  const title = activeDays === 1 ? '今日訊號' : `近${activeDays}日訊號`;

  return (
    <main className="signals-page-v115">
      <RangePicker activeDays={activeDays} />

      <section className="signals-hero-v115">
        <h1>{title}</h1>
        <DataQuality data={data} activeDays={activeDays} />
      </section>

      <section className="focus-grid-v115">
        <FocusCard title="淨資金流入最多" row={focus.inflow} kind="red" />
        <FocusCard title="淨資金流出最多" row={focus.outflow} kind="green" />
        <FocusCard title="最多 ETF 加碼" row={focus.add} kind="red" />
        <FocusCard title="最多 ETF 減碼" row={focus.reduce} kind="green" />
      </section>

      <section className="signals-detail-v115">
        <h2>資金交易明細：共 {rows.length} 檔</h2>

        <div className="signals-chip-row-v115" aria-label="狀態篩選">
          <StatusChip label="新增" count={counts['新增']} active={statusFilter === '新增'} onClick={() => setStatusFilter(statusFilter === '新增' ? '全部' : '新增')} />
          <StatusChip label="刪除" count={counts['刪除']} active={statusFilter === '刪除'} onClick={() => setStatusFilter(statusFilter === '刪除' ? '全部' : '刪除')} />
          <StatusChip label="加碼" count={counts['加碼']} active={statusFilter === '加碼'} onClick={() => setStatusFilter(statusFilter === '加碼' ? '全部' : '加碼')} />
          <StatusChip label="減碼" count={counts['減碼']} active={statusFilter === '減碼'} onClick={() => setStatusFilter(statusFilter === '減碼' ? '全部' : '減碼')} />
        </div>

        <div className="signals-sort-row-v115" aria-label="排序">
          <SortChip label="淨流入" sortKey="netIn" currentKey={sortKey} dir={sortDir} onClick={() => changeSort('netIn')} />
          <SortChip label="淨流出" sortKey="netOut" currentKey={sortKey} dir={sortDir} onClick={() => changeSort('netOut')} />
          <SortChip label="絕對金額" sortKey="absAmount" currentKey={sortKey} dir={sortDir} onClick={() => changeSort('absAmount')} />
          <SortChip label="張數" sortKey="lots" currentKey={sortKey} dir={sortDir} onClick={() => changeSort('lots')} />
          <SortChip label="共識" sortKey="consensus" currentKey={sortKey} dir={sortDir} onClick={() => changeSort('consensus')} />
          <SortChip label="股價" sortKey="price" currentKey={sortKey} dir={sortDir} onClick={() => changeSort('price')} />
          <SortChip label="漲跌幅" sortKey="pct" currentKey={sortKey} dir={sortDir} onClick={() => changeSort('pct')} />
        </div>

        <div className="signal-table-head-v115">
          <span>標的</span>
          <span>股價</span>
          <span>淨額 / 張數</span>
          <span>狀態 / 共識</span>
        </div>

        <div className="signal-list-v115">
          {rows.length === 0 ? (
            <div className="signals-empty-v115">目前沒有符合條件的訊號。</div>
          ) : (
            rows.map((row, idx) => <SignalRow row={row} key={`${codeOf(row)}-${idx}`} />)
          )}
        </div>
      </section>
    </main>
  );
}
""".strip() + "\n", encoding='utf-8')

css_block = r"""

/* ===== V115 signals UI final cleanup ===== */
.signals-page-v115,
.signals-page-v115 * {
  box-sizing: border-box;
}

.signals-page-v115 {
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
  padding: 0 16px 48px;
  overflow-x: hidden;
}

.signals-range-v115 {
  margin: 22px 0 30px;
}

.signals-range-label-v115 {
  font-size: 22px;
  font-weight: 900;
  color: #7c8798;
  margin: 0 0 10px;
}

.signals-range-pill-v115 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  width: 100%;
  height: 54px;
  padding: 6px;
  border-radius: 999px;
  background: #eef3f9;
  border: 1px solid #dce4ef;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, .05);
}

.signals-range-pill-v115 a {
  min-width: 0;
  display: grid;
  place-items: center;
  border-radius: 999px;
  text-decoration: none;
  color: #66758a;
  font-size: 20px;
  font-weight: 900;
}

.signals-range-pill-v115 a.active {
  background: #fff;
  color: #2f6bc4;
  box-shadow: 0 4px 12px rgba(30, 64, 175, .12);
}

.signals-hero-v115 h1 {
  font-size: clamp(42px, 11vw, 64px);
  line-height: 1;
  font-weight: 1000;
  color: #121827;
  margin: 0 0 14px;
  letter-spacing: -.04em;
}

.signals-quality-v115 {
  display: grid;
  gap: 5px;
  margin: 0 0 20px;
  color: #778397;
  font-size: 20px;
  font-weight: 900;
  line-height: 1.35;
}

.signals-quality-v115 div {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.signals-quality-v115 span {
  color: #778397;
}

.signals-quality-v115 b {
  color: #172033;
}

.signals-warning-v115 {
  padding: 0;
  border: 0;
  background: transparent;
  color: #aa7624;
  text-align: left;
  font: inherit;
  font-weight: 1000;
  cursor: pointer;
}

.focus-grid-v115 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 26px;
}

.focus-card-v115 {
  min-width: 0;
  display: block;
  text-decoration: none;
  border-radius: 18px;
  padding: 18px 14px;
  border: 1.5px solid #e6edf5;
  background: #fff;
  overflow: hidden;
}

.focus-card-v115.red { background: #fff8f9; border-color: #f3c8cf; }
.focus-card-v115.green { background: #f2fffa; border-color: #bee9d8; }

.focus-title-v115 {
  color: #df5362;
  font-size: clamp(19px, 4.9vw, 25px);
  font-weight: 1000;
  margin-bottom: 12px;
  white-space: nowrap;
}
.focus-card-v115.green .focus-title-v115 { color: #28a77a; }

.focus-name-v115 {
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}

.focus-name-v115 span {
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #111827;
  font-size: clamp(22px, 6vw, 34px);
  font-weight: 1000;
}

.focus-name-v115 em {
  flex: 0 0 auto;
  font-style: normal;
  color: #8a96a8;
  font-size: clamp(16px, 4.2vw, 22px);
  font-weight: 1000;
}

.focus-price-v115 {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
  margin: 2px 0 8px;
}

.focus-price-v115 b {
  font-size: clamp(32px, 8.8vw, 46px);
  line-height: 1;
  font-weight: 1000;
}

.focus-price-v115 span {
  font-size: clamp(16px, 4.5vw, 24px);
  font-weight: 1000;
}

.focus-meta-v115 {
  display: grid;
  gap: 3px;
  color: #7b8798;
  font-size: clamp(14px, 3.8vw, 18px);
  font-weight: 1000;
  line-height: 1.25;
}

.focus-meta-v115 b { font-weight: 1000; }
.focus-empty-v115 { color: #7b8798; font-size: 18px; font-weight: 900; padding: 16px 0; }

.signals-detail-v115 h2 {
  font-size: clamp(34px, 8vw, 48px);
  line-height: 1.08;
  margin: 0 0 14px;
  color: #121827;
  font-weight: 1000;
  letter-spacing: -.04em;
}

.signals-chip-row-v115,
.signals-sort-row-v115 {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  overflow-y: hidden;
  width: 100%;
  max-width: 100%;
  padding: 0 0 10px;
  margin: 0 0 4px;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.signals-chip-row-v115::-webkit-scrollbar,
.signals-sort-row-v115::-webkit-scrollbar { display: none; }

.status-chip-v115,
.sort-chip-v115 {
  flex: 0 0 auto;
  border-radius: 999px;
  background: #fff;
  border: 2px solid #cdd6e2;
  color: #687589;
  min-height: 44px;
  padding: 0 15px;
  font-size: 18px;
  font-weight: 1000;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  white-space: nowrap;
}

.status-chip-v115 b { font-weight: 1000; }
.status-chip-v115.new { color: #b59b07; border-color: #c4aa0b; }
.status-chip-v115.delete { color: #737d8b; }
.status-chip-v115.add { color: #d95666; border-color: #d95666; }
.status-chip-v115.reduce { color: #28a77a; border-color: #28a77a; }
.status-chip-v115.active,
.sort-chip-v115.active {
  color: #2f6bc4;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.signal-table-head-v115 {
  display: grid;
  grid-template-columns: minmax(74px, 1fr) 82px 96px 78px;
  gap: 8px;
  align-items: center;
  background: #f2f5f8;
  color: #6e7a8c;
  font-size: 16px;
  font-weight: 1000;
  padding: 11px 10px;
  margin-top: 4px;
}

.signal-row-v115 {
  display: grid;
  grid-template-columns: minmax(74px, 1fr) 82px 96px 78px;
  gap: 8px;
  align-items: center;
  min-width: 0;
  width: 100%;
  color: inherit;
  text-decoration: none;
  border-bottom: 1px solid #e5edf5;
  padding: 16px 10px;
}

.signal-stock-v115,
.signal-price-v115,
.signal-money-v115,
.signal-status-v115 {
  min-width: 0;
}

.signal-stock-v115 b {
  display: block;
  color: #111827;
  font-size: clamp(20px, 5vw, 28px);
  font-weight: 1000;
  line-height: 1.05;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.signal-stock-v115 span,
.signal-price-v115 span,
.signal-money-v115 span,
.signal-status-v115 span {
  display: block;
  color: #8490a2;
  font-size: clamp(14px, 3.6vw, 19px);
  font-weight: 900;
  line-height: 1.2;
}
.signal-price-v115 b,
.signal-money-v115 b {
  display: inline-block;
  color: #111827;
  font-size: clamp(20px, 5.2vw, 30px);
  font-weight: 1000;
  line-height: 1.05;
}
.signal-money-v115,
.signal-status-v115 { text-align: right; }
.signal-status-v115 { display: grid; justify-items: end; gap: 5px; }

.status-badge-v115 {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  border-radius: 999px;
  padding: 5px 8px;
  font-size: 15px;
  font-weight: 1000;
}
.status-badge-v115.新增 { background: #fff5c7; color: #aa9400; }
.status-badge-v115.刪除 { background: #eef2f7; color: #6b7280; }
.status-badge-v115.加碼 { background: #ffe8ec; color: #d95666; }
.status-badge-v115.減碼 { background: #e5fbf1; color: #28a77a; }

.is-red { color: #d95666 !important; }
.is-green { color: #28a77a !important; }
.is-muted { color: #8490a2 !important; }
.limit-up { background: #d95666; color: #fff !important; border-radius: 8px; padding: 0 5px; }
.limit-down { background: #28a77a; color: #fff !important; border-radius: 8px; padding: 0 5px; }

.signals-empty-v115 {
  padding: 28px 12px;
  color: #7c8798;
  font-size: 18px;
  font-weight: 900;
}

.signals-modal-mask-v115 {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(15, 23, 42, .42);
  display: grid;
  place-items: center;
  padding: 18px;
}

.signals-modal-v115 {
  width: min(520px, 100%);
  max-height: min(78vh, 680px);
  overflow: auto;
  background: #fff;
  border-radius: 22px;
  padding: 22px;
  box-shadow: 0 18px 60px rgba(15, 23, 42, .24);
}

.signals-modal-title-v115 {
  color: #111827;
  font-size: 28px;
  font-weight: 1000;
  text-align: center;
  margin-bottom: 8px;
}

.signals-modal-desc-v115 {
  color: #6b7280;
  font-size: 17px;
  font-weight: 800;
  line-height: 1.5;
  margin: 0 0 16px;
}

.signals-missing-row-v115 {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid #edf2f7;
  padding: 12px 0;
}
.signals-missing-row-v115 b {
  display: block;
  font-size: 20px;
  color: #111827;
  font-weight: 1000;
}
.signals-missing-row-v115 span {
  display: block;
  color: #6f7b8e;
  font-size: 15px;
  font-weight: 800;
}
.signals-missing-row-v115 em {
  flex: 0 0 auto;
  font-style: normal;
  color: #9a6a1b;
  font-size: 14px;
  font-weight: 900;
}

.signals-missing-empty-v115 {
  color: #6b7280;
  background: #f8fafc;
  border-radius: 14px;
  padding: 14px;
  font-size: 16px;
  font-weight: 800;
}

.signals-modal-close-v115 {
  width: 100%;
  margin-top: 18px;
  border: 0;
  border-radius: 14px;
  background: #3b82f6;
  color: #fff;
  min-height: 48px;
  font-size: 18px;
  font-weight: 1000;
}

@media (max-width: 420px) {
  .signals-page-v115 { padding-left: 14px; padding-right: 14px; }
  .focus-grid-v115 { gap: 10px; }
  .focus-card-v115 { padding: 15px 12px; border-radius: 16px; }
  .signal-table-head-v115,
  .signal-row-v115 {
    grid-template-columns: minmax(72px, 1fr) 74px 90px 70px;
    gap: 7px;
    padding-left: 8px;
    padding-right: 8px;
  }
  .status-chip-v115,
  .sort-chip-v115 { min-height: 42px; padding: 0 13px; font-size: 17px; }
}
/* ===== end V115 signals UI final cleanup ===== */
"""

old_css = GLOBALS.read_text(encoding='utf-8') if GLOBALS.exists() else ''
marker_start = '/* ===== V115 signals UI final cleanup ===== */'
marker_end = '/* ===== end V115 signals UI final cleanup ===== */'
if marker_start in old_css and marker_end in old_css:
    before = old_css.split(marker_start)[0].rstrip()
    after = old_css.split(marker_end, 1)[1].lstrip()
    old_css = before + '\n' + after
GLOBALS.write_text(old_css.rstrip() + css_block + '\n', encoding='utf-8')

readme = ROOT / 'README_V115_SIGNALS_UI_FINAL.md'
readme.write_text("""# V115 Signals UI Final

修正內容：

- 移除重複的「訊號區間」，只保留一組。
- 今日訊號顯示資料完整度：已取得今日資料 x / 27 檔 ETF。
- 未更新 ETF 可點開查看清單；若後端未回傳清單，會明確提示。
- 資金交易明細改成手機不超版的表格列。
- 排序改回 ▲ / ▼ 顯示，不再使用容易誤解的 emoji。
- 排序分成「淨流入 / 淨流出 / 絕對金額 / 張數 / 共識 / 股價 / 漲跌幅」。
- 個股列可點進 `/stock/{code}`。
- 漲停 / 跌停股價會以色塊凸顯。
""", encoding='utf-8')

print('✅ V115 已完成：訊號區間、未更新清單、排序箭頭與手機版不超版排版已修正')
print('接著執行：cd frontend && npm run build')
