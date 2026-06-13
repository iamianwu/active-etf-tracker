import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

export const ETF_CODES = [
  '00980A',
  '00982A',
  '00981A',
  '00983A',
  '00984A',
  '00985A',
  '00986A',
  '00989A',
  '00988A',
  '00991A',
  '00990A',
  '00987A',
  '00992A',
  '00994A',
  '00995A',
  '00993A',
  '00996A',
  '00400A',
  '00401A',
  '00997A',
  '00999A',
  '00403A',
];

export const ETF_NAMES: Record<string, string> = {
  '00980A': '主動野村臺灣優選',
  '00981A': '主動統一台股增長',
  '00982A': '主動群益台灣強棒',
  '00983A': '主動中信ARK創新',
  '00984A': '主動安聯台灣高息',
  '00985A': '主動野村台灣50',
  '00986A': '主動元大臺灣價值',
  '00987A': '主動凱基台灣精選',
  '00988A': '主動統一全球創新',
  '00989A': '主動復華未來50',
  '00990A': '主動永豐臺灣ESG',
  '00991A': '主動富邦未來車',
  '00992A': '主動國泰台灣領袖',
  '00993A': '主動台新台灣成長',
  '00994A': '主動第一金台股優',
  '00995A': '主動兆豐台灣科技',
  '00996A': '主動群益科技高息',
  '00997A': '主動中信台灣成長',
  '00999A': '主動台新全球AI',
  '00400A': '主動野村全球優選',
  '00401A': '主動統一美國增長',
  '00403A': '主動統一升級50',
};

