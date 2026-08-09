import { createClient } from '@supabase/supabase-js';

export const ACTIVE_ETF_CODES_V112 = [
  '00400A','00401A','00402A','00403A','00404A','00405A','00406A','00407A','00410A',
  '00980A','00981A','00982A','00983A','00984A','00985A','00986A','00987A','00988A','00989A','00990A','00991A','00992A','00993A','00994A','00995A','00996A','00997A','00998A','00999A',
];

const ETF_NAME_FALLBACK: Record<string, string> = {
  '00400A': '主動國泰動能高息',
  '00401A': '主動摩根台灣鑫收',
  '00402A': '主動安聯美國科技',
  '00403A': '主動統一升級50',
  '00404A': '主動聯博動能50',
  '00405A': '主動富邦台灣龍耀',
  '00406A': '主動中信台灣收益',
  '00407A': '主動凱基台灣',
  '00410A': '主動永豐科技趨勢',
  '00980A': '主動野村臺灣優選',
  '00981A': '主動統一台股增長',
  '00982A': '主動群益台灣強棒',
  '00983A': '主動中信成長高股息',
  '00984A': '主動安聯台灣高息成長',
  '00985A': '主動野村台灣50',
  '00986A': '主動凱基台灣AI50',
  '00987A': '主動凱基台灣精選',
  '00988A': '主動統一全球創新',
  '00989A': '主動野村台灣50',
  '00990A': '主動元大AI新經濟',
  '00991A': '主動復華未來50',
  '00992A': '主動群益科技創新',
  '00993A': '主動安聯台灣',
  '00994A': '主動第一金台股優',
  '00995A': '主動野村台灣優選高息',
  '00996A': '主動兆豐台灣豐收',
  '00997A': '主動群益美國增長',
  '00998A': '主動復華金融股息',
  '00999A': '主動野村臺灣高息',
};

type AnyRow = Record<string, any>;

