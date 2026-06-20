from pathlib import Path

root = Path(".")
comp = root / "frontend/components/SignalsClient.tsx"
css = root / "frontend/app/globals.css"
page = root / "frontend/app/signals/page.tsx"
home = root / "frontend/app/page.tsx"

comp.write_text(r''''use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

type AnyRow = Record<string, any>;
type Status = '新增' | '刪除' | '加碼' | '減碼';
type SortKey = 'inflow' | 'outflow' | 'absAmount' | 'lots' | 'price' | 'pct';
type FilterKey = '全部' | Status;

const TOTAL_ACTIVE_ETFS = 27;
const STATUSES: Status[] = ['新增', '刪除', '加碼', '減碼'];

function num(v: any, fallback = 0): number {
  if (v === null || v === undefined || v === '') return fallback;
  const x = Number(String(v).replace(/,/g, '').replace(/[^\d.-]/g, ''));
  return Number.isFinite(x) ? x : fallback;
}

function txt(row: AnyRow, keys: string[], fallback = ''): string {
  for (const k of keys) {
    const v = row?.[k];
    if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
  }
  return fallback;
}

function firstNum(row: AnyRow, keys: string[], fallback = NaN): number {
  for (const k of keys) {
    const v = row?.[k];
    if (v !== undefined && v !== null && String(v).trim() !== '') {
      const n = num(v, NaN);
      if (Number.isFinite(n)) return n;
    }
  }
  return fallback;
}

function arr(data: any, keys: string[]): AnyRow[] {
  const out: AnyRow[] = [];
  for (const k of keys) {
    const v = data?.[k];
    if (Array.isArray(v)) out.push(...v);
  }
  return out;
}

function rowsOf(data: any): AnyRow[] {
  const v = data?.rows ?? data?.changes ?? data?.aggregate ?? data?.items ?? data?.signals ?? [];
  return Array.isArray(v) ? v : [];
}

function codeOf(r: AnyRow): string {
  return txt(r, ['stock_code', 'stockCode', 'code', 'symbol']);
}

function nameOf(r: AnyRow): string {
  return txt(r, ['stock_name', 'stockName', 'name', 'stock'], codeOf(r));
}

function etfCodeOf(r: AnyRow): string {
  return txt(r, ['etf_code', 'etfCode', 'fund_code', 'fundCode', 'etf']);
}

function etfNameOf(r: AnyRow): string {
  return txt(r, ['etf_name', 'etfName', 'fund_name', 'fundName'], etfCodeOf(r));
}

function dateOf(r: AnyRow): string {
  return txt(r, ['data_date', 'date', 'trade_date', 'tradeDate', 'dt']);
}

function priceOf(r: AnyRow): number | null {
  const v = firstNum(r, ['price', 'close_price', 'close', 'last_price', 'stock_price'], NaN);
  return Number.isFinite(v) ? v : null;
}

function pctOf(r: AnyRow): number | null {
  const v = firstNum(r, ['change_pct', 'pct', 'percent', 'changePercent', 'price_change_pct'], NaN);
  return Number.isFinite(v) ? v : null;
}

function lotsOf(r: AnyRow): number {
  const lotVal = firstNum(r, [
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
  ], NaN);
  if (Number.isFinite(lotVal)) return lotVal;

  let shareVal = firstNum(r, [
    'delta_shares',
    'shares_change',
    'shares_diff',
    'diff_shares',
    'shareDiff',
  ], 0);

  if (Math.abs(shareVal) >= 10000) shareVal = shareVal / 1000;
  return shareVal;
}

function amountOf(r: AnyRow): number {
  const direct = firstNum(r, [
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

  const p = priceOf(r);
  const lots = lotsOf(r);
  if (p !== null && Number.isFinite(lots)) return p * lots * 1000 / 100000000;
  return 0;
}

function statusOf(r: AnyRow): Status | null {
  const s = String(r.status ?? r.type ?? r.action ?? '').trim();
  if (STATUSES.includes(s as Status)) return s as Status;

  const lots = lotsOf(r);
  if (lots > 0) return '加碼';
  if (lots < 0) return '減碼';
  return null;
}

function sourceRowsOf(data: any): AnyRow[] {
  const direct = arr(data, [
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
  ]);

  const nested = rowsOf(data).flatMap((r) => arr(r, [
    'source_rows',
    'sourceRows',
    'details',
    'records',
    'operation_records',
    'operationRecords',
    'etf_changes',
    'etfChanges',
  ]));

  const fromRows = rowsOf(data).filter((r) => etfCodeOf(r) && codeOf(r));
  const all = [...direct, ...nested, ...fromRows].filter((r) => etfCodeOf(r) && codeOf(r));

  const seen = new Set<string>();
  return all.filter((r) => {
    const key = [dateOf(r), etfCodeOf(r), codeOf(r), lotsOf(r), amountOf(r), statusOf(r) ?? ''].join('|');
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function groupFromSources(src: AnyRow[]): AnyRow[] {
  const m = new Map<string, AnyRow>();

  for (const r of src) {
    const code = codeOf(r);
    if (!code) continue;

    const cur = m.get(code) ?? {
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

    m.set(code, cur);
  }

  return Array.from(m.values());
}

function displayRowsOf(data: any, src: AnyRow[]): AnyRow[] {
  const aggregate = rowsOf(data).filter((r) => codeOf(r) && !etfCodeOf(r));
  if (aggregate.length) return aggregate;
  if (src.length) return groupFromSources(src);
  return rowsOf(data).filter((r) => codeOf(r));
}

function sourcesFor(row: AnyRow, allSrc: AnyRow[]): AnyRow[] {
  const code = codeOf(row);
  const nested = arr(row, [
    'source_rows',
    'sourceRows',
    'details',
    'records',
    'operation_records',
    'operationRecords',
    'etf_changes',
    'etfChanges',
  ]);

  const global = allSrc.filter((r) => codeOf(r) === code);
  const seen = new Set<string>();

  return [...nested, ...global]
    .filter((r) => etfCodeOf(r))
    .filter((r) => {
      const key = [dateOf(r), etfCodeOf(r), lotsOf(r), amountOf(r), statusOf(r) ?? ''].join('|');
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function buySell(row: AnyRow, src: AnyRow[]): { buy: number; sell: number } {
  if (src.length) {
    let buy = 0;
    let sell = 0;
    for (const s of src) {
      const lots = lotsOf(s);
      if (lots > 0) buy += 1;
      if (lots < 0) sell += 1;
    }
    return { buy, sell };
  }

  const directBuy = firstNum(row, ['buy_count', 'buy_etf_count', 'add_etf_count', 'increase_count'], NaN);
  const directSell = firstNum(row, ['sell_count', 'sell_etf_count', 'reduce_etf_count', 'decrease_count'], NaN);
  if (Number.isFinite(directBuy) || Number.isFinite(directSell)) {
    return {
      buy: Math.max(0, Math.round(Number.isFinite(directBuy) ? directBuy : 0)),
      sell: Math.max(0, Math.round(Number.isFinite(directSell) ? directSell : 0)),
    };
  }

  const s = statusOf(row);
  if (s === '新增' || s === '加碼') return { buy: 1, sell: 0 };
  if (s === '刪除' || s === '減碼') return { buy: 0, sell: 1 };
  return { buy: 0, sell: 0 };
}

function mmdd(v: any): string {
  const s = String(v ?? '').trim();
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

function tone(v: number): string {
  if (v > 0) return 'red';
  if (v < 0) return 'green';
  return 'muted';
}

function isLimitUp(row: AnyRow): boolean {
  const p = pctOf(row);
  return p !== null && p >= 9.7;
}

function getTotalEtfs(data: any): number {
  const v = firstNum(data, ['total_etf_count', 'totalEtfCount', 'total_etfs', 'totalEtfs'], NaN);
  return Number.isFinite(v) && v > 0 ? Math.max(TOTAL_ACTIVE_ETFS, Math.round(v)) : TOTAL_ACTIVE_ETFS;
}

function getTodayEtfs(data: any, total: number): number {
  const v = firstNum(data, ['today_etf_count', 'todayEtfCount', 'today_etfs', 'todayEtfs', 'fetched_etf_count', 'includedEtfCount'], NaN);
  if (Number.isFinite(v) && v >= 0) return Math.min(total, Math.round(v));

  const missing = firstNum(data, ['non_today_etf_count', 'nonTodayEtfCount', 'missing_etf_count'], NaN);
  if (Number.isFinite(missing) && missing >= 0) return Math.max(0, total - Math.round(missing));

  return total;
}

function missingRowsOf(data: any): AnyRow[] {
  return arr(data, ['non_today_etfs', 'nonTodayEtfs', 'missing_etfs', 'missingEtfs', 'stale_etfs', 'staleEtfs']);
}

function sortRows(rows: AnyRow[], key: SortKey): AnyRow[] {
  const copy = [...rows];

  copy.sort((a, b) => {
    if (key === 'inflow') return amountOf(b) - amountOf(a);
    if (key === 'outflow') return amountOf(a) - amountOf(b);
    if (key === 'absAmount') return Math.abs(amountOf(b)) - Math.abs(amountOf(a));
    if (key === 'lots') return Math.abs(lotsOf(b)) - Math.abs(lotsOf(a));
    if (key === 'price') return (priceOf(b) ?? -Infinity) - (priceOf(a) ?? -Infinity);
    if (key === 'pct') return (pctOf(b) ?? -Infinity) - (pctOf(a) ?? -Infinity);
    return 0;
  });

  return copy;
}

function getFocusRows(rows: AnyRow[]) {
  const inflow = rows.filter((r) => amountOf(r) > 0).sort((a, b) => amountOf(b) - amountOf(a))[0] ?? null;
  const outflow = rows.filter((r) => amountOf(r) < 0).sort((a, b) => amountOf(a) - amountOf(b))[0] ?? null;
  const mostAdd = rows.filter((r) => lotsOf(r) > 0).sort((a, b) => (b.__buySell.buy - a.__buySell.buy) || (lotsOf(b) - lotsOf(a)))[0] ?? null;
  const mostReduce = rows.filter((r) => lotsOf(r) < 0).sort((a, b) => (b.__buySell.sell - a.__buySell.sell) || (Math.abs(lotsOf(b)) - Math.abs(lotsOf(a))))[0] ?? null;
  return { inflow, outflow, mostAdd, mostReduce };
}

function FocusCard({ title, row, kind }: { title: string; row: AnyRow | null; kind: 'red' | 'green' }) {
  if (!row) {
    return (
      <div className={`v120-focus ${kind}`}>
        <b>{title}</b>
        <span>尚無有效訊號</span>
      </div>
    );
  }

  const amount = amountOf(row);
  const lots = lotsOf(row);
  const p = priceOf(row);
  const pct = pctOf(row);
  const bs = row.__buySell ?? { buy: 0, sell: 0 };

  return (
    <Link className={`v120-focus ${kind}`} href={`/stock/${codeOf(row)}`}>
      <b>{title}</b>
      <div className="v120-focus-name">
        <strong>{nameOf(row)}</strong>
        <em>{codeOf(row)}</em>
      </div>
      <div className="v120-focus-price">
        <strong>{fmtPrice(p)}</strong>
        <span className={tone(pct ?? 0)}>{fmtPct(pct)}</span>
      </div>
      <div className="v120-focus-meta">
        <span>淨額 <i className={tone(amount)}>{fmtBillion(amount)}</i></span>
        <span>張數 <i className={tone(lots)}>{fmtLots(lots)}</i></span>
        <span>異動ETF {bs.buy}:{bs.sell}</span>
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
    <div className="v120-modal-mask" onClick={onClose}>
      <div className="v120-modal" onClick={(e) => e.stopPropagation()}>
        <button className="v120-modal-x" type="button" onClick={onClose}>×</button>
        <h3>未更新 ETF</h3>
        <p>今日訊號只使用當日資料，不混入前一日資料。</p>
        <div className="v120-modal-count">已取得 {today} / {total} 檔，未更新 {missing} 檔</div>

        {rows.length ? (
          <div className="v120-missing-list">
            {rows.map((r, i) => (
              <div className="v120-missing-row" key={`${etfCodeOf(r) || i}`}>
                <b>{etfCodeOf(r)}</b>
                <span>{etfNameOf(r)}</span>
                <em>{dateOf(r) ? `最後資料 ${mmdd(dateOf(r))}` : '尚無日期'}</em>
              </div>
            ))}
          </div>
        ) : (
          <div className="v120-modal-note">
            目前 API 只回傳「未更新數量」，尚未回傳 ETF 代號清單，所以這裡不再顯示 ETF 1、ETF 2 這種假資料。
          </div>
        )}

        <button className="v120-modal-ok" type="button" onClick={onClose}>我知道了</button>
      </div>
    </div>
  );
}

function RangeTabs({ activeDays }: { activeDays: number }) {
  const items = [1, 5, 10, 20];
  return (
    <section className="v120-range">
      <div className="v120-range-label">訊號區間</div>
      <div className="v120-range-tabs">
        {items.map((d) => (
          <Link key={d} href={d === 1 ? '/signals' : `/signals?days=${d}`} className={activeDays === d ? 'active' : ''}>
            {d === 1 ? '今日' : `${d}日`}
          </Link>
        ))}
      </div>
    </section>
  );
}

function SortButton({ label, active, onClick, arrow }: { label: string; active: boolean; onClick: () => void; arrow: string }) {
  return (
    <button type="button" className={active ? 'active' : ''} onClick={onClick}>
      {label} <span>{arrow}</span>
    </button>
  );
}

function DetailRow({ row }: { row: AnyRow }) {
  const p = priceOf(row);
  const pct = pctOf(row);
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const st = statusOf(row);
  const bs = row.__buySell ?? { buy: 0, sell: 0 };

  return (
    <Link className="v120-row" href={`/stock/${codeOf(row)}`}>
      <div className="v120-target">
        <b>{nameOf(row)}</b>
        <span>{codeOf(row)}</span>
      </div>

      <div className="v120-price">
        <b>{fmtPrice(p)}</b>
        <span className={tone(pct ?? 0)}>{fmtPct(pct)}</span>
        {isLimitUp(row) && <em>漲停</em>}
      </div>

      <div className="v120-flow">
        <b className={tone(amount)}>{fmtBillion(amount)}</b>
        <span className={tone(lots)}>{fmtLots(lots)}</span>
      </div>

      <div className="v120-status">
        {st && <b className={st === '新增' ? 'new' : st === '加碼' ? 'add' : 'reduce'}>{st}</b>}
        <span>異動 {bs.buy}:{bs.sell}</span>
      </div>
    </Link>
  );
}

export default function SignalsClient(props: { data: any; activeDays?: number }) {
  const data = props.data ?? {};
  const activeDays = Number(props.activeDays ?? data?.signalRangeDays ?? data?.rangeDays ?? 1) || 1;

  const [filter, setFilter] = useState<FilterKey>('全部');
  const [sortKey, setSortKey] = useState<SortKey>(activeDays === 1 ? 'inflow' : 'absAmount');
  const [showMissing, setShowMissing] = useState(false);

  const sourceRows = useMemo(() => sourceRowsOf(data), [data]);

  const rows = useMemo(() => {
    const base = displayRowsOf(data, sourceRows)
      .filter((r) => codeOf(r))
      .map((r) => {
        const src = sourcesFor(r, sourceRows);
        return { ...r, __sources: src, __buySell: buySell(r, src) };
      });

    return base;
  }, [data, sourceRows]);

  const counts = useMemo(() => {
    const out: Record<Status, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0 };
    for (const r of rows) {
      const s = statusOf(r);
      if (s) out[s] += 1;
    }
    return out;
  }, [rows]);

  const filteredRows = useMemo(() => {
    const f = filter === '全部' ? rows : rows.filter((r) => statusOf(r) === filter);
    return sortRows(f, sortKey);
  }, [rows, filter, sortKey]);

  const focus = useMemo(() => getFocusRows(rows), [rows]);

  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';

  return (
    <main className="signals-v120">
      <RangeTabs activeDays={activeDays} />

      <section className="v120-title">
        <h1>{activeDays === 1 ? '今日訊號' : `近${activeDays}日訊號`}</h1>
        <div className="v120-quality">
          {activeDays === 1 ? (
            <>
              <span>資料日 <b>{mmdd(date)}</b></span>
              <span>已取得今日資料 <b>{today} / {total}</b> 檔 ETF</span>
              {missing > 0 && (
                <button type="button" onClick={() => setShowMissing(true)}>
                  未更新 {missing} 檔，查看說明
                </button>
              )}
            </>
          ) : (
            <>
              <span>區間 <b>近 {activeDays} 日</b></span>
              <span>最新資料日 <b>{mmdd(date)}</b></span>
            </>
          )}
        </div>
      </section>

      <section className="v120-focus-grid">
        <FocusCard title="淨資金流入最多" row={focus.inflow} kind="red" />
        <FocusCard title="淨資金流出最多" row={focus.outflow} kind="green" />
        <FocusCard title="最多 ETF 加碼" row={focus.mostAdd} kind="red" />
        <FocusCard title="最多 ETF 減碼" row={focus.mostReduce} kind="green" />
      </section>

      <section className="v120-detail">
        <h2>資金交易明細：共 {filteredRows.length} 檔</h2>

        <div className="v120-status-tabs">
          <button type="button" className={filter === '全部' ? 'active all' : ''} onClick={() => setFilter('全部')}>全部 {rows.length}</button>
          <button type="button" className={filter === '新增' ? 'active new' : 'new'} onClick={() => setFilter('新增')}>新增 {counts.新增}</button>
          <button type="button" className={filter === '刪除' ? 'active remove' : 'remove'} onClick={() => setFilter('刪除')}>刪除 {counts.刪除}</button>
          <button type="button" className={filter === '加碼' ? 'active add' : 'add'} onClick={() => setFilter('加碼')}>加碼 {counts.加碼}</button>
          <button type="button" className={filter === '減碼' ? 'active reduce' : 'reduce'} onClick={() => setFilter('減碼')}>減碼 {counts.減碼}</button>
        </div>

        <div className="v120-sort-tabs">
          <SortButton label="淨流入" active={sortKey === 'inflow'} arrow={sortKey === 'inflow' ? '▼' : '↕'} onClick={() => setSortKey('inflow')} />
          <SortButton label="淨流出" active={sortKey === 'outflow'} arrow={sortKey === 'outflow' ? '▼' : '↕'} onClick={() => setSortKey('outflow')} />
          <SortButton label="絕對金額" active={sortKey === 'absAmount'} arrow={sortKey === 'absAmount' ? '▼' : '↕'} onClick={() => setSortKey('absAmount')} />
          <SortButton label="張數" active={sortKey === 'lots'} arrow={sortKey === 'lots' ? '▼' : '↕'} onClick={() => setSortKey('lots')} />
          <SortButton label="股價" active={sortKey === 'price'} arrow={sortKey === 'price' ? '▼' : '↕'} onClick={() => setSortKey('price')} />
          <SortButton label="漲跌幅" active={sortKey === 'pct'} arrow={sortKey === 'pct' ? '▼' : '↕'} onClick={() => setSortKey('pct')} />
        </div>

        <div className="v120-table">
          <div className="v120-head">
            <span>標的</span>
            <span>股價</span>
            <span>淨額 / 張數</span>
            <span>狀態 / 異動</span>
          </div>

          {filteredRows.length ? (
            filteredRows.map((r) => <DetailRow key={`${codeOf(r)}-${amountOf(r)}-${lotsOf(r)}-${sortKey}`} row={r} />)
          ) : (
            <div className="v120-empty">目前沒有符合條件的訊號。</div>
          )}
        </div>
      </section>

      {showMissing && <MissingModal data={data} onClose={() => setShowMissing(false)} />}
    </main>
  );
}
''', encoding="utf-8")

