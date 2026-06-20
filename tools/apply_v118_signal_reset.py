from pathlib import Path

root = Path(".")
comp = root / "frontend/components/SignalsClient.tsx"
page = root / "frontend/app/signals/page.tsx"
home = root / "frontend/app/page.tsx"
css = root / "frontend/app/globals.css"
readme = root / "README_V118_SIGNAL_RESET.md"

comp.write_text(r''''use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

type AnyRow = Record<string, any>;
type Status = '新增' | '刪除' | '加碼' | '減碼';
type SortKey = 'amount' | 'outflow' | 'absAmount' | 'lots' | 'consensus' | 'price' | 'pct' | 'code';
type SortDir = 'asc' | 'desc';

const TOTAL_ACTIVE_ETFS = 27;
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

function firstText(row: AnyRow, keys: string[], fallback = ''): string {
  for (const k of keys) {
    const v = row?.[k];
    if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
  }
  return fallback;
}

function arrayFrom(data: any, keys: string[]): AnyRow[] {
  const out: AnyRow[] = [];
  for (const k of keys) {
    const v = data?.[k];
    if (Array.isArray(v)) out.push(...v);
  }
  return out;
}

function rowsOf(data: any): AnyRow[] {
  const src = data?.rows ?? data?.changes ?? data?.aggregate ?? data?.items ?? data?.signals ?? [];
  return Array.isArray(src) ? src : [];
}

function codeOf(row: AnyRow): string {
  return firstText(row, ['stock_code', 'stockCode', 'code', 'symbol']);
}

function nameOf(row: AnyRow): string {
  return firstText(row, ['stock_name', 'stockName', 'name', 'stock'], codeOf(row));
}

function etfCodeOf(row: AnyRow): string {
  return firstText(row, ['etf_code', 'etfCode', 'fund_code', 'fundCode', 'etf']);
}

function etfNameOf(row: AnyRow): string {
  return firstText(row, ['etf_name', 'etfName', 'fund_name', 'fundName'], etfCodeOf(row));
}

function dateOf(row: AnyRow): string {
  return firstText(row, ['data_date', 'date', 'trade_date', 'tradeDate', 'dt']);
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
    'shares_diff_lots',
    'diff_lots',
    'delta_shares',
    'shares_change',
    'shares_diff',
    'diff_shares',
  ], 0);

  // 大於等於 10 萬通常是「股」，轉成「張」。
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
  const s = String(row.status ?? row.type ?? row.action ?? '').trim();
  if (STATUSES.includes(s as Status)) return s as Status;

  const lots = lotsOf(row);
  if (lots > 0) return '加碼';
  if (lots < 0) return '減碼';
  return null;
}

function sourceRowsOf(data: any): AnyRow[] {
  const possible = arrayFrom(data, [
    'source_rows',
    'sourceRows',
    'detail_rows',
    'detailRows',
    'details',
    'records',
    'operation_records',
    'operationRecords',
    'operations',
    'raw_rows',
    'rawRows',
    'change_rows',
    'changeRows',
    'stock_recent_operation_records',
    'stockRecentOperationRecords',
  ]);

  const nested = rowsOf(data).flatMap((r: AnyRow) => arrayFrom(r, [
    'source_rows',
    'sourceRows',
    'details',
    'records',
    'operation_records',
    'operationRecords',
    'etf_changes',
    'etfChanges',
  ]));

  const fromMainRows = rowsOf(data).filter((r: AnyRow) => etfCodeOf(r) && codeOf(r));
  const all = [...possible, ...nested, ...fromMainRows].filter((r) => etfCodeOf(r) && codeOf(r));

  const seen = new Set<string>();
  return all.filter((r) => {
    const key = [dateOf(r), etfCodeOf(r), codeOf(r), lotsOf(r), statusOf(r) ?? ''].join('|');
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function groupRowsFromSources(sourceRows: AnyRow[]): AnyRow[] {
  const map = new Map<string, AnyRow>();

  for (const r of sourceRows) {
    const code = codeOf(r);
    if (!code) continue;

    const cur = map.get(code) ?? {
      stock_code: code,
      stock_name: nameOf(r),
      price: priceOf(r),
      change_pct: pctOf(r),
      net_lots: 0,
      net_amount_billion: 0,
      __sources: [],
    };

    cur.stock_name = cur.stock_name || nameOf(r);
    if (cur.price === null || cur.price === undefined) cur.price = priceOf(r);
    if (cur.change_pct === null || cur.change_pct === undefined) cur.change_pct = pctOf(r);

    cur.net_lots += lotsOf(r);
    cur.net_amount_billion += amountOf(r);
    cur.__sources.push(r);
    map.set(code, cur);
  }

  return Array.from(map.values());
}

function sourcesFor(row: AnyRow, allSources: AnyRow[]): AnyRow[] {
  const code = codeOf(row);
  const nested = arrayFrom(row, [
    'source_rows',
    'sourceRows',
    'details',
    'records',
    'operation_records',
    'operationRecords',
    'etf_changes',
    'etfChanges',
    '__sources',
  ]).filter((r) => etfCodeOf(r));

  const global = allSources.filter((r) => codeOf(r) === code);

  const seen = new Set<string>();
  return [...nested, ...global]
    .filter((r) => etfCodeOf(r))
    .filter((r) => {
      const key = [dateOf(r), etfCodeOf(r), lotsOf(r), amountOf(r)].join('|');
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function buySellOf(row: AnyRow, sources: AnyRow[]): { buy: number; sell: number } {
  if (sources.length) {
    let buy = 0;
    let sell = 0;
    for (const s of sources) {
      const lots = lotsOf(s);
      if (lots > 0) buy += 1;
      if (lots < 0) sell += 1;
    }
    return { buy, sell };
  }

  const buy = firstNum(row, ['buy_count', 'buy_etf_count', 'add_etf_count', 'increase_count'], NaN);
  const sell = firstNum(row, ['sell_count', 'sell_etf_count', 'reduce_etf_count', 'decrease_count'], NaN);

  if (Number.isFinite(buy) || Number.isFinite(sell)) {
    return {
      buy: Math.max(0, Math.round(Number.isFinite(buy) ? buy : 0)),
      sell: Math.max(0, Math.round(Number.isFinite(sell) ? sell : 0)),
    };
  }

  const s = statusOf(row);
  if (s === '新增' || s === '加碼') return { buy: 1, sell: 0 };
  if (s === '刪除' || s === '減碼') return { buy: 0, sell: 1 };
  return { buy: 0, sell: 0 };
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

function missingRowsOf(data: any): AnyRow[] {
  return arrayFrom(data, ['non_today_etfs', 'nonTodayEtfs', 'missing_etfs', 'missingEtfs', 'stale_etfs', 'staleEtfs']);
}

function statusCounts(rows: AnyRow[]) {
  const out: Record<Status, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0 };
  for (const r of rows) {
    const s = statusOf(r);
    if (s) out[s] += 1;
  }
  return out;
}

function enrichRows(data: any): AnyRow[] {
  const sourceRows = sourceRowsOf(data);
  const grouped = sourceRows.length ? groupRowsFromSources(sourceRows) : [];

  // 重要：有來源 ETF 明細時，以來源明細重新彙總，避免 aggregate 舊欄位造成國巨 600 張又變錯。
  const base = grouped.length
    ? grouped
    : rowsOf(data).filter((r) => codeOf(r) && !etfCodeOf(r));

  return base.map((r) => {
    const sources = sourcesFor(r, sourceRows);
    const bs = buySellOf(r, sources);
    return {
      ...r,
      __sources: sources,
      __buySell: bs,
    };
  });
}

function sortValue(row: AnyRow, key: SortKey): number | string {
  if (key === 'amount') return amountOf(row);
  if (key === 'outflow') return amountOf(row);
  if (key === 'absAmount') return Math.abs(amountOf(row));
  if (key === 'lots') return lotsOf(row);
  if (key === 'consensus') {
    const bs = row.__buySell ?? { buy: 0, sell: 0 };
    return bs.buy - bs.sell;
  }
  if (key === 'price') return priceOf(row) ?? -Infinity;
  if (key === 'pct') return pctOf(row) ?? -Infinity;
  if (key === 'code') return codeOf(row);
  return 0;
}

function sortRows(rows: AnyRow[], key: SortKey, dir: SortDir): AnyRow[] {
  const m = dir === 'desc' ? -1 : 1;
  return rows.slice().sort((a, b) => {
    const av = sortValue(a, key);
    const bv = sortValue(b, key);

    if (typeof av === 'string' || typeof bv === 'string') {
      return String(av).localeCompare(String(bv)) * m;
    }

    if (av === bv) return Math.abs(amountOf(b)) - Math.abs(amountOf(a));
    return ((av as number) - (bv as number)) * m;
  });
}

function FocusCard({
  title,
  row,
  kind,
}: {
  title: string;
  row?: AnyRow | null;
  kind: 'red' | 'green';
}) {
  if (!row) {
    return (
      <div className={`v118-focus-card ${kind}`}>
        <div className="v118-focus-title">{title}</div>
        <div className="v118-empty">尚無有效訊號</div>
      </div>
    );
  }

  const amount = amountOf(row);
  const lots = lotsOf(row);
  const price = priceOf(row);
  const pct = pctOf(row);
  const bs = row.__buySell ?? { buy: 0, sell: 0 };

  return (
    <Link className={`v118-focus-card ${kind}`} href={`/stock/${codeOf(row)}`}>
      <div className="v118-focus-title">{title}</div>
      <div className="v118-focus-name">
        <b>{nameOf(row)}</b>
        <span>{codeOf(row)}</span>
      </div>
      <div className="v118-focus-price">
        <strong>{fmtPrice(price)}</strong>
        <em className={toneClass(pct ?? 0)}>{fmtPct(pct)}</em>
      </div>
      <div className="v118-focus-meta">
        <span>淨額 <b className={toneClass(amount)}>{fmtBillion(amount)}</b></span>
        <span>張數 <b className={toneClass(lots)}>{fmtLots(lots)}</b></span>
        <span>異動ETF <b>{bs.buy}:{bs.sell}</b></span>
      </div>
    </Link>
  );
}

function MissingModal({ data, onClose }: { data: any; onClose: () => void }) {
  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const rows = missingRowsOf(data);

  return (
    <div className="v118-modal-mask" onClick={onClose}>
      <div className="v118-modal" onClick={(e) => e.stopPropagation()}>
        <div className="v118-modal-head">
          <div>
            <h3>未更新 ETF 清單</h3>
            <p>今日訊號只使用當日資料，不混入前一日資料。</p>
          </div>
          <button type="button" onClick={onClose} aria-label="關閉">×</button>
        </div>

        <div className="v118-missing-summary">已取得 {today} / {total} 檔，未更新 {missing} 檔</div>

        {rows.length ? (
          <div className="v118-missing-list">
            {rows.map((r, i) => (
              <div className="v118-missing-row" key={`${etfCodeOf(r) || firstText(r, ['etf_code', 'code'], `ETF-${i}`)}-${i}`}>
                <b>{etfCodeOf(r) || firstText(r, ['etf_code', 'code'], '-')}</b>
                <span>{etfNameOf(r) || firstText(r, ['name', 'etf_name'], '')}</span>
                <em>{dateOf(r) ? `最後資料 ${mmdd(dateOf(r))}` : '尚無日期'}</em>
              </div>
            ))}
          </div>
        ) : (
          <div className="v118-missing-note">
            目前 API 只回傳未更新數量，尚未回傳 ETF 代號清單。因此本頁不再顯示 ETF 1、ETF 2 這種假資料。若要列出實際未更新 ETF，下一步需在 /signals API 補回 non_today_etfs。
          </div>
        )}

        <button type="button" className="v118-ok" onClick={onClose}>我知道了</button>
      </div>
    </div>
  );
}

function RangeTabs({ activeDays }: { activeDays: number }) {
  const items = [1, 5, 10, 20];

  return (
    <section className="v118-range">
      <div className="v118-range-label">訊號區間</div>
      <div className="v118-segment">
        {items.map((d) => (
          <Link
            key={d}
            href={d === 1 ? '/' : `/?days=${d}`}
            className={activeDays === d ? 'active' : ''}
          >
            {d === 1 ? '今日' : `${d}日`}
          </Link>
        ))}
      </div>
    </section>
  );
}

function DataQuality({ data, activeDays, onOpenMissing }: { data: any; activeDays: number; onOpenMissing: () => void }) {
  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';

  if (activeDays !== 1) {
    return (
      <div className="v118-quality">
        <span>資料區間 <b>近 {activeDays} 日</b></span>
        <span>資料日 <b>{mmdd(date)}</b></span>
      </div>
    );
  }

  return (
    <div className="v118-quality">
      <span>資料日 <b>{mmdd(date)}</b></span>
      <span>已取得今日資料 <b>{today} / {total}</b> 檔 ETF</span>
      {missing > 0 && (
        <button type="button" onClick={onOpenMissing}>
          未更新 {missing} 檔，查看清單
        </button>
      )}
    </div>
  );
}

function SortButton({
  label,
  sortKey,
  currentKey,
  dir,
  onClick,
}: {
  label: string;
  sortKey: SortKey;
  currentKey: SortKey;
  dir: SortDir;
  onClick: () => void;
}) {
  const active = sortKey === currentKey;
  return (
    <button type="button" className={active ? 'active' : ''} onClick={onClick}>
      {label} <span>{active ? (dir === 'desc' ? '▼' : '▲') : '↕'}</span>
    </button>
  );
}

function SignalRow({ row }: { row: AnyRow }) {
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const price = priceOf(row);
  const pct = pctOf(row);
  const st = statusOf(row);
  const bs = row.__buySell ?? { buy: 0, sell: 0 };

  return (
    <Link className="v118-row" href={`/stock/${codeOf(row)}`}>
      <div className="v118-stock">
        <b>{nameOf(row)}</b>
        <span>{codeOf(row)}</span>
      </div>

      <div className="v118-price">
        <b className={isLimitUp(row) ? 'limit-up' : isLimitDown(row) ? 'limit-down' : ''}>{fmtPrice(price)}</b>
        <span className={toneClass(pct ?? 0)}>{fmtPct(pct)}</span>
        {isLimitUp(row) && <em className="limit-tag">漲停</em>}
        {isLimitDown(row) && <em className="limit-tag green">跌停</em>}
      </div>

      <div className="v118-flow">
        <b className={toneClass(amount)}>{fmtBillion(amount)}</b>
        <span className={toneClass(lots)}>{fmtLots(lots)}</span>
      </div>

      <div className="v118-action">
        <b className={`pill ${st ?? ''}`}>{st ?? '-'}</b>
        <span>異動 {bs.buy}:{bs.sell}</span>
      </div>
    </Link>
  );
}

export default function SignalsClient(props: { data: any; activeDays?: number }) {
  const data = props.data ?? {};
  const activeDays = Number(props.activeDays ?? data?.days ?? data?.signalRangeDays ?? 1) || 1;

  const [missingOpen, setMissingOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState<Status | '全部'>('全部');
  const [sortKey, setSortKey] = useState<SortKey>('amount');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const rows = useMemo(() => enrichRows(data), [data]);
  const sourceRows = useMemo(() => sourceRowsOf(data), [data]);

  const counts = useMemo(() => {
    const base = sourceRows.length ? sourceRows : rows;
    return statusCounts(base);
  }, [sourceRows, rows]);

  const filteredRows = useMemo(() => {
    const base = statusFilter === '全部'
      ? rows
      : rows.filter((r) => statusOf(r) === statusFilter);

    return sortRows(base, sortKey, sortDir);
  }, [rows, statusFilter, sortKey, sortDir]);

  const totalDetailCount = sourceRows.length || rows.length;
  const title = activeDays === 1 ? '今日訊號' : `近${activeDays}日訊號`;

  const focusIn = rows.filter((r) => amountOf(r) > 0).sort((a, b) => amountOf(b) - amountOf(a))[0];
  const focusOut = rows.filter((r) => amountOf(r) < 0).sort((a, b) => amountOf(a) - amountOf(b))[0];
  const focusBuy = rows
    .filter((r) => (r.__buySell?.buy ?? 0) > 0)
    .sort((a, b) => (b.__buySell?.buy ?? 0) - (a.__buySell?.buy ?? 0) || lotsOf(b) - lotsOf(a))[0];
  const focusSell = rows
    .filter((r) => (r.__buySell?.sell ?? 0) > 0)
    .sort((a, b) => (b.__buySell?.sell ?? 0) - (a.__buySell?.sell ?? 0) || lotsOf(a) - lotsOf(b))[0];

  function toggleSort(k: SortKey, defaultDir: SortDir = 'desc') {
    if (sortKey === k) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    else {
      setSortKey(k);
      setSortDir(defaultDir);
    }
  }

  return (
    <main className="v118-page">
      <RangeTabs activeDays={activeDays} />

      <section className="v118-hero">
        <h1>{title}</h1>
        <DataQuality data={data} activeDays={activeDays} onOpenMissing={() => setMissingOpen(true)} />
      </section>

      <section className="v118-focus-grid">
        <FocusCard title="淨資金流入最多" row={focusIn} kind="red" />
        <FocusCard title="淨資金流出最多" row={focusOut} kind="green" />
        <FocusCard title="最多 ETF 加碼" row={focusBuy} kind="red" />
        <FocusCard title="最多 ETF 減碼" row={focusSell} kind="green" />
      </section>

      <section className="v118-detail">
        <h2>資金交易明細：共 {totalDetailCount} 檔</h2>

        <div className="v118-status-tabs">
          <button type="button" className={statusFilter === '新增' ? 'on add' : 'add'} onClick={() => setStatusFilter(statusFilter === '新增' ? '全部' : '新增')}>新增 {counts.新增}</button>
          <button type="button" className={statusFilter === '刪除' ? 'on del' : 'del'} onClick={() => setStatusFilter(statusFilter === '刪除' ? '全部' : '刪除')}>刪除 {counts.刪除}</button>
          <button type="button" className={statusFilter === '加碼' ? 'on buy' : 'buy'} onClick={() => setStatusFilter(statusFilter === '加碼' ? '全部' : '加碼')}>加碼 {counts.加碼}</button>
          <button type="button" className={statusFilter === '減碼' ? 'on sell' : 'sell'} onClick={() => setStatusFilter(statusFilter === '減碼' ? '全部' : '減碼')}>減碼 {counts.減碼}</button>
        </div>

        <div className="v118-table">
          <div className="v118-head">
            <SortButton label="標的" sortKey="code" currentKey={sortKey} dir={sortDir} onClick={() => toggleSort('code', 'asc')} />
            <SortButton label="股價" sortKey="price" currentKey={sortKey} dir={sortDir} onClick={() => toggleSort('price')} />
            <SortButton label="淨額/張數" sortKey="amount" currentKey={sortKey} dir={sortDir} onClick={() => toggleSort('amount')} />
            <SortButton label="狀態/異動" sortKey="consensus" currentKey={sortKey} dir={sortDir} onClick={() => toggleSort('consensus')} />
          </div>

          {filteredRows.length ? (
            filteredRows.map((r) => <SignalRow key={`${codeOf(r)}-${amountOf(r)}-${lotsOf(r)}`} row={r} />)
          ) : (
            <div className="v118-empty-table">尚無符合條件的訊號。</div>
          )}
        </div>
      </section>

      {missingOpen && <MissingModal data={data} onClose={() => setMissingOpen(false)} />}
    </main>
  );
}
''', encoding='utf-8')

