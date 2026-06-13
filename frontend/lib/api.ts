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


// v70: 回傳最新日往前第 N 個可用持股資料日。
// range=1 等於今日訊號：最新日 vs 前一個持股日。
// range=3/5/10/20 等於最新日 vs N 個持股資料日前，做區間淨變動。
function signalWindowPreviousDate_v70(holdings: any[], etfCode: string, date: string, windowInput: any) {
  const windowDays = Math.max(1, Math.min(20, Number(windowInput || 1) || 1));
  const dates = Array.from(new Set(
    holdings
      .filter((h) => h.etf_code === etfCode)
      .map((h) => String(h.data_date))
      .filter((d) => d && d < String(date))
  )).sort();

  if (!dates.length) return null;

  const idx = Math.max(0, dates.length - windowDays);
  return dates[idx] || dates[0] || null;
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

async function getSignals(signalType?: string | null, windowInput?: string | number | null) {
  const { holdings, stockQuoteMap } = await loadBaseData();
  const latest = latestDateByEtf(holdings);
  const etfCodes = Object.keys(latest).sort();

  const dataDate = etfCodes.length
    ? etfCodes.map((c) => latest[c]).sort().slice(-1)[0]
    : null;

  const fetchedEtfCount = dataDate
    ? etfCodes.filter((code) => latest[code] === dataDate).length
    : 0;

  const staleEtfs = dataDate
    ? etfCodes.filter((code) => latest[code] !== dataDate).map((code) => ({ etf_code: code, data_date: latest[code] }))
    : [];

  let changes: any[] = [];

  for (const etf of etfCodes) {
    const d = latest[etf];
    const prev = signalWindowPreviousDate_v70(holdings, etf, d, windowDays);
    if (d && prev) changes.push(...computeEtfChanges(holdings, etf, d, prev));
  }

  changes = changes.filter((c: any) => ["新增", "刪除", "加碼", "減碼"].includes(c.status));

  const signalStockCodes = Array.from(new Set(changes.map((c: any) => c.stock_code).filter(Boolean)));
  const historyPriceMap = await loadLatestPriceHistoryMap(signalStockCodes);

  const quoteFor = (stockCode: string) => {
    const q = stockQuoteMap?.[stockCode] || {};
    const fallback = historyPriceMap?.[stockCode] || {};

    return {
      price: q.price ?? fallback.price ?? null,
      change_pct: q.change_pct ?? fallback.change_pct ?? null,
      volume: q.volume ?? fallback.volume ?? null,
    };
  };

  changes = changes.map((c: any) => {
    const q = quoteFor(c.stock_code);
    const price = Number(q.price || 0);
    const deltaShares = Number(c.delta_shares || 0);
    return {
      ...c,
      price: q.price,
      change_pct: q.change_pct,
      volume: q.volume,
      delta_value_billion: price ? deltaShares * price / 100000000 : null,
    };
  });

  const typeMap: Record<string, string> = {
    added: "新增",
    removed: "刪除",
    increased: "加碼",
    decreased: "減碼",
  };

  if (signalType && typeMap[signalType]) {
    changes = changes.filter((c) => c.status === typeMap[signalType]);
  }

  const byStock: Record<string, any> = {};

  for (const c of changes) {
    const stockCode = c.stock_code;
    const price = Number(c.price || 0);
    const deltaShares = Number(c.delta_shares || 0);
    const deltaValue = price ? deltaShares * price / 100000000 : null;
    const currentShares = Number(c.shares || 0);
    const previousShares = currentShares - deltaShares;

    if (!byStock[stockCode]) {
      byStock[stockCode] = {
        stock_code: stockCode,
        stock_name: c.stock_name,
        price: c.price ?? null,
        change_pct: c.change_pct ?? null,
        volume: c.volume ?? null,
        current_shares: 0,
        previous_shares: 0,
        delta_shares: 0,
        delta_weight: 0,
        delta_value_billion: 0,
        has_price: false,
        count: 0,
        etf_count: 0,
        etf_codes: [],
        buy_etf_count: 0,
        sell_etf_count: 0,
        increase_etf_count: 0,
        decrease_etf_count: 0,
        add_etf_count: 0,
        remove_etf_count: 0,
        statuses: [],
      };
    }

    const b = byStock[stockCode];

    b.current_shares += currentShares;
    b.previous_shares += previousShares;
    b.delta_shares += deltaShares;
    b.delta_weight += Number(c.delta_weight || 0);
    b.count += 1;
    b.etf_codes.push(c.etf_code);
    b.statuses.push(`${c.etf_code} ${c.status}`);

    if (deltaValue !== null) {
      b.delta_value_billion += deltaValue;
      b.has_price = true;
    }

    if (c.status === "加碼") {
      b.increase_etf_count += 1;
      b.buy_etf_count += 1;
    }
    if (c.status === "新增") {
      b.add_etf_count += 1;
      b.buy_etf_count += 1;
    }
    if (c.status === "減碼") {
      b.decrease_etf_count += 1;
      b.sell_etf_count += 1;
    }
    if (c.status === "刪除") {
      b.remove_etf_count += 1;
      b.sell_etf_count += 1;
    }
  }

  const aggregate = Object.values(byStock).map((x: any) => {
    const uniqueEtfs = Array.from(new Set(x.etf_codes || []));
    let status = "混合";
    if (x.delta_shares > 0) status = x.add_etf_count > 0 && x.increase_etf_count === 0 ? "新增" : "加碼";
    else if (x.delta_shares < 0) status = x.remove_etf_count > 0 && x.decrease_etf_count === 0 ? "刪除" : "減碼";

    const magnitude_pct = x.previous_shares ? (x.delta_shares / x.previous_shares) * 100 : null;

    return {
      ...x,
      status,
      etf_count: uniqueEtfs.length,
      etf_codes: uniqueEtfs,
      delta_value_billion: x.has_price ? x.delta_value_billion : null,
      magnitude_pct,
    };
  }).sort((a: any, b: any) => {
    const av = a.delta_value_billion !== null ? Math.abs(Number(a.delta_value_billion || 0)) : Math.abs(Number(a.delta_shares || 0));
    const bv = b.delta_value_billion !== null ? Math.abs(Number(b.delta_value_billion || 0)) : Math.abs(Number(b.delta_shares || 0));
    return bv - av;
  });

  return {
    signal_window_days: windowDays,
    signal_window_label: windowDays === 1 ? '今日' : `近${windowDays}日`,
    data_date: dataDate,
    data_date_mmdd: fmtDateMMDD(dataDate),
    fetched_etf_count: fetchedEtfCount,
    total_etf_count: etfCodes.length,
    stale_etfs: staleEtfs,
    summary: summarizeChanges(changes),
    changes,
    aggregate,
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
    return getSignals(u.searchParams.get("type"), u.searchParams.get("range") || u.searchParams.get("window") || u.searchParams.get("days"));
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
