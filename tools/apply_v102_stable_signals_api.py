#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
api_path = ROOT / "frontend" / "lib" / "api.ts"

if not api_path.exists():
    raise SystemExit("❌ 找不到 frontend/lib/api.ts，請在 repo 根目錄執行。")

text = api_path.read_text(encoding="utf-8")
bak = api_path.with_suffix(api_path.suffix + ".bak_v102")
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
            if ch == "\n":
                in_line_comment = False
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

new_get_signals = r"""
async function getSignals(signalType?: string | null, signalRangeDaysInput: any = 1) {
  try {
    const rangeDaysRaw = Number(signalRangeDaysInput ?? 1);
    const signalRangeDays = Number.isFinite(rangeDaysRaw)
      ? Math.max(1, Math.min(120, Math.round(rangeDaysRaw)))
      : 1;

    function n(v: any, fallback = 0): number {
      if (v === null || v === undefined || v === '') return fallback;
      const x = Number(String(v).replace(/,/g, ''));
      return Number.isFinite(x) ? x : fallback;
    }

    function codeOf(r: any): string {
      return String(r?.stock_code ?? r?.code ?? '').trim();
    }

    function etfCodeOf(r: any): string {
      return String(r?.etf_code ?? r?.etfCode ?? '').trim();
    }

    function dateOf(r: any): string {
      return String(r?.data_date ?? r?.date ?? '').slice(0, 10);
    }

    function isStockCode(code: string): boolean {
      return /^[0-9]{4}$/.test(String(code || '').trim());
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

    function quotePrice(q: any): number {
      return n(q?.price ?? q?.close_price ?? q?.close ?? q?.last_price, NaN);
    }

    function quotePct(q: any): number {
      return n(q?.change_pct ?? q?.percent ?? q?.pct ?? q?.changePercent, NaN);
    }

    function quoteChange(q: any): number {
      return n(q?.change ?? q?.diff ?? q?.price_change, NaN);
    }

    // 不依賴舊的 signal helper，避免 helper 狀態不同造成 server-side exception。
    const [holdings, stockQuotes] = await Promise.all([
      selectAll("holdings"),
      selectAll("stock_quotes"),
    ]);

    const quoteMap: Record<string, any> = {};
    for (const q of stockQuotes || []) {
      const c = String(q?.stock_code ?? q?.code ?? '').trim();
      if (c) quoteMap[c] = q;
    }

    const byEtf: Record<string, any[]> = {};
    for (const r of holdings || []) {
      const etf = etfCodeOf(r);
      const code = codeOf(r);
      const d = dateOf(r);
      if (!etf || !d || !isStockCode(code)) continue;
      if (!byEtf[etf]) byEtf[etf] = [];
      byEtf[etf].push(r);
    }

    const agg: Record<string, any> = {};
    let fetchedEtfCount = 0;
    let latestDataDate = '';

    for (const etf of Object.keys(byEtf)) {
      const rows = byEtf[etf] || [];

      const dateSet = Array.from(new Set(rows.map(dateOf).filter(Boolean))).sort();
      if (dateSet.length < 2) continue;

      const latest = dateSet[dateSet.length - 1];
      const latestIndex = dateSet.length - 1;
      const prevIndex = Math.max(0, latestIndex - signalRangeDays);
      const prev = dateSet[prevIndex];

      if (!latest || !prev || latest === prev) continue;

      fetchedEtfCount += 1;
      if (!latestDataDate || latest > latestDataDate) latestDataDate = latest;

      const current: Record<string, any> = {};
      const previous: Record<string, any> = {};

      for (const r of rows) {
        const d = dateOf(r);
        const c = codeOf(r);
        if (!isStockCode(c)) continue;
        if (d === latest) current[c] = r;
        if (d === prev) previous[c] = r;
      }

      const codes = Array.from(new Set([...Object.keys(current), ...Object.keys(previous)]));

      for (const code of codes) {
        const cur = current[code];
        const old = previous[code];

        // holdings.shares 是「股」。前端張數欄位統一送「張」，避免前端把股數誤顯示成張數。
        const curSharesRaw = n(cur?.shares ?? cur?.share ?? cur?.quantity ?? cur?.qty, 0);
        const oldSharesRaw = n(old?.shares ?? old?.share ?? old?.quantity ?? old?.qty, 0);
        const deltaSharesRaw = curSharesRaw - oldSharesRaw;

        if (Math.abs(deltaSharesRaw) < 1) continue;

        const deltaLots = deltaSharesRaw / 1000;
        const curLots = curSharesRaw / 1000;
        const oldLots = oldSharesRaw / 1000;

        const base = cur || old || {};
        const q = quoteMap[code] || {};
        const price = quotePrice(q);
        const pct = quotePct(q);
        const chg = quoteChange(q);
        const flowBillion = Number.isFinite(price) ? deltaSharesRaw * price / 100000000 : null;

        if (!agg[code]) {
          const name = stockNameFix(code, String(base?.stock_name ?? base?.name ?? code));
          agg[code] = {
            stock_code: code,
            code,
            stock_name: name,
            name,
            price: Number.isFinite(price) ? price : null,
            change: Number.isFinite(chg) ? chg : null,
            change_pct: Number.isFinite(pct) ? pct : null,
            volume: n(q?.volume, null as any),
            amount: n(q?.amount, null as any),
            data_date: latest,
            etf_code_list: [],
            net_raw_shares: 0,
            net_delta_lots: 0,
            delta_lots: 0,
            delta_shares: 0,
            flow_billion: 0,
            money_billion: 0,
            amount_billion: 0,
            delta_amount_billion: 0,
            delta_value_billion: 0,
            net_amount_billion: 0,
            add_etf_count: 0,
            reduce_etf_count: 0,
            add_count: 0,
            reduce_count: 0,
            current_lots_total: 0,
            previous_lots_total: 0,
            source: 'api_getSignals_v102_holdings_only',
          };
        }

        const a = agg[code];

        a.etf_code_list.push(etf);
        a.net_raw_shares += deltaSharesRaw;
        a.net_delta_lots += deltaLots;
        a.delta_lots += deltaLots;

        // 注意：這裡刻意讓 delta_shares 也是「張」而不是「股」，
        // 因為現有 SignalsClient 會把 delta_shares 直接標示為「張」。
        a.delta_shares += deltaLots;

        a.current_lots_total += curLots;
        a.previous_lots_total += oldLots;

        if (flowBillion !== null && Number.isFinite(flowBillion)) {
          a.flow_billion += flowBillion;
          a.money_billion += flowBillion;
          a.amount_billion += flowBillion;
          a.delta_amount_billion += flowBillion;
          a.delta_value_billion += flowBillion;
          a.net_amount_billion += flowBillion;
        }

        if (deltaLots > 0) {
          a.add_etf_count += 1;
          a.add_count += 1;
        } else if (deltaLots < 0) {
          a.reduce_etf_count += 1;
          a.reduce_count += 1;
        }
      }
    }

    let rows = Object.values(agg)
      .map((a: any) => {
        const status =
          a.net_delta_lots > 0
            ? (a.previous_lots_total <= 0 ? '新增' : '加碼')
            : a.net_delta_lots < 0
              ? (a.current_lots_total <= 0 ? '刪除' : '減碼')
              : '異動';

        return {
          ...a,
          status,
          etf_count: a.etf_code_list.length,
          // 方便前端各版本取不同欄位時都能拿到一致結果
          net_lots: a.net_delta_lots,
          shares_change: a.delta_lots,
          change_lots: a.delta_lots,
          display_delta_lots: a.delta_lots,
        };
      })
      .filter((x: any) => x.status !== '異動');

    const typeMap: Record<string, string> = {
      added: '新增',
      removed: '刪除',
      increased: '加碼',
      decreased: '減碼',
    };
    if (signalType && typeMap[String(signalType)]) {
      rows = rows.filter((x: any) => x.status === typeMap[String(signalType)]);
    }

    rows.sort((a: any, b: any) => {
      const av = Number.isFinite(Number(a.flow_billion)) ? Math.abs(Number(a.flow_billion)) : Math.abs(Number(a.delta_lots || 0));
      const bv = Number.isFinite(Number(b.flow_billion)) ? Math.abs(Number(b.flow_billion)) : Math.abs(Number(b.delta_lots || 0));
      return bv - av;
    });

    const summary: Record<string, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0, 異動: 0 };
    for (const r of rows) summary[String(r.status)] = (summary[String(r.status)] || 0) + 1;

    return {
      summary,
      changes: rows,
      rows,
      aggregate: rows,
      rangeDays: signalRangeDays,
      signalRangeDays,
      range_days: signalRangeDays,
      rangeLabel: signalRangeDays === 1 ? '今日' : `${signalRangeDays}日`,
      latestDataDate,
      data_date: latestDataDate,
      includedEtfCount: fetchedEtfCount,
      fetched_etf_count: fetchedEtfCount,
      total_etf_count: typeof ETF_CODES !== 'undefined' ? ETF_CODES.length : Object.keys(byEtf).length,
      comparisonMode: signalRangeDays === 1 ? '前一交易日' : `${signalRangeDays}個交易日前`,
      source: 'api_getSignals_v102_holdings_only',
    };
  } catch (err: any) {
    console.error('[getSignals v102] failed:', err);
    return {
      summary: { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0, 異動: 0 },
      changes: [],
      rows: [],
      aggregate: [],
      rangeDays: 1,
      signalRangeDays: 1,
      range_days: 1,
      rangeLabel: '今日',
      latestDataDate: '',
      data_date: '',
      includedEtfCount: 0,
      fetched_etf_count: 0,
      total_etf_count: typeof ETF_CODES !== 'undefined' ? ETF_CODES.length : 0,
      comparisonMode: '前一交易日',
      source: 'api_getSignals_v102_error_fallback',
      error: String(err?.message || err || 'unknown error'),
    };
  }
}
"""