page.write_text(r'''import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

type SearchParams = {
  days?: string | string[];
  rangeDays?: string | string[];
  signalRangeDays?: string | string[];
};

function one(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}

function normalizeSignalDays(searchParams?: SearchParams): number {
  const raw = one(searchParams?.days) || one(searchParams?.rangeDays) || one(searchParams?.signalRangeDays) || '1';
  const n = Number(raw);
  return [1, 5, 10, 20].includes(n) ? n : 1;
}

export default async function Page({ searchParams }: { searchParams?: SearchParams }) {
  const days = normalizeSignalDays(searchParams);
  const data = await apiGet(`/signals?days=${days}`);
  return <SignalsClient data={data} activeDays={days} />;
}
''', encoding='utf-8')

# 首頁就是今日訊號，避免 app/page.tsx 又多包一組區間造成重複。
home.write_text(page.read_text(encoding='utf-8'), encoding='utf-8')

css_append = r'''

/* ============================================================
   V118 Signal Reset
   單一乾淨版：不吃舊 v3/v7/v113/v117 signals CSS
   ============================================================ */

.v118-page,
.v118-page * {
  box-sizing: border-box;
}

.v118-page {
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
  padding: 22px 16px 88px;
  overflow-x: hidden;
  color: #111827;
  background: #fff;
}

.v118-range {
  margin: 0 0 34px;
}

.v118-range-label {
  color: #7b8798;
  font-size: 22px;
  font-weight: 900;
  margin-bottom: 10px;
}

.v118-segment {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  width: 100%;
  background: #edf2f8;
  border: 1px solid #dbe3ee;
  border-radius: 999px;
  padding: 5px;
  box-shadow: inset 0 2px 6px rgba(15, 23, 42, .05);
}

.v118-segment a {
  min-width: 0;
  text-align: center;
  text-decoration: none;
  color: #657386;
  border-radius: 999px;
  padding: 12px 0;
  font-size: 20px;
  font-weight: 950;
}

.v118-segment a.active {
  color: #2f6ecb;
  background: #fff;
  box-shadow: 0 5px 14px rgba(15, 23, 42, .08);
}

.v118-hero h1 {
  margin: 0 0 8px;
  font-size: 46px;
  line-height: 1;
  letter-spacing: -.04em;
  font-weight: 1000;
}

.v118-quality {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 14px;
  align-items: center;
  color: #7a8596;
  font-size: 18px;
  line-height: 1.35;
  font-weight: 900;
}

.v118-quality b {
  color: #111827;
}

.v118-quality button {
  appearance: none;
  border: 0;
  background: transparent;
  color: #9a6b0b;
  padding: 0;
  border-bottom: 1.5px solid #9a6b0b;
  font: inherit;
  font-weight: 950;
}

.v118-focus-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 20px 0 32px;
}

.v118-focus-card {
  min-width: 0;
  min-height: 174px;
  display: block;
  text-decoration: none;
  color: inherit;
  border: 1.5px solid #e5eaf2;
  border-radius: 20px;
  padding: 16px;
  overflow: hidden;
}

.v118-focus-card.red {
  background: #fff8f9;
  border-color: #f3c8cf;
}

.v118-focus-card.green {
  background: #f2fffa;
  border-color: #bee9d8;
}

.v118-focus-title {
  font-size: 21px;
  line-height: 1.12;
  font-weight: 1000;
  margin-bottom: 12px;
}

.v118-focus-card.red .v118-focus-title { color: #d95561; }
.v118-focus-card.green .v118-focus-title { color: #27a575; }

.v118-focus-name {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}

.v118-focus-name b {
  min-width: 0;
  color: #111827;
  font-size: 23px;
  line-height: 1.08;
  font-weight: 1000;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.v118-focus-name span {
  color: #8793a5;
  font-size: 16px;
  font-weight: 900;
}

.v118-focus-price {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 10px;
}

.v118-focus-price strong {
  color: #111827;
  font-size: 36px;
  line-height: 1;
  letter-spacing: -.04em;
  font-weight: 1000;
}

.v118-focus-price em {
  font-size: 18px;
  font-style: normal;
  font-weight: 1000;
  white-space: nowrap;
}

.v118-focus-meta {
  display: grid;
  gap: 2px;
  color: #7a8596;
  font-size: 16px;
  line-height: 1.32;
  font-weight: 900;
}

.v118-focus-meta b {
  font-weight: 1000;
}

.v118-detail h2 {
  margin: 0 0 12px;
  font-size: 34px;
  line-height: 1.08;
  letter-spacing: -.03em;
  font-weight: 1000;
}

.v118-status-tabs {
  display: flex;
  gap: 9px;
  overflow-x: auto;
  padding: 0 0 10px;
  margin-bottom: 8px;
  scrollbar-width: none;
}

.v118-status-tabs::-webkit-scrollbar {
  display: none;
}

.v118-status-tabs button {
  flex: 0 0 auto;
  min-width: 88px;
  border: 2px solid #cbd5e1;
  background: #fff;
  color: #64748b;
  border-radius: 999px;
  padding: 9px 14px;
  font-size: 18px;
  line-height: 1;
  font-weight: 950;
}

.v118-status-tabs .add,
.v118-status-tabs .add.on {
  color: #b59b09;
  border-color: #bda70a;
  background: #fffdf0;
}

.v118-status-tabs .buy,
.v118-status-tabs .buy.on {
  color: #d95561;
  border-color: #d95561;
  background: #fff8f9;
}

.v118-status-tabs .sell,
.v118-status-tabs .sell.on {
  color: #27a575;
  border-color: #27a575;
  background: #f2fffa;
}

.v118-table {
  width: 100%;
  overflow: hidden;
}

.v118-head,
.v118-row {
  display: grid;
  grid-template-columns: minmax(82px, 1.1fr) minmax(68px, .82fr) minmax(92px, 1fr) minmax(76px, .9fr);
  column-gap: 8px;
  align-items: center;
}

.v118-head {
  background: #f1f4f8;
  border-radius: 0;
  min-height: 48px;
  padding: 0 9px;
  margin-bottom: 2px;
}

.v118-head button {
  min-width: 0;
  border: 0;
  background: transparent;
  color: #64748b;
  text-align: left;
  font-size: 15px;
  line-height: 1.15;
  font-weight: 950;
  padding: 0;
}

.v118-head button.active {
  color: #2f6ecb;
}

.v118-head button span {
  color: inherit;
  font-size: 13px;
}

.v118-row {
  text-decoration: none;
  color: inherit;
  min-height: 82px;
  padding: 11px 9px;
  border-bottom: 1px solid #e6edf5;
}

.v118-stock,
.v118-price,
.v118-flow,
.v118-action {
  min-width: 0;
}

.v118-stock b {
  display: block;
  color: #111827;
  font-size: 21px;
  line-height: 1.1;
  font-weight: 1000;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.v118-stock span,
.v118-price span,
.v118-flow span,
.v118-action span {
  display: block;
  color: #8793a5;
  font-size: 14px;
  line-height: 1.2;
  font-weight: 900;
}

.v118-price b {
  display: inline-block;
  max-width: 100%;
  color: #111827;
  font-size: 22px;
  line-height: 1.05;
  font-weight: 1000;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.v118-price b.limit-up,
.v118-price b.limit-down {
  color: #fff;
  background: #d75a64;
  border-radius: 8px;
  padding: 2px 6px;
}

.v118-price b.limit-down {
  background: #27a575;
}

.v118-flow {
  text-align: right;
}

.v118-flow b {
  display: block;
  font-size: 20px;
  line-height: 1.15;
  font-weight: 1000;
  white-space: nowrap;
}

.v118-action {
  text-align: right;
}

.v118-action .pill {
  display: inline-block;
  min-width: 54px;
  text-align: center;
  border-radius: 999px;
  padding: 5px 8px;
  font-size: 15px;
  line-height: 1;
  font-weight: 950;
  background: #eef2f7;
  color: #64748b;
}

.v118-action .pill.新增 {
  color: #a99106;
  background: #fff5c7;
}

.v118-action .pill.加碼 {
  color: #d95561;
  background: #ffecef;
}

.v118-action .pill.減碼 {
  color: #27a575;
  background: #e9fbf4;
}

.v118-action .pill.刪除 {
  color: #64748b;
  background: #eef2f7;
}

.limit-tag {
  display: inline-block;
  margin-top: 4px;
  color: #fff;
  background: #d75a64;
  border-radius: 999px;
  padding: 3px 7px;
  font-size: 12px;
  line-height: 1;
  font-style: normal;
  font-weight: 950;
}

.limit-tag.green {
  background: #27a575;
}

.is-red { color: #d95561 !important; }
.is-green { color: #27a575 !important; }
.is-muted { color: #8793a5 !important; }

.v118-empty-table,
.v118-empty {
  color: #8793a5;
  font-size: 16px;
  font-weight: 900;
  padding: 20px 0;
}

.v118-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: grid;
  place-items: end center;
  background: rgba(15, 23, 42, .48);
  padding: 18px;
}

.v118-modal {
  width: min(100%, 520px);
  max-height: 84vh;
  overflow: auto;
  background: #fff;
  border-radius: 24px;
  padding: 24px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, .24);
}

.v118-modal-head {
  display: grid;
  grid-template-columns: 1fr 44px;
  gap: 12px;
  align-items: start;
}

.v118-modal-head h3 {
  margin: 0 0 8px;
  font-size: 30px;
  line-height: 1.1;
  letter-spacing: -.03em;
  font-weight: 1000;
}

.v118-modal-head p {
  margin: 0;
  color: #6b7586;
  font-size: 16px;
  line-height: 1.45;
  font-weight: 850;
}

.v118-modal-head button {
  border: 0;
  width: 42px;
  height: 42px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 28px;
  font-weight: 900;
}

.v118-missing-summary {
  color: #9a6b0b;
  font-size: 18px;
  font-weight: 950;
  margin: 18px 0 12px;
}

.v118-missing-list {
  display: grid;
  gap: 8px;
}

.v118-missing-row {
  display: grid;
  grid-template-columns: 76px 1fr;
  gap: 3px 10px;
  padding: 10px 0;
  border-bottom: 1px solid #e6edf5;
}

.v118-missing-row b {
  font-size: 18px;
  font-weight: 1000;
}

.v118-missing-row span {
  color: #111827;
  font-size: 16px;
  font-weight: 900;
}

.v118-missing-row em {
  grid-column: 2;
  color: #9a6b0b;
  font-size: 13px;
  font-style: normal;
  font-weight: 850;
}

.v118-missing-note {
  margin: 16px 0;
  color: #64748b;
  background: #f8fafc;
  border: 1px solid #e6edf5;
  border-radius: 16px;
  padding: 14px;
  font-size: 16px;
  line-height: 1.55;
  font-weight: 850;
}

.v118-ok {
  width: 100%;
  border: 0;
  border-radius: 14px;
  background: #3b82f6;
  color: #fff;
  font-size: 20px;
  font-weight: 950;
  padding: 14px 18px;
  margin-top: 16px;
}

@media (max-width: 430px) {
  .v118-page {
    padding-left: 14px;
    padding-right: 14px;
  }

  .v118-range-label {
    font-size: 20px;
  }

  .v118-segment a {
    font-size: 18px;
    padding: 11px 0;
  }

  .v118-hero h1 {
    font-size: 38px;
  }

  .v118-quality {
    font-size: 16px;
  }

  .v118-focus-grid {
    gap: 10px;
  }

  .v118-focus-card {
    min-height: 160px;
    padding: 13px 12px;
    border-radius: 18px;
  }

  .v118-focus-title {
    font-size: 18px;
  }

  .v118-focus-name b {
    font-size: 20px;
  }

  .v118-focus-name span {
    font-size: 14px;
  }

  .v118-focus-price strong {
    font-size: 30px;
  }

  .v118-focus-price em {
    font-size: 16px;
  }

  .v118-focus-meta {
    font-size: 14px;
  }

  .v118-detail h2 {
    font-size: 30px;
  }

  .v118-head,
  .v118-row {
    grid-template-columns: minmax(78px, 1.05fr) minmax(62px, .72fr) minmax(86px, .98fr) minmax(68px, .82fr);
    column-gap: 6px;
  }

  .v118-head {
    padding-left: 7px;
    padding-right: 7px;
  }

  .v118-head button {
    font-size: 13px;
  }

  .v118-row {
    min-height: 78px;
    padding-left: 7px;
    padding-right: 7px;
  }

  .v118-stock b {
    font-size: 19px;
  }

  .v118-stock span,
  .v118-price span,
  .v118-flow span,
  .v118-action span {
    font-size: 13px;
  }

  .v118-price b {
    font-size: 19px;
  }

  .v118-flow b {
    font-size: 18px;
  }

  .v118-action .pill {
    min-width: 48px;
    font-size: 13px;
    padding: 5px 7px;
  }

  .v118-modal {
    padding: 22px 20px;
    border-radius: 22px;
  }

  .v118-modal-head h3 {
    font-size: 26px;
  }
}

@media (max-width: 370px) {
  .v118-focus-grid {
    grid-template-columns: 1fr;
  }

  .v118-head,
  .v118-row {
    grid-template-columns: minmax(72px, 1fr) 60px 82px 62px;
  }

  .v118-flow b {
    font-size: 16px;
  }
}
'''

if "V118 Signal Reset" not in css.read_text(encoding='utf-8'):
    css.write_text(css.read_text(encoding='utf-8') + css_append, encoding='utf-8')

readme.write_text("""# V118 Signal Reset

修正內容：
- 今日訊號只保留一組訊號區間。
- 首頁與 /signals 使用同一份 SignalsClient，避免重複區塊。
- 有 ETF 來源明細時，重新由來源 ETF 彙總，避免國巨張數等 aggregate 舊欄位覆蓋。
- 明細改成緊湊四欄，不再超出手機頁面。
- 排序改回欄位標題 ▲ / ▼。
- 點明細列可進入個股頁。
- 未更新 ETF 不再顯示 ETF 1、ETF 2 假資料。
""", encoding='utf-8')

print("✅ V118 已完成：SignalsClient 重置、首頁/訊號頁統一、緊湊表格與排序修正")
