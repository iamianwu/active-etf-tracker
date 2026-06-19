#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
css_path = ROOT / "frontend" / "app" / "globals.css"

if not css_path.exists():
    raise SystemExit("❌ 找不到 frontend/app/globals.css，請在 repo 根目錄執行。")

css = r'''
/* ===== V88 CSS-only safe mobile polish ===== */
/* only CSS, no React/data logic changes */

.v86-page > .v86-range-block {
  display: none !important;
}

.v86-focus-grid {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 10px !important;
}

.v86-focus-card {
  min-height: 138px !important;
  padding: 11px 12px !important;
  border-radius: 14px !important;
}

.v86-focus-title {
  font-size: 16px !important;
  line-height: 1.2 !important;
  margin-bottom: 7px !important;
}

.v86-focus-main {
  grid-template-columns: 1fr !important;
  gap: 6px !important;
}

.v86-focus-stock {
  font-size: 17px !important;
  line-height: 1.18 !important;
  white-space: normal !important;
}

.v86-focus-stock span {
  font-size: 13px !important;
  margin-left: 5px !important;
}

.v86-focus-price {
  font-size: 25px !important;
  line-height: 1.08 !important;
  white-space: nowrap !important;
}

.v86-focus-price small {
  font-size: 13px !important;
}

.v86-focus-meta {
  display: grid !important;
  grid-template-columns: auto 1fr !important;
  column-gap: 6px !important;
  row-gap: 1px !important;
  font-size: 11.5px !important;
}

.v86-focus-meta strong {
  font-size: 12.5px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.v86-title-block h1,
.v86-list-head h1 {
  font-size: 28px !important;
  line-height: 1.15 !important;
  margin-top: 22px !important;
}

.v86-data-line,
.v86-list-head p {
  font-size: 14px !important;
}

.v86-status-row {
  gap: 8px !important;
}

.v86-status-pill {
  padding: 8px 12px !important;
  font-size: 16px !important;
  min-height: 44px !important;
}

.v86-signal-row {
  grid-template-columns: minmax(82px, 1fr) 76px 58px 78px !important;
  min-height: 66px !important;
  gap: 6px !important;
  padding: 9px 4px !important;
}

.v86-row-left b,
.v86-holding-row b,
.v86-etf-holding-row b {
  font-size: 17px !important;
  line-height: 1.18 !important;
}

.v86-row-left span,
.v86-holding-row span,
.v86-etf-holding-row span {
  font-size: 13px !important;
}

.v86-row-mid b {
  font-size: 18px !important;
  line-height: 1.12 !important;
}

.v86-row-mid span {
  font-size: 13px !important;
}

.v86-badge {
  font-size: 13px !important;
  padding: 4px 9px !important;
}

.v86-etf-card,
.v86-stock-card {
  padding: 10px 11px !important;
  border-radius: 13px !important;
  margin-bottom: 9px !important;
}

.v86-etf-top b,
.v86-stock-card b {
  font-size: 19px !important;
}

.v86-etf-top span,
.v86-stock-card span,
.v86-stock-card small {
  font-size: 12.5px !important;
}

.v86-etf-price strong,
.v86-stock-price strong {
  font-size: 20px !important;
}

.v86-etf-metrics {
  gap: 4px !important;
  margin-top: 8px !important;
}

.v86-etf-metrics span {
  font-size: 11.5px !important;
}

.v86-etf-metrics b {
  font-size: 12.5px !important;
}

.v86-badge-row {
  margin-top: 8px !important;
}

.v86-badge-row span {
  font-size: 11.5px !important;
  padding: 3px 7px !important;
}

.v86-search-line input {
  height: 42px !important;
  font-size: 15px !important;
}

.v86-kpi {
  min-height: 92px !important;
  padding: 12px !important;
}

.v86-kpi b {
  font-size: 24px !important;
}

@media (max-width: 390px) {
  .v86-focus-grid {
    grid-template-columns: 1fr !important;
  }

  .v86-signal-row {
    grid-template-columns: minmax(78px, 1fr) 72px 56px 72px !important;
    gap: 5px !important;
  }
}
'''

old = css_path.read_text(encoding="utf-8")
if "V88 CSS-only safe mobile polish" in old:
    print("ℹ️ V88 CSS 已存在，未重複加入。")
else:
    bak = css_path.with_suffix(css_path.suffix + ".bak_v88")
    if not bak.exists():
        bak.write_text(old, encoding="utf-8")
    css_path.write_text(old + "\n\n" + css, encoding="utf-8")
    print("✅ 已加入 V88 CSS-only mobile polish。")

readme = ROOT / "README_CSS_ONLY_SAFE_UI_V88.md"
readme.write_text('''# V88 CSS-only Safe Mobile Polish

這版只修改 CSS，不碰 React/資料邏輯，目標是安全修 UI：

- 隱藏今日訊號頁重複的第二組「訊號區間」
- 今日訊號四張重點卡片縮小
- 明細 row 縮小
- ETF 列表 / 資金持股卡片縮小
- 詳情頁 KPI 不要太大

若要回復，還原 `frontend/app/globals.css.bak_v88` 即可。
''', encoding="utf-8")
print("✅ wrote README_CSS_ONLY_SAFE_UI_V88.md")
