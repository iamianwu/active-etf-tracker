import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

export const ETF_CODES = [
  '00400A',
  '00401A',
  '00402A',
  '00403A',
  '00404A',
  '00405A',
  '00406A',
  '00407A',
  '00980A',
  '00981A',
  '00982A',
  '00983A',
  '00984A',
  '00985A',
  '00986A',
  '00987A',
  '00988A',
  '00989A',
  '00990A',
  '00991A',
  '00992A',
  '00993A',
  '00994A',
  '00995A',
  '00996A',
  '00997A',
  '00998A',
  '00999A',
];

export const ETF_NAMES: Record<string, string> = {
  "00400A": "主動國泰動能高息",
  "00401A": "主動摩根台灣鑫收",
  "00402A": "主動安聯美國科技",
  "00403A": "主動統一升級50",
  "00404A": "主動聯博動能50",
  "00405A": "主動富邦台灣龍耀",
  "00406A": "主動中信台灣收益",
    "00407A": "主動凱基台灣",
  "00980A": "主動野村臺灣優選",
  "00981A": "主動統一台股增長",
  "00982A": "主動群益台灣強棒",
  "00983A": "主動中信ARK創新",
  "00984A": "主動安聯台灣高息",
  "00985A": "主動野村台灣50",
  "00986A": "主動台新龍頭成長",
  "00987A": "主動台新優勢成長",
  "00988A": "主動統一全球創新",
  "00989A": "主動摩根美國科技",
  "00990A": "主動元大AI新經濟",
  "00991A": "主動復華未來50",
  "00992A": "主動群益科技創新",
  "00993A": "主動安聯台灣",
  "00994A": "主動第一金台股優",
  "00995A": "主動中信台灣卓越",
  "00996A": "主動兆豐台灣豐收",
  "00997A": "主動群益美國增長",
  "00998A": "主動復華金融股息",
  "00999A": "主動野村臺灣高息",
};

export function num(v: any): number | null {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export function isNormalStockCode(code: string) {
  return /^[0-9]{4}$/.test(String(code || ''));
}

export function isHoldingSecurityCode(code: string) {
  const c = String(code || '').trim().toUpperCase();
  if (!c) return false;
  if (/^[0-9]{5}A$/.test(c)) return false;
  if (['CASH', '現金', '合計', '總計'].includes(c)) return false;
  return true;
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

    if (isHoldingSecurityCode(String(r.stock_code))) {
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


const ETF_NAME_FALLBACK_V80: Record<string, string> = {
  "00400A": "主動國泰動能高息",
  "00401A": "主動摩根台灣鑫收",
  "00402A": "主動安聯美國科技",
  "00403A": "主動統一升級50",
  "00404A": "主動聯博動能50",
  "00405A": "主動富邦台灣龍耀",
  "00406A": "主動中信台灣收益",
  "00980A": "主動野村臺灣優選",
  "00981A": "主動統一台股增長",
  "00982A": "主動群益台灣強棒",
  "00983A": "主動中信ARK創新",
  "00984A": "主動安聯台灣高息",
  "00985A": "主動野村台灣50",
  "00986A": "主動台新龍頭成長",
  "00987A": "主動台新優勢成長",
  "00988A": "主動統一全球創新",
  "00989A": "主動摩根美國科技",
  "00990A": "主動元大AI新經濟",
  "00991A": "主動復華未來50",
  "00992A": "主動群益科技創新",
  "00993A": "主動安聯台灣",
  "00994A": "主動第一金台股優",
  "00995A": "主動中信台灣卓越",
  "00996A": "主動兆豐台灣豐收",
  "00997A": "主動群益美國增長",
  "00998A": "主動復華金融股息",
  "00999A": "主動野村臺灣高息",
};

function isActiveEtfCodeV80(code: any) {
  const c = String(code || '').trim().toUpperCase();
  return /^[0-9]{5}A$/.test(c);
}

function normalizeEtfCodeV80(code: any) {
  return String(code || '').trim().toUpperCase();
}

async function selectMaybePagedV80(table: string, build: (q: any) => any, pageSize = 1000) {
  const out: any[] = [];

  for (let from = 0; ; from += pageSize) {
    const to = from + pageSize - 1;
    const rows = await selectMaybe(table, (q) => build(q).range(from, to));
    out.push(...(rows || []));

    if (!rows || rows.length < pageSize) break;
    if (from > 200000) break;
  }

  return out;
}

export async function getEtfListRows() {
  const [quotes, holdingCodes] = await Promise.all([
    selectMaybe('etf_quotes', (q) => q),
    selectMaybePagedV80(
      'holdings',
      (q) => q.select('etf_code,data_date').order('data_date', { ascending: false })
    ),
  ]);

  const quoteMap: Record<string, any> = {};
  const latestHoldingDateMap: Record<string, string> = {};
  const codeSet = new Set<string>();

  for (const code of ETF_CODES || []) {
    const c = normalizeEtfCodeV80(code);
    if (isActiveEtfCodeV80(c)) codeSet.add(c);
  }

  for (const q of quotes || []) {
    const c = normalizeEtfCodeV80(q.etf_code || q.code || q.stock_code);
    if (!isActiveEtfCodeV80(c)) continue;
    quoteMap[c] = q;
    codeSet.add(c);
  }

  for (const r of holdingCodes || []) {
    const c = normalizeEtfCodeV80(r.etf_code);
    const d = String(r.data_date || '');
    if (!isActiveEtfCodeV80(c)) continue;
    codeSet.add(c);
    if (d && (!latestHoldingDateMap[c] || d > latestHoldingDateMap[c])) {
      latestHoldingDateMap[c] = d;
    }
  }

  return Array.from(codeSet)
    .sort()
    .map((code) => {
      const q = quoteMap[code] || {};
      const fallbackName = ETF_NAME_FALLBACK_V80[code] || q.etf_name || q.name || q.stock_name || code;
      const normalized = normalizeQuote(code, {
        ...q,
        etf_code: code,
        code,
        stock_code: code,
        etf_name: q.etf_name || q.name || q.stock_name || fallbackName,
        name: q.name || q.etf_name || q.stock_name || fallbackName,
        stock_name: q.stock_name || q.etf_name || q.name || fallbackName,
      });

      return {
        ...normalized,
        ...q,
        etf_code: code,
        code,
        stock_code: code,
        etf_name: normalized.etf_name || normalized.name || fallbackName,
        name: normalized.name || normalized.etf_name || fallbackName,
        stock_name: normalized.stock_name || normalized.etf_name || normalized.name || fallbackName,
        latest_holding_date: latestHoldingDateMap[code] || null,
        latestHoldingDate: latestHoldingDateMap[code] || null,
        has_holding_data: !!latestHoldingDateMap[code],
        has_quote: !!quoteMap[code],
      };
    });
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
    selectMaybe('holdings', (q) =>
      q
        .eq('etf_code', normalizedCode)
        .order('data_date', { ascending: false })
        .limit(1000)
    ),
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
    .filter((r: any) => String(r.data_date) === latestDate && isHoldingSecurityCode(String(r.stock_code)))
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
      if (!isHoldingSecurityCode(stockCode) || currMap[stockCode]) continue;

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
