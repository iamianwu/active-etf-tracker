#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
signals_path = ROOT / "frontend/components/SignalsClient.tsx"

if not signals_path.exists():
    raise SystemExit("找不到 frontend/components/SignalsClient.tsx，請確認你在 repo 根目錄執行。")

text = signals_path.read_text(encoding="utf-8")

# 1) 修掉 v80 可能殘留在畫面上的 literal： ` : ''}
#    最常見狀況是 JSX 裡被替換成：
#    {dataDateV80 ? `，資料日期 ${dataDateV80}` : ''}` : ''}
#    或文字節點殘留：` : ''}
text = text.replace("{dataDateV80 ? `，資料日期 ${dataDateV80}` : ''}` : ''}", "{dataDateV80 ? `，資料日期 ${dataDateV80}` : ''}")
text = text.replace("{dataDateV79 ? `，資料日期 ${dataDateV79}` : ''}` : ''}", "{dataDateV80 ? `，資料日期 ${dataDateV80}` : ''}")
text = text.replace("` : ''}", "")

# 2) 強制把 signals-data-status 區塊整理成乾淨版本。
#    只改這個 div，不動其他 UI。
replacement = """<div className={`signals-data-status ${completeV80 ? 'ok' : 'warn'}`}>
          已抓取 {fetchedEtfCountV80} / {totalEtfCountV80} 檔 ETF
          {dataDateV80 ? `，資料日期 ${dataDateV80}` : ''}
        </div>"""

pattern = re.compile(
    r"<div\s+className=\{`signals-data-status[\s\S]*?</div>",
    re.MULTILINE
)

new_text, n = pattern.subn(replacement, text, count=1)

if n == 0:
    raise SystemExit("找不到 signals-data-status 區塊，請貼 frontend/components/SignalsClient.tsx 340-360 給我。")

signals_path.write_text(new_text, encoding="utf-8")

print("✅ v81 已修正今日訊號狀態列多出來的 ` : ''} 顯示問題。")
print("請接著 cd frontend && npm run build")
