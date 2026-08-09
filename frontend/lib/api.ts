import { compactSignalsPayload } from './signalsCompact';
import { createClient } from "@supabase/supabase-js";
import { ETF_CODES } from './etfData';
import { REFERENCE_ETF_CODES } from './referenceEtfs';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function readAppCache(cacheKey: string) {
  try {
    const { data, error } = await supabase
      .from("app_cache")
      .select("payload,data_date,updated_at")
      .eq("cache_key", cacheKey)
      .maybeSingle();

    if (error || !data?.payload) return null;

    return {
      ...data.payload,
      cache_hit: true,
      cache_key: cacheKey,
      cache_updated_at: data.updated_at,
    };
  } catch {
    return null;
  }
}

async function writeAppCache(cacheKey: string, dataDate: string | null, payload: any) {
  try {
    await supabase
      .from("app_cache")
      .upsert({
        cache_key: cacheKey,
        data_date: dataDate || null,
        payload,
        updated_at: new Date().toISOString(),
      }, { onConflict: "cache_key" });
  } catch {}
}

async function getLatestHoldingsDataDate() {
  const { data } = await supabase
    .from("holdings")
    .select("data_date")
    .order("data_date", { ascending: false })
    .limit(1)
    .maybeSingle();

  return String(data?.data_date || "").slice(0, 10);
}


