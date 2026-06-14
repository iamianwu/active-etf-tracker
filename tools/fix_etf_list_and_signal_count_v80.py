#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
etf_data_path = ROOT / "frontend/lib/etfData.ts"
signals_path = ROOT / "frontend/components/SignalsClient.tsx"

if not etf_data_path.exists():
    raise SystemExit("找不到 frontend/lib/etfData.ts，請確認你在 repo 根目錄執行。")

if not signals_path.exists():
    raise SystemExit("找不到 frontend/components/SignalsClient.tsx，請確認你在 repo 根目錄執行。")


def replace_function(source: str, fn_name: str, replacement: str) -> str:
    m = re.search(rf"(export\s+)?async\s+function\s+{re.escape(fn_name)}\s*\(", source)
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


# =============================
# 1) ETF list: fix hidden 1000-row limit
# =============================
etf_text = etf_data_path.read_text(encoding="utf-8")

helper_block = """
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
  "00983A": "主動中信成長高股息",
  "00984A": "主動安聯台灣高息成長",
  "00985A": "主動野村台灣高息動能",
  "00986A": "主動凱基台灣AI50",
  "00988A": "主動統一全球創新",
  "00989A": "主動野村台灣50",
  "00990A": "主動元大AI新經濟",
  "00991A": "主動復華未來50",
  "00992A": "主動群益科技創新",
  "00993A": "主動安聯台灣",
  "00994A": "主動第一金台股優",
  "00995A": "主動野村台灣優選高息",
  "00996A": "主動兆豐台灣豐收",
  "00997A": "主動群益美國增長",
  "00998A": "主動復華金融股息",
  "00999A": "主動台股ETF",
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
"""

if "selectMaybePagedV80" not in etf_text:
    idx = etf_text.find("export async function getEtfListRows")
    if idx < 0:
        raise SystemExit("找不到 export async function getEtfListRows。")
    etf_text = etf_text[:idx] + helper_block + "\n" + etf_text[idx:]

new_get_etf_list_rows = """export async function getEtfListRows() {
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
}"""

etf_text = replace_function(etf_text, "getEtfListRows", new_get_etf_list_rows)
etf_data_path.write_text(etf_text, encoding="utf-8")


# =============================
# 2) SignalsClient: robust count fallback
# =============================
signals_text = signals_path.read_text(encoding="utf-8")

helper = """
  const signalDetailRowsV80 = data.changes || data.rows || data.detail || [];
  const signalRowEtfCountV80 = new Set(
    (signalDetailRowsV80 || [])
      .map((x: any) => String(x.etf_code || x.etfCode || ''))
      .filter(Boolean)
  ).size;

  const totalEtfCountV80 = Number(
    data.total_etf_count ??
    data.totalEtfCount ??
    data.etf_count ??
    data.etfCount ??
    data.total_count ??
    data.totalCount ??
    data.summary?.total_etf_count ??
    data.summary?.totalEtfCount ??
    data.summary?.etf_count ??
    data.summary?.etfCount ??
    data.summary?.total_count ??
    data.summary?.totalCount ??
    data.stats?.total_etf_count ??
    data.stats?.totalEtfCount ??
    data.stats?.etf_count ??
    data.stats?.etfCount ??
    data.stats?.total_count ??
    data.stats?.totalCount ??
    data.meta?.total_etf_count ??
    data.meta?.totalEtfCount ??
    data.meta?.etf_count ??
    data.meta?.etfCount ??
    data.meta?.total_count ??
    data.meta?.totalCount ??
    0
  );

  const fetchedEtfCountRawV80 = Number(
    data.fetched_etf_count ??
    data.fetchedEtfCount ??
    data.captured_etf_count ??
    data.capturedEtfCount ??
    data.included_etf_count ??
    data.includedEtfCount ??
    data.summary?.fetched_etf_count ??
    data.summary?.fetchedEtfCount ??
    data.summary?.captured_etf_count ??
    data.summary?.capturedEtfCount ??
    data.summary?.included_etf_count ??
    data.summary?.includedEtfCount ??
    data.stats?.fetched_etf_count ??
    data.stats?.fetchedEtfCount ??
    data.stats?.captured_etf_count ??
    data.stats?.capturedEtfCount ??
    data.stats?.included_etf_count ??
    data.stats?.includedEtfCount ??
    data.meta?.fetched_etf_count ??
    data.meta?.fetchedEtfCount ??
    data.meta?.captured_etf_count ??
    data.meta?.capturedEtfCount ??
    data.meta?.included_etf_count ??
    data.meta?.includedEtfCount ??
    0
  );

  const fetchedEtfCountV80 =
    fetchedEtfCountRawV80 ||
    signalRowEtfCountV80 ||
    ((totalEtfCountV80 > 0 && (signalDetailRowsV80 || []).length > 0) ? totalEtfCountV80 : 0);

  const dataDateV80 =
    data.data_date ||
    data.dataDate ||
    data.latest_data_date ||
    data.latestDataDate ||
    data.meta?.data_date ||
    data.meta?.dataDate ||
    data.meta?.latest_data_date ||
    data.meta?.latestDataDate ||
    '';

  const completeV80 =
    totalEtfCountV80 > 0 &&
    fetchedEtfCountV80 > 0 &&
    fetchedEtfCountV80 >= totalEtfCountV80;
"""

# Remove v79 helper if exists to prevent duplicate variable names.
signals_text = re.sub(
    r"\n\s*const fetchedEtfCountV79[\s\S]*?const completeV79\s*=\s*[\s\S]*?;\n",
    "\n",
    signals_text,
    count=1
)

if "fetchedEtfCountV80" not in signals_text:
    marker = '  return (\n    <main className="page signals-v7-page">'
    if marker not in signals_text:
        raise SystemExit("找不到 SignalsClient return marker。")
    signals_text = signals_text.replace(marker, helper + "\n" + marker, 1)

signals_text = signals_text.replace(
    "className={`signals-data-status ${complete ? 'ok' : 'warn'}`}",
    "className={`signals-data-status ${completeV80 ? 'ok' : 'warn'}`}"
)
signals_text = signals_text.replace(
    "className={`signals-data-status ${completeV79 ? 'ok' : 'warn'}`}",
    "className={`signals-data-status ${completeV80 ? 'ok' : 'warn'}`}"
)

signals_text = re.sub(
    r"已抓取\s*\{[^}]+\}\s*/\s*\{[^}]+\}\s*檔 ETF\s*\n\s*\{[^}]+data_date[^}]+\}",
    "已抓取 {fetchedEtfCountV80} / {totalEtfCountV80} 檔 ETF\n          {dataDateV80 ? `，資料日期 ${dataDateV80}` : ''}",
    signals_text,
    count=1
)

# Fallback exact old line.
signals_text = signals_text.replace(
    "已抓取 {data.fetched_etf_count || 0} / {data.total_etf_count || 0} 檔 ETF\n          {data.data_date ? `，資料日期 ${data.data_date}` : ''}",
    "已抓取 {fetchedEtfCountV80} / {totalEtfCountV80} 檔 ETF\n          {dataDateV80 ? `，資料日期 ${dataDateV80}` : ''}"
)

signals_path.write_text(signals_text, encoding="utf-8")

print("✅ v80 已修正：")
print(" - ETF列表：holdings 改成分頁抓取，不再被 Supabase 預設 1000 rows 卡住")
print(" - ETF列表：使用 ETF_CODES + etf_quotes + holdings 聯集，排除 D 類")
print(" - 今日訊號：已抓取 X/Y 加上 rows fallback，不再顯示 0/25")
print("")
print("請接著 cd frontend && npm run build")
