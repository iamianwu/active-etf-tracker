import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const ETF_NAMES: Record<string, string> = {
  "00980A": "主動野村臺灣優選",
  "00981A": "主動統一台股增長",
  "00982A": "主動群益台灣強棒",
  "00983A": "主動中信ARK創新",
  "00984A": "主動安聯台灣高息",
  "00985A": "主動野村台灣50",
  "00986A": "主動元大臺灣價值",
  "00987A": "主動凱基台灣精選",
  "00988A": "主動統一全球創新",
  "00989A": "主動復華未來50",
  "00990A": "主動永豐臺灣ESG",
  "00991A": "主動富邦未來車",
  "00992A": "主動國泰台灣領袖",
  "00993A": "主動台新台灣成長",
  "00994A": "主動第一金台股優",
  "00995A": "主動兆豐台灣科技",
  "00996A": "主動群益科技高息",
  "00997A": "主動中信台灣成長",
  "00998A": "主動台新台灣科技",
  "00999A": "主動台新全球AI",
  "00400A": "主動野村全球優選",
  "00401A": "主動統一美國增長",
  "00403A": "主動統一升級50",
};

function isNormalStockCode(code: string) {
  return /^[0-9]{4}$/.test(String(code || ""));
}

function fmtDateMMDD(dateStr: string | null | undefined) {
  if (!dateStr) return "";
  const s = String(dateStr);
  if (s.includes("-")) {
    const [, m, d] = s.split("-");
    return `${m}/${d}`;
  }
  if (s.includes("/")) {
    const parts = s.split("/");
    return `${parts[1]?.padStart(2, "0")}/${parts[2]?.padStart(2, "0")}`;
  }
  return s;
}

async function selectAll(table: string, order?: { column: string; ascending?: boolean }) {
  const out: any[] = [];
  const pageSize = 1000;

  for (let from = 0; ; from += pageSize) {
    const to = from + pageSize - 1;
    let q = supabase.from(table).select("*").range(from, to);
    if (order) q = q.order(order.column, { ascending: order.ascending ?? true });

    const { data, error } = await q;
    if (error) {
      if (String(error.message || "").includes("Could not find the table")) return [];
      throw new Error(`${table}: ${error.message}`);
    }

    const rows = data || [];
    out.push(...rows);

    if (rows.length < pageSize) break;
  }

  return out;
}

async function loadBaseData() {
  const [holdings, etfQuotes, stockQuotes] = await Promise.all([
    selectAll("holdings"),
    selectAll("etf_quotes"),
    selectAll("stock_quotes"),
  ]);

  const etfQuoteMap: Record<string, any> = {};
  for (const q of etfQuotes) etfQuoteMap[q.etf_code] = q;

  const stockQuoteMap: Record<string, any> = {};
  for (const q of stockQuotes) stockQuoteMap[q.stock_code] = q;

  return { holdings, etfQuoteMap, stockQuoteMap };
}

async function loadLatestPriceHistoryMap(stockCodes: string[]) {
  const uniqueCodes = Array.from(new Set(stockCodes.filter(Boolean)));
  const out: Record<string, any> = {};
  const pageSize = 1000;
  const chunkSize = 80;

  for (let i = 0; i < uniqueCodes.length; i += chunkSize) {
    const chunk = uniqueCodes.slice(i, i + chunkSize);

    for (let from = 0; ; from += pageSize) {
      const to = from + pageSize - 1;

      const { data, error } = await supabase
        .from("stock_price_history")
        .select("stock_code,trade_date,close,change_pct,volume")
        .in("stock_code", chunk)
        .order("trade_date", { ascending: false })
        .range(from, to);

      if (error) {
        if (String(error.message || "").includes("Could not find the table")) return out;
        break;
      }

      const rows = data || [];

      for (const r of rows) {
        const code = String(r.stock_code || "");
        if (!code) continue;

        if (!out[code] || String(r.trade_date || "") > String(out[code].trade_date || "")) {
          out[code] = {
            price: r.close,
            change_pct: r.change_pct,
            volume: r.volume,
            trade_date: r.trade_date,
          };
        }
      }

      if (rows.length < pageSize) break;
    }
  }

  return out;
}

