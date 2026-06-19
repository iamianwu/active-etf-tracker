'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

type AnyRow = Record<string, any>;
type SortKey = 'amount' | 'lots' | 'consensus' | 'price' | 'pct' | 'status';
type SortDir = 'asc' | 'desc';

const STATUS_ORDER: Record<string, number> = {
  新增: 1,
  加碼: 2,
  減碼: 3,
  刪除: 4,
  異動: 5,
};

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

function getRows(data: any): AnyRow[] {
  const src = data?.rows ?? data?.changes ?? data?.aggregate ?? data?.items ?? [];
  return Array.isArray(src) ? src : [];
}

function getCode(row: AnyRow): string {
  return String(row.stock_code ?? row.code ?? '').trim();
}

function getName(row: AnyRow): string {
  return String(row.stock_name ?? row.name ?? row.stockName ?? getCode(row)).trim();
}

function getPrice(row: AnyRow): number | null {
  const v = firstNum(row, ['price', 'close_price', 'close', 'last_price'], NaN);
  return Number.isFinite(v) ? v : null;
}

function getPct(row: AnyRow): number | null {
  const v = firstNum(row, ['change_pct', 'pct', 'percent', 'changePercent'], NaN);
  return Number.isFinite(v) ? v : null;
}

function isLimitUp(row: AnyRow): boolean {
  const pct = getPct(row);
  if (pct === null) return false;
  return pct >= 9.7;
}

function isLimitDown(row: AnyRow): boolean {
  const pct = getPct(row);
  if (pct === null) return false;
  return pct <= -9.7;
}

function getLots(row: AnyRow): number {
  let v = firstNum(row, [
    'net_lots',
    'display_delta_lots',
    'change_lots',
    'delta_lots',
    'lot_change',
    'shares_change',
    'delta_shares',
  ], 0);

  // 若來源仍是「股」，轉成「張」
  if (Math.abs(v) >= 100000) v = v / 1000;
  return v;
}

function getAmountBillion(row: AnyRow): number {
  const v = firstNum(row, [
    'flow_billion',
    'money_billion',
    'amount_billion',
    'delta_amount_billion',
    'delta_value_billion',
    'net_amount_billion',
    'trade_amount_billion',
  ], NaN);

  if (Number.isFinite(v)) return v;

  const price = getPrice(row);
  const lots = getLots(row);
  if (price !== null && Number.isFinite(lots)) {
    return price * lots * 1000 / 100000000;
  }

  return 0;
}

function rowStatus(row: AnyRow): string {
  const s = String(row.status ?? row.type ?? '').trim();
  if (s) return s;
  const lots = getLots(row);
  if (lots > 0) return '加碼';
  if (lots < 0) return '減碼';
  return '異動';
}

function getBuyCount(row: AnyRow): number {
  const direct = firstNum(row, ['add_etf_count', 'add_count', 'buy_count', 'buy_etf_count', 'increase_count'], NaN);
  if (Number.isFinite(direct)) return Math.max(0, Math.round(direct));

  const status = rowStatus(row);
  const etfCount = Math.max(0, Math.round(firstNum(row, ['etf_count', 'count'], 0)));
  return status === '新增' || status === '加碼' ? etfCount : 0;
}

function getSellCount(row: AnyRow): number {
  const direct = firstNum(row, ['reduce_etf_count', 'sell_count', 'sell_etf_count', 'decrease_count'], NaN);
  if (Number.isFinite(direct)) return Math.max(0, Math.round(direct));

  const status = rowStatus(row);
  const etfCount = Math.max(0, Math.round(firstNum(row, ['etf_count', 'count'], 0)));
  return status === '刪除' || status === '減碼' ? etfCount : 0;
}

function getConsensusScore(row: AnyRow): number {
  return getBuyCount(row) - getSellCount(row);
}

