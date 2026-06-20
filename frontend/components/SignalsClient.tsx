'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useMemo, useState } from 'react';

type AnyRow = Record<string, any>;
type Status = '新增' | '刪除' | '加碼' | '減碼';
type SortKey = 'netIn' | 'netOut' | 'absAmount' | 'lots' | 'consensus' | 'price' | 'pct' | 'name';
type SortDir = 'asc' | 'desc';

const TOTAL_ACTIVE_ETFS = 27;
const RANGE_OPTIONS = [
  { days: 1, label: '今日' },
  { days: 5, label: '5日' },
  { days: 10, label: '10日' },
  { days: 20, label: '20日' },
];
const STATUSES: Status[] = ['新增', '刪除', '加碼', '減碼'];

function num(v: any, fallback = 0): number {
  if (v === null || v === undefined || v === '') return fallback;
  const x = Number(String(v).replace(/,/g, '').replace(/[^\d.-]/g, ''));
  return Number.isFinite(x) ? x : fallback;
}

function firstNum(row: AnyRow | undefined | null, keys: string[], fallback = 0): number {
  for (const k of keys) {
    if (row && row[k] !== undefined && row[k] !== null && row[k] !== '') {
      const v = num(row[k], NaN);
      if (Number.isFinite(v)) return v;
    }
  }
  return fallback;
}

function rowsOf(data: any): AnyRow[] {
  const src = data?.rows ?? data?.changes ?? data?.aggregate ?? data?.items ?? data?.signals ?? [];
  return Array.isArray(src) ? src : [];
}

function isNormalStockCode(code: string): boolean {
  return /^\d{4}$/.test(String(code || '').trim());
}

function codeOf(row: AnyRow): string {
  return String(row.stock_code ?? row.code ?? row.stockCode ?? row.ticker ?? '').trim();
}

function nameOf(row: AnyRow): string {
  return String(row.stock_name ?? row.name ?? row.stockName ?? row.security_name ?? codeOf(row)).trim();
}

function priceOf(row: AnyRow): number | null {
  const v = firstNum(row, ['price', 'close_price', 'close', 'last_price', 'stock_price'], NaN);
  return Number.isFinite(v) ? v : null;
}

function pctOf(row: AnyRow): number | null {
  const v = firstNum(row, ['change_pct', 'pct', 'percent', 'changePercent', 'price_change_pct'], NaN);
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
    'net_value_billion',
  ], NaN);
  if (Number.isFinite(direct)) return direct;
  const p = priceOf(row);
  const lots = lotsOf(row);
  if (p !== null && Number.isFinite(lots)) return p * lots * 1000 / 100000000;
  return 0;
}

function statusOf(row: AnyRow): Status | null {
  const raw = String(row.status ?? row.type ?? row.action ?? '').trim();
  if (STATUSES.includes(raw as Status)) return raw as Status;
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
  const digits = abs >= 10 ? 1 : 2;
  return `${sign}${v.toLocaleString('zh-TW', { maximumFractionDigits: digits })}億`;
}

function toneClass(v: number | null | undefined): string {
  const x = Number(v ?? 0);
  if (x > 0) return 'is-red';
  if (x < 0) return 'is-green';
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

function getMissingEtfs(data: any): AnyRow[] {
  const keys = ['non_today_etfs', 'nonTodayEtfs', 'missing_etfs', 'missingEtfs', 'stale_etfs', 'staleEtfs'];
  for (const k of keys) {
    const v = data?.[k];
    if (Array.isArray(v)) {
      return v.map((x) => typeof x === 'string' ? { etf_code: x } : x).filter(Boolean);
    }
  }
  return [];
}

function statusCounts(rows: AnyRow[]) {
  const out: Record<Status, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0 };
  for (const r of rows) {
    const s = statusOf(r);
    if (s) out[s] += 1;
  }
  return out;
}

function rowScore(row: AnyRow, sortKey: SortKey): number | string {
  if (sortKey === 'netIn' || sortKey === 'netOut' || sortKey === 'absAmount') return amountOf(row);
  if (sortKey === 'lots') return lotsOf(row);
  if (sortKey === 'consensus') return consensusScore(row);
  if (sortKey === 'price') return priceOf(row) ?? -Infinity;
  if (sortKey === 'pct') return pctOf(row) ?? -Infinity;
  return `${codeOf(row)} ${nameOf(row)}`;
}