function latestDateByEtf(holdings: any[]) {
  const m: Record<string, string> = {};

  for (const h of holdings) {
    const code = h.etf_code;
    const d = String(h.data_date || "");
    if (!m[code] || d > m[code]) m[code] = d;
  }

  return m;
}

function latestHoldings(holdings: any[]) {
  const latest = latestDateByEtf(holdings);
  return holdings.filter((h) => String(h.data_date) === latest[h.etf_code]);
}

function previousDateForEtf(holdings: any[], etfCode: string, date: string) {
  const dates = Array.from(
    new Set(
      holdings
        .filter((h) => h.etf_code === etfCode && String(h.data_date) < date)
        .map((h) => String(h.data_date))
    )
  ).sort();

  return dates.length ? dates[dates.length - 1] : null;
}

function computeEtfChanges(holdings: any[], etfCode: string, date: string, prevDate: string | null) {
  if (!prevDate) return [];

  const curr = holdings.filter((h) => h.etf_code === etfCode && String(h.data_date) === date);
  const prev = holdings.filter((h) => h.etf_code === etfCode && String(h.data_date) === prevDate);

  const currMap: Record<string, any> = {};
  const prevMap: Record<string, any> = {};

  for (const r of curr) currMap[r.stock_code] = r;
  for (const r of prev) prevMap[r.stock_code] = r;

  const out: any[] = [];

  for (const code of Object.keys(currMap)) {
    if (!isNormalStockCode(code)) continue;

    const r = currMap[code];
    const p = prevMap[code];

    let status = "";
    let delta_shares = 0;
    let delta_weight = 0;

    if (!p) {
      status = "新增";
      delta_shares = Number(r.shares || 0);
      delta_weight = Number(r.weight || 0);
    } else {
      delta_shares = Number(r.shares || 0) - Number(p.shares || 0);
      delta_weight = Number(r.weight || 0) - Number(p.weight || 0);

      if (delta_shares > 0) status = "加碼";
      else if (delta_shares < 0) status = "減碼";
      else continue;
    }

    out.push({ ...r, status, delta_shares, delta_weight });
  }

  for (const code of Object.keys(prevMap)) {
    if (!isNormalStockCode(code) || currMap[code]) continue;

    const p = prevMap[code];
    out.push({
      ...p,
      data_date: date,
      status: "刪除",
      shares: 0,
      weight: 0,
      delta_shares: -Number(p.shares || 0),
      delta_weight: -Number(p.weight || 0),
    });
  }

  const order: Record<string, number> = { 新增: 0, 刪除: 1, 加碼: 2, 減碼: 3 };
  return out.sort((a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9));
}

function summarizeChanges(changes: any[]) {
  return {
    新增: changes.filter((x) => x.status === "新增").length,
    刪除: changes.filter((x) => x.status === "刪除").length,
    加碼: changes.filter((x) => x.status === "加碼").length,
    減碼: changes.filter((x) => x.status === "減碼").length,
  };
}

async function getEtfs() {
  const { holdings, etfQuoteMap } = await loadBaseData();
  const rows = latestHoldings(holdings);
  const grouped: Record<string, any> = {};

  for (const h of rows) {
    const code = h.etf_code;

    if (!grouped[code]) {
      const q = etfQuoteMap[code] || {};
      grouped[code] = {
        etf_code: code,
        etf_name: q.etf_name || ETF_NAMES[code] || code,
        data_date: h.data_date,
        holding_count: 0,
        stock_weight: 0,
        price: q.price ?? null,
        change_pct: q.change_pct ?? null,
        volume: q.volume ?? null,
        amount: q.amount ?? null,
        aum_billion: q.aum_billion ?? null,
      };
    }

    if (isNormalStockCode(h.stock_code)) {
      grouped[code].holding_count += 1;
      grouped[code].stock_weight += Number(h.weight || 0);
    }
  }

  return Object.values(grouped).sort((a: any, b: any) => String(a.etf_code).localeCompare(String(b.etf_code)));
}

