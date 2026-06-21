'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import styles from './SignalsClient.module.css';

type RawRow = Record<string, unknown>;
type Status = '新增' | '刪除' | '加碼' | '減碼';
type StatusFilter = '全部' | Status;
type SortKey = 'inflow' | 'outflow' | 'absoluteAmount' | 'lots' | 'price' | 'changePct';
type SortDirection = 'asc' | 'desc';
type LimitState = 'up' | 'down' | null;

type Signal = {
  code: string;
  name: string;
  price: number | null;
  changePct: number | null;
  amount: number;
  lots: number;
  status: Status;
  buyCount: number;
  sellCount: number;
  dataDate: string;
  limitState: LimitState;
};

type MissingEtf = {
  code: string;
  name: string;
  lastDate: string;
};

type SortState = {
  key: SortKey;
  direction: SortDirection;
};

const ACTIVE_ETF_TOTAL = 27;
const STATUSES: Status[] = ['新增', '刪除', '加碼', '減碼'];
const RANGE_OPTIONS = [1, 5, 10, 20];

const SORT_OPTIONS: Array<{ key: SortKey; label: string }> = [
  { key: 'inflow', label: '淨流入' },
  { key: 'outflow', label: '淨流出' },
  { key: 'absoluteAmount', label: '絕對金額' },
  { key: 'lots', label: '張數' },
  { key: 'price', label: '股價' },
  { key: 'changePct', label: '漲跌幅' },
];