function n(v: any, fallback = 0): number {
  if (v === null || v === undefined || v === '') return fallback;
  const x = Number(String(v).replace(/,/g, '').replace(/[^\d.-]/g, ''));
  return Number.isFinite(x) ? x : fallback;
}
function isActiveEtf(code: any) {
  return /^[0-9]{5}A$/.test(String(code || '').trim().toUpperCase());
}
function isTwStock(code: any) {
  return /^[0-9]{4}$/.test(String(code || '').trim());
}
function dateOnly(v: any) {
  const s = String(v || '').trim();
  const m = s.match(/(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : s;
}
function minusDays(date: string, days: number) {
  const d = new Date(`${date}T00:00:00+08:00`);
  d.setDate(d.getDate() - days);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}
async function selectPaged(supabase: any, table: string, columns: string, build: (q: any) => any, pageSize = 1000, maxRows = 80000) {
  const out: AnyRow[] = [];
  for (let from = 0; from < maxRows; from += pageSize) {
    const to = from + pageSize - 1;
    const { data, error } = await build(supabase.from(table).select(columns)).range(from, to);
    if (error) {
      const msg = String(error.message || '');
      if (msg.includes('does not exist') || msg.includes('Could not find the table')) return [];
      throw new Error(`${table}: ${msg}`);
    }
    out.push(...(data || []));
    if (!data || data.length < pageSize) break;
  }
  return out;
}
function buildStockMap(rows: AnyRow[]) {
  const map: Record<string, AnyRow> = {};
  for (const r of rows || []) {
    const code = String(r.stock_code || '').trim();
    if (!isTwStock(code)) continue;
    if (!map[code]) map[code] = { stock_code: code, stock_name: r.stock_name || code, shares: 0, weight: 0 };
    map[code].stock_name = r.stock_name || map[code].stock_name || code;
    map[code].shares += n(r.shares, 0);
    map[code].weight += n(r.weight, 0);
  }
  return map;
}
function quoteMap(rows: AnyRow[]) {
  const map: Record<string, AnyRow> = {};
  for (const r of rows || []) {
    const c = String(r.stock_code || r.code || '').trim();
    if (c) map[c] = r;
  }
  return map;
}
function qPrice(q: AnyRow | undefined) {
  const x = n(q?.price, NaN);
  return Number.isFinite(x) && x > 0 ? x : null;
}
function qPct(q: AnyRow | undefined) {
  const x = n(q?.change_pct, NaN);
  return Number.isFinite(x) ? x : null;
}

export async function getSignalsV112() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    return {
      rows: [],
      total_etf_count: ACTIVE_ETF_CODES_V112.length,
      fetched_etf_count: 0,
      today_etf_count: 0,
      non_today_etf_count: ACTIVE_ETF_CODES_V112.length,
      data_date: '',
      warning: '缺少 NEXT_PUBLIC_SUPABASE_URL 或 NEXT_PUBLIC_SUPABASE_ANON_KEY',
    };
  }

  const supabase = createClient(url, key, { auth: { persistSession: false } });

  const dateRows = await selectPaged(
    supabase,
    'holdings',
    'etf_code,data_date',
    (q) => q.order('data_date', { ascending: false }),
    1000,
    100000,
  );

  const codeSet = new Set<string>(ACTIVE_ETF_CODES_V112);
  const latestByEtf: Record<string, string> = {};
  for (const r of dateRows || []) {
    const c = String(r.etf_code || '').trim().toUpperCase();
    const d = dateOnly(r.data_date);
    if (!isActiveEtf(c) || !d) continue;
    codeSet.add(c);
    if (!latestByEtf[c] || d > latestByEtf[c]) latestByEtf[c] = d;
  }

  const targetDate = Object.values(latestByEtf).sort().pop() || '';
  const totalEtfs = codeSet.size;
  const todayEtfs = Object.entries(latestByEtf).filter(([, d]) => d === targetDate).map(([c]) => c);
  const todayEtfSet = new Set(todayEtfs);
  const nonTodayEtfs = Array.from(codeSet).filter((c) => latestByEtf[c] !== targetDate);

  if (!targetDate || todayEtfs.length === 0) {
    return {
      rows: [],
      total_etf_count: totalEtfs,
      fetched_etf_count: 0,
      today_etf_count: 0,
      non_today_etf_count: totalEtfs,
      data_date: targetDate,
      non_today_etfs: nonTodayEtfs,
    };
  }

  const fromDate = minusDays(targetDate, 35);
  const [holdingRows, stockQuoteRows] = await Promise.all([
    selectPaged(
      supabase,
      'holdings',
      'etf_code,data_date,stock_code,stock_name,shares,weight',
      (q) => q.gte('data_date', fromDate).lte('data_date', targetDate).order('data_date', { ascending: true }),
      1000,
      120000,
    ),
    selectPaged(supabase, 'stock_quotes', '*', (q) => q, 1000, 5000),
  ]);

  const sq = quoteMap(stockQuoteRows || []);
  const grouped: Record<string, Record<string, AnyRow[]>> = {};
  for (const r of holdingRows || []) {
    const etf = String(r.etf_code || '').trim().toUpperCase();
    if (!todayEtfSet.has(etf)) continue;
    const d = dateOnly(r.data_date);
    if (!d) continue;
    if (!grouped[etf]) grouped[etf] = {};
    if (!grouped[etf][d]) grouped[etf][d] = [];
    grouped[etf][d].push(r);
  }

  const byStock: Record<string, AnyRow> = {};
  for (const etf of todayEtfs) {
    const dates = Object.keys(grouped[etf] || {}).sort();
    const latest = dates.filter((d) => d === targetDate).pop();
    const prev = dates.filter((d) => d < targetDate).pop();
    if (!latest || !prev) continue;

    const currMap = buildStockMap(grouped[etf][latest] || []);
    const prevMap = buildStockMap(grouped[etf][prev] || []);
    const allStocks = new Set([...Object.keys(currMap), ...Object.keys(prevMap)]);

    for (const stock of allStocks) {
      const curr = currMap[stock];
      const pre = prevMap[stock];
      const currShares = n(curr?.shares, 0);
      const prevShares = n(pre?.shares, 0);
      const deltaShares = currShares - prevShares;
      if (Math.abs(deltaShares) < 1) continue;

      const deltaLots = deltaShares / 1000;
      if (!byStock[stock]) {
        const q = sq[stock] || {};
        byStock[stock] = {
          stock_code: stock,
          code: stock,
          stock_name: curr?.stock_name || pre?.stock_name || q.stock_name || q.name || stock,
          name: curr?.stock_name || pre?.stock_name || q.stock_name || q.name || stock,
          price: qPrice(q),
          change_pct: qPct(q),
          curr_shares: 0,
          prev_shares: 0,
          net_lots: 0,
          buy_count: 0,
          sell_count: 0,
          add_etf_count: 0,
          reduce_etf_count: 0,
          data_date: targetDate,
          etf_changes: [],
        };
      }
      const item = byStock[stock];
      item.curr_shares += currShares;
      item.prev_shares += prevShares;
      item.net_lots += deltaLots;
      if (deltaLots > 0) {
        item.buy_count += 1;
        item.add_etf_count += 1;
      }
      if (deltaLots < 0) {
        item.sell_count += 1;
        item.reduce_etf_count += 1;
      }
      item.etf_changes.push({
        etf_code: etf,
        etf_name: ETF_NAME_FALLBACK[etf] || etf,
        data_date: targetDate,
        previous_date: prev,
        delta_lots: deltaLots,
        curr_lots: currShares / 1000,
        prev_lots: prevShares / 1000,
      });
    }
  }

  const rows = Object.values(byStock).map((r: AnyRow) => {
    const price = r.price;
    const netAmount = price ? price * r.net_lots * 1000 / 100000000 : 0;
    const currLots = r.curr_shares / 1000;
    const prevLots = r.prev_shares / 1000;
    let status = '異動';
    if (prevLots <= 0 && currLots > 0) status = '新增';
    else if (currLots <= 0 && prevLots > 0) status = '刪除';
    else if (r.net_lots > 0) status = '加碼';
    else if (r.net_lots < 0) status = '減碼';
    return {
      ...r,
      status,
      type: status,
      current_lots: currLots,
      previous_lots: prevLots,
      net_amount_billion: netAmount,
      delta_amount_billion: netAmount,
      amount_billion: netAmount,
    };
  }).filter((r) => ['新增', '刪除', '加碼', '減碼'].includes(r.status));

  const statusCount: Record<string, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0 };
  for (const r of rows) statusCount[r.status] = (statusCount[r.status] || 0) + 1;

  return {
    rows,
    changes: rows,
    aggregate: rows,
    data_date: targetDate,
    target_date: targetDate,
    total_etf_count: totalEtfs,
    fetched_etf_count: todayEtfs.length,
    today_etf_count: todayEtfs.length,
    non_today_etf_count: nonTodayEtfs.length,
    today_etfs: todayEtfs,
    non_today_etfs: nonTodayEtfs,
    status_count: statusCount,
    note: `本頁僅統計 ${targetDate} 已更新的 ETF；未更新 ETF 不混入前一日資料。`,
  };
}