function mmdd(dateLike: any): string {
  const s = String(dateLike ?? '').trim();
  const m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[2]}-${m[3]}`;
  return s;
}

function fmt0(v: any): string {
  const x = num(v, NaN);
  if (!Number.isFinite(x)) return '-';
  return Math.round(x).toLocaleString('zh-TW');
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

function fmtSigned(v: number, suffix = ''): string {
  if (!Number.isFinite(v)) return '-';
  if (Math.abs(v) < 0.01) return `0${suffix}`;
  const sign = v > 0 ? '+' : '';
  return `${sign}${Math.round(v).toLocaleString('zh-TW')}${suffix}`;
}

function fmtBillion(v: number): string {
  if (!Number.isFinite(v)) return '-';
  const sign = v > 0 ? '+' : '';
  const abs = Math.abs(v);
  const digits = abs >= 100 ? 1 : abs >= 10 ? 1 : 2;
  return `${sign}${v.toLocaleString('zh-TW', { minimumFractionDigits: 0, maximumFractionDigits: digits })}億`;
}

function toneByValue(v: number): 'up' | 'down' | 'flat' {
  if (v > 0) return 'up';
  if (v < 0) return 'down';
  return 'flat';
}

function FocusCard({ title, item, tone }: { title: string; item?: AnyRow | null; tone: 'red' | 'green' }) {
  if (!item) {
    return (
      <div className={`signal106-focus ${tone}`}>
        <div className="signal106-focus-title">{title}</div>
        <div className="signal106-empty">尚無有效訊號</div>
      </div>
    );
  }

  const price = getPrice(item);
  const pct = getPct(item);
  const lots = getLots(item);
  const amount = getAmountBillion(item);
  const buy = getBuyCount(item);
  const sell = getSellCount(item);

  return (
    <Link href={`/stock/${getCode(item)}`} className={`signal106-focus ${tone} signal107-link-card`}>
      <div className="signal106-focus-title">{title}</div>
      <div className="signal106-focus-name">
        <span>{getName(item)}</span>
        <b>{getCode(item)}</b>
      </div>
      <div className={`signal106-focus-price ${isLimitUp(item) ? 'limit-up' : ''} ${isLimitDown(item) ? 'limit-down' : ''}`}>
        <span className="signal107-price-number">{fmtPrice(price)}</span>
        <span className={toneByValue(pct ?? 0)}>{fmtPct(pct)}</span>
      </div>
      <div className="signal106-focus-sub">
        <span>淨額 <b className={toneByValue(amount)}>{fmtBillion(amount)}</b></span>
        <span>張數 <b className={toneByValue(lots)}>{fmtSigned(lots, '張')}</b></span>
        <span>買賣 <b>{buy}:{sell}</b></span>
      </div>
    </Link>
  );
}

function SortPill({
  label,
  sortKey,
  activeKey,
  dir,
  onClick,
}: {
  label: string;
  sortKey: SortKey;
  activeKey: SortKey;
  dir: SortDir;
  onClick: (key: SortKey) => void;
}) {
  const active = activeKey === sortKey;
  return (
    <button className={`signal106-pill sort ${active ? 'active' : ''}`} onClick={() => onClick(sortKey)} type="button">
      {label} {active ? (dir === 'desc' ? '↓' : '↑') : '↕'}
    </button>
  );
}

function StatusPill({
  label,
  active,
  count,
  onClick,
}: {
  label: string;
  active: boolean;
  count: number;
  onClick: () => void;
}) {
  return (
    <button className={`signal106-pill status ${label} ${active ? 'active' : ''}`} onClick={onClick} type="button">
      {label}<b>{count || 0}</b>
    </button>
  );
}

function SignalRow({ row }: { row: AnyRow }) {
  const code = getCode(row);
  const status = rowStatus(row);
  const price = getPrice(row);
  const pct = getPct(row);
  const amount = getAmountBillion(row);
  const lots = getLots(row);
  const buy = getBuyCount(row);
  const sell = getSellCount(row);
  const limitUp = isLimitUp(row);
  const limitDown = isLimitDown(row);

  return (
    <Link href={`/stock/${code}`} className={`signal106-row signal107-clickable-row ${limitUp ? 'limit-up-row' : ''} ${limitDown ? 'limit-down-row' : ''}`}>
      <div className="signal106-cell stock">
        <b>{getName(row)}</b>
        <span>{code}</span>
      </div>

      <div className={`signal106-cell quote ${limitUp ? 'limit-up' : ''} ${limitDown ? 'limit-down' : ''}`}>
        <b>{fmtPrice(price)}</b>
        <span className={toneByValue(pct ?? 0)}>{fmtPct(pct)}</span>
      </div>

      <div className="signal106-cell trade">
        <b className={toneByValue(amount)}>{fmtBillion(amount)}</b>
        <span className={toneByValue(lots)}>{fmtSigned(lots, '張')}</span>
      </div>

      <div className="signal106-cell action">
        <span className={`signal106-status ${status}`}>{status}</span>
        <em>買賣 {buy}:{sell}</em>
      </div>
    </Link>
  );
}

export default function SignalsClient(props: any) {
  const data = props?.data ?? props ?? {};
  const sourceRows = getRows(data);

  const [selectedStatuses, setSelectedStatuses] = useState<string[]>(['新增', '刪除', '加碼', '減碼']);
  const [sortKey, setSortKey] = useState<SortKey>('amount');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const rows = useMemo(() => {
    const filtered = sourceRows.filter((r) => selectedStatuses.includes(rowStatus(r)));

    const valueOf = (r: AnyRow) => {
      switch (sortKey) {
        case 'amount':
          return getAmountBillion(r);
        case 'lots':
          return getLots(r);
        case 'consensus':
          return getConsensusScore(r);
        case 'price':
          return getPrice(r) ?? -Infinity;
        case 'pct':
          return getPct(r) ?? -Infinity;
        case 'status':
          return STATUS_ORDER[rowStatus(r)] ?? 99;
        default:
          return 0;
      }
    };

    return [...filtered].sort((a, b) => {
      const av = valueOf(a);
      const bv = valueOf(b);
      return sortDir === 'desc' ? bv - av : av - bv;
    });
  }, [sourceRows, selectedStatuses, sortKey, sortDir]);

  const summary = useMemo(() => {
    const out: Record<string, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0 };
    for (const r of sourceRows) {
      const s = rowStatus(r);
      if (out[s] !== undefined) out[s] += 1;
    }
    return out;
  }, [sourceRows]);

  const focus = useMemo(() => {
    const usable = sourceRows.filter((r) => rowStatus(r) !== '異動');
    const positive = usable.filter((r) => getAmountBillion(r) > 0);
    const negative = usable.filter((r) => getAmountBillion(r) < 0);
    const addLike = usable.filter((r) => ['新增', '加碼'].includes(rowStatus(r)));
    const reduceLike = usable.filter((r) => ['刪除', '減碼'].includes(rowStatus(r)));

    const maxBy = (arr: AnyRow[], fn: (x: AnyRow) => number) =>
      arr.length ? [...arr].sort((a, b) => fn(b) - fn(a))[0] : null;

    const minBy = (arr: AnyRow[], fn: (x: AnyRow) => number) =>
      arr.length ? [...arr].sort((a, b) => fn(a) - fn(b))[0] : null;

    return {
      inflow: maxBy(positive, getAmountBillion),
      outflow: minBy(negative, getAmountBillion),
      mostAdd: maxBy(addLike, (r) => getBuyCount(r) * 1000000 + getLots(r)),
      mostReduce: maxBy(reduceLike, (r) => getSellCount(r) * 1000000 + Math.abs(getLots(r))),
    };
  }, [sourceRows]);

  const dataDate = data?.data_date ?? data?.latestDataDate ?? '';
  const fetched = data?.fetched_etf_count ?? data?.includedEtfCount ?? 0;
  const total = data?.total_etf_count ?? data?.totalEtfCount ?? 0;

  function toggleStatus(s: string) {
    setSelectedStatuses((prev) => {
      if (prev.includes(s)) return prev.filter((x) => x !== s);
      return [...prev, s];
    });
  }

  function toggleSort(k: SortKey) {
    if (sortKey === k) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortKey(k);
      setSortDir('desc');
    }
  }

  return (
    <main className="page signals-v7-page signal106-page signal107-page">
      <div className="signals-title-block signal106-title-block">
        <h2>今日訊號</h2>
        <div className="signals-data-status ok">
          已抓取 {fetched || total || 0} / {total || fetched || 0} 檔 ETF
          {dataDate ? `，資料日期 ${mmdd(dataDate)}` : ''}
        </div>
      </div>

      <div className="signal106-focus-grid">
        <FocusCard title="淨資金流入最多" item={focus.inflow} tone="red" />
        <FocusCard title="淨資金流出最多" item={focus.outflow} tone="green" />
        <FocusCard title="最多 ETF 加碼" item={focus.mostAdd} tone="red" />
        <FocusCard title="最多 ETF 減碼" item={focus.mostReduce} tone="green" />
      </div>

      <section className="signal106-detail">
        <h3>資金交易明細：共 {fmt0(rows.length)} 檔</h3>

        <div className="signal106-pill-row">
          <StatusPill label="新增" active={selectedStatuses.includes('新增')} count={summary['新增']} onClick={() => toggleStatus('新增')} />
          <StatusPill label="刪除" active={selectedStatuses.includes('刪除')} count={summary['刪除']} onClick={() => toggleStatus('刪除')} />
          <StatusPill label="加碼" active={selectedStatuses.includes('加碼')} count={summary['加碼']} onClick={() => toggleStatus('加碼')} />
          <StatusPill label="減碼" active={selectedStatuses.includes('減碼')} count={summary['減碼']} onClick={() => toggleStatus('減碼')} />
        </div>

        <div className="signal106-pill-row sortrow">
          <SortPill label="金額" sortKey="amount" activeKey={sortKey} dir={sortDir} onClick={toggleSort} />
          <SortPill label="張數" sortKey="lots" activeKey={sortKey} dir={sortDir} onClick={toggleSort} />
          <SortPill label="共識" sortKey="consensus" activeKey={sortKey} dir={sortDir} onClick={toggleSort} />
          <SortPill label="股價" sortKey="price" activeKey={sortKey} dir={sortDir} onClick={toggleSort} />
          <SortPill label="漲跌幅" sortKey="pct" activeKey={sortKey} dir={sortDir} onClick={toggleSort} />
          <SortPill label="狀態" sortKey="status" activeKey={sortKey} dir={sortDir} onClick={toggleSort} />
        </div>

        <div className="signal106-header">
          <span>標的</span>
          <span>股價</span>
          <span>淨額 / 張數</span>
          <span>狀態 / 共識</span>
        </div>

        <div className="signal106-list">
          {rows.length ? rows.map((row, idx) => <SignalRow key={`${getCode(row)}-${idx}`} row={row} />) : (
            <div className="signal106-empty-list">目前沒有符合篩選的訊號。</div>
          )}
        </div>
      </section>
    </main>
  );
}