try:
    text2 = replace_function(text, "getSignals", new_get_signals)
except RuntimeError as e:
    print(f"❌ {e}")
    print("\n請先執行下面這行，把結果貼給我：")
    print("grep -R \"async function .*Signal\\|function .*Signal\\|getSignals\\|/signals\" -n frontend/lib frontend/app frontend/components | head -80")
    raise SystemExit(1)

api_path.write_text(text2, encoding="utf-8")

readme = ROOT / "README_V102_STABLE_SIGNALS_API.md"
readme.write_text("""# V102 Stable Signals API

修正 V101 造成 `/signals` server-side exception 的問題。

V102 重點：

1. 不再依賴舊 signal helper，直接從 `holdings` 與 `stock_quotes` 計算今日訊號。
2. 所有「張數」欄位統一回傳「張」，避免前端把股數誤顯示成張數。
3. 焦點卡與明細共用同一份 rows，避免明細減碼、焦點卡卻顯示流入。
4. 加入 try/catch fallback，避免 server component 直接白畫面。
5. 金額 = 淨股數 × 股價 / 1e8，單位為「億」。

套用後請推上 Vercel，等 Ready 後重新整理 `/signals`。
""", encoding="utf-8")

print("✅ V102 已完成：已替換 frontend/lib/api.ts 的 getSignals()")
print("下一步：git add / commit / push，等 Vercel Ready。")
