import {
  toggleWatchlistItem,
  watchlistHas,
} from '@/lib/watchlist';

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
  const shares = num(
    r?.shares ??
    r?.total_shares ??
    r?.holding_shares ??
    r?.share_count
  );
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
  return toggleWatchlistItem(item);
}

export function favoriteExists(code: string, type: 'etf' | 'stock'): boolean {
  return watchlistHas(code, type);
}