async function getEtfDetail(etfCode: string) {
  const { holdings, etfQuoteMap, stockQuoteMap } = await loadBaseData();
  const latest = latestDateByEtf(holdings);
  const date = latest[etfCode];

  if (!date) return { etf_code: etfCode, error: "no data" };

  const prev = previousDateForEtf(holdings, etfCode, date);
  const q = etfQuoteMap[etfCode] || {};
  const changes = computeEtfChanges(holdings, etfCode, date, prev);

  const h = holdings
    .filter((r) => r.etf_code === etfCode && String(r.data_date) === date)
    .map((r) => {
      const sq = stockQuoteMap[r.stock_code] || {};
      const price = sq.price ?? null;
      return {
        ...r,
        price,
        change_pct: sq.change_pct ?? null,
        market_value_billion: price ? Number(r.shares || 0) * Number(price) / 100000000 : null,
      };
    })
    .sort((a, b) => Number(b.weight || 0) - Number(a.weight || 0));

  return {
    etf_code: etfCode,
    etf_name: q.etf_name || ETF_NAMES[etfCode] || etfCode,
    data_date: date,
    previous_date: prev,
    quote: q,
    holdings: h,
    change_summary: summarizeChanges(changes),
    changes,
  };
}

async function getConstituentSummary() {
  const { holdings, stockQuoteMap } = await loadBaseData();
  const rows = latestHoldings(holdings).filter((h) => isNormalStockCode(h.stock_code));
  const stockCodes = Array.from(new Set(rows.map((r) => r.stock_code)));
  const fallbackPriceMap = await loadLatestPriceHistoryMap(stockCodes);

  const grouped: Record<string, any> = {};

  for (const r of rows) {
    const code = r.stock_code;
    const sq = stockQuoteMap[code] || {};
    const fallback = fallbackPriceMap[code] || {};
    const price = sq.price ?? fallback.price ?? null;
    const changePct = sq.change_pct ?? fallback.change_pct ?? null;
    const quoteDate = sq.updated_at ?? fallback.trade_date ?? null;

    if (!grouped[code]) {
      grouped[code] = {
        stock_code: code,
        stock_name: r.stock_name,
        etf_count: 0,
        total_weight: 0,
        total_shares: 0,
        price,
        change_pct: changePct,
        quote_date: quoteDate,
        etfs: [],
      };
    }

    grouped[code].etf_count += 1;
    grouped[code].total_weight += Number(r.weight || 0);
    grouped[code].total_shares += Number(r.shares || 0);
    grouped[code].etfs.push(`${r.etf_code}:${Number(r.weight || 0).toFixed(2)}`);
  }

  const out = Object.values(grouped).map((g: any) => {
    g.market_value_billion = g.price ? g.total_shares * Number(g.price) / 100000000 : null;
    g.etfs = g.etfs.join(", ");
    return g;
  });

  return out.sort((a: any, b: any) =>
    Number(b.market_value_billion || 0) - Number(a.market_value_billion || 0) ||
    Number(b.etf_count || 0) - Number(a.etf_count || 0) ||
    Number(b.total_weight || 0) - Number(a.total_weight || 0)
  );
}

