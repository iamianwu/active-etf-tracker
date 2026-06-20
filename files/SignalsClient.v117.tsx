use client";

import Link from 'next/link';
import { useMemo, useState } from 'react';

type AnyRow = Record<string, any>;
type Status = '新增' | '刪除' | '加碼' | '減碼';
type SortKey = 'inflow' | 'outflow' | 'absAmount' | 'lots' | 'consensus' | 'price' | 'pct';

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

function explicitBuySell(row: AnyRow): { buy: number; sell: number; known: boolean } {
  const buy = firstNum(row, [
    'today_buy_etf_count',
    'today_add_etf_count',
    'net_buy_etf_count',
    'add_etf_count',
    'increase_etf_count',
    'increased_etf_count',
    'buy_etf_count',
  ], NaN);
  const sell = firstNum(row, [
    'today_sell_etf_count',
    'today_reduce_etf_count',
    'net_sell_etf_count',
    'reduce_etf_count',
    'decrease_etf_count',
    'decreased_etf_count',
    'sell_etf_count',
  ], NaN);

  if (Number.isFinite(buy) || Number.isFinite(sell)) {
    return {
      buy: Math.max(0, Math.round(Number.isFinite(buy) ? buy : 0)),
      sell: Math.max(0, Math.round(Number.isFinite(sell) ? sell : 0)),
      known: true,
    };
  }

  return { buy: 0, sell: 0, known: false };
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
    const key = [dateOf(r), etfCodeOf(r), codeOf(r), lotsOf(r), amountOf(r), statusOf(r) ?? ''].join('|');
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
      source_rows: [],
    };
    cur.stock_name = cur.stock_name || nameOf(r);
    if (cur.price === null || cur.price === undefined) cur.price = priceOf(r);
    if (cur.change_pct === null || cur.change_pct === undefined) cur.change_pct = pctOf(r);
    cur.net_lots += lotsOf(r);
    cur.net_amount_billion += amountOf(r);
    cur.source_rows.push(r);
    map.set(code, cur);
  }
  return Array.from(map.values());
}

function isAggregateCandidate(row: AnyRow): boolean {
  return Boolean(codeOf(row)) && !etfCodeOf(row);
}

function displayRowsOf(data: any, sourceRows: AnyRow[]): AnyRow[] {
  const main = rowsOf(data).filter(isAggregateCandidate);
  if (main.length) return main;
  if (sourceRows.length) return groupRowsFromSources(sourceRows);
  return rowsOf(data);
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
    })
    .sort((a, b) => Math.abs(lotsOf(b)) - Math.abs(lotsOf(a)));
}

function buySellOf(row: AnyRow, sources: AnyRow[]): { buy: number; sell: number; known: boolean } {
  if (sources.length) {
    let buy = 0;
    let sell = 0;
    for (const s of sources) {
      const lots = lotsOf(s);
      if (lots > 0) buy += 1;
      if (lots < 0) sell += 1;
    }
    return { buy, sell, known: true };
  }

  const direct = explicitBuySell(row);
  if (direct.known) return direct;

  const s = statusOf(row);
  if (s === '新增' || s === '加碼') return { buy: 1, sell: 0, known: false };
  if (s === '刪除' || s === '減碼') return { buy: 0, sell: 1, known: false };
  return { buy: 0, sell: 0, known: false };
}

