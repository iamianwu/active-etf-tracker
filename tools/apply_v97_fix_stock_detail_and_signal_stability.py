#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
COMP = FRONTEND / "components"
APP = FRONTEND / "app"

stock = COMP / "StockDetailClient.tsx"
signals = COMP / "SignalsClient.tsx"
css = APP / "globals.css"

if not FRONTEND.exists():
    raise SystemExit("❌ 找不到 frontend 目錄，請在 repo 根目錄執行。")

def backup(path: Path, tag="v97"):
    if path.exists():
        bak = path.with_suffix(path.suffix + f".bak_{tag}")
        if not bak.exists():
            bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

changed = []

# 1) Fix V96 wrong JSX props: data={{data}} / etfRows={{etfRows}} cause runtime client exception.
if stock.exists():
    backup(stock)
    s = stock.read_text(encoding="utf-8")
    old = s

    s = s.replace("<StockRecentOperationPanel data={{data}} etfRows={{etfRows}} />",
                  "<StockRecentOperationPanel data={data} etfRows={etfRows} />")
    s = s.replace("data={{ data }} etfRows={{ etfRows }}",
                  "data={data} etfRows={etfRows}")

    # Make component defensive if etfRows accidentally comes in as object.
    s = s.replace(
        "function buildStockRecentOperationRows(data: any, etfRows: any[]) {\n  const etfMap: Record<string, any> = {};",
        "function buildStockRecentOperationRows(data: any, etfRows: any[]) {\n"
        "  data = data?.data || data;\n"
        "  etfRows = Array.isArray(etfRows) ? etfRows : (Array.isArray(etfRows?.etfRows) ? etfRows.etfRows : []);\n"
        "  const etfMap: Record<string, any> = {};"
    )

    if s != old:
        stock.write_text(s, encoding="utf-8")
        changed.append(str(stock))

# 2) Hide duplicated range tabs if old patches left two copies.
if css.exists():
    backup(css)
    c = css.read_text(encoding="utf-8")
    add = '''
/* ===== V97 duplicate signal range guard ===== */
.signals-v7-page .signal-range-block + .signal-range-block,
.signals-v7-page .signals-range-block + .signals-range-block,
.signals-v7-page .v75-range-block + .v75-range-block,
.signals-v7-page .signal-range-tabs-wrap + .signal-range-tabs-wrap {
  display: none !important;
}
'''
    if "V97 duplicate signal range guard" not in c:
        c += add
        css.write_text(c, encoding="utf-8")
        changed.append(str(css))

# 3) Deterministic signal rows on the client.
if signals.exists():
    backup(signals)
    s = signals.read_text(encoding="utf-8")
    old = s

    if "function stableSignalCompareV97" not in s:
        helper = '''
function stableSignalCompareV97(a: any, b: any) {
  const ac = String(a?.stock_code || a?.code || '');
  const bc = String(b?.stock_code || b?.code || '');
  if (ac !== bc) return ac.localeCompare(bc);
  const an = String(a?.stock_name || a?.name || '');
  const bn = String(b?.stock_name || b?.name || '');
  if (an !== bn) return an.localeCompare(bn);
  const as = String(a?.status || '');
  const bs = String(b?.status || '');
  return as.localeCompare(bs);
}
'''
        m = re.search(r"\nexport default function|\nfunction SignalsClient|\nexport function", s)
        if m:
            s = s[:m.start()] + "\n" + helper + s[m.start():]
        else:
            s = helper + "\n" + s

    s = s.replace(
        "return sortDir === 'asc' ? cmp : -cmp;",
        "if (cmp === 0) cmp = stableSignalCompareV97(a, b);\n      return sortDir === 'asc' ? cmp : -cmp;"
    )

    if s != old:
        signals.write_text(s, encoding="utf-8")
        changed.append(str(signals))

readme = ROOT / "README_V97_FIX_STOCK_DETAIL_SIGNAL_STABILITY.md"
readme.write_text(
    "# V97 Fix Stock Detail Client Exception and Signal Stability\n\n"
    "修正內容：\n"
    "1. 修正 V96 在個股頁插入 `data={{data}}` / `etfRows={{etfRows}}` 造成的 client-side exception。\n"
    "2. StockRecentOperationPanel 加入防呆，避免 props 型態錯誤時整頁崩潰。\n"
    "3. 隱藏重複的訊號區間 selector。\n"
    "4. 今日訊號排序加入穩定 tie-breaker，避免同分資料重新整理時順序漂移。\n",
    encoding="utf-8"
)
changed.append(str(readme))

print("✅ V97 已完成。修改檔案：")
for x in changed:
    print(" -", x)
print("\n接著請 git status / commit / push，並等 Vercel Ready。")