# 讓首頁和 /signals 使用同一份邏輯，避免首頁與 signals 頁不同步
page_content = r'''import { apiGet } from '@/lib/api';
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
'''
page.write_text(page_content, encoding="utf-8")
home.write_text(page_content, encoding="utf-8")

# 只加最後一段 V120 CSS，完全壓過舊版 signals 樣式
block = r'''
/* ===== V120 FINAL SIGNALS RESET ===== */
.signals-v120 {
  --navy: #121a2b;
  --muted: #7b8798;
  --line: #e6ecf4;
  --blue: #2f70d0;
  --red: #d85b66;
  --green: #2fa879;
  max-width: 460px;
  margin: 0 auto;
  padding: 18px 16px 72px;
  color: var(--navy);
  background: #fff;
  overflow-x: hidden;
  box-sizing: border-box;
}

.signals-v120 * {
  box-sizing: border-box;
}

.signals-v120 a {
  color: inherit;
  text-decoration: none;
}

.v120-range {
  margin: 4px 0 30px;
}

.v120-range-label {
  color: var(--muted);
  font-size: 18px;
  font-weight: 900;
  margin-bottom: 10px;
}

.v120-range-tabs {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  background: #eef3f9;
  border: 1px solid #dce5f0;
  border-radius: 999px;
  padding: 5px;
}

.v120-range-tabs a {
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  color: #66758a;
  font-size: 19px;
  font-weight: 950;
}

.v120-range-tabs a.active {
  color: var(--blue);
  background: #fff;
  box-shadow: 0 4px 12px rgba(20, 40, 70, 0.08);
}

.v120-title {
  margin-bottom: 18px;
}

.v120-title h1 {
  margin: 0 0 8px;
  font-size: 40px;
  line-height: 1.05;
  letter-spacing: -0.04em;
  font-weight: 1000;
}

.v120-quality {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  color: var(--muted);
  font-size: 17px;
  line-height: 1.35;
  font-weight: 900;
}

.v120-quality b {
  color: var(--navy);
}

.v120-quality button {
  border: 0;
  background: transparent;
  padding: 0;
  color: #a67b20;
  font: inherit;
  text-decoration: underline;
}

.v120-focus-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0 28px;
}

.v120-focus {
  min-width: 0;
  min-height: 160px;
  border: 1.5px solid #f0cbd1;
  border-radius: 20px;
  padding: 14px 13px;
  background: #fff8f9;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  text-align: left;
}

.v120-focus.green {
  border-color: #bfe8d9;
  background: #f3fffa;
}

.v120-focus > b {
  color: var(--red);
  font-size: 19px;
  line-height: 1.2;
  font-weight: 1000;
}

.v120-focus.green > b {
  color: var(--green);
}

.v120-focus-name {
  margin-top: 12px;
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.v120-focus-name strong {
  min-width: 0;
  max-width: 118px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 23px;
  line-height: 1.1;
  font-weight: 1000;
}

.v120-focus-name em {
  flex: 0 0 auto;
  color: #8b96a8;
  font-style: normal;
  font-size: 15px;
  font-weight: 950;
}

.v120-focus-price {
  margin-top: 8px;
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.v120-focus-price strong {
  min-width: 0;
  font-size: 34px;
  line-height: 0.95;
  font-weight: 1000;
  letter-spacing: -0.045em;
}

.v120-focus-price span {
  flex: 0 0 auto;
  font-size: 16px;
  font-weight: 1000;
}

.v120-focus-meta {
  margin-top: 9px;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.35;
  font-weight: 900;
  display: grid;
  gap: 1px;
}

.v120-focus-meta i {
  font-style: normal;
}

.v120-detail h2 {
  margin: 0 0 12px;
  font-size: 30px;
  line-height: 1.1;
  letter-spacing: -0.04em;
  font-weight: 1000;
}

.v120-status-tabs,
.v120-sort-tabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  padding: 1px 0 10px;
  scrollbar-width: none;
}

.v120-status-tabs::-webkit-scrollbar,
.v120-sort-tabs::-webkit-scrollbar {
  display: none;
}

.v120-status-tabs button,
.v120-sort-tabs button {
  flex: 0 0 auto;
  border: 2px solid #cfd8e5;
  border-radius: 999px;
  background: #fff;
  color: #6f7b8e;
  min-height: 39px;
  padding: 0 15px;
  font-size: 17px;
  font-weight: 950;
}

.v120-status-tabs button.active,
.v120-sort-tabs button.active {
  color: var(--blue);
  border-color: #c7dcff;
  background: #eef6ff;
}

.v120-status-tabs .new,
.v120-status-tabs .new.active {
  color: #b89a10;
  border-color: #d2b500;
}

.v120-status-tabs .add,
.v120-status-tabs .add.active {
  color: var(--red);
  border-color: var(--red);
}

.v120-status-tabs .reduce,
.v120-status-tabs .reduce.active {
  color: var(--green);
  border-color: var(--green);
}

.v120-table {
  margin-top: 8px;
  width: 100%;
  overflow: hidden;
  border-top: 1px solid var(--line);
}

.v120-head,
.v120-row {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) 72px 100px 74px;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.v120-head {
  min-height: 48px;
  padding: 0 8px;
  background: #f1f4f8;
  color: #687589;
  font-size: 14px;
  font-weight: 950;
}

.v120-row {
  min-height: 92px;
  padding: 13px 8px;
  border-bottom: 1px solid var(--line);
}

.v120-target,
.v120-price,
.v120-flow,
.v120-status {
  min-width: 0;
}

.v120-target b {
  display: block;
  max-width: 100%;
  color: var(--navy);
  font-size: 20px;
  line-height: 1.15;
  font-weight: 1000;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.v120-target span {
  display: block;
  margin-top: 2px;
  color: #8a96a8;
  font-size: 15px;
  line-height: 1.1;
  font-weight: 950;
}

.v120-price b {
  display: block;
  max-width: 100%;
  color: var(--navy);
  font-size: 20px;
  line-height: 1.05;
  font-weight: 1000;
  letter-spacing: -0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: clip;
}

.v120-price span {
  display: block;
  margin-top: 2px;
  font-size: 15px;
  line-height: 1.1;
  font-weight: 950;
}

.v120-price em {
  display: inline-block;
  margin-top: 5px;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--red);
  color: #fff;
  font-size: 12px;
  line-height: 1.1;
  font-style: normal;
  font-weight: 950;
}

.v120-flow {
  text-align: right;
}

.v120-flow b {
  display: block;
  max-width: 100%;
  font-size: 20px;
  line-height: 1.05;
  font-weight: 1000;
  letter-spacing: -0.02em;
  white-space: nowrap;
}

.v120-flow span {
  display: block;
  margin-top: 4px;
  font-size: 15px;
  line-height: 1.1;
  font-weight: 950;
  white-space: nowrap;
}

.v120-status {
  text-align: right;
}

.v120-status b {
  display: inline-grid;
  place-items: center;
  min-width: 44px;
  min-height: 28px;
  padding: 0 8px;
  border-radius: 999px;
  background: #fdecef;
  color: var(--red);
  font-size: 14px;
  font-weight: 1000;
  border: 1px solid rgba(216, 91, 102, .15);
}

.v120-status b.new {
  background: #fff5c9;
  color: #a79210;
}

.v120-status b.reduce {
  background: #e8fbf3;
  color: var(--green);
}

.v120-status span {
  display: block;
  margin-top: 6px;
  color: #7c8798;
  font-size: 14px;
  line-height: 1.1;
  font-weight: 950;
  white-space: nowrap;
}

.v120-empty {
  padding: 24px 8px;
  color: var(--muted);
  font-size: 16px;
  font-weight: 900;
}

.red { color: var(--red) !important; }
.green { color: var(--green) !important; }
.muted { color: var(--muted) !important; }

.v120-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(15, 23, 42, .45);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 18px;
}

.v120-modal {
  width: min(420px, 100%);
  max-height: 82vh;
  overflow: auto;
  background: #fff;
  border-radius: 24px;
  padding: 24px 22px 20px;
  position: relative;
  box-shadow: 0 18px 48px rgba(15, 23, 42, .25);
}

.v120-modal-x {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 50%;
  background: #f1f4f8;
  color: #718096;
  font-size: 30px;
  line-height: 1;
  font-weight: 900;
}

.v120-modal h3 {
  margin: 0 52px 10px 0;
  color: var(--navy);
  font-size: 28px;
  line-height: 1.1;
  font-weight: 1000;
}

.v120-modal p,
.v120-modal-count {
  color: #6f7b8d;
  font-size: 17px;
  line-height: 1.45;
  font-weight: 900;
}

.v120-modal-count {
  margin-top: 14px;
  color: #9a741e;
}

.v120-modal-note {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #f8fafc;
  color: #677489;
  font-size: 15px;
  line-height: 1.6;
  font-weight: 850;
}

.v120-missing-list {
  margin-top: 14px;
  display: grid;
  gap: 8px;
}

.v120-missing-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 4px 10px;
  padding: 10px 0;
  border-bottom: 1px solid #edf2f7;
}

.v120-missing-row b {
  font-size: 17px;
  font-weight: 1000;
}

.v120-missing-row span {
  min-width: 0;
  color: var(--navy);
  font-size: 16px;
  font-weight: 900;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.v120-missing-row em {
  grid-column: 2;
  color: #9a741e;
  font-size: 13px;
  font-style: normal;
  font-weight: 850;
}

.v120-modal-ok {
  margin-top: 18px;
  width: 100%;
  height: 52px;
  border: 0;
  border-radius: 14px;
  background: #3b82f6;
  color: #fff;
  font-size: 19px;
  font-weight: 1000;
}

@media (max-width: 390px) {
  .signals-v120 {
    padding-left: 14px;
    padding-right: 14px;
  }

  .v120-title h1 {
    font-size: 36px;
  }

  .v120-focus {
    padding: 13px 11px;
  }

  .v120-focus > b {
    font-size: 18px;
  }

  .v120-focus-name strong {
    max-width: 102px;
    font-size: 21px;
  }

  .v120-focus-price strong {
    font-size: 30px;
  }

  .v120-head,
  .v120-row {
    grid-template-columns: minmax(0, 1fr) 64px 90px 68px;
    gap: 7px;
  }

  .v120-head {
    font-size: 13px;
  }

  .v120-target b,
  .v120-price b,
  .v120-flow b {
    font-size: 18px;
  }

  .v120-flow span,
  .v120-price span,
  .v120-status span {
    font-size: 13px;
  }

  .v120-status b {
    min-width: 40px;
    font-size: 13px;
  }
}
/* ===== END V120 FINAL SIGNALS RESET ===== */
'''

css_text = css.read_text(encoding="utf-8")
marker = "/* ===== V120 FINAL SIGNALS RESET ===== */"
if marker not in css_text:
  css.write_text(css_text + "\n" + block, encoding="utf-8")

print("✅ V120 完成：SignalsClient 乾淨重置、首頁與 /signals 同步、表格不超出、排序改回 ▲/▼ 邏輯")
