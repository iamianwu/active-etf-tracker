#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
stock = ROOT / "frontend" / "components" / "StockDetailClient.tsx"

if not stock.exists():
    raise SystemExit("❌ 找不到 frontend/components/StockDetailClient.tsx，請確認你在 repo 根目錄執行。")

text = stock.read_text(encoding="utf-8")
bak = stock.with_suffix(stock.suffix + ".bak_v98")
if not bak.exists():
    bak.write_text(text, encoding="utf-8")

old = text

# 主要修正：v96/v97 後可能殘留 StockRecentOperationRecords，但實際 component 名稱是 StockRecentOperationPanel
# 這會造成瀏覽器 console: ReferenceError: StockRecentOperationRecords is not defined
if "StockRecentOperationRecords" in text and "StockRecentOperationPanel" in text:
    text = text.replace("StockRecentOperationRecords", "StockRecentOperationPanel")

# 再補一次 v97 的 props 修正，避免 data/etfRows 被包成錯誤物件。
text = text.replace("<StockRecentOperationPanel data={{data}} etfRows={{etfRows}} />",
                    "<StockRecentOperationPanel data={data} etfRows={etfRows} />")
text = text.replace("data={{ data }} etfRows={{ etfRows }}",
                    "data={data} etfRows={etfRows}")

# 防呆：如果 buildStockRecentOperationRows 還沒有防呆，補上。
needle = "function buildStockRecentOperationRows(data: any, etfRows: any[]) {\n  const etfMap: Record<string, any> = {};"
if needle in text:
    text = text.replace(
        needle,
        "function buildStockRecentOperationRows(data: any, etfRows: any[]) {\n"
        "  data = data?.data || data;\n"
        "  etfRows = Array.isArray(etfRows) ? etfRows : (Array.isArray(etfRows?.etfRows) ? etfRows.etfRows : []);\n"
        "  const etfMap: Record<string, any> = {};"
    )

stock.write_text(text, encoding="utf-8")

readme = ROOT / "README_V98_FIX_STOCK_OPERATION_REFERENCE.md"
readme.write_text(
    "# V98 Fix Stock Operation Reference\n\n"
    "修正個股頁 client-side exception：\n\n"
    "`ReferenceError: StockRecentOperationRecords is not defined`\n\n"
    "原因是 JSX 還在呼叫不存在的 `StockRecentOperationRecords`，實際 component 是 `StockRecentOperationPanel`。\n",
    encoding="utf-8",
)

print("✅ V98 已完成")
if text != old:
    print("已修改：frontend/components/StockDetailClient.tsx")
else:
    print("StockDetailClient.tsx 沒有需要替換的內容；請把 grep 結果貼給我。")
print("已新增：README_V98_FIX_STOCK_OPERATION_REFERENCE.md")
print("\n請接著 git status / commit / push，並等 Vercel Ready。")
