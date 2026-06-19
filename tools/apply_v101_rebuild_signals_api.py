#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
api_path = ROOT / "frontend" / "lib" / "api.ts"

if not api_path.exists():
    raise SystemExit("❌ 找不到 frontend/lib/api.ts，請在 repo 根目錄執行。")

text = api_path.read_text(encoding="utf-8")
bak = api_path.with_suffix(api_path.suffix + ".bak_v101")
if not bak.exists():
    bak.write_text(text, encoding="utf-8")

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
            if ch == "\n": in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
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
        if ch in ('"', "'", "`"):
            in_str = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                return source[:start] + replacement.strip() + source[end:]
        i += 1

    raise RuntimeError(f"找不到 {fn_name} function end")

new_get_signals = r'''
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
'''

try:
    text2 = replace_function(text, "getSignals", new_get_signals)
except RuntimeError as e:
    print(f"❌ {e}")
    print("\n請先執行下面這行，把結果貼給我：")
    print("grep -R \"async function .*Signal\\|function .*Signal\\|getSignals\\|/signals\" -n frontend/lib frontend/app frontend/components | head -80")
    raise SystemExit(1)

api_path.write_text(text2, encoding="utf-8")

readme = ROOT / "README_V101_REBUILD_SIGNALS_API.md"
readme.write_text("""# V101 Rebuild Signals API

修正 v100 套錯檔案的問題。

v100 去找 `frontend/lib/etfData.ts` 的 `getSignalsData()`，但目前專案的今日訊號資料來源是在 `frontend/lib/api.ts` 的 `getSignals()`。

V101 直接替換 `api.ts/getSignals()`：

- 從 holdings 計算每檔 ETF 最新有效日 vs 前一有效日。
- 使用 `delta_shares / 1000` 當張數。
- 交易淨額 = 淨張數 × 1000 × 股價 / 1e8。
- 回傳 `rows` 與 `aggregate` 皆為同一份淨變動資料。
- 避免明細是減碼、焦點卡卻顯示淨流入。
""", encoding="utf-8")

print("✅ V101 已完成：已替換 frontend/lib/api.ts 的 getSignals()")
print("下一步：git add / commit / push，等 Vercel Ready。")