const ETF_NAMES: Record<string, string> = {
  "00400A": "主動國泰動能高息",
  "00401A": "主動摩根台灣鑫收",
  "00402A": "主動安聯美國科技",
  "00403A": "主動統一升級50",
  "00404A": "主動聯博動能50",
  "00405A": "主動富邦台灣龍耀",
  "00406A": "主動中信台灣收益",
  "00407A": "主動凱基台灣",
  "00410A": "主動永豐科技趨勢",
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
  const { data: latestRow, error: latestErr } = await supabase
    .from("holdings")
    .select("data_date")
    .order("data_date", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (latestErr) throw latestErr;

  const targetDate = String(latestRow?.data_date || "").slice(0, 10);
  if (!targetDate) return [];

  const { data: marketCapVersionRow } = await supabase
    .from("stock_quotes")
    .select("market_cap_updated_at")
    .not("market_cap_updated_at", "is", null)
    .order("market_cap_updated_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const marketCapVersion = String(
    marketCapVersionRow?.market_cap_updated_at || "none"
  ).slice(0, 19);
  const appCacheKey =
    `holdings_summary:v2:date=${targetDate}:market_caps=${marketCapVersion}`;
  const cached = await readAppCache(appCacheKey);

  if (cached && Array.isArray((cached as any).rows)) {
    return (cached as any).rows;
  }

  const [latestRows, stockQuotes] = await Promise.all([
    selectPaged(
      "holdings",
      "etf_code,data_date,stock_code,stock_name,weight,shares",
      (q) => q.eq("data_date", targetDate)
    ),
    selectAll("stock_quotes"),
  ]);

  const stockQuoteMap: Record<string, any> = {};
  for (const q of stockQuotes || []) {
    stockQuoteMap[String(q.stock_code || "")] = q;
  }

  const rows = (latestRows || []).filter((h) => isNormalStockCode(String(h.stock_code || "")));
  const grouped: Record<string, any> = {};

  for (const r of rows) {
    const code = String(r.stock_code || "");
    const sq = stockQuoteMap[code] || {};
    const price = sq.price ?? null;
    const changePct = sq.change_pct ?? null;
    const quoteDate = sq.updated_at ?? null;
    const marketCapBillion = Number(sq.market_cap_billion || 0) || null;

    if (!grouped[code]) {
      grouped[code] = {
        stock_code: code,
        stock_name: r.stock_name,
        data_date: targetDate,
        etf_count: 0,
        total_weight: 0,
        total_shares: 0,
        price,
        change_pct: changePct,
        quote_date: quoteDate,
        market_cap_billion: marketCapBillion,
        market_cap_updated_at: sq.market_cap_updated_at ?? null,
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
    g.estimated_holding_pct =
      g.market_value_billion && g.market_cap_billion
        ? g.market_value_billion / g.market_cap_billion * 100
        : null;
    g.etfs = g.etfs.join(", ");
    return g;
  });

  const result = out.sort((a: any, b: any) =>
    Number(b.market_value_billion || 0) - Number(a.market_value_billion || 0) ||
    Number(b.etf_count || 0) - Number(a.etf_count || 0) ||
    Number(b.total_weight || 0) - Number(a.total_weight || 0)
  );

  await writeAppCache(appCacheKey, targetDate, {
    rows: result,
    data_date: targetDate,
  });

  return result;
}


async function getStockDetail(stockCode: string, fresh = false) {
  const code = String(stockCode || "").trim();
  const appCacheDate = await getLatestHoldingsDataDate();
  const appCacheKey = `stock_detail:v2:${code}:date=${appCacheDate || "latest"}`;

  if (!fresh) {
    const cached = await readAppCache(appCacheKey);
    if (cached) return cached;
  }

  const [stockHistoryRows, stockQuoteRows, priceHistoryRes, institutionalRes] = await Promise.all([
    selectPaged(
      "holdings",
      "*",
      (q) => q.eq("stock_code", code)
    ),
    selectPaged(
      "stock_quotes",
      "*",
      (q) => q.eq("stock_code", code).limit(1)
    ),
    supabase
      .from("stock_price_history")
      .select("*")
      .eq("stock_code", code)
      .order("trade_date", { ascending: true })
      .limit(160),
    supabase
      .from("institutional_flows")
      .select("*")
      .eq("stock_code", code)
      .order("trade_date", { ascending: false })
      .limit(80),
  ]);

  const relatedEtfs = Array.from(new Set(
    (stockHistoryRows || [])
      .map((r: any) => String(r.etf_code || "").trim())
      .filter(Boolean)
  ));

  const [dateRows, etfQuotes] = await Promise.all([
    relatedEtfs.length
      ? selectPaged(
          "holdings",
          "etf_code,data_date",
          (q) => q.in("etf_code", relatedEtfs).order("data_date", { ascending: false })
        )
      : Promise.resolve([]),
    relatedEtfs.length
      ? selectPaged(
          "etf_quotes",
          "*",
          (q) => q.in("etf_code", relatedEtfs)
        )
      : Promise.resolve([]),
  ]);

  const etfQuoteMap: Record<string, any> = {};
  for (const q of etfQuotes || []) {
    const etf = String(q.etf_code || "");
    if (etf) etfQuoteMap[etf] = q;
  }

  const datesByEtf: Record<string, Set<string>> = {};
  for (const r of dateRows || []) {
    const etf = String(r.etf_code || "");
    const d = String(r.data_date || "");
    if (!etf || !d) continue;
    if (!datesByEtf[etf]) datesByEtf[etf] = new Set();
    datesByEtf[etf].add(d);
  }

  const latestByEtf: Record<string, string> = {};
  for (const etf of Object.keys(datesByEtf)) {
    const dates = Array.from(datesByEtf[etf]).sort();
    if (dates.length) latestByEtf[etf] = dates[dates.length - 1];
  }

  const stockQuote = stockQuoteRows?.[0] || {};
  const priceHistory = priceHistoryRes.data || [];
  const institutional = institutionalRes.data || [];
  const latestPrice = priceHistory.length ? priceHistory[priceHistory.length - 1] : {};

  const quote = {
    ...latestPrice,
    ...stockQuote,
    stock_code: code,
    stock_name: stockQuote.stock_name || latestPrice.stock_name || stockHistoryRows?.[0]?.stock_name || code,
    price: stockQuote.price ?? latestPrice.close ?? null,
    change_pct: stockQuote.change_pct ?? latestPrice.change_pct ?? null,
  };

  const rows = (stockHistoryRows || [])
    .filter((h: any) => {
      const etf = String(h.etf_code || "");
      const d = String(h.data_date || "");
      return etf && d && d === latestByEtf[etf];
    })
    .map((r: any) => {
      const etf = String(r.etf_code || "");
      const q = etfQuoteMap[etf] || {};
      const price = quote.price ?? null;
      return {
        ...r,
        etf_name: q.etf_name || ETF_NAMES[etf] || etf,
        market_value_billion: price ? Number(r.shares || 0) * Number(price) / 100000000 : null,
      };
    })
    .sort((a: any, b: any) => Number(b.weight || 0) - Number(a.weight || 0));

  const stockRowByEtfDate: Record<string, Record<string, any>> = {};

  for (const h of stockHistoryRows || []) {
    const etf = String(h.etf_code || "");
    const date = String(h.data_date || "");
    if (!etf || !date) continue;
    if (!stockRowByEtfDate[etf]) stockRowByEtfDate[etf] = {};
    stockRowByEtfDate[etf][date] = h;
  }

  const augmentedHistory = [...(stockHistoryRows || [])];
  const seenHistoryKeys = new Set(
    augmentedHistory.map((h: any) => [h.etf_code, h.data_date, h.stock_code].join("|"))
  );

  function addSyntheticHistoryRow(row: any) {
    const key = [row.etf_code, row.data_date, row.stock_code].join("|");
    if (seenHistoryKeys.has(key)) return;
    seenHistoryKeys.add(key);
    augmentedHistory.push(row);
  }

  for (const etf of Object.keys(datesByEtf)) {
    const dates = Array.from(datesByEtf[etf]).sort();
    const byDate = stockRowByEtfDate[etf] || {};

    for (let i = 1; i < dates.length; i++) {
      const prevDate = dates[i - 1];
      const currDate = dates[i];
      const prev = byDate[prevDate];
      const curr = byDate[currDate];

      if (prev && !curr) {
        const prevShares = Number(prev.shares || 0);
        addSyntheticHistoryRow({
          ...prev,
          data_date: currDate,
          shares: 0,
          weight: 0,
          status: "刪除",
          operation_status: "刪除",
          prev_date: prevDate,
          delta_raw_shares: -prevShares,
          delta_shares: -prevShares / 1000,
          curr_weight: 0,
          prev_weight: Number(prev.weight || 0),
        });
      }

      if (!prev && curr) {
        addSyntheticHistoryRow({
          ...curr,
          data_date: prevDate,
          shares: 0,
          weight: 0,
          status: "新增基準",
          operation_status: "新增基準",
          prev_date: prevDate,
          delta_raw_shares: 0,
          delta_shares: 0,
          curr_weight: 0,
          prev_weight: 0,
        });
      }
    }
  }

  const history = augmentedHistory
    .map((r: any) => {
      const etf = String(r.etf_code || "");
      return {
        ...r,
        etf_name: r.etf_name || etfQuoteMap[etf]?.etf_name || ETF_NAMES[etf] || etf,
      };
    })
    .sort((a: any, b: any) =>
      String(b.data_date).localeCompare(String(a.data_date)) ||
      String(a.etf_code).localeCompare(String(b.etf_code))
    )
    .slice(0, 300);

  const operationRecords: any[] = [];

  for (const etf of Object.keys(datesByEtf)) {
    const dates = Array.from(datesByEtf[etf]).sort();
    const byDate = stockRowByEtfDate[etf] || {};

    for (let i = 1; i < dates.length; i++) {
      const prevDate = dates[i - 1];
      const currDate = dates[i];
      const prev = byDate[prevDate];
      const curr = byDate[currDate];

      if (!prev && !curr) continue;

      const prevRawShares = Number(prev?.shares || 0);
      const currRawShares = Number(curr?.shares || 0);
      const prevWeight = Number(prev?.weight || 0);
      const currWeight = Number(curr?.weight || 0);

      const deltaRawShares = currRawShares - prevRawShares;
      const deltaWeight = currWeight - prevWeight;

      if (
        Math.abs(deltaRawShares) < 0.000001 &&
        Math.abs(deltaWeight) < 0.000001
      ) continue;

      let status = "";
      if (!prev && curr) status = "新增";
      else if (prev && !curr) status = "刪除";
      else if (deltaRawShares > 0) status = "加碼";
      else if (deltaRawShares < 0) status = "減碼";
      else if (deltaWeight > 0) status = "加碼";
      else if (deltaWeight < 0) status = "減碼";

      if (!status) continue;

      operationRecords.push({
        data_date: currDate,
        prev_date: prevDate,
        etf_code: etf,
        etf_name: etfQuoteMap[etf]?.etf_name || ETF_NAMES[etf] || etf,
        stock_code: code,
        stock_name: curr?.stock_name || prev?.stock_name || quote.stock_name || code,
        prev_raw_shares: prevRawShares,
        curr_raw_shares: currRawShares,
        delta_raw_shares: deltaRawShares,
        delta_shares: deltaRawShares / 1000,
        prev_weight: prevWeight,
        curr_weight: currWeight,
        delta_weight: deltaWeight,
        change_pct: prevRawShares > 0
          ? deltaRawShares / prevRawShares * 100
          : null,
        status,
        operation_status: status,
      });
    }
  }

  operationRecords.sort((a, b) =>
    String(b.data_date).localeCompare(String(a.data_date)) ||
    String(a.etf_code).localeCompare(String(b.etf_code))
  );

  const name = rows[0]?.stock_name || quote.stock_name || code;

  const result = {
    stock_code: code,
    stock_name: name,
    quote,
    summary: {
      etf_count: new Set(rows.map((r: any) => r.etf_code)).size,
      total_shares: rows.reduce((sum: number, r: any) => sum + Number(r.shares || 0), 0),
      total_weight: rows.reduce((sum: number, r: any) => sum + Number(r.weight || 0), 0),
      market_value_billion: rows.reduce((sum: number, r: any) => sum + Number(r.market_value_billion || 0), 0),
    },
    etfs: rows,
    history,
    operation_records: operationRecords.slice(0, 500),
    price_history: priceHistory,
    institutional,
  };

  await writeAppCache(appCacheKey, appCacheDate, result);

  return result;
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





function normalizeSignalUniverse(input: any): 'active' | 'reference' | 'all' {
  const raw = String(input || 'active').toLowerCase();
  if (raw === 'reference' || raw === 'passive' || raw === 'general') return 'reference';
  if (raw === 'all') return 'all';
  return 'active';
}

function makeSignalsCacheSignalType(
  signalType:
    string | null | undefined,
  universe:
    'active' | 'reference' | 'all',
  compact = false,
) {
  const base =
    `${universe}::${String(
      signalType || '',
    )}`;

  return compact
    ? `compact::${base}`
    : base;
}

async function getSignalsCacheScope() {
  const toDate = (v: any) => String(v ?? '').slice(0, 10);

  const { data: latestRow, error: latestErr } = await supabase
    .from('holdings')
    .select('data_date')
    .order('data_date', { ascending: false })
    .limit(1)
    .maybeSingle();

  if (latestErr) throw latestErr;

  const dataDate = toDate(latestRow?.data_date);
  if (!dataDate) return { dataDate: '', holdingsRowCount: 0 };

  const { count, error: countErr } = await supabase
    .from('holdings')
    .select('*', { count: 'exact', head: true })
    .eq('data_date', dataDate);

  if (countErr) {
    console.warn('[signals_cache] count failed:', countErr.message);
    return { dataDate, holdingsRowCount: 0 };
  }

  return { dataDate, holdingsRowCount: count || 0 };
}

function makeSignalsCacheKey(
  signalType:
    string | null | undefined,
  days: number,
  scope: {
    dataDate: string;
    holdingsRowCount: number;
  },
  universe:
    'active' | 'reference' | 'all' =
      'active',
  compact = false,
) {
  const type =
    String(signalType || 'all');

  const prefix =
    compact
      ? 'signals:v3:compact'
      : 'signals:v2';

  return (
    `${prefix}:${universe}:${type}` +
    `:days=${days}` +
    `:date=${scope.dataDate}` +
    `:rows=${scope.holdingsRowCount}`
  );
}

async function readSignalsCache(signalType: string | null | undefined, days: number, scope: { dataDate: string; holdingsRowCount: number }, universe: 'active' | 'reference' | 'all' = 'active') {
  if (!hasSupabaseEnv) return null;
  if (!scope.dataDate) return null;

  const cacheKey = makeSignalsCacheKey(signalType, days, scope, universe);
  const cacheSignalType = makeSignalsCacheSignalType(signalType, universe);

  const { data, error } = await supabase
    .from('signals_cache')
    .select('payload,cache_key,updated_at,data_date')
    .eq('cache_key', cacheKey)
    .eq('days', days)
    .eq('signal_type', cacheSignalType)
    .maybeSingle();

  if (error) {
    const msg = String(error.message || '');
    if (!msg.includes('does not exist')) console.warn('[signals_cache] read failed:', msg);
    return null;
  }

  if (!data?.payload) return null;

  return {
    ...data.payload,
    cache_hit: true,
    cache_mode: 'exact',
    cache_key: data.cache_key,
    cache_updated_at: data.updated_at,
  };
}

async function writeSignalsCache(
  signalType:
    string | null | undefined,
  days: number,
  scope: {
    dataDate: string;
    holdingsRowCount: number;
  },
  payload: any,
  universe:
    'active' | 'reference' | 'all' =
      'active',
) {
  if (!hasSupabaseEnv) return;
  if (!scope.dataDate) return;

  const updatedAt =
    new Date().toISOString();

  const fullCacheKey =
    makeSignalsCacheKey(
      signalType,
      days,
      scope,
      universe,
      false,
    );

  const compactCacheKey =
    makeSignalsCacheKey(
      signalType,
      days,
      scope,
      universe,
      true,
    );

  const fullSignalType =
    makeSignalsCacheSignalType(
      signalType,
      universe,
      false,
    );

  const compactSignalType =
    makeSignalsCacheSignalType(
      signalType,
      universe,
      true,
    );

  const compactPayload =
    compactSignalsPayload(
      payload,
    );

  const rows = [
    {
      cache_key:
        fullCacheKey,
      data_date:
        scope.dataDate,
      holdings_row_count:
        scope.holdingsRowCount,
      days,
      signal_type:
        fullSignalType,
      payload,
      updated_at:
        updatedAt,
    },
    {
      cache_key:
        compactCacheKey,
      data_date:
        scope.dataDate,
      holdings_row_count:
        scope.holdingsRowCount,
      days,
      signal_type:
        compactSignalType,
      payload:
        compactPayload,
      updated_at:
        updatedAt,
    },
  ];

  const { error } =
    await supabase
      .from('signals_cache')
      .upsert(
        rows,
        {
          onConflict:
            'cache_key',
        },
      );

  if (error) {
    const message =
      String(
        error.message || '',
      );

    if (
      !message.includes(
        'does not exist',
      )
    ) {
      console.warn(
        '[signals_cache] full/compact write failed:',
        message,
      );
    }
  }
}

async function getSignals(signalType?: string | null, signalRangeDaysInput: any = 1, universeInput: any = 'active') {
  const toDate = (v: any) => String(v ?? '').slice(0, 10);
  const n = (v: any) => {
    const x = Number(v);
    return Number.isFinite(x) ? x : 0;
  };
  const isTwStockCode = (v: any) => /^[0-9]{4}$/.test(String(v ?? '').trim());
  const codeKey = (v: any) => String(v ?? '').trim();
  const activeEtfCodes: string[] = Array.from(new Set(
    (Array.isArray(ETF_CODES) ? ETF_CODES : [])
      .map((x: any) => codeKey(x))
      .filter(Boolean)
  ));
  const referenceEtfCodes: string[] = Array.from(new Set(
    (Array.isArray(REFERENCE_ETF_CODES) ? REFERENCE_ETF_CODES : [])
      .map((x: any) => codeKey(x))
      .filter(Boolean)
  ));
  const rawUniverse = String(universeInput || 'active').toLowerCase();
  const universe = rawUniverse === 'reference' || rawUniverse === 'passive' || rawUniverse === 'general'
    ? 'reference'
    : rawUniverse === 'all'
      ? 'all'
      : 'active';
  const totalEtfCodes: string[] = universe === 'reference'
    ? referenceEtfCodes
    : universe === 'all'
      ? Array.from(new Set([...activeEtfCodes, ...referenceEtfCodes]))
      : activeEtfCodes;
  const signalRangeDays = Math.max(1, Math.trunc(n(signalRangeDaysInput || 1)) || 1);
  const pageSize = 1000;

  async function selectAll(table: string, columns: string, build?: (q: any) => any) {
    let out: any[] = [];
    for (let from = 0; ; from += pageSize) {
      let q: any = supabase.from(table).select(columns);
      if (build) q = build(q);
      const { data, error } = await q.range(from, from + pageSize - 1);
      if (error) throw error;
      const rows = data || [];
      out = out.concat(rows);
      if (rows.length < pageSize) break;
    }
    return out;
  }

  try {
    // 1) 全站統一 targetDate：只允許 current holdings 使用這一天。
    //    這會避免 06/18 今日訊號混入 06/17 ETF 的持股。
    const { data: latestRow, error: latestErr } = await supabase
      .from('holdings')
      .select('data_date')
      .in('etf_code', totalEtfCodes)
      .order('data_date', { ascending: false })
      .limit(1)
      .maybeSingle();
    if (latestErr) throw latestErr;
    const targetDate = toDate(latestRow?.data_date);
    if (!targetDate) {
      return {
        rows: [], changes: [], rawChanges: [], items: [], signals: [],
        data_date: '', target_data_date: '', includedEtfCount: 0,
        fetched_etf_count: 0, total_etf_count: totalEtfCodes.length,
        signal_count: 0, today_change_count: 0,
        source: 'api_getSignals_v109_today_only_empty',
        universe, etf_universe: universe,
      };
    }

    // 2) 今天所有 holdings。只有有 targetDate 的 ETF 可以進今日訊號。
    const todayRowsAll = await selectAll(
      'holdings',
      'etf_code,data_date,stock_code,stock_name,weight,shares',
      (q) => q
        .in('etf_code', totalEtfCodes)
        .eq('data_date', targetDate)
        .order('etf_code', { ascending: true })
        .order('stock_code', { ascending: true })
    );
    const todayEtfSet = new Set(todayRowsAll.map((r: any) => codeKey(r.etf_code)).filter(Boolean));

    const universeEtfs = totalEtfCodes;

    const missingTodayEtfCodes = universeEtfs.filter((c) => !todayEtfSet.has(c));

    // 3) 讀所有 ETF 日期，只用來找「同一檔 ETF 的前 N 個交易日」。
    const dateRows = await selectAll(
      'holdings',
      'etf_code,data_date',
      (q) => q
        .in('etf_code', universeEtfs)
        .lte('data_date', targetDate)
        .order('etf_code', { ascending: true })
        .order('data_date', { ascending: true })
    );
    const datesByEtf: Record<string, string[]> = {};
    for (const r of dateRows) {
      const etf = codeKey(r.etf_code);
      const d = toDate(r.data_date);
      if (!etf || !d) continue;
      if (!datesByEtf[etf]) datesByEtf[etf] = [];
      if (!datesByEtf[etf].includes(d)) datesByEtf[etf].push(d);
    }
    Object.values(datesByEtf).forEach((arr) => arr.sort());

    const prevDateByEtf: Record<string, string> = {};
    const noCompareEtfCodes: string[] = [];
    const includedEtfs: string[] = [];
    for (const etf of universeEtfs) {
      if (!todayEtfSet.has(etf) && !Array.from(datesByEtf[etf] || []).includes(targetDate)) continue;
      const dates = datesByEtf[etf] || [];
      const idx = dates.indexOf(targetDate);
      const prevIdx = idx - signalRangeDays;
      if (idx < 0 || prevIdx < 0) {
        noCompareEtfCodes.push(etf);
        continue;
      }
      prevDateByEtf[etf] = dates[prevIdx];
      includedEtfs.push(etf);
    }

    const dateList = Array.from(new Set([targetDate, ...Object.values(prevDateByEtf)])).filter(Boolean);
    const holdingsRows = includedEtfs.length
      ? await selectAll(
          'holdings',
          'etf_code,data_date,stock_code,stock_name,weight,shares',
          (q) => q
            .in('etf_code', includedEtfs)
            .in('data_date', dateList)
            .order('etf_code', { ascending: true })
            .order('data_date', { ascending: true })
            .order('stock_code', { ascending: true })
        )
      : [];

    const currMap = new Map<string, any>();
    const prevMap = new Map<string, any>();
    const nameByCode: Record<string, string> = {};
    for (const r of holdingsRows) {
      const etf = codeKey(r.etf_code);
      const code = codeKey(r.stock_code);
      const d = toDate(r.data_date);
      if (!etf || !isTwStockCode(code)) continue;
      if (r.stock_name) nameByCode[code] = String(r.stock_name);
      const key = `${etf}|${code}`;
      if (d === targetDate) currMap.set(key, r);
      else if (d === prevDateByEtf[etf]) prevMap.set(key, r);
    }

    const agg: Record<string, any> = {};
    for (const etf of includedEtfs) {
      const stockSet = new Set<string>();
      for (const key of currMap.keys()) if (key.startsWith(`${etf}|`)) stockSet.add(key.split('|')[1]);
      for (const key of prevMap.keys()) if (key.startsWith(`${etf}|`)) stockSet.add(key.split('|')[1]);

      for (const code of stockSet) {
        const key = `${etf}|${code}`;
        const curr = currMap.get(key);
        const prev = prevMap.get(key);
        const currRawShares = n(curr?.shares);
        const prevRawShares = n(prev?.shares);
        const deltaRawShares = currRawShares - prevRawShares;
        const currWeight = n(curr?.weight);
        const prevWeight = n(prev?.weight);
        const deltaWeight = currWeight - prevWeight;

        // 若該日期沒有持股 row，視為已知的 0 股。
        // 只有 shares 欄位本身缺失時，才使用權重變化作為 fallback。
        const currSharesKnown =
          !curr ||
          (curr.shares !== null &&
            curr.shares !== undefined &&
            String(curr.shares).trim() !== '');

        const prevSharesKnown =
          !prev ||
          (prev.shares !== null &&
            prev.shares !== undefined &&
            String(prev.shares).trim() !== '');

        const sharesComparable = currSharesKnown && prevSharesKnown;

        let etfStatus = '';

        if (sharesComparable) {
          // 股數未改變時，權重波動不視為 ETF 實際操作。
          if (Math.abs(deltaRawShares) < 1) continue;

          if (prevRawShares <= 0 && currRawShares > 0) etfStatus = '新增';
          else if (currRawShares <= 0 && prevRawShares > 0) etfStatus = '刪除';
          else if (deltaRawShares > 0) etfStatus = '加碼';
          else if (deltaRawShares < 0) etfStatus = '減碼';
        } else {
          // 部分來源沒有提供持股股數時，才退回權重判斷。
          if (!prev && curr) etfStatus = '新增';
          else if (prev && !curr) etfStatus = '刪除';
          else if (deltaWeight > 0) etfStatus = '加碼';
          else if (deltaWeight < 0) etfStatus = '減碼';
        }

        if (!etfStatus) continue;

        if (!agg[code]) {
          agg[code] = {
            stock_code: code,
            code,
            symbol: code,
            stock_name: nameByCode[code] || String(curr?.stock_name || prev?.stock_name || ''),
            name: nameByCode[code] || String(curr?.stock_name || prev?.stock_name || ''),
            curr_raw_shares: 0,
            prev_raw_shares: 0,
            delta_raw_shares: 0,
            curr_weight: 0,
            prev_weight: 0,
            delta_weight: 0,
            buy_etf_count: 0,
            sell_etf_count: 0,
            add_count: 0,
            delete_count: 0,
            increase_count: 0,
            decrease_count: 0,
            etf_change_count: 0,
            changed_etfs: [],
          };
        }
        const g = agg[code];
        g.curr_raw_shares += currRawShares;
        g.prev_raw_shares += prevRawShares;
        g.delta_raw_shares += deltaRawShares;
        g.curr_weight += currWeight;
        g.prev_weight += prevWeight;
        g.delta_weight += deltaWeight;
        g.etf_change_count += 1;
        g.changed_etfs.push({
          etf_code: etf,
          data_date: targetDate,
          prev_date: prevDateByEtf[etf],
          stock_code: code,
          stock_name: g.stock_name,
          status: etfStatus,
          delta_raw_shares: deltaRawShares,
          delta_shares: deltaRawShares / 1000,
          delta_weight: deltaWeight,
          curr_weight: currWeight,
          prev_weight: prevWeight,
        });
        if (etfStatus === '新增') g.add_count += 1;
        if (etfStatus === '刪除') g.delete_count += 1;
        if (etfStatus === '加碼') g.increase_count += 1;
        if (etfStatus === '減碼') g.decrease_count += 1;
        if (etfStatus === '新增' || etfStatus === '加碼') g.buy_etf_count += 1;
        if (etfStatus === '刪除' || etfStatus === '減碼') g.sell_etf_count += 1;
      }
    }

    const stockCodes = Object.keys(agg);

    const quoteRows = stockCodes.length
      ? await selectAll(
          'stock_quotes',
          'stock_code,stock_name,price,change,change_pct,volume,amount,updated_at',
          (q) => q.in('stock_code', stockCodes)
        )
      : [];

    const quoteByCode: Record<string, any> = {};
    for (const q of quoteRows) quoteByCode[codeKey(q.stock_code)] = q;

    let targetPriceRows: any[] = [];
    try {
      targetPriceRows = stockCodes.length
        ? await selectAll(
            'stock_price_history',
            'stock_code,trade_date,stock_name,close,change,change_pct,volume,amount,source,updated_at',
            (q) => q
              .in('stock_code', stockCodes)
              .lte('trade_date', targetDate)
              .order('trade_date', { ascending: false })
          )
        : [];
    } catch (e) {
      console.warn('[signals] stock_price_history unavailable:', e);
      targetPriceRows = [];
    }

    const targetPriceByCode: Record<string, any> = {};
    for (const h of targetPriceRows) {
      const code = codeKey(h.stock_code);
      const d = toDate(h.trade_date);
      if (!code || !d || d > targetDate) continue;

      const old = targetPriceByCode[code];
      if (!old || d > toDate(old.trade_date)) {
        targetPriceByCode[code] = h;
      }
    }

    let historyQuoteRows: any[] = [];
    try {
      historyQuoteRows = stockCodes.length
        ? await selectAll(
            'stock_price_history',
            'stock_code,trade_date,close,change_pct,volume',
            (q) => q
              .in('stock_code', stockCodes)
              .lte('trade_date', targetDate)
              .order('trade_date', { ascending: false })
          )
        : [];
    } catch (e) {
      console.warn('[signals] stock_price_history fallback failed:', e);
      historyQuoteRows = [];
    }

    const historyQuoteByCode: Record<string, any> = {};
    for (const h of historyQuoteRows) {
      const code = codeKey(h.stock_code);
      const d = toDate(h.trade_date);
      if (!code || !d) continue;
      const old = historyQuoteByCode[code];
      if (!old || d > toDate(old.trade_date)) historyQuoteByCode[code] = h;
    }

    for (const code of stockCodes) {
      const h = historyQuoteByCode[code];
      if (!h) continue;
      const q = quoteByCode[code] || {};
      quoteByCode[code] = {
        ...q,
        price: h.close,
        change_pct: h.change_pct,
        volume: h.volume ?? q.volume,
        updated_at: h.trade_date ?? q.updated_at,
        quote_source: 'stock_price_history',
      };
    }

    let rows = Object.values(agg).map((g: any) => {
      const historyQ = targetPriceByCode[g.stock_code];
      const rawQ = quoteByCode[g.stock_code] || {};

      const quoteTradeDate = toDate(rawQ.trade_date || '');
      const quoteDateOk = quoteTradeDate === targetDate;

      const historyTradeDate = toDate(historyQ?.trade_date || '');
      const historyDateOk = Boolean(historyQ && historyTradeDate && historyTradeDate <= targetDate);

      const q = historyDateOk
        ? {
            ...rawQ,
            stock_name: historyQ.stock_name || rawQ.stock_name || g.stock_name,
            price: historyQ.close,
            change: historyQ.change,
            change_pct: historyQ.change_pct,
            volume: historyQ.volume ?? rawQ.volume,
            amount: historyQ.amount ?? rawQ.amount,
            trade_date: historyQ.trade_date,
            updated_at: historyQ.updated_at || historyQ.trade_date,
            source: historyQ.source || 'stock_price_history',
            quote_source: 'stock_price_history',
          }
        : quoteDateOk
          ? rawQ
          : { stock_name: rawQ.stock_name || g.stock_name };

      const priceDateOk = historyDateOk || quoteDateOk;
      const priceExactDate = (historyDateOk && historyTradeDate === targetDate) || quoteDateOk;
      const price = n(q.price, NaN);
      const deltaLots = g.delta_raw_shares / 1000;
      const currLots = g.curr_raw_shares / 1000;
      const prevLots = g.prev_raw_shares / 1000;
      const netAmountBillion = Number.isFinite(price) && price ? (g.delta_raw_shares * price / 100000000) : 0;
      let status = '';
      if (prevLots <= 0 && currLots > 0) status = '新增';
      else if (currLots <= 0 && prevLots > 0) status = '刪除';
      else if (deltaLots > 0) status = '加碼';
      else if (deltaLots < 0) status = '減碼';
      else if (g.delta_weight > 0) status = '加碼';
      else if (g.delta_weight < 0) status = '減碼';
      return {
        ...g,
        stock_name: String(q.stock_name || g.stock_name || ''),
        name: String(q.stock_name || g.stock_name || ''),
        price,
        change: Number.isFinite(n(q.change, NaN)) ? n(q.change, NaN) : null,
        change_pct: Number.isFinite(n(q.change_pct, NaN)) ? n(q.change_pct, NaN) : null,
        updated_at: q.trade_date || q.updated_at || null,
        quote_trade_date: q.trade_date || rawQ.trade_date || null,
        quote_source: q.quote_source || q.source || rawQ.source || null,
        quote_stale: !priceExactDate,
        status,
        buy_count: g.buy_etf_count,
        sell_count: g.sell_etf_count,
        add_etf_count: g.buy_etf_count,
        reduce_etf_count: g.sell_etf_count,
        increase_etf_count: g.increase_count,
        decrease_etf_count: g.decrease_count,
        add_count: g.add_count,
        delete_count: g.delete_count,
        increase_count: g.increase_count,
        decrease_count: g.decrease_count,
        etf_count: g.etf_change_count,
        delta_shares: deltaLots,              // UI 以「張」顯示。
        delta_shares_lots: deltaLots,
        shares_change: deltaLots,
        curr_shares: currLots,
        prev_shares: prevLots,
        current_shares: currLots,
        net_delta_shares: deltaLots,
        net_amount_billion: netAmountBillion,
        amount_billion: netAmountBillion,
        delta_amount_billion: netAmountBillion,
        amount: netAmountBillion,
        abs_amount_billion: Math.abs(netAmountBillion),
        consensus: `買賣檔數 ${g.buy_etf_count}:${g.sell_etf_count}`,
        long_short_consensus: `買賣檔數 ${g.buy_etf_count}:${g.sell_etf_count}`,
        buySellText: `買賣檔數 ${g.buy_etf_count}:${g.sell_etf_count}`,
        data_date: targetDate,
        target_data_date: targetDate,
        signal_range_days: signalRangeDays,
      };
    }).filter((r: any) => r.status && Math.abs(n(r.delta_shares)) >= 0.001);

    rows.sort((a: any, b: any) => Math.abs(n(b.net_amount_billion)) - Math.abs(n(a.net_amount_billion)));

    const typeMap: Record<string, string> = {
      add: '新增', added: '新增', new: '新增',
      remove: '刪除', removed: '刪除', delete: '刪除', deleted: '刪除',
      increase: '加碼', inc: '加碼', buy: '加碼',
      decrease: '減碼', dec: '減碼', sell: '減碼',
      新增: '新增', 刪除: '刪除', 加碼: '加碼', 減碼: '減碼',
    };
    const filteredRows = signalType && typeMap[String(signalType)]
      ? rows.filter((x: any) => x.status === typeMap[String(signalType)])
      : rows;

    const positiveRows = rows.filter((r: any) => n(r.net_amount_billion) > 0).sort((a: any, b: any) => n(b.net_amount_billion) - n(a.net_amount_billion));
    const negativeRows = rows.filter((r: any) => n(r.net_amount_billion) < 0).sort((a: any, b: any) => n(a.net_amount_billion) - n(b.net_amount_billion));
    const buyConsensusRows = rows.filter((r: any) => n(r.buy_etf_count) > 0).sort((a: any, b: any) => n(b.buy_etf_count) - n(a.buy_etf_count) || n(b.net_amount_billion) - n(a.net_amount_billion));
    const sellConsensusRows = rows.filter((r: any) => n(r.sell_etf_count) > 0).sort((a: any, b: any) => n(b.sell_etf_count) - n(a.sell_etf_count) || n(a.net_amount_billion) - n(b.net_amount_billion));

    const topInflow = positiveRows[0] || null;
    const topOutflow = negativeRows[0] || null;
    const topIncreaseEtf = buyConsensusRows[0] || null;
    const topDecreaseEtf = sellConsensusRows[0] || null;

    const counts = {
      total: rows.length,
      all: rows.length,
      add: rows.filter((r: any) => r.status === '新增').length,
      remove: rows.filter((r: any) => r.status === '刪除').length,
      increase: rows.filter((r: any) => r.status === '加碼').length,
      decrease: rows.filter((r: any) => r.status === '減碼').length,
    };


    const normalizeEtfCodeForDisplay = (x: any): string => {
      const raw = typeof x === 'string'
        ? x
        : (x?.etf_code ?? x?.etfCode ?? x?.code ?? x?.fund_code ?? x?.fundCode ?? x?.symbol ?? '');
      return String(raw).trim().toUpperCase();
    };

    const universeEtfCodesForDisplay = Array.from(new Set(
      (Array.isArray(universeEtfs) ? universeEtfs : [])
        .map(normalizeEtfCodeForDisplay)
        .filter(Boolean)
    ));

    const todayEtfCodesForDisplay = new Set(
      Array.from(todayEtfSet ?? [])
        .map(normalizeEtfCodeForDisplay)
        .filter(Boolean)
    );

    const explicitMissingCodesForDisplay = (Array.isArray(missingTodayEtfCodes) ? missingTodayEtfCodes : [])
      .map(normalizeEtfCodeForDisplay)
      .filter(Boolean);

    const calculatedMissingCodesForDisplay = universeEtfCodesForDisplay
      .filter((code: string) => code && !todayEtfCodesForDisplay.has(code));

    const missingTodayEtfCodesForDisplay = Array.from(new Set([
      ...explicitMissingCodesForDisplay,
      ...calculatedMissingCodesForDisplay,
    ]));

    const latestDateByEtfForDisplay: Record<string, string> = {};
    for (const code of universeEtfCodesForDisplay) {
      const dates = Array.from(datesByEtf[code] || [])
        .map((d: any) => toDate(d))
        .filter(Boolean)
        .sort();
      latestDateByEtfForDisplay[code] = dates.length ? String(dates[dates.length - 1]) : '';
    }

    const makeMissingEtfDisplayRow = (code0: any) => {
      const code = normalizeEtfCodeForDisplay(code0);
      const latestDate = latestDateByEtfForDisplay[code] || '';
      const name = ETF_NAMES[code] || '';
      return {
        etf_code: code,
        etfCode: code,
        code,
        etf_name: name,
        etfName: name,
        latest_date: latestDate,
        latestDate,
        data_date: latestDate,
        status: '非今日資料',
      };
    };

    const meta = {
      data_date: targetDate,
      target_data_date: targetDate,
      rangeDays: signalRangeDays,
      signalRangeDays,
      range_days: signalRangeDays,
      rangeLabel: signalRangeDays === 1 ? '今日' : `${signalRangeDays}日`,
      comparisonMode: signalRangeDays === 1 ? '前一交易日' : `${signalRangeDays}個交易日前`,
      includedEtfCount: includedEtfs.length,
      comparable_etf_count: includedEtfs.length,
      signal_etf_count: includedEtfs.length,
      fetched_etf_count: todayEtfSet.size,
      total_etf_count: universeEtfs.length,
      all_etf_codes: universeEtfs,
      today_etf_codes: Array.from(todayEtfSet),
      today_etf_count: todayEtfSet.size,
      missing_today_etf_count: missingTodayEtfCodesForDisplay.length,
      missing_today_etf_codes: missingTodayEtfCodesForDisplay,
      missing_today_etf_codes_text: missingTodayEtfCodesForDisplay.join(','),
      non_today_etf_codes_text: missingTodayEtfCodesForDisplay.join(','),
      no_compare_etf_count: noCompareEtfCodes.length,
      excluded_compare_etf_count: Math.max(0, universeEtfs.length - includedEtfs.length),
      non_today_etf_count: missingTodayEtfCodesForDisplay.length,
      non_today_etfs: missingTodayEtfCodesForDisplay.map(makeMissingEtfDisplayRow),
      missing_etfs: missingTodayEtfCodesForDisplay.map(makeMissingEtfDisplayRow),
      no_compare_etf_codes: noCompareEtfCodes,
      today_holding_rows: todayRowsAll.length,
      included_holding_rows: holdingsRows.length,
      signal_count: rows.length,
      today_change_count: rows.length,
      source: 'api_getSignals_v109_today_only_global_date',
      universe, etf_universe: universe,
      data_note: `今日有資料 ${todayEtfSet.size}/${universeEtfs.length} 檔 ETF；可計算訊號 ${includedEtfs.length} 檔；未納入 ${Math.max(0, universeEtfs.length - includedEtfs.length)} 檔（${missingTodayEtfCodesForDisplay.length} 檔非今日資料、${noCompareEtfCodes.length} 檔缺前日比較）。`,
    };

    return {
      ...meta,
      rows: filteredRows,
      changes: filteredRows,
      rawChanges: filteredRows,
      items: filteredRows,
      signals: filteredRows,
      allRows: rows,
      all_changes: rows,
      counts,
      status_counts: counts,
      summary: {
        ...meta,
        counts,
        topInflow,
        topOutflow,
        topIncreaseEtf,
        topDecreaseEtf,
      },
      focus: { topInflow, topOutflow, topIncreaseEtf, topDecreaseEtf },
      focusCards: { topInflow, topOutflow, topIncreaseEtf, topDecreaseEtf },
      top_cards: { topInflow, topOutflow, topIncreaseEtf, topDecreaseEtf },
      topInflow,
      topOutflow,
      topIncreaseEtf,
      topDecreaseEtf,
    };
  } catch (err) {
    console.error('[getSignals v109 today only] failed:', err);
    return {
      rows: [], changes: [], rawChanges: [], items: [], signals: [],
      allRows: [], all_changes: [],
      counts: { total: 0, all: 0, add: 0, remove: 0, increase: 0, decrease: 0 },
      data_date: '', target_data_date: '', includedEtfCount: 0,
      fetched_etf_count: 0, total_etf_count: totalEtfCodes.length,
      signal_count: 0, today_change_count: 0,
      source: 'api_getSignals_v109_today_only_error_fallback',
        universe, etf_universe: universe,
      error: String((err as any)?.message || err),
    };
  }
}




async function readLatestSignalsCache(signalType: string | null | undefined, days: number, universe: 'active' | 'reference' | 'all' = 'active') {
  if (!hasSupabaseEnv) return null;

  const cacheSignalType = makeSignalsCacheSignalType(signalType, universe);

  const { data, error } = await supabase
    .from('signals_cache')
    .select('payload,cache_key,updated_at,data_date')
    .eq('days', days)
    .eq('signal_type', cacheSignalType)
    .order('updated_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) {
    const msg = String(error.message || '');
    if (!msg.includes('does not exist')) console.warn('[signals_cache] latest read failed:', msg);
    return null;
  }

  if (!data?.payload) return null;

  return {
    ...data.payload,
    cache_hit: true,
    cache_mode: 'latest',
    cache_key: data.cache_key,
    cache_updated_at: data.updated_at,
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
    const fresh = ["1", "true", "yes"].includes(
      String(u.searchParams.get("fresh") || "").toLowerCase()
    );

    return getStockDetail(
      decodeURIComponent(u.pathname.split("/")[2]),
      fresh
    );
  }

  if (u.pathname === "/signals") {
    const days = normalizeSignalRangeDays(
      u.searchParams.get("days") ||
      u.searchParams.get("rangeDays") ||
      u.searchParams.get("signalRangeDays") ||
      "1"
    );

    const signalType = u.searchParams.get("type");
    const universe = normalizeSignalUniverse(
      u.searchParams.get("universe") ||
      u.searchParams.get("etfUniverse") ||
      "active"
    );
    const fresh = ["1", "true", "yes"].includes(String(u.searchParams.get("fresh") || "").toLowerCase());

    try {
      if (!fresh) {
        const latestCached = await readLatestSignalsCache(signalType, days, universe);
        if (latestCached) return latestCached;
      }

      const scope = await getSignalsCacheScope();

      if (!fresh) {
        const cached = await readSignalsCache(signalType, days, scope, universe);
        if (cached) return cached;
      }

      const data = await getSignals(signalType, days, universe);
      await writeSignalsCache(signalType, days, scope, data, universe);
      return data;
    } catch (e) {
      console.warn("[signals_cache] fallback to live calculation:", e);
      return getSignals(signalType, days, universe);
    }
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
