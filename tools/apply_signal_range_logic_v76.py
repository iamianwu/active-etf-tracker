#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
api_path = ROOT / "frontend/lib/api.ts"

if not api_path.exists():
    raise SystemExit("找不到 frontend/lib/api.ts，請確認你在 repo 根目錄執行。")

text = api_path.read_text(encoding="utf-8")


def replace_function(source: str, fn_name: str, replacement: str) -> str:
    m = re.search(rf"async\s+function\s+{re.escape(fn_name)}\s*\(", source)
    if not m:
        raise RuntimeError(f"找不到 async function {fn_name}()")
    start = m.start()
    brace = source.find("{", m.end())
    if brace < 0:
        raise RuntimeError(f"找不到 {fn_name} function body")

    depth = 0
    i = brace
    in_str = None
    escape = False
    in_line_comment = False
    in_block_comment = False

    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_str:
                in_str = None
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        if ch in ("'", '"', "`"):
            in_str = ch
            i += 1
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                return source[:start] + replacement + source[end:]

        i += 1

    raise RuntimeError(f"找不到 {fn_name} function 結尾")


helper_block = """
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

"""

if "loadSignalRowsByRange" not in text:
    idx = text.find("async function getSignals")
    if idx < 0:
        raise SystemExit("找不到 getSignals，無法插入 v76 helper。")
    text = text[:idx] + helper_block + "\n" + text[idx:]


new_get_signals = """
async function getSignals(signalType?: string | null, signalRangeDaysInput: any = 1) {
  const signalRangeDays = normalizeSignalRangeDays(signalRangeDaysInput);

  const [{ holdings, pairByEtf }, stockQuotes] = await Promise.all([
    loadSignalRowsByRange(signalRangeDays),
    selectAll("stock_quotes"),
  ]);

  const stockQuoteMap: Record<string, any> = {};
  for (const q of stockQuotes || []) stockQuoteMap[q.stock_code] = q;

  let changes: any[] = [];
  let includedEtfCount = 0;
  let latestDataDate = "";

  for (const etf of Object.keys(pairByEtf)) {
    const pair = pairByEtf[etf];
    if (!pair?.current || !pair?.previous || pair.current === pair.previous) continue;

    const etfChanges = computeEtfChanges(holdings, etf, pair.current, pair.previous);
    if (etfChanges.length || pair.current) includedEtfCount += 1;
    if (pair.current > latestDataDate) latestDataDate = pair.current;

    changes.push(...etfChanges.map((x) => ({
      ...x,
      compare_date: pair.previous,
      signal_range_days: signalRangeDays,
    })));
  }

  changes = changes.filter((c: any) => ["新增", "刪除", "加碼", "減碼"].includes(c.status));

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
    const q = stockQuoteMap?.[stockCode] || {};
    const price = Number(q.price || 0);
    const deltaShares = Number(c.delta_shares || 0);
    const deltaWeight = Number(c.delta_weight || 0);
    const deltaValue = price ? deltaShares * price / 100000000 : null;

    if (!byStock[stockCode]) {
      byStock[stockCode] = {
        stock_code: stockCode,
        stock_name: c.stock_name,
        price: price || null,
        change_pct: q.change_pct ?? null,
        delta_shares: 0,
        delta_weight: 0,
        delta_value_billion: 0,
        has_price: false,
        count: 0,
        increase_etf_count: 0,
        decrease_etf_count: 0,
        add_etf_count: 0,
        remove_etf_count: 0,
        statuses: [],
      };
    }

    const b = byStock[stockCode];

    b.delta_shares += deltaShares;
    b.delta_weight += deltaWeight;
    b.count += 1;
    b.statuses.push(`${c.etf_code} ${c.status}`);

    if (deltaValue !== null) {
      b.delta_value_billion += deltaValue;
      b.has_price = true;
    }

    if (c.status === "加碼") b.increase_etf_count += 1;
    if (c.status === "減碼") b.decrease_etf_count += 1;
    if (c.status === "新增") b.add_etf_count += 1;
    if (c.status === "刪除") b.remove_etf_count += 1;
  }

  const aggregate = Object.values(byStock).map((x: any) => ({
    ...x,
    delta_value_billion: x.has_price ? x.delta_value_billion : null,
  })).sort((a: any, b: any) => {
    const av = a.delta_value_billion !== null ? Math.abs(Number(a.delta_value_billion || 0)) : Math.abs(Number(a.delta_shares || 0));
    const bv = b.delta_value_billion !== null ? Math.abs(Number(b.delta_value_billion || 0)) : Math.abs(Number(b.delta_shares || 0));
    return bv - av;
  });

  return {
    summary: summarizeChanges(changes),
    changes,
    aggregate,
    rangeDays: signalRangeDays,
    signalRangeDays,
    rangeLabel: signalRangeDays === 1 ? "今日" : `${signalRangeDays}日`,
    latestDataDate,
    includedEtfCount,
    comparisonMode: signalRangeDays === 1 ? "前一交易日" : `${signalRangeDays}個交易日前`,
  };
}
"""

text = replace_function(text, "getSignals", new_get_signals)

old_patterns = [
    'return getSignals(u.searchParams.get("type"));',
    "return getSignals(u.searchParams.get('type'));",
]
replaced_route = False
for old in old_patterns:
    if old in text:
        text = text.replace(old, """const days = normalizeSignalRangeDays(
      u.searchParams.get("days") ||
      u.searchParams.get("rangeDays") ||
      u.searchParams.get("signalRangeDays") ||
      "1"
    );
    return getSignals(u.searchParams.get("type"), days);""")
        replaced_route = True

if not replaced_route:
    text = re.sub(
        r'if\s*\(\s*u\.pathname\s*===\s*["\']/signals["\']\s*\)\s*\{\s*return\s+getSignals\((.*?)\);\s*\}',
        """if (u.pathname === "/signals") {
    const days = normalizeSignalRangeDays(
      u.searchParams.get("days") ||
      u.searchParams.get("rangeDays") ||
      u.searchParams.get("signalRangeDays") ||
      "1"
    );
    return getSignals(u.searchParams.get("type"), days);
  }""",
        text,
        count=1,
        flags=re.S,
    )

api_path.write_text(text, encoding="utf-8")

print("✅ v76 已修正訊號區間邏輯與速度。")
print("- 5日/10日/20日 現在會比較 N 個交易日前，不再只是今日")
print("- /signals 不再用 loadBaseData() 載入全部 holdings")
print("- 僅先查 date，再查需要的 current/previous holdings")
print("")
print("請接著執行：cd frontend && npm run build")