export function num(v: any): number | null {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export function isNormalStockCode(code: string) {
  return /^[0-9]{4}$/.test(String(code || ''));
}

export function fmt(n: any, digits = 2, empty = '-') {
  const x = num(n);
  if (x === null) return empty;
  return x.toLocaleString('zh-TW', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

export function fmt0(n: any, empty = '-') {
  const x = num(n);
  if (x === null) return empty;
  return x.toLocaleString('zh-TW', { maximumFractionDigits: 0 });
}

export function signedClass(n: any) {
  const x = num(n) || 0;
  if (x > 0) return 'red';
  if (x < 0) return 'green';
  return 'muted';
}

function pickName(code: string, q?: any) {
  return q?.etf_name || ETF_NAMES[code] || code;
}

function calcAmount(q: any) {
  const amount = num(q?.amount);
  if (amount && amount > 0) return amount;

  const price = num(q?.price);
  const volume = num(q?.volume);
  if (price && volume) return price * volume * 1000;

  return null;
}

function normalizeQuote(code: string, q?: any) {
  const price = num(q?.price);
  const changePct = num(q?.change_pct);

  return {
    etf_code: code,
    etf_name: pickName(code, q),
    price: price && price > 0 ? price : null,
    change: price && price > 0 ? num(q?.change) : null,
    change_pct: price && price > 0 ? changePct : null,
    volume: num(q?.volume),
    amount: calcAmount(q),
    nav: num(q?.nav),
    premium_pct: num(q?.premium_pct),
    aum_billion: num(q?.aum_billion),
    expense_ratio: num(q?.expense_ratio),
    inception_date: q?.inception_date || null,
    holder_count: num(q?.holder_count),
    dividend_frequency: q?.dividend_frequency || null,
    dividend_yield: num(q?.dividend_yield),
    week_return: num(q?.week_return),
    total_return: num(q?.total_return),
    region: q?.region || null,
    currency: q?.currency || 'NTD',
    manager: q?.manager || null,
    company: q?.company || null,
    custodian: q?.custodian || null,
    updated_at: q?.updated_at || null,
  };
}

async function selectMaybe(table: string, queryFn: (q: any) => any) {
  const q = queryFn(supabase.from(table).select('*'));
  const { data, error } = await q;

  if (error) {
    if (
      String(error.message || '').includes('Could not find the table') ||
      String(error.message || '').includes('does not exist') ||
      String(error.code || '') === '42P01'
    ) {
      return [];
    }
    throw new Error(`${table}: ${error.message}`);
  }

  return data || [];
}


function holdingDateStats(rows: any[]) {
  const map: Record<string, { date: string; row_count: number; stock_count: number; stock_weight: number }> = {};

  for (const r of rows || []) {
    const d = String(r.data_date || '');
    if (!d) continue;
    if (!map[d]) map[d] = { date: d, row_count: 0, stock_count: 0, stock_weight: 0 };
    map[d].row_count += 1;

    if (isNormalStockCode(String(r.stock_code))) {
      map[d].stock_count += 1;
      map[d].stock_weight += num(r.weight) || 0;
    }
  }

  return Object.values(map).sort((a, b) => a.date.localeCompare(b.date));
}

function pickLatestValidHoldingDate(rows: any[], minStockCount = 20, minStockWeight = 30) {
  const stats = holdingDateStats(rows);
  const valid = stats.filter((x) => x.stock_count >= minStockCount && x.stock_weight >= minStockWeight);
  const pool = valid.length ? valid : stats;
  return pool.length ? pool[pool.length - 1].date : null;
}

function pickPrevValidHoldingDate(rows: any[], latestDate: string | null, minStockCount = 20, minStockWeight = 30) {
  if (!latestDate) return null;
  const stats = holdingDateStats(rows).filter((x) => x.date < latestDate);
  const valid = stats.filter((x) => x.stock_count >= minStockCount && x.stock_weight >= minStockWeight);
  const pool = valid.length ? valid : stats;
  return pool.length ? pool[pool.length - 1].date : null;
}

export async function getEtfListRows() {
  const quotes = await selectMaybe('etf_quotes', (q) => q);
  const map: Record<string, any> = {};

  for (const q of quotes) {
    map[String(q.etf_code)] = q;
  }

  return ETF_CODES.map((code) => normalizeQuote(code, map[code]));
}

export async function getEtfDetailData(code: string) {
  const normalizedCode = decodeURIComponent(code);

  const [
    quotes,
    priceRows,
    navRows,
    basicRows,
    holdingsRows,
    stockQuotes,
  ] = await Promise.all([
    selectMaybe('etf_quotes', (q) => q.eq('etf_code', normalizedCode).limit(1)),
    selectMaybe('etf_price_history', (q) => q.eq('etf_code', normalizedCode).order('trade_date', { ascending: true }).limit(520)),
    selectMaybe('etf_nav_history', (q) => q.eq('etf_code', normalizedCode).order('trade_date', { ascending: true }).limit(520)),
    selectMaybe('etf_basic_info', (q) => q.eq('etf_code', normalizedCode).limit(1)),
    selectMaybe('holdings', (q) => q.eq('etf_code', normalizedCode)),
    selectMaybe('stock_quotes', (q) => q),
  ]);

  const q = quotes?.[0] || {};
  const basic = basicRows?.[0] || {};
  const quote = {
    ...normalizeQuote(normalizedCode, { ...basic, ...q }),
    ...basic,
  };

  const latestDate = pickLatestValidHoldingDate(holdingsRows);
  const prevDate = pickPrevValidHoldingDate(holdingsRows, latestDate);
  const dateStats = holdingDateStats(holdingsRows);

  const sq: Record<string, any> = {};
  for (const s of stockQuotes || []) sq[String(s.stock_code)] = s;

  const currentRows = holdingsRows
    .filter((r: any) => String(r.data_date) === latestDate && isNormalStockCode(String(r.stock_code)))
    .map((r: any) => {
      const stockQuote = sq[String(r.stock_code)] || {};
      const price = num(stockQuote.price);
      const shares = num(r.shares) || 0;

      return {
        ...r,
        price,
        change_pct: num(stockQuote.change_pct),
        market_value_billion: price ? shares * price / 100000000 : null,
      };
    })
    .sort((a: any, b: any) => (num(b.weight) || 0) - (num(a.weight) || 0));

  const prevMap: Record<string, any> = {};
  for (const r of holdingsRows.filter((x: any) => String(x.data_date) === prevDate)) {
    prevMap[String(r.stock_code)] = r;
  }

  const currMap: Record<string, any> = {};
  for (const r of currentRows) currMap[String(r.stock_code)] = r;

  const changes: any[] = [];

  if (latestDate && prevDate) {
    for (const r of currentRows) {
      const prev = prevMap[String(r.stock_code)];
      const currShares = num(r.shares) || 0;
      const currWeight = num(r.weight) || 0;

      if (!prev) {
        changes.push({
          ...r,
          status: '新增',
          delta_shares: currShares,
          delta_weight: currWeight,
          previous_weight: 0,
        });
      } else {
        const deltaShares = currShares - (num(prev.shares) || 0);
        const deltaWeight = currWeight - (num(prev.weight) || 0);

        if (deltaShares > 0) {
          changes.push({
            ...r,
            status: '加碼',
            delta_shares: deltaShares,
            delta_weight: deltaWeight,
            previous_weight: num(prev.weight) || 0,
          });
        } else if (deltaShares < 0) {
          changes.push({
            ...r,
            status: '減碼',
            delta_shares: deltaShares,
            delta_weight: deltaWeight,
            previous_weight: num(prev.weight) || 0,
          });
        }
      }
    }

    for (const [stockCode, prev] of Object.entries(prevMap)) {
      if (!isNormalStockCode(stockCode) || currMap[stockCode]) continue;

      const stockQuote = sq[stockCode] || {};
      const price = num(stockQuote.price);
      const prevShares = num((prev as any).shares) || 0;

      changes.push({
        ...(prev as any),
        data_date: latestDate,
        status: '刪除',
        shares: 0,
        weight: 0,
        price,
        change_pct: num(stockQuote.change_pct),
        market_value_billion: null,
        delta_shares: -prevShares,
        delta_weight: -(num((prev as any).weight) || 0),
        previous_weight: num((prev as any).weight) || 0,
      });
    }
  }

  const changeSummary = {
    added: changes.filter((x) => x.status === '新增').length,
    removed: changes.filter((x) => x.status === '刪除').length,
    increased: changes.filter((x) => x.status === '加碼').length,
    decreased: changes.filter((x) => x.status === '減碼').length,
  };

  const totalStockWeight = currentRows.reduce((s: number, r: any) => s + (num(r.weight) || 0), 0);
  const totalValue = currentRows.reduce((s: number, r: any) => s + (num(r.market_value_billion) || 0), 0);

  return {
    code: normalizedCode,
    name: quote.etf_name || ETF_NAMES[normalizedCode] || normalizedCode,
    quote,
    basic,
    price_history: priceRows || [],
    nav_history: navRows || [],
    holdings: currentRows,
    latest_date: latestDate,
    previous_date: prevDate,
    date_stats: dateStats,
    changes,
    change_summary: changeSummary,
    summary: {
      stock_weight: totalStockWeight,
      holding_count: currentRows.length,
      market_value_billion: totalValue,
    },
  };
}