function sortRows(rows: AnyRow[], sortKey: SortKey, sortDir: SortDir): AnyRow[] {
  const base = [...rows];
  base.sort((a, b) => {
    let av: number | string = rowScore(a, sortKey);
    let bv: number | string = rowScore(b, sortKey);

    if (sortKey === 'absAmount') {
      av = Math.abs(Number(av));
      bv = Math.abs(Number(bv));
    }
    if (sortKey === 'netOut') {
      av = -Number(av);
      bv = -Number(bv);
    }

    let result = 0;
    if (typeof av === 'string' || typeof bv === 'string') {
      result = String(av).localeCompare(String(bv), 'zh-Hant');
    } else {
      result = Number(bv) - Number(av);
    }
    return sortDir === 'desc' ? result : -result;
  });
  return base;
}

function pickMax(rows: AnyRow[], predicate: (r: AnyRow) => boolean, score: (r: AnyRow) => number): AnyRow | null {
  let best: AnyRow | null = null;
  let bestScore = -Infinity;
  for (const r of rows) {
    if (!predicate(r)) continue;
    const s = score(r);
    if (Number.isFinite(s) && s > bestScore) {
      best = r;
      bestScore = s;
    }
  }
  return best;
}

function RangeSwitch({ activeDays }: { activeDays: number }) {
  const pathname = usePathname() || '/';
  const base = pathname === '/signals' ? '/signals' : '/';
  const hrefFor = (days: number) => days === 1 ? base : `${base}?days=${days}`;

  return (
    <section className="signals-range-v117" aria-label="訊號區間">
      <div className="signals-section-label-v117">訊號區間</div>
      <div className="signals-range-tabs-v117">
        {RANGE_OPTIONS.map((opt) => (
          <Link key={opt.days} className={activeDays === opt.days ? 'is-active' : ''} href={hrefFor(opt.days)}>
            {opt.label}
          </Link>
        ))}
      </div>
    </section>
  );
}

