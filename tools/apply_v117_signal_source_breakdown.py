#!/usr/bin/env python3
from pathlib import Path
import re
from datetime import datetime

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent.parent
sig = ROOT / "frontend" / "components" / "SignalsClient.tsx"
css = ROOT / "frontend" / "app" / "globals.css"
src_sig = HERE / "files" / "SignalsClient.v117.tsx"
src_css = HERE / "files" / "v117_signal_source_breakdown.css"

if not sig.exists():
    raise SystemExit("❌ 找不到 frontend/components/SignalsClient.tsx，請確認你在 repo 根目錄執行。")
if not css.exists():
    raise SystemExit("❌ 找不到 frontend/app/globals.css，請確認你在 repo 根目錄執行。")
if not src_sig.exists() or not src_css.exists():
    raise SystemExit("❌ patch 檔案不完整，請重新解壓縮 zip。")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
sig_bak = sig.with_suffix(sig.suffix + f".bak_v117_{stamp}")
css_bak = css.with_suffix(css.suffix + f".bak_v117_{stamp}")
sig_bak.write_text(sig.read_text(encoding="utf-8"), encoding="utf-8")
css_bak.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")

sig.write_text(src_sig.read_text(encoding="utf-8"), encoding="utf-8")

css_text = css.read_text(encoding="utf-8")
css_text = re.sub(r"/\* V117_SIGNAL_SOURCE_BREAKDOWN_START \*/.*?/\* V117_SIGNAL_SOURCE_BREAKDOWN_END \*/\n?", "", css_text, flags=re.S)
css.write_text(css_text.rstrip() + "\n\n" + src_css.read_text(encoding="utf-8").lstrip(), encoding="utf-8")

readme = ROOT / "README_V117_SIGNAL_SOURCE_BREAKDOWN.md"
readme.write_text("""# V117 Signal Source Breakdown

本版修正今日訊號容易誤判的問題：

- 今日訊號列表仍顯示全部 ETF 合計後的淨額 / 張數。
- 不再把 generic buy_count / sell_count 誤當作今日買賣共識，避免把「持有 ETF 檔數」顯示成「買賣 14:0」。
- 點摘要卡或明細列的淨額 / 張數，可以查看來源 ETF 明細；若 API 尚未回傳來源 ETF，會明確提示。
- 明細排序改回 ▲ / ▼ / ↕ 形式。
- 明細表改成較緊湊的 4 欄版面，避免文字超出頁面。
- 保留點股票名稱 / 股價進入個股頁。

注意：若 /signals API 尚未回傳 source_rows / detail_rows / operation_records，前端只能顯示合計值，無法列出 ETF 來源清單。下一步可在 API 補回每檔股票的來源 ETF 明細。
""", encoding="utf-8")

print("✅ V117 已完成：SignalsClient 已改成合計訊號 + 來源 ETF 明細版")
print(f"備份：{sig_bak}")
print(f"備份：{css_bak}")
