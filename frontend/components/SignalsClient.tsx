'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

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
    data?.outdated_etfs,
    data?.outdatedEtfs,
    data?.not_updated_etfs,
    data?.notUpdatedEtfs,
    data?.stale_etfs,
    data?.staleEtfs,
    data?.etf_status,
    data?.etfStatus,
  ];

  for (const c of candidates) {
    if (Array.isArray(c)) {
      return c.map((x: any) => {
        if (typeof x === 'string') return { etf_code: x };
        return x || {};
      });
    }

    if (c && typeof c === 'object') {
      return Object.values(c).map((x: any) => {
        if (typeof x === 'string') return { etf_code: x };
        return x || {};
      });
    }
  }

  return [];
}

function etfCodeOf(row: AnyRow): string {
  if (typeof row === 'string') return row.trim();
  return String(row?.etf_code ?? row?.etfCode ?? row?.code ?? row?.id ?? '').trim();
}

function etfNameOf(row: AnyRow): string {
  if (typeof row === 'string') return '';
  return String(row?.etf_name ?? row?.etfName ?? row?.name ?? row?.title ?? '').trim();
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




// V117_MISSING_ETF_LIST_HELPERS_START
const ACTIVE_ETF_CODES_V117 = [
  '00400A','00401A','00402A','00403A','00404A','00405A','00406A',
  '00980A','00981A','00982A','00983A','00984A','00985A','00986A','00987A','00988A','00989A','00990A',
  '00991A','00992A','00993A','00994A','00995A','00996A','00997A','00998A','00999A'
];

const ETF_NAME_HINT_V117: Record<string, string> = {
  '00400A': '主動國泰動能高息',
  '00401A': '主動摩根台灣鑫收',
  '00402A': '主動群益科技創新',
  '00403A': '主動統一升級50',
  '00404A': '主動聯博動能50',
  '00405A': '主動富邦台灣龍耀',
  '00406A': '主動中信台灣收益',
  '00980A': '主動野村臺灣優選',
  '00981A': '主動統一台股增長',
  '00982A': '主動群益台灣強棒',
  '00983A': '主動中信ARK創新',
  '00984A': '主動安聯台灣高息',
  '00985A': '主動野村台灣50',
  '00986A': '主動群益全球創新AI',
  '00987A': '主動群益美國增長',
  '00988A': '主動統一全球創新',
  '00989A': '主動摩根全球基建',
  '00990A': '主動元大AI新經濟',
  '00991A': '主動復華未來50',
  '00992A': '主動群益科技創新',
  '00993A': '主動安聯台灣',
  '00994A': '主動第一金台股優',
  '00995A': '主動中信小資高息',
  '00996A': '主動兆豐台灣豐收',
  '00997A': '主動群益美國增長',
  '00998A': '主動中信台灣高股息',
  '00999A': '主動野村臺灣高息'
};

function dateKeyV117(v: any): string {
  const s = String(v ?? '').trim();
  const full = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (full) return `${full[1]}-${full[2]}-${full[3]}`;
  const md = s.match(/(\d{2})-(\d{2})/);
  if (md) return `${md[1]}-${md[2]}`;
  return s;
}

function sameDateV117(a: any, b: any): boolean {
  const ak = dateKeyV117(a);
  const bk = dateKeyV117(b);
  if (!ak || !bk) return false;
  if (ak === bk) return true;
  if (ak.length === 10 && bk.length === 5) return ak.slice(5) === bk;
  if (bk.length === 10 && ak.length === 5) return bk.slice(5) === ak;
  return false;
}

function etfLatestDateV117(row: AnyRow): string {
  return String(row?.latest_date ?? row?.latestDate ?? row?.data_date ?? row?.dataDate ?? row?.date ?? '').trim();
}

async function loadMissingEtfsV117(targetDate: any): Promise<AnyRow[]> {
  const target = String(targetDate ?? '').trim();
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !anonKey || !target) return [];

  const headers = {
    apikey: anonKey,
    Authorization: `Bearer ${anonKey}`,
  };

  try {
    const codeExpr = ACTIVE_ETF_CODES_V117.join(',');
    const holdingUrl = `${supabaseUrl}/rest/v1/holdings?select=etf_code,data_date&etf_code=in.(${codeExpr})&order=data_date.desc&limit=8000`;
    const holdingRes = await fetch(holdingUrl, { headers, cache: 'no-store' });
    if (!holdingRes.ok) return [];
    const holdingRows = await holdingRes.json();

    const latest = new Map<string, string>();
    if (Array.isArray(holdingRows)) {
      for (const r of holdingRows) {
        const code = String(r?.etf_code ?? '').trim();
        const dt = String(r?.data_date ?? '').trim();
        if (code && dt && !latest.has(code)) latest.set(code, dt);
      }
    }

    const names = new Map<string, string>();
    try {
      const quoteUrl = `${supabaseUrl}/rest/v1/etf_quotes?select=etf_code,etf_name&etf_code=in.(${codeExpr})&limit=200`;
      const quoteRes = await fetch(quoteUrl, { headers, cache: 'no-store' });
      if (quoteRes.ok) {
        const quoteRows = await quoteRes.json();
        if (Array.isArray(quoteRows)) {
          for (const r of quoteRows) {
            const c = String(r?.etf_code ?? '').trim();
            const n = String(r?.etf_name ?? '').trim();
            if (c && n) names.set(c, n);
          }
        }
      }
    } catch (_) {}

    return ACTIVE_ETF_CODES_V117
      .filter((code) => !sameDateV117(latest.get(code), target))
      .map((code) => ({
        etf_code: code,
        etf_name: names.get(code) || ETF_NAME_HINT_V117[code] || '',
        latest_date: latest.get(code) || '',
      }));
  } catch (_) {
    return [];
  }
}
// V117_MISSING_ETF_LIST_HELPERS_END