function MissingModal({ data, onClose }: { data: any; onClose: () => void }) {
  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const list = getMissingEtfs(data);
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';
  return (
    <div className="signals-modal-mask-v117" role="dialog" aria-modal="true">
      <div className="signals-modal-v117">
        <button className="signals-modal-close-v117" onClick={onClose} aria-label="關閉">×</button>
        <h3>未更新 ETF 清單</h3>
        <p>今日訊號只使用 {mmdd(date)} 當日資料，不混入前一日資料。</p>
        <div className="signals-modal-count-v117">已取得 {today} / {total} 檔，未更新 {missing} 檔</div>
        {list.length > 0 ? (
          <div className="signals-missing-list-v117">
            {list.map((x, idx) => {
              const code = String(x.etf_code ?? x.code ?? x.etfCode ?? '').trim() || `ETF ${idx + 1}`;
              const name = String(x.etf_name ?? x.name ?? x.etfName ?? '').trim();
              const d = x.latest_date ?? x.data_date ?? x.date ?? '';
              return (
                <div key={`${code}-${idx}`} className="signals-missing-item-v117">
                  <b>{code}</b>
                  {name && <span>{name}</span>}
                  <em>{d ? `最新 ${mmdd(d)}` : '尚無日期'}</em>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="signals-modal-note-v117">目前 API 只回傳未更新數量，尚未回傳 ETF 代號清單；所以這裡不再顯示 ETF 1、ETF 2 這種假資料。</div>
        )}
        <button className="signals-modal-ok-v117" onClick={onClose}>我知道了</button>
      </div>
    </div>
  );
}

function DataQuality({ data, activeDays }: { data: any; activeDays: number }) {
  const [open, setOpen] = useState(false);
  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';

  if (activeDays !== 1) {
    return (
      <div className="signals-quality-v117">
        <span>資料區間 近 {activeDays} 日</span>
        <span>資料日 {mmdd(date)}</span>
      </div>
    );
  }

  return (
    <>
      <div className="signals-quality-v117">
        <span>資料日 <b>{mmdd(date)}</b></span>
        <span>已取得今日資料 <b>{today} / {total}</b> 檔 ETF</span>
        {missing > 0 && (
          <button type="button" className="signals-missing-btn-v117" onClick={() => setOpen(true)}>
            未更新 {missing} 檔，查看清單
          </button>
        )}
      </div>
      {open && <MissingModal data={data} onClose={() => setOpen(false)} />}
    </>
  );
}

function FocusCard({ title, row, tone }: { title: string; row: AnyRow | null; tone: 'red' | 'green' }) {
  if (!row) {
    return (
      <div className={`signals-focus-card-v117 ${tone}`}>
        <div className="signals-focus-title-v117">{title}</div>
        <div className="signals-focus-empty-v117">尚無有效訊號</div>
      </div>
    );
  }
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const price = priceOf(row);
  const pct = pctOf(row);
  const code = codeOf(row);
  return (
    <Link href={`/stock/${code}`} className={`signals-focus-card-v117 ${tone}`}>
      <div className="signals-focus-title-v117">{title}</div>
      <div className="signals-focus-stock-v117">
        <b>{nameOf(row)}</b>
        <span>{code}</span>
      </div>
      <div className="signals-focus-price-v117">
        <strong className={toneClass(pct)}>{fmtPrice(price)}</strong>
        <span className={toneClass(pct)}>{fmtPct(pct)}</span>
      </div>
      <div className="signals-focus-meta-v117">
        <span>淨額 <b className={toneClass(amount)}>{fmtBillion(amount)}</b></span>
        <span>張數 <b className={toneClass(lots)}>{fmtLots(lots)}</b></span>
        <span>買賣 <b>{buyOf(row)}:{sellOf(row)}</b></span>
      </div>
    </Link>
  );
}

function SummaryGrid({ rows }: { rows: AnyRow[] }) {
  const netIn = pickMax(rows, (r) => amountOf(r) > 0, (r) => amountOf(r));
  const netOut = pickMax(rows, (r) => amountOf(r) < 0, (r) => Math.abs(amountOf(r)));
  const mostAdd = pickMax(rows, (r) => buyOf(r) > 0, (r) => buyOf(r));
  const mostReduce = pickMax(rows, (r) => sellOf(r) > 0, (r) => sellOf(r));
  return (
    <div className="signals-focus-grid-v117">
      <FocusCard title="淨資金流入最多" row={netIn} tone="red" />
      <FocusCard title="淨資金流出最多" row={netOut} tone="green" />
      <FocusCard title="最多 ETF 加碼" row={mostAdd} tone="red" />
      <FocusCard title="最多 ETF 減碼" row={mostReduce} tone="green" />
    </div>
  );
}

function SortLabel({ label, active, dir, onClick }: { label: string; active: boolean; dir: SortDir; onClick: () => void }) {
  return (
    <button type="button" className={active ? 'is-active' : ''} onClick={onClick}>
      <span>{label}</span>
      <b>{active ? (dir === 'desc' ? '▼' : '▲') : '↕'}</b>
    </button>
  );
}

function StatusChip({ status }: { status: Status | null }) {
  const cls = status === '新增' ? 'new' : status === '刪除' ? 'delete' : status === '加碼' ? 'add' : status === '減碼' ? 'reduce' : 'neutral';
  return <span className={`signals-status-v117 ${cls}`}>{status ?? '-'}</span>;
}

function DetailRow({ row }: { row: AnyRow }) {
  const code = codeOf(row);
  const price = priceOf(row);
  const pct = pctOf(row);
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const status = statusOf(row);
  const limit = isLimitUp(row) ? '漲停' : isLimitDown(row) ? '跌停' : '';

  return (
    <Link className="signals-table-row-v117" href={`/stock/${code}`}>
      <div className="signals-cell-stock-v117">
        <b>{nameOf(row)}</b>
        <span>{code}</span>
      </div>
      <div className="signals-cell-price-v117">
        <strong className={limit ? 'is-limit' : ''}>{fmtPrice(price)}</strong>
        <span className={toneClass(pct)}>{fmtPct(pct)}</span>
        {limit && <em className={isLimitUp(row) ? 'limit-up' : 'limit-down'}>{limit}</em>}
      </div>
      <div className="signals-cell-flow-v117">
        <strong className={toneClass(amount)}>{fmtBillion(amount)}</strong>
        <span className={toneClass(lots)}>{fmtLots(lots)}</span>
      </div>
      <div className="signals-cell-status-v117">
        <StatusChip status={status} />
        <span>買賣 {buyOf(row)}:{sellOf(row)}</span>
      </div>
    </Link>
  );
}

function SignalsTable({ rows }: { rows: AnyRow[] }) {
  const [sortKey, setSortKey] = useState<SortKey>('netIn');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const counts = statusCounts(rows);

  function changeSort(next: SortKey) {
    if (sortKey === next) setSortDir((d) => d === 'desc' ? 'asc' : 'desc');
    else {
      setSortKey(next);
      setSortDir('desc');
    }
  }

  const shown = useMemo(() => sortRows(rows, sortKey, sortDir), [rows, sortKey, sortDir]);

  return (
    <section className="signals-detail-v117">
      <h2>資金交易明細：共 {rows.length} 檔</h2>
      <div className="signals-counts-v117">
        <span className="new">新增 {counts['新增']}</span>
        <span className="delete">刪除 {counts['刪除']}</span>
        <span className="add">加碼 {counts['加碼']}</span>
        <span className="reduce">減碼 {counts['減碼']}</span>
      </div>
      <div className="signals-sortbar-v117" aria-label="排序">
        <SortLabel label="淨流入" active={sortKey === 'netIn'} dir={sortDir} onClick={() => changeSort('netIn')} />
        <SortLabel label="淨流出" active={sortKey === 'netOut'} dir={sortDir} onClick={() => changeSort('netOut')} />
        <SortLabel label="絕對金額" active={sortKey === 'absAmount'} dir={sortDir} onClick={() => changeSort('absAmount')} />
        <SortLabel label="張數" active={sortKey === 'lots'} dir={sortDir} onClick={() => changeSort('lots')} />
        <SortLabel label="共識" active={sortKey === 'consensus'} dir={sortDir} onClick={() => changeSort('consensus')} />
        <SortLabel label="股價" active={sortKey === 'price'} dir={sortDir} onClick={() => changeSort('price')} />
      </div>
      <div className="signals-table-v117">
        <div className="signals-table-head-v117">
          <button onClick={() => changeSort('name')}>標的 {sortKey === 'name' ? (sortDir === 'desc' ? '▼' : '▲') : '↕'}</button>
          <button onClick={() => changeSort('price')}>股價 {sortKey === 'price' ? (sortDir === 'desc' ? '▼' : '▲') : '↕'}</button>
          <button onClick={() => changeSort(sortKey === 'lots' ? 'absAmount' : 'lots')}>淨額 / 張數 ↕</button>
          <button onClick={() => changeSort('consensus')}>狀態 / 共識 {sortKey === 'consensus' ? (sortDir === 'desc' ? '▼' : '▲') : '↕'}</button>
        </div>
        {shown.length > 0 ? shown.map((row, idx) => <DetailRow key={`${codeOf(row)}-${idx}`} row={row} />) : <div className="signals-empty-v117">目前沒有符合條件的訊號。</div>}
      </div>
    </section>
  );
}

export default function SignalsClient(props: { data: any; activeDays?: number }) {
  const data = props.data ?? {};
  const activeDays = Number(props.activeDays ?? data?.days ?? 1) || 1;
  const rawRows = rowsOf(data);
  const rows = useMemo(() => rawRows.filter((r) => isNormalStockCode(codeOf(r))), [rawRows]);

  return (
    <main className="signals-page-v117">
      <RangeSwitch activeDays={activeDays} />
      <header className="signals-title-v117">
        <h1>{activeDays === 1 ? '今日訊號' : `近${activeDays}日訊號`}</h1>
        <DataQuality data={data} activeDays={activeDays} />
      </header>
      <SummaryGrid rows={rows} />
      <SignalsTable rows={rows} />
    </main>
  );
}
