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


new_get_signals = """
async function getSignals(signalType?: string | null, signalRangeDaysInput: any = 1) {
  const signalRangeDays = normalizeSignalRangeDays(signalRangeDaysInput);

  const [{ holdings, pairByEtf }, stockQuotes] = await Promise.all([
    loadSignalRowsByRange(signalRangeDays),
    selectAll("stock_quotes"),
  ]);

  const stockQuoteMap: Record<string, any> = {};
  for (const q of stockQuotes || []) {
    stockQuoteMap[String(q.stock_code || "")] = q;
  }

  const pairEtfs = Object.keys(pairByEtf || {});
  const totalEtfCount = pairEtfs.length;

  let changes: any[] = [];
  let includedEtfCount = 0;
  let latestDataDate = "";

  for (const etf of pairEtfs) {
    const pair = pairByEtf[etf];
    if (!pair?.current || !pair?.previous || pair.current === pair.previous) continue;

    includedEtfCount += 1;
    if (pair.current > latestDataDate) latestDataDate = pair.current;

    const etfChanges = computeEtfChanges(holdings, etf, pair.current, pair.previous);

    changes.push(...etfChanges.map((x: any) => ({
      ...x,
      data_date: pair.current,
      current_date: pair.current,
      compare_date: pair.previous,
      previous_date: pair.previous,
      signal_range_days: signalRangeDays,
      signalRangeDays,
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
    changes = changes.filter((c: any) => c.status === typeMap[signalType]);
  }

  changes = changes.map((c: any) => {
    const q = stockQuoteMap[String(c.stock_code || "")] || {};
    const price = Number(q.price || 0);
    const changePct = q.change_pct ?? q.changePct ?? null;
    const deltaShares = Number(c.delta_shares ?? c.deltaShares ?? 0);
    const deltaWeight = Number(c.delta_weight ?? c.deltaWeight ?? 0);
    const deltaValueBillion = price ? deltaShares * price / 100000000 : null;

    return {
      ...c,
      stock_name: c.stock_name || q.stock_name || q.name || "",
      price: price || null,
      stock_price: price || null,
      close_price: price || null,
      change_pct: changePct,
      changePct,
      delta_shares: deltaShares,
      deltaShares,
      delta_weight: deltaWeight,
      deltaWeight,
      delta_value_billion: deltaValueBillion,
      deltaValueBillion,
      amount_billion: deltaValueBillion,
      amount: deltaValueBillion,
      has_price: !!price,
      hasPrice: !!price,
    };
  });

  const byStock: Record<string, any> = {};

  for (const c of changes) {
    const stockCode = String(c.stock_code || "");
    const deltaShares = Number(c.delta_shares || 0);
    const deltaWeight = Number(c.delta_weight || 0);
    const deltaValue = c.delta_value_billion === null || c.delta_value_billion === undefined
      ? null
      : Number(c.delta_value_billion);

    if (!byStock[stockCode]) {
      byStock[stockCode] = {
        stock_code: stockCode,
        stock_name: c.stock_name,
        price: c.price ?? null,
        stock_price: c.price ?? null,
        change_pct: c.change_pct ?? null,
        changePct: c.change_pct ?? null,
        delta_shares: 0,
        deltaShares: 0,
        delta_weight: 0,
        deltaWeight: 0,
        delta_value_billion: 0,
        deltaValueBillion: 0,
        amount_billion: 0,
        has_price: false,
        hasPrice: false,
        count: 0,
        etf_count: 0,
        etfCount: 0,
        increase_etf_count: 0,
        decrease_etf_count: 0,
        add_etf_count: 0,
        remove_etf_count: 0,
        increaseEtfCount: 0,
        decreaseEtfCount: 0,
        addEtfCount: 0,
        removeEtfCount: 0,
        buy_etf_count: 0,
        sell_etf_count: 0,
        buyEtfCount: 0,
        sellEtfCount: 0,
        statuses: [],
      };
    }

    const b = byStock[stockCode];

    b.delta_shares += deltaShares;
    b.deltaShares = b.delta_shares;
    b.delta_weight += deltaWeight;
    b.deltaWeight = b.delta_weight;
    b.count += 1;
    b.etf_count = b.count;
    b.etfCount = b.count;
    b.statuses.push(`${c.etf_code} ${c.status}`);

    if (deltaValue !== null && Number.isFinite(deltaValue)) {
      b.delta_value_billion += deltaValue;
      b.deltaValueBillion = b.delta_value_billion;
      b.amount_billion = b.delta_value_billion;
      b.has_price = true;
      b.hasPrice = true;
    }

    if (c.status === "加碼") {
      b.increase_etf_count += 1;
      b.increaseEtfCount = b.increase_etf_count;
    }
    if (c.status === "減碼") {
      b.decrease_etf_count += 1;
      b.decreaseEtfCount = b.decrease_etf_count;
    }
    if (c.status === "新增") {
      b.add_etf_count += 1;
      b.addEtfCount = b.add_etf_count;
    }
    if (c.status === "刪除") {
      b.remove_etf_count += 1;
      b.removeEtfCount = b.remove_etf_count;
    }

    b.buy_etf_count = b.increase_etf_count + b.add_etf_count;
    b.sell_etf_count = b.decrease_etf_count + b.remove_etf_count;
    b.buyEtfCount = b.buy_etf_count;
    b.sellEtfCount = b.sell_etf_count;
  }

  const aggregate = Object.values(byStock).map((x: any) => ({
    ...x,
    delta_value_billion: x.has_price ? x.delta_value_billion : null,
    deltaValueBillion: x.has_price ? x.delta_value_billion : null,
    amount_billion: x.has_price ? x.delta_value_billion : null,
  })).sort((a: any, b: any) => {
    const av = a.delta_value_billion !== null ? Math.abs(Number(a.delta_value_billion || 0)) : Math.abs(Number(a.delta_shares || 0));
    const bv = b.delta_value_billion !== null ? Math.abs(Number(b.delta_value_billion || 0)) : Math.abs(Number(b.delta_shares || 0));
    return bv - av;
  });

  const summary = summarizeChanges(changes);
  const rangeLabel = signalRangeDays === 1 ? "今日" : `${signalRangeDays}日`;
  const comparisonMode = signalRangeDays === 1 ? "前一交易日" : `${signalRangeDays}個交易日前`;

  return {
    summary,
    stats: summary,
    changes,
    rows: changes,
    detail: changes,
    aggregate,
    aggregated: aggregate,
    rangeDays: signalRangeDays,
    signalRangeDays,
    rangeLabel,
    latestDataDate,
    latest_data_date: latestDataDate,
    dataDate: latestDataDate,
    data_date: latestDataDate,
    includedEtfCount,
    included_etf_count: includedEtfCount,
    totalEtfCount,
    total_etf_count: totalEtfCount,
    comparisonMode,
    comparison_mode: comparisonMode,
    meta: {
      rangeDays: signalRangeDays,
      signalRangeDays,
      rangeLabel,
      latestDataDate,
      latest_data_date: latestDataDate,
      dataDate: latestDataDate,
      data_date: latestDataDate,
      includedEtfCount,
      included_etf_count: includedEtfCount,
      totalEtfCount,
      total_etf_count: totalEtfCount,
      comparisonMode,
      comparison_mode: comparisonMode,
    },
  };
}
"""

text = replace_function(text, "getSignals", new_get_signals)
api_path.write_text(text, encoding="utf-8")

print("✅ v77 已修正 v76 回傳格式。")
print("- 已補回 includedEtfCount / totalEtfCount 的多種命名")
print("- 已補回 latestDataDate / data_date")
print("- 已補回 changes 每列的 price / change_pct / delta_value_billion")
print("- 已補回 aggregate 的 buy/sell ETF count aliases")
print("")
print("請接著 cd frontend && npm run build")