function DataQuality({ data, activeDays }: { data: any; activeDays: number }) {
  const [open, setOpen] = useState(false);
  const [loadingMissing, setLoadingMissing] = useState(false);
  const [loadedMissing, setLoadedMissing] = useState<AnyRow[]>([]);
  const [loadedOnce, setLoadedOnce] = useState(false);

  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const missingEtfs = missingEtfsOf(data);
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';
  const shownMissingEtfs = missingEtfs.length > 0 ? missingEtfs : loadedMissing;

  useEffect(() => {
    if (!open || activeDays !== 1 || missing <= 0 || loadedOnce || missingEtfs.length > 0) return;
    setLoadingMissing(true);
    loadMissingEtfsV117(date)
      .then((rows) => {
        setLoadedMissing(rows);
        setLoadedOnce(true);
      })
      .finally(() => setLoadingMissing(false));
  }, [open, activeDays, missing, loadedOnce, missingEtfs.length, date]);

  if (activeDays !== 1) {
    return (
      <div className="signals-quality-v114 compact-v117">
        <span>資料區間：近 {activeDays} 日</span>
        <span>資料日 {mmdd(date)}</span>
      </div>
    );
  }

  return (
    <>
      <div className="signals-quality-v114 compact-v117">
        <span>資料日 <b>{mmdd(date)}</b></span>
        <span>已取得今日資料 <b>{today}</b> / {total} 檔 ETF</span>
        {missing > 0 && (
          <button type="button" className="signals-warning-link-v117" onClick={() => setOpen(true)}>
            未更新 {missing} 檔，查看清單
          </button>
        )}
      </div>

      {open && (
        <div className="signals-modal-mask-v117" onClick={() => setOpen(false)}>
          <div className="signals-modal-v117" onClick={(e) => e.stopPropagation()}>
            <div className="signals-modal-head-v117">
              <div>
                <h3>未更新 ETF 清單</h3>
                <p>今日訊號只使用 {mmdd(date)} 當日資料，不混入前一日。</p>
              </div>
              <button type="button" onClick={() => setOpen(false)} aria-label="關閉">×</button>
            </div>

            {loadingMissing ? (
              <div className="signals-modal-note-v117">正在查詢未更新 ETF 清單…</div>
            ) : shownMissingEtfs.length > 0 ? (
              <div className="signals-missing-list-v117">
                {shownMissingEtfs.map((row, idx) => {
                  const code = etfCodeOf(row) || `ETF ${idx + 1}`;
                  const name = etfNameOf(row);
                  const latest = etfLatestDateV117(row);
                  return (
                    <div className="signals-missing-row-v117" key={`${code}-${idx}`}>
                      <div>
                        <b>{code}</b>
                        {name && <span>{name}</span>}
                      </div>
                      <em>{latest ? `最新 ${mmdd(latest)}` : '尚無資料'}</em>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="signals-modal-note-v117">
                目前 API 只回傳「未更新 {missing} 檔」的數量，尚未回傳 ETF 代號清單。若仍看不到清單，請確認 Supabase 的 holdings / etf_quotes 已開啟 public read policy。
              </div>
            )}

            <button type="button" className="signals-modal-ok-v117" onClick={() => setOpen(false)}>我知道了</button>
          </div>
        </div>
      )}
    </>
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
      {label}<span>{active ? (dir === 'desc' ? '▼' : '▲') : '▲▼'}</span>
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
    <main className="signals-page-v115"><section className="signals-hero-v115">
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