function consensusScore(row: AnyRow): number {
  const bs = row.__buySell ?? { buy: 0, sell: 0 };
  return bs.buy - bs.sell;
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

function FocusCard({ title, row, kind, onOpen }: { title: string; row?: AnyRow | null; kind: 'red' | 'green'; onOpen: (row: AnyRow) => void }) {
  if (!row) {
    return (
      <div className={`focus-card-v117 ${kind}`}>
        <div className="focus-title-v117">{title}</div>
        <div className="focus-empty-v117">尚無有效訊號</div>
      </div>
    );
  }

  const amount = amountOf(row);
  const lots = lotsOf(row);
  const price = priceOf(row);
  const pct = pctOf(row);
  const bs = row.__buySell ?? { buy: 0, sell: 0 };

  return (
    <button type="button" className={`focus-card-v117 ${kind}`} onClick={() => onOpen(row)}>
      <div className="focus-title-v117">{title}</div>
      <div className="focus-name-v117">
        <span>{nameOf(row)}</span>
        <b>{codeOf(row)}</b>
      </div>
      <div className="focus-price-line-v117">
        <span className={isLimitUp(row) ? 'limit-up-pill-v117' : isLimitDown(row) ? 'limit-down-pill-v117' : ''}>{fmtPrice(price)}</span>
        <b className={toneClass(pct ?? 0)}>{fmtPct(pct)}</b>
      </div>
      <div className="focus-metrics-v117">
        <span>淨額 <b className={toneClass(amount)}>{fmtBillion(amount)}</b></span>
        <span>張數 <b className={toneClass(lots)}>{fmtLots(lots)}</b></span>
        <span>異動ETF <b>{bs.buy}:{bs.sell}</b></span>
      </div>
    </button>
  );
}

function SourceModal({ row, onClose }: { row: AnyRow | null; onClose: () => void }) {
  if (!row) return null;

  const sources: AnyRow[] = row.__sources ?? [];
  const amount = amountOf(row);
  const lots = lotsOf(row);

  return (
    <div className="signals-modal-mask-v117" onClick={onClose}>
      <div className="signals-modal-v117" onClick={(e) => e.stopPropagation()}>
        <div className="signals-modal-head-v117">
          <div>
            <h3>{nameOf(row)} {codeOf(row)}</h3>
            <p>全部 ETF 合計：<b className={toneClass(amount)}>{fmtBillion(amount)}</b>，<b className={toneClass(lots)}>{fmtLots(lots)}</b></p>
          </div>
          <button type="button" onClick={onClose} aria-label="關閉">×</button>
        </div>

        {sources.length ? (
          <div className="source-list-v117">
            {sources.map((s, i) => {
              const sl = lotsOf(s);
              const sa = amountOf(s);
              const st = statusOf(s);
              return (
                <div className="source-row-v117" key={`${etfCodeOf(s)}-${dateOf(s)}-${i}`}>
                  <div>
                    <b>{etfCodeOf(s)}</b>
                    <span>{etfNameOf(s)}</span>
                    <em>{mmdd(dateOf(s))}</em>
                  </div>
                  <div>
                    <b className={toneClass(sl)}>{fmtLots(sl)}</b>
                    <span className={toneClass(sa)}>{fmtBillion(sa)}</span>
                  </div>
                  <strong className={st === '新增' || st === '加碼' ? 'is-red' : 'is-green'}>{st ?? '-'}</strong>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="source-empty-v117">
            目前 /signals API 尚未回傳這檔股票的來源 ETF 明細。此列顯示的是全部 ETF 合計後的淨變化。
          </div>
        )}

        <Link className="source-stock-link-v117" href={`/stock/${codeOf(row)}`}>進入個股詳情 ›</Link>
      </div>
    </div>
  );
}

function MissingModal({ data, onClose }: { data: any; onClose: () => void }) {
  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const rows = missingRowsOf(data);

  return (
    <div className="signals-modal-mask-v117" onClick={onClose}>
      <div className="signals-modal-v117" onClick={(e) => e.stopPropagation()}>
        <div className="signals-modal-head-v117">
          <div>
            <h3>未更新 ETF 清單</h3>
            <p>今日訊號只使用當日資料，不混入前一日資料。</p>
          </div>
          <button type="button" onClick={onClose} aria-label="關閉">×</button>
        </div>

        <div className="missing-summary-v117">已取得 {today} / {total} 檔，未更新 {missing} 檔</div>

        {rows.length ? (
          <div className="missing-list-v117">
            {rows.map((r, i) => (
              <div className="missing-row-v117" key={`${etfCodeOf(r) || firstText(r, ['etf_code', 'code'], `ETF ${i + 1}`)}-${i}`}>
                <b>{etfCodeOf(r) || firstText(r, ['etf_code', 'code'], `ETF ${i + 1}`)}</b>
                <span>{etfNameOf(r) || firstText(r, ['name', 'etf_name'], '')}</span>
                <em>{dateOf(r) ? `最後資料 ${mmdd(dateOf(r))}` : '尚無日期'}</em>
              </div>
            ))}
          </div>
        ) : (
          <div className="source-empty-v117">
            目前 API 只回傳未更新數量，尚未回傳 ETF 代號清單。下一步可在 /signals API 補回 non_today_etfs。
          </div>
        )}

        <button type="button" className="modal-ok-v117" onClick={onClose}>我知道了</button>
      </div>
    </div>
  );
}

function DataQuality({ data, activeDays, onOpenMissing }: { data: any; activeDays: number; onOpenMissing: () => void }) {
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
    <div className="signals-quality-v117">
      <span>資料日 <b>{mmdd(date)}</b></span>
      <span>已取得今日資料 <b>{today} / {total}</b> 檔 ETF</span>
      {missing > 0 && (
        <button type="button" className="missing-link-v117" onClick={onOpenMissing}>
          未更新 {missing} 檔，查看清單
        </button>
      )}
    </div>
  );
}

function SortButton({ label, sortKey, active, order, onClick }: { label: string; sortKey: SortKey; active: SortKey; order: 'asc' | 'desc'; onClick: (key: SortKey) => void }) {
  const isActive = active === sortKey;
  return (
    <button type="button" className={isActive ? 'active' : ''} onClick={() => onClick(sortKey)}>
      {label} <span>{isActive ? (order === 'desc' ? '▼' : '▲') : '↕'}</span>
    </button>
  );
}

function RowLine({ row, onOpen }: { row: AnyRow; onOpen: (row: AnyRow) => void }) {
  const code = codeOf(row);
  const price = priceOf(row);
  const pct = pctOf(row);
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const st = statusOf(row);
  const bs = row.__buySell ?? { buy: 0, sell: 0 };
  const sources: AnyRow[] = row.__sources ?? [];

  return (
    <div className="signal-row-v117">
      <Link href={`/stock/${code}`} className="signal-cell-target-v117">
        <b>{nameOf(row)}</b>
        <span>{code}</span>
      </Link>

      <Link href={`/stock/${code}`} className="signal-cell-price-v117">
        <b className={isLimitUp(row) ? 'limit-up-pill-v117' : isLimitDown(row) ? 'limit-down-pill-v117' : ''}>{fmtPrice(price)}</b>
        <span className={toneClass(pct ?? 0)}>{fmtPct(pct)}</span>
      </Link>

      <button type="button" className="signal-cell-flow-v117" onClick={() => onOpen(row)}>
        <b className={toneClass(amount)}>{fmtBillion(amount)}</b>
        <span className={toneClass(lots)}>{fmtLots(lots)}</span>
        {sources.length > 0 && <em>來源 {sources.length} 檔</em>}
      </button>

      <div className="signal-cell-status-v117">
        <span className={`status-pill-v117 ${st === '新增' ? 'add' : st === '刪除' ? 'delete' : st === '加碼' ? 'buy' : st === '減碼' ? 'sell' : ''}`}>{st ?? '-'}</span>
        <b>買賣 {bs.buy}:{bs.sell}</b>
      </div>
    </div>
  );
}

export default function SignalsClient(props: { data: any; activeDays?: number }) {
  const data = props?.data ?? {};
  const activeDays = Number(props?.activeDays ?? data?.days ?? 1) || 1;

  const [filter, setFilter] = useState<'全部' | Status>('全部');
  const [sortKey, setSortKey] = useState<SortKey>('inflow');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [openedRow, setOpenedRow] = useState<AnyRow | null>(null);
  const [showMissing, setShowMissing] = useState(false);

  const preparedRows = useMemo(() => {
    const sources = sourceRowsOf(data);
    return displayRowsOf(data, sources)
      .filter((r) => codeOf(r))
      .map((r) => {
        const rowSources = sourcesFor(r, sources);
        return {
          ...r,
          __sources: rowSources,
          __buySell: buySellOf(r, rowSources),
        };
      });
  }, [data]);

  const counts = useMemo(() => statusCounts(preparedRows), [preparedRows]);

  const filteredRows = useMemo(() => {
    const base = filter === '全部' ? preparedRows : preparedRows.filter((r) => statusOf(r) === filter);
    const dir = sortOrder === 'desc' ? -1 : 1;

    const valueOf = (r: AnyRow) => {
      switch (sortKey) {
        case 'inflow':
          return amountOf(r);
        case 'outflow':
          return amountOf(r);
        case 'absAmount':
          return Math.abs(amountOf(r));
        case 'lots':
          return lotsOf(r);
        case 'consensus':
          return consensusScore(r);
        case 'price':
          return priceOf(r) ?? -Infinity;
        case 'pct':
          return pctOf(r) ?? -Infinity;
        default:
          return 0;
      }
    };

    return [...base].sort((a, b) => {
      const av = valueOf(a);
      const bv = valueOf(b);
      return av === bv ? codeOf(a).localeCompare(codeOf(b)) : (av > bv ? 1 : -1) * dir;
    });
  }, [preparedRows, filter, sortKey, sortOrder]);

  const focus = useMemo(() => {
    const inflows = preparedRows.filter((r) => amountOf(r) > 0).sort((a, b) => amountOf(b) - amountOf(a));
    const outflows = preparedRows.filter((r) => amountOf(r) < 0).sort((a, b) => amountOf(a) - amountOf(b));
    const buys = preparedRows.filter((r) => (r.__buySell?.buy ?? 0) > 0).sort((a, b) => (b.__buySell?.buy ?? 0) - (a.__buySell?.buy ?? 0) || lotsOf(b) - lotsOf(a));
    const sells = preparedRows.filter((r) => (r.__buySell?.sell ?? 0) > 0).sort((a, b) => (b.__buySell?.sell ?? 0) - (a.__buySell?.sell ?? 0) || lotsOf(a) - lotsOf(b));

    return {
      inflow: inflows[0] ?? null,
      outflow: outflows[0] ?? null,
      buy: buys[0] ?? null,
      sell: sells[0] ?? null,
    };
  }, [preparedRows]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortOrder((old) => (old === 'desc' ? 'asc' : 'desc'));
      return;
    }
    setSortKey(key);
    setSortOrder(key === 'outflow' ? 'asc' : 'desc');
  }

  const title = activeDays === 1 ? '今日訊號' : `近${activeDays}日訊號`;

  return (
    <div className="signals-page-v117">
      <h1>{title}</h1>
      <DataQuality data={data} activeDays={activeDays} onOpenMissing={() => setShowMissing(true)} />

      <div className="focus-grid-v117">
        <FocusCard title="淨資金流入最多" row={focus.inflow} kind="red" onOpen={setOpenedRow} />
        <FocusCard title="淨資金流出最多" row={focus.outflow} kind="green" onOpen={setOpenedRow} />
        <FocusCard title="最多 ETF 加碼" row={focus.buy} kind="red" onOpen={setOpenedRow} />
        <FocusCard title="最多 ETF 減碼" row={focus.sell} kind="green" onOpen={setOpenedRow} />
      </div>

      <section className="signal-detail-v117">
        <h2>資金交易明細：共 {filteredRows.length} 檔</h2>

        <div className="status-chips-v117">
          <button className={filter === '新增' ? 'active add' : 'add'} onClick={() => setFilter(filter === '新增' ? '全部' : '新增')}>新增 {counts.新增}</button>
          <button className={filter === '刪除' ? 'active delete' : 'delete'} onClick={() => setFilter(filter === '刪除' ? '全部' : '刪除')}>刪除 {counts.刪除}</button>
          <button className={filter === '加碼' ? 'active buy' : 'buy'} onClick={() => setFilter(filter === '加碼' ? '全部' : '加碼')}>加碼 {counts.加碼}</button>
          <button className={filter === '減碼' ? 'active sell' : 'sell'} onClick={() => setFilter(filter === '減碼' ? '全部' : '減碼')}>減碼 {counts.減碼}</button>
        </div>

        <div className="sort-scroll-v117">
          <SortButton label="淨流入" sortKey="inflow" active={sortKey} order={sortOrder} onClick={toggleSort} />
          <SortButton label="淨流出" sortKey="outflow" active={sortKey} order={sortOrder} onClick={toggleSort} />
          <SortButton label="絕對金額" sortKey="absAmount" active={sortKey} order={sortOrder} onClick={toggleSort} />
          <SortButton label="張數" sortKey="lots" active={sortKey} order={sortOrder} onClick={toggleSort} />
          <SortButton label="共識" sortKey="consensus" active={sortKey} order={sortOrder} onClick={toggleSort} />
          <SortButton label="股價" sortKey="price" active={sortKey} order={sortOrder} onClick={toggleSort} />
          <SortButton label="漲跌幅" sortKey="pct" active={sortKey} order={sortOrder} onClick={toggleSort} />
        </div>

        <div className="signal-table-v117">
          <div className="signal-header-v117">
            <span>標的 ↕</span>
            <span>股價 ↕</span>
            <span>淨額 / 張數 ↕</span>
            <span>狀態 / 異動ETF</span>
          </div>
          {filteredRows.map((row, i) => (
            <RowLine key={`${codeOf(row)}-${i}`} row={row} onOpen={setOpenedRow} />
          ))}
        </div>
      </section>

      <SourceModal row={openedRow} onClose={() => setOpenedRow(null)} />
      {showMissing && <MissingModal data={data} onClose={() => setShowMissing(false)} />}
    </div>
  );
}