async function getStockDetail(stockCode: string) {
  const { holdings, etfQuoteMap, stockQuoteMap } = await loadBaseData();

  const latest = latestDateByEtf(holdings);
  const quote = stockQuoteMap[stockCode] || {};

  const rows = holdings
    .filter((h) => h.stock_code === stockCode && String(h.data_date) === latest[h.etf_code])
    .map((r) => {
      const q = etfQuoteMap[r.etf_code] || {};
      const price = quote.price ?? null;
      return {
        ...r,
        etf_name: q.etf_name || ETF_NAMES[r.etf_code] || r.etf_code,
        market_value_billion: price ? Number(r.shares || 0) * Number(price) / 100000000 : null,
      };
    })
    .sort((a, b) => Number(b.weight || 0) - Number(a.weight || 0));

  const history = holdings
    .filter((h) => h.stock_code === stockCode)
    .sort((a, b) => String(b.data_date).localeCompare(String(a.data_date)) || String(a.etf_code).localeCompare(String(b.etf_code)))
    .slice(0, 300);

  const [{ data: priceHistory }, { data: institutional }] = await Promise.all([
    supabase
      .from("stock_price_history")
      .select("*")
      .eq("stock_code", stockCode)
      .order("trade_date", { ascending: true })
      .limit(160),
    supabase
      .from("institutional_flows")
      .select("*")
      .eq("stock_code", stockCode)
      .order("trade_date", { ascending: false })
      .limit(80),
  ]);

  const name = rows[0]?.stock_name || quote.stock_name || stockCode;

  return {
    stock_code: stockCode,
    stock_name: name,
    quote,
    summary: {
      etf_count: new Set(rows.map((r) => r.etf_code)).size,
      total_shares: rows.reduce((s, r) => s + Number(r.shares || 0), 0),
      total_weight: rows.reduce((s, r) => s + Number(r.weight || 0), 0),
      market_value_billion: rows.reduce((s, r) => s + Number(r.market_value_billion || 0), 0),
    },
    etfs: rows,
    history,
    price_history: priceHistory || [],
    institutional: institutional || [],
  };
}


const VALID_SIGNAL_RANGE_DAYS = [1, 5, 10, 20];

function normalizeSignalRangeDays(raw: any) {
  const n = Number(raw || 1);
  return VALID_SIGNAL_RANGE_DAYS.includes(n) ? n : 1;
}

async function selectPaged(table: string, selectExpr: string, build?: (q: any) => any) {
  const out: any[] = [];
  const pageSize = 1000;

  for (let from = 0; ; from += pageSize) {
    const to = from + pageSize - 1;
    let q: any = supabase.from(table).select(selectExpr).range(from, to);
    if (build) q = build(q);

    const { data, error } = await q;
    if (error) throw new Error(`${table}: ${error.message}`);

    const rows = data || [];
    out.push(...rows);
    if (rows.length < pageSize) break;
  }

  return out;
}

async function loadSignalRowsByRange(signalRangeDays: number) {
  const dateOnlyRows = await selectPaged(
    "holdings",
    "etf_code,data_date",
    (q) => q.order("data_date", { ascending: false })
  );

  const datesByEtf: Record<string, Set<string>> = {};

  for (const r of dateOnlyRows) {
    const etf = String(r.etf_code || "");
    const d = String(r.data_date || "");
    if (!etf || !d) continue;
    if (!datesByEtf[etf]) datesByEtf[etf] = new Set();
    datesByEtf[etf].add(d);
  }

  const pairByEtf: Record<string, { current: string; previous: string | null }> = {};
  const neededEtfs = new Set<string>();
  const neededDates = new Set<string>();

  for (const etf of Object.keys(datesByEtf)) {
    const dates = Array.from(datesByEtf[etf]).sort();
    if (!dates.length) continue;

    const current = dates[dates.length - 1];
    const previousIndex = Math.max(0, dates.length - 1 - signalRangeDays);
    const previous = dates.length > 1 ? dates[previousIndex] : null;

    pairByEtf[etf] = { current, previous };
    neededEtfs.add(etf);
    neededDates.add(current);
    if (previous) neededDates.add(previous);
  }

  const etfList = Array.from(neededEtfs);
  const dateList = Array.from(neededDates);

  if (!etfList.length || !dateList.length) {
    return { holdings: [], pairByEtf };
  }

  const holdings = await selectPaged(
    "holdings",
    "*",
    (q) => q.in("etf_code", etfList).in("data_date", dateList)
  );

  return { holdings, pairByEtf };
}