function isRecord(value: unknown): value is RawRow {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asNumber(value: unknown, fallback = Number.NaN): number {
  if (value === null || value === undefined || value === '') return fallback;
  const parsed = Number(String(value).replace(/,/g, '').replace(/[^\d.-]/g, ''));
  return Number.isFinite(parsed) ? parsed : fallback;
}

function firstNumber(row: RawRow, keys: string[], fallback = Number.NaN): number {
  for (const key of keys) {
    const value = asNumber(row[key]);
    if (Number.isFinite(value)) return value;
  }
  return fallback;
}

function firstText(row: RawRow, keys: string[], fallback = ''): string {
  for (const key of keys) {
    const value = row[key];
    if (value !== null && value !== undefined && String(value).trim()) {
      return String(value).trim();
    }
  }
  return fallback;
}

function rawRows(data: RawRow): RawRow[] {
  for (const key of ['rows', 'changes', 'aggregate', 'items', 'signals']) {
    const value = data[key];
    if (Array.isArray(value)) return value.filter(isRecord);
  }
  return [];
}

function codeOf(row: RawRow): string {
  return firstText(row, ['stock_code', 'stockCode', 'code', 'symbol']);
}

function rowDateOf(row: RawRow): string {
  return firstText(row, ['target_date', 'target_data_date', 'data_date', 'trade_date', 'date']);
}

function targetDateOf(data: RawRow): string {
  return firstText(data, ['target_date', 'target_data_date', 'data_date']);
}

function priceOf(row: RawRow): number | null {
  const value = firstNumber(row, ['price', 'close_price', 'close', 'last_price', 'stock_price']);
  return Number.isFinite(value) ? value : null;
}

function changePctOf(row: RawRow): number | null {
  const value = firstNumber(row, ['change_pct', 'pct', 'percent', 'changePercent', 'price_change_pct']);
  return Number.isFinite(value) ? value : null;
}

function lotsOf(row: RawRow): number {
  const lots = firstNumber(row, [
    'net_lots',
    'display_delta_lots',
    'change_lots',
    'delta_lots',
    'lot_change',
    'delta_shares_lots',
    'shares_change_lots',
    'shares_diff_lots',
  ]);
  if (Number.isFinite(lots)) return lots;

  const shares = firstNumber(row, ['delta_shares', 'shares_change', 'shares_diff', 'diff_shares'], 0);
  return Math.abs(shares) >= 10_000 ? shares / 1_000 : shares;
}

function amountOf(row: RawRow, price: number | null, lots: number): number {
  const amount = firstNumber(row, [
    'net_amount_billion',
    'delta_amount_billion',
    'flow_billion',
    'amount_billion',
    'delta_value_billion',
    'net_value_billion',
  ]);
  if (Number.isFinite(amount)) return amount;
  return price === null ? 0 : price * lots * 1_000 / 100_000_000;
}

function statusOf(row: RawRow, lots: number): Status | null {
  const value = firstText(row, ['status', 'type', 'action']);
  if (STATUSES.includes(value as Status)) return value as Status;
  if (lots > 0) return '加碼';
  if (lots < 0) return '減碼';
  return null;
}

function countOf(row: RawRow, keys: string[]): number {
  const value = firstNumber(row, keys, 0);
  return Math.max(0, Math.round(value));
}

function booleanOf(row: RawRow, keys: string[]): boolean {
  return keys.some((key) => row[key] === true || row[key] === 1 || row[key] === '1');
}

function limitStateOf(row: RawRow, changePct: number | null): LimitState {
  if (booleanOf(row, ['is_limit_up', 'limit_up', 'isLimitUp'])) return 'up';
  if (booleanOf(row, ['is_limit_down', 'limit_down', 'isLimitDown'])) return 'down';
  if (changePct !== null && changePct >= 9.7) return 'up';
  if (changePct !== null && changePct <= -9.7) return 'down';
  return null;
}

function normalizeSignal(row: RawRow): Signal | null {
  const code = codeOf(row);
  const lots = lotsOf(row);
  const status = statusOf(row, lots);
  if (!code || !status) return null;

  const price = priceOf(row);
  const changePct = changePctOf(row);
  return {
    code,
    name: firstText(row, ['stock_name', 'stockName', 'name', 'stock'], code),
    price,
    changePct,
    amount: amountOf(row, price, lots),
    lots,
    status,
    buyCount: countOf(row, ['buy_count', 'buy_etf_count', 'add_etf_count']),
    sellCount: countOf(row, ['sell_count', 'sell_etf_count', 'reduce_etf_count']),
    dataDate: rowDateOf(row),
    limitState: limitStateOf(row, changePct),
  };
}

function normalizeSignals(data: RawRow, activeDays: number): Signal[] {
  const targetDate = targetDateOf(data);
  const seen = new Set<string>();

  return rawRows(data)
    .filter((row) => {
      if (activeDays !== 1) return true;
      const rowDate = rowDateOf(row);
      return Boolean(targetDate) && rowDate === targetDate;
    })
    .map(normalizeSignal)
    .filter((row): row is Signal => row !== null)
    .filter((row) => {
      if (seen.has(row.code)) return false;
      seen.add(row.code);
      return true;
    });
}

function sortValue(row: Signal, key: SortKey): number {
  if (key === 'inflow' || key === 'outflow' || key === 'absoluteAmount') return Math.abs(row.amount);
  if (key === 'lots') return Math.abs(row.lots);
  if (key === 'price') return row.price ?? Number.NEGATIVE_INFINITY;
  return row.changePct ?? Number.NEGATIVE_INFINITY;
}

function sortedSignals(rows: Signal[], sort: SortState): Signal[] {
  const eligible = rows.filter((row) => {
    if (sort.key === 'inflow') return row.amount > 0;
    if (sort.key === 'outflow') return row.amount < 0;
    return true;
  });

  const direction = sort.direction === 'desc' ? -1 : 1;
  return [...eligible].sort((a, b) => {
    const difference = sortValue(a, sort.key) - sortValue(b, sort.key);
    return difference === 0 ? a.code.localeCompare(b.code) : difference * direction;
  });
}

function focusSignals(rows: Signal[]) {
  const byAmount = (a: Signal, b: Signal) => b.amount - a.amount;
  const byOutflow = (a: Signal, b: Signal) => a.amount - b.amount;
  const byBuyCount = (a: Signal, b: Signal) => b.buyCount - a.buyCount || byAmount(a, b);
  const bySellCount = (a: Signal, b: Signal) => b.sellCount - a.sellCount || byOutflow(a, b);

  return {
    inflow: [...rows].filter((row) => row.amount > 0).sort(byAmount)[0] ?? null,
    outflow: [...rows].filter((row) => row.amount < 0).sort(byOutflow)[0] ?? null,
    mostBought: [...rows].filter((row) => row.buyCount > 0).sort(byBuyCount)[0] ?? null,
    mostSold: [...rows].filter((row) => row.sellCount > 0).sort(bySellCount)[0] ?? null,
  };
}

function todayCountOf(data: RawRow): number {
  const count = firstNumber(data, ['today_etf_count', 'fetched_etf_count', 'includedEtfCount']);
  if (Number.isFinite(count)) return Math.min(ACTIVE_ETF_TOTAL, Math.max(0, Math.round(count)));
  if (Array.isArray(data.today_etfs)) return Math.min(ACTIVE_ETF_TOTAL, data.today_etfs.length);

  const missing = firstNumber(data, ['non_today_etf_count', 'missing_today_etf_count']);
  return Number.isFinite(missing) ? Math.max(0, ACTIVE_ETF_TOTAL - Math.round(missing)) : 0;
}

function missingEtfsOf(data: RawRow): MissingEtf[] | null {
  if (!Array.isArray(data.non_today_etfs)) return null;

  return data.non_today_etfs.map((value) => {
    if (!isRecord(value)) return { code: String(value), name: '', lastDate: '' };
    return {
      code: firstText(value, ['etf_code', 'etfCode', 'code']),
      name: firstText(value, ['etf_name', 'etfName', 'name']),
      lastDate: firstText(value, ['data_date', 'last_date', 'lastDataDate']),
    };
  }).filter((row) => row.code);
}

function formatDate(value: string): string {
  const match = value.match(/\d{4}-(\d{2})-(\d{2})/);
  return match ? `${match[1]}-${match[2]}` : value || '-';
}

function formatPrice(value: number | null): string {
  if (value === null) return '-';
  return value.toLocaleString('zh-TW', { maximumFractionDigits: value >= 100 ? 1 : 2 });
}

function formatPct(value: number | null): string {
  if (value === null) return '-';
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatLots(value: number): string {
  if (Math.abs(value) < 0.01) return '0張';
  return `${value > 0 ? '+' : ''}${Math.round(value).toLocaleString('zh-TW')}張`;
}

function formatAmount(value: number): string {
  if (Math.abs(value) < 0.005) return '0億';
  return `${value > 0 ? '+' : ''}${value.toLocaleString('zh-TW', {
    maximumFractionDigits: Math.abs(value) >= 10 ? 1 : 2,
  })}億`;
}

function toneClass(value: number): string {
  if (value > 0) return styles.positive;
  if (value < 0) return styles.negative;
  return styles.neutral;
}

function FocusCard({ title, signal, tone }: { title: string; signal: Signal | null; tone: 'positive' | 'negative' }) {
  const className = `${styles.focusCard} ${tone === 'positive' ? styles.focusPositive : styles.focusNegative}`;
  if (!signal) {
    return <div className={className}><strong className={styles.focusTitle}>{title}</strong><span className={styles.noSignal}>尚無有效訊號</span></div>;
  }

  return (
    <Link className={className} href={`/stock/${signal.code}`}>
      <strong className={styles.focusTitle}>{title}</strong>
      <div className={styles.focusName}><b>{signal.name}</b><span>{signal.code}</span></div>
      <div className={styles.focusPrice}>
        <b>{formatPrice(signal.price)}</b>
        <span className={toneClass(signal.changePct ?? 0)}>{formatPct(signal.changePct)}</span>
      </div>
      <div className={styles.focusMeta}>
        <span>淨額 <b className={toneClass(signal.amount)}>{formatAmount(signal.amount)}</b></span>
        <span>張數 <b className={toneClass(signal.lots)}>{formatLots(signal.lots)}</b></span>
        <span>異動ETF {signal.buyCount}:{signal.sellCount}</span>
      </div>
    </Link>
  );
}

function SortButton({ option, sort, onSelect }: {
  option: { key: SortKey; label: string };
  sort: SortState;
  onSelect: (key: SortKey) => void;
}) {
  const active = sort.key === option.key;
  const arrow = active && sort.direction === 'asc' ? '▲' : '▼';
  return (
    <button type="button" className={active ? styles.activeSort : ''} aria-pressed={active} onClick={() => onSelect(option.key)}>
      {option.label} <span aria-hidden="true">{arrow}</span>
    </button>
  );
}

function SignalRow({ signal }: { signal: Signal }) {
  const limitClass = signal.limitState === 'up' ? styles.limitUp : signal.limitState === 'down' ? styles.limitDown : '';
  const statusClass = signal.status === '新增'
    ? styles.statusNew
    : signal.status === '加碼'
      ? styles.statusBuy
      : signal.status === '減碼'
        ? styles.statusSell
        : styles.statusRemoved;

  return (
    <Link className={styles.tableRow} href={`/stock/${signal.code}`} aria-label={`${signal.name} ${signal.code} 詳細資料`}>
      <div className={styles.targetCell}><b>{signal.name}</b><span>{signal.code}</span></div>
      <div className={styles.priceCell}>
        <b className={limitClass}>{formatPrice(signal.price)}</b>
        <span className={toneClass(signal.changePct ?? 0)}>{formatPct(signal.changePct)}</span>
      </div>
      <div className={styles.flowCell}>
        <b className={toneClass(signal.amount)}>{formatAmount(signal.amount)}</b>
        <span className={toneClass(signal.lots)}>{formatLots(signal.lots)}</span>
      </div>
      <div className={styles.statusCell}>
        <b className={statusClass}>{signal.status}</b>
        <span>異動ETF {signal.buyCount}:{signal.sellCount}</span>
      </div>
    </Link>
  );
}

function MissingEtfModal({ data, todayCount, onClose }: { data: RawRow; todayCount: number; onClose: () => void }) {
  const missingCount = Math.max(0, ACTIVE_ETF_TOTAL - todayCount);
  const missingEtfs = missingEtfsOf(data);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [onClose]);

  return (
    <div className={styles.modalBackdrop} onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className={styles.modal} role="dialog" aria-modal="true" aria-labelledby="missing-etf-title">
        <button className={styles.modalClose} type="button" onClick={onClose} aria-label="關閉">×</button>
        <h2 id="missing-etf-title">未更新 ETF</h2>
        <p>今日訊號只使用 target_date 當日資料，不混入前一日資料。</p>
        <strong className={styles.modalSummary}>已取得 {todayCount} / {ACTIVE_ETF_TOTAL} 檔、未更新 {missingCount} 檔</strong>

        {missingEtfs && missingEtfs.length > 0 ? (
          <div className={styles.missingList}>
            {missingEtfs.map((etf) => (
              <div className={styles.missingRow} key={etf.code}>
                <b>{etf.code}</b>
                <span>{etf.name || '名稱未提供'}</span>
                <small>{etf.lastDate ? `最後資料 ${formatDate(etf.lastDate)}` : '最後資料日未提供'}</small>
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.missingNotice}>目前 API 尚未回傳未更新 ETF 清單</div>
        )}

        <button className={styles.modalConfirm} type="button" onClick={onClose}>我知道了</button>
      </section>
    </div>
  );
}

export default function SignalsClient({ data: dataProp, activeDays: activeDaysProp }: { data: unknown; activeDays?: number }) {
  const data = isRecord(dataProp) ? dataProp : {};
  const activeDays = Number(activeDaysProp ?? firstNumber(data, ['signalRangeDays', 'rangeDays'], 1)) || 1;
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('全部');
  const [sort, setSort] = useState<SortState>({ key: activeDays === 1 ? 'inflow' : 'absoluteAmount', direction: 'desc' });
  const [showMissing, setShowMissing] = useState(false);

  const signals = useMemo(() => normalizeSignals(data, activeDays), [data, activeDays]);
  const targetDate = targetDateOf(data);
  const todayCount = todayCountOf(data);
  const missingCount = Math.max(0, ACTIVE_ETF_TOTAL - todayCount);

  const counts = useMemo(() => {
    const result: Record<Status, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0 };
    signals.forEach((signal) => { result[signal.status] += 1; });
    return result;
  }, [signals]);

  const statusRows = useMemo(
    () => statusFilter === '全部' ? signals : signals.filter((signal) => signal.status === statusFilter),
    [signals, statusFilter],
  );
  const displayedRows = useMemo(() => sortedSignals(statusRows, sort), [statusRows, sort]);
  const focus = useMemo(() => focusSignals(signals), [signals]);

  const selectSort = (key: SortKey) => {
    setSort((current) => current.key === key
      ? { key, direction: current.direction === 'desc' ? 'asc' : 'desc' }
      : { key, direction: 'desc' });
  };

  return (
    <main className={styles.page}>
      <section className={styles.rangeSection} aria-label="訊號區間">
        <span>訊號區間</span>
        <div className={styles.rangeTabs}>
          {RANGE_OPTIONS.map((days) => (
            <Link key={days} href={days === 1 ? '/signals' : `/signals?days=${days}`} className={activeDays === days ? styles.activeRange : ''}>
              {days === 1 ? '今日' : `${days}日`}
            </Link>
          ))}
        </div>
      </section>

      <header className={styles.hero}>
        <h1>{activeDays === 1 ? '今日訊號' : `近${activeDays}日訊號`}</h1>
        {activeDays === 1 ? (
          <div className={styles.dataQuality}>
            <span>資料日 <b>{formatDate(targetDate)}</b></span>
            <span>已取得 {todayCount} / {ACTIVE_ETF_TOTAL} 檔、未更新 {missingCount} 檔</span>
            {missingCount > 0 && <button type="button" onClick={() => setShowMissing(true)}>查看未更新 ETF</button>}
          </div>
        ) : (
          <div className={styles.dataQuality}><span>最新資料日 <b>{formatDate(targetDate)}</b></span></div>
        )}
      </header>

      <section className={styles.focusGrid} aria-label="重點訊號">
        <FocusCard title="淨資金流入最多" signal={focus.inflow} tone="positive" />
        <FocusCard title="淨資金流出最多" signal={focus.outflow} tone="negative" />
        <FocusCard title="最多 ETF 加碼" signal={focus.mostBought} tone="positive" />
        <FocusCard title="最多 ETF 減碼" signal={focus.mostSold} tone="negative" />
      </section>

      <section className={styles.detailSection}>
        <h2>資金交易明細</h2>
        <p className={styles.resultCount}>顯示 {displayedRows.length} / 共 {statusRows.length} 檔</p>

        <div className={styles.filterTabs} aria-label="狀態篩選">
          <button type="button" className={statusFilter === '全部' ? styles.activeFilter : ''} onClick={() => setStatusFilter('全部')}>全部 {signals.length}</button>
          {STATUSES.map((status) => (
            <button key={status} type="button" className={statusFilter === status ? styles.activeFilter : ''} onClick={() => setStatusFilter(status)}>
              {status} {counts[status]}
            </button>
          ))}
        </div>

        <div className={styles.sortTabs} aria-label="明細排序">
          {SORT_OPTIONS.map((option) => <SortButton key={option.key} option={option} sort={sort} onSelect={selectSort} />)}
        </div>

        <div className={styles.table}>
          <div className={styles.tableHead} aria-hidden="true">
            <span>標的</span>
            <span>股價</span>
            <span>淨額 / 張數</span>
            <span>狀態 / 異動ETF</span>
          </div>
          {displayedRows.length > 0
            ? displayedRows.map((signal) => <SignalRow key={signal.code} signal={signal} />)
            : <div className={styles.emptyState}>目前沒有符合條件的訊號。</div>}
        </div>
      </section>

      {showMissing && <MissingEtfModal data={data} todayCount={todayCount} onClose={() => setShowMissing(false)} />}
    </main>
  );
}