async function getSignals(signalType?: string | null, signalRangeDaysInput: any = 1) {
  const signalRangeDays = normalizeSignalRangeDays(signalRangeDaysInput);

  function n(v: any, fallback = 0): number {
    if (v === null || v === undefined || v === '') return fallback;
    const x = Number(String(v).replace(/,/g, ''));
    return Number.isFinite(x) ? x : fallback;
  }

  function stockNameFix(code: string, fallback: string) {
    const fixes: Record<string, string> = {
      '2330': '台積電',
      '2327': '國巨',
      '2454': '聯發科',
      '2383': '台光電',
      '2382': '廣達',
      '2303': '聯電',
      '3711': '日月光投控',
      '2317': '鴻海',
      '6223': '旺矽',
      '3037': '欣興',
      '2308': '台達電',
      '2345': '智邦',
      '3017': '奇鋐',
      '6669': '緯穎',
      '8210': '勤誠',
      '4105': '東洋',
      '5274': '信驊科技',
      '6139': '亞翔工程',
    };
    return fixes[code] || fallback || code;
  }

  const [{ holdings, pairByEtf }, stockQuotes] = await Promise.all([
    loadSignalRowsByRange(signalRangeDays),
    selectAll("stock_quotes"),
  ]);

  const stockQuoteMap: Record<string, any> = {};
  for (const q of stockQuotes || []) {
    const code = String(q?.stock_code || q?.code || '').trim();
    if (code) stockQuoteMap[code] = q;
  }

  let rawChanges: any[] = [];
  let includedEtfCount = 0;
  let latestDataDate = "";

  for (const etf of Object.keys(pairByEtf || {})) {
    const pair = pairByEtf[etf];
    if (!pair?.current || !pair?.previous || pair.current === pair.previous) continue;

    const etfChanges = computeEtfChanges(holdings, etf, pair.current, pair.previous)
      .filter((c: any) => ["新增", "刪除", "加碼", "減碼"].includes(String(c.status)));

    includedEtfCount += 1;
    if (pair.current > latestDataDate) latestDataDate = pair.current;

    rawChanges.push(...etfChanges.map((x: any) => ({
      ...x,
      compare_date: pair.previous,
      signal_range_days: signalRangeDays,
    })));
  }

  const typeMap: Record<string, string> = {
    added: "新增",
    removed: "刪除",
    increased: "加碼",
    decreased: "減碼",
  };

  if (signalType && typeMap[signalType]) {
    rawChanges = rawChanges.filter((c: any) => c.status === typeMap[signalType]);
  }

  const byStock: Record<string, any> = {};

  for (const c of rawChanges) {
    const code = String(c.stock_code || c.code || '').trim();
    if (!/^[0-9]{4}$/.test(code)) continue;

    const q = stockQuoteMap[code] || {};
    const price = n(q.price ?? q.close_price ?? q.close ?? q.last_price, NaN);
    const changePct = n(q.change_pct ?? q.percent ?? q.pct ?? q.changePercent, NaN);
    const deltaShares = n(c.delta_shares ?? c.shares_change ?? c.change_shares, 0);
    if (!deltaShares) continue;

    if (!byStock[code]) {
      const name = stockNameFix(code, String(c.stock_name || c.name || code));
      byStock[code] = {
        stock_code: code,
        code,
        stock_name: name,
        name,
        price: Number.isFinite(price) ? price : null,
        change_pct: Number.isFinite(changePct) ? changePct : null,
        delta_shares: 0,
        delta_lots: 0,
        net_delta_lots: 0,
        flow_billion: 0,
        money_billion: 0,
        amount_billion: 0,
        delta_amount_billion: 0,
        delta_value_billion: 0,
        net_amount_billion: 0,
        has_price: Number.isFinite(price),
        add_etf_count: 0,
        reduce_etf_count: 0,
        add_count: 0,
        reduce_count: 0,
        etf_code_list: [],
        statuses: [],
        data_date: latestDataDate,
        source: 'api_getSignals_v101_net_holdings',
      };
    }

    const b = byStock[code];
    b.delta_shares += deltaShares;
    b.delta_lots += deltaShares / 1000;
    b.net_delta_lots += deltaShares / 1000;
    b.etf_code_list.push(c.etf_code);
    b.statuses.push(`${c.etf_code} ${c.status}`);

    if (deltaShares > 0) {
      b.add_etf_count += 1;
      b.add_count += 1;
    } else if (deltaShares < 0) {
      b.reduce_etf_count += 1;
      b.reduce_count += 1;
    }
  }

  const rows = Object.values(byStock).map((x: any) => {
    const price = n(x.price, NaN);
    const flow = Number.isFinite(price) ? x.delta_lots * 1000 * price / 100000000 : null;
    const status = x.delta_lots > 0 ? '加碼' : x.delta_lots < 0 ? '減碼' : '異動';

    return {
      ...x,
      status,
      flow_billion: flow,
      money_billion: flow,
      amount_billion: flow,
      delta_amount_billion: flow,
      delta_value_billion: flow,
      net_amount_billion: flow,
      etf_count: x.etf_code_list.length,
    };
  }).filter((x: any) => x.status !== '異動');

  const summary: Record<string, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0, 異動: 0 };
  for (const r of rows) summary[String(r.status)] = (summary[String(r.status)] || 0) + 1;

  const aggregate = [...rows].sort((a: any, b: any) => {
    const av = Number.isFinite(Number(a.flow_billion)) ? Math.abs(Number(a.flow_billion)) : Math.abs(Number(a.delta_lots || 0));
    const bv = Number.isFinite(Number(b.flow_billion)) ? Math.abs(Number(b.flow_billion)) : Math.abs(Number(b.delta_lots || 0));
    return bv - av;
  });

  return {
    summary,
    changes: rawChanges,
    rows: aggregate,
    aggregate,
    rangeDays: signalRangeDays,
    signalRangeDays,
    range_days: signalRangeDays,
    rangeLabel: signalRangeDays === 1 ? "今日" : `${signalRangeDays}日`,
    latestDataDate,
    data_date: latestDataDate,
    includedEtfCount,
    fetched_etf_count: includedEtfCount,
    total_etf_count: ETF_CODES.length,
    comparisonMode: signalRangeDays === 1 ? "前一交易日" : `${signalRangeDays}個交易日前`,
    source: 'api_getSignals_v101_net_holdings',
  };
}



export async function apiGet(path: string) {
  const u = new URL(path, "https://local");

  if (u.pathname === "/etfs") return getEtfs();

  if (u.pathname.startsWith("/etfs/")) {
    return getEtfDetail(decodeURIComponent(u.pathname.split("/")[2]));
  }

  if (u.pathname === "/holdings") return getConstituentSummary();

  if (u.pathname.startsWith("/stocks/")) {
    return getStockDetail(decodeURIComponent(u.pathname.split("/")[2]));
  }

  if (u.pathname === "/signals") {
    const days = normalizeSignalRangeDays(
      u.searchParams.get("days") ||
      u.searchParams.get("rangeDays") ||
      u.searchParams.get("signalRangeDays") ||
      "1"
    );
    return getSignals(u.searchParams.get("type"), days);
  }

  throw new Error(`Unknown API path: ${path}`);
}

export async function apiPost(_path: string) {
  throw new Error("此免費部署版不支援前端手動更新；請用 GitHub Actions 更新資料。");
}

export function fmt(n: any, digits = 2, empty = "-") {
  if (n === null || n === undefined || n === "" || Number.isNaN(Number(n))) return empty;
  return Number(n).toLocaleString("zh-TW", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function fmt0(n: any, empty = "-") {
  if (n === null || n === undefined || n === "" || Number.isNaN(Number(n))) return empty;
  return Number(n).toLocaleString("zh-TW", { maximumFractionDigits: 0 });
}

export function signedClass(n: any) {
  const v = Number(n || 0);
  if (v > 0) return "red";
  if (v < 0) return "green";
  return "muted";
}
