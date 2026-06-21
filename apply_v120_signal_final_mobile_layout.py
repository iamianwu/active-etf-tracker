from pathlib import Path
import re

root = Path(".")
css_path = root / "frontend/app/globals.css"

css = css_path.read_text(encoding="utf-8")

marker = "/* ===== V120 SIGNAL FINAL MOBILE LAYOUT ===== */"

block = r'''
/* ===== V120 SIGNAL FINAL MOBILE LAYOUT ===== */

/* 只針對今日訊號頁做最後覆蓋，避免舊版 v114/v117/v118/v119 互相打架 */
.signals-client-v114,
.signals-client-v117,
.signals-page-v114 {
  max-width: 100%;
  overflow-x: hidden !important;
}

/* 上方四張重點卡：改成手機穩定版，股價與漲跌幅分行，不再擠在一起 */
.focus-grid-v114,
.focus-grid-v117 {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 12px !important;
  width: 100% !important;
  overflow: visible !important;
}

.focus-card-v114,
.focus-card-v117 {
  min-width: 0 !important;
  width: 100% !important;
  min-height: 176px !important;
  padding: 14px 13px !important;
  border-radius: 18px !important;
  box-sizing: border-box !important;
  overflow: hidden !important;
}

.focus-title-v114,
.focus-title-v117 {
  font-size: 19px !important;
  line-height: 1.15 !important;
  margin-bottom: 10px !important;
  white-space: normal !important;
}

.focus-name-v114,
.focus-name-v117 {
  display: flex !important;
  align-items: baseline !important;
  gap: 7px !important;
  min-width: 0 !important;
  line-height: 1.12 !important;
  margin-bottom: 8px !important;
}

.focus-name-v114 span,
.focus-name-v117 span {
  display: block !important;
  min-width: 0 !important;
  max-width: 100% !important;
  font-size: 22px !important;
  font-weight: 950 !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}

.focus-name-v114 em,
.focus-name-v117 b {
  flex: 0 0 auto !important;
  font-size: 15px !important;
  color: #8a96a8 !important;
  font-weight: 900 !important;
}

/* 關鍵：股價與漲跌幅不要同列硬塞 */
.focus-price-v114,
.focus-price-line-v117 {
  display: block !important;
  margin-top: 2px !important;
  min-width: 0 !important;
  white-space: normal !important;
}

.focus-price-v114 span,
.focus-price-line-v117 span {
  display: block !important;
  max-width: 100% !important;
  font-size: 34px !important;
  line-height: 1 !important;
  font-weight: 950 !important;
  letter-spacing: -0.03em !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}

.focus-price-v114 small,
.focus-price-line-v117 b {
  display: block !important;
  margin-top: 5px !important;
  font-size: 17px !important;
  line-height: 1.1 !important;
  font-weight: 950 !important;
  white-space: nowrap !important;
}

.focus-meta-v114,
.focus-metrics-v117 {
  margin-top: 9px !important;
  display: grid !important;
  gap: 2px !important;
  font-size: 14px !important;
  line-height: 1.25 !important;
  font-weight: 900 !important;
  color: #768297 !important;
}

.focus-meta-v114 b,
.focus-metrics-v117 b {
  font-size: 15px !important;
}

/* 交易明細：不要做大卡片，也不要讓右側超出。固定 4 欄，像資料表但字體縮小 */
.signal-list-head-v114,
.signal-list-head-v117,
.v118-list-head {
  width: 100% !important;
  max-width: 100% !important;
  overflow: hidden !important;
}

.signal-table-v114,
.signal-table-v117,
.v118-table,
.v118-signal-table {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
  table-layout: fixed !important;
}

/* 如果明細是 div grid */
.v118-head,
.v118-row,
.signal-row-v114,
.signal-row-v117 {
  display: grid !important;
  grid-template-columns: minmax(72px, 1.05fr) minmax(58px, 0.78fr) minmax(86px, 1.02fr) minmax(70px, 0.86fr) !important;
  column-gap: 8px !important;
  align-items: center !important;
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  box-sizing: border-box !important;
  overflow: hidden !important;
}

.v118-head > *,
.v118-row > *,
.signal-row-v114 > *,
.signal-row-v117 > * {
  min-width: 0 !important;
  overflow: hidden !important;
}

/* 表頭 */
.v118-head,
.signal-table-head-v114,
.signal-table-head-v117 {
  background: #f3f6fa !important;
  border-radius: 0 !important;
}

.v118-head *,
.signal-table-head-v114 *,
.signal-table-head-v117 * {
  font-size: 13px !important;
  line-height: 1.15 !important;
  font-weight: 900 !important;
  color: #647085 !important;
}

/* 標的欄 */
.v118-target b,
.signal-stock-v114 b,
.signal-stock-v117 b {
  display: block !important;
  font-size: 18px !important;
  line-height: 1.08 !important;
  font-weight: 950 !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}

.v118-target span,
.signal-stock-v114 span,
.signal-stock-v117 span {
  display: block !important;
  margin-top: 3px !important;
  font-size: 13px !important;
  line-height: 1 !important;
  color: #8b96a8 !important;
  font-weight: 850 !important;
}

/* 股價欄：不要再把 308.5 變 30... */
.v118-price,
.signal-price-v114,
.signal-price-v117 {
  text-align: left !important;
}

.v118-price b,
.signal-price-v114 b,
.signal-price-v117 b {
  display: inline-block !important;
  max-width: none !important;
  width: auto !important;
  font-size: 18px !important;
  line-height: 1.05 !important;
  font-weight: 950 !important;
  overflow: visible !important;
  text-overflow: clip !important;
  white-space: nowrap !important;
  padding: 0 !important;
}

.v118-price .limit-up,
.v118-price .limit-up-pill,
.v118-price .limit-up-pill-v117,
.limit-up-pill-v117 {
  padding: 2px 7px !important;
  border-radius: 8px !important;
  max-width: none !important;
  overflow: visible !important;
  text-overflow: clip !important;
}

.v118-price small,
.signal-price-v114 small,
.signal-price-v117 small {
  display: block !important;
  margin-top: 3px !important;
  font-size: 13px !important;
  line-height: 1.05 !important;
  font-weight: 900 !important;
}

/* 淨額 / 張數欄 */
.v118-flow,
.signal-flow-v114,
.signal-flow-v117 {
  text-align: right !important;
}

.v118-flow b,
.signal-flow-v114 b,
.signal-flow-v117 b {
  display: block !important;
  font-size: 16px !important;
  line-height: 1.05 !important;
  font-weight: 950 !important;
  white-space: nowrap !important;
}

.v118-flow span,
.v118-flow small,
.signal-flow-v114 span,
.signal-flow-v117 span {
  display: block !important;
  margin-top: 4px !important;
  font-size: 13px !important;
  line-height: 1.05 !important;
  font-weight: 900 !important;
  white-space: nowrap !important;
}

/* 狀態 / 異動 ETF 欄 */
.v118-action,
.signal-action-v114,
.signal-action-v117 {
  text-align: right !important;
  overflow: hidden !important;
}

.v118-action .pill,
.signal-action-v114 .pill,
.signal-action-v117 .pill {
  display: inline-flex !important;
  justify-content: center !important;
  align-items: center !important;
  min-width: 38px !important;
  max-width: 52px !important;
  height: 26px !important;
  padding: 0 8px !important;
  border-radius: 999px !important;
  font-size: 12px !important;
  line-height: 1 !important;
  font-weight: 950 !important;
  white-space: nowrap !important;
}

.v118-action small,
.signal-action-v114 small,
.signal-action-v117 small {
  display: block !important;
  margin-top: 5px !important;
  font-size: 12px !important;
  line-height: 1.05 !important;
  font-weight: 900 !important;
  color: #7b8798 !important;
  white-space: nowrap !important;
}

/* 排序按鈕區：保留水平滑動，但不要把內容撐出頁面 */
.signal-sort-row-v114,
.signal-sort-row-v117,
.v118-sort-row,
.v118-filter-row {
  display: flex !important;
  gap: 8px !important;
  overflow-x: auto !important;
  overflow-y: hidden !important;
  max-width: 100% !important;
  padding-bottom: 4px !important;
  -webkit-overflow-scrolling: touch !important;
  scrollbar-width: none !important;
}

.signal-sort-row-v114::-webkit-scrollbar,
.signal-sort-row-v117::-webkit-scrollbar,
.v118-sort-row::-webkit-scrollbar,
.v118-filter-row::-webkit-scrollbar {
  display: none !important;
}

.signal-sort-row-v114 button,
.signal-sort-row-v117 button,
.v118-sort-row button,
.v118-filter-row button {
  flex: 0 0 auto !important;
  height: 38px !important;
  padding: 0 14px !important;
  border-radius: 999px !important;
  font-size: 15px !important;
  font-weight: 950 !important;
  white-space: nowrap !important;
}

/* 手機更窄時再縮一點 */
@media (max-width: 390px) {
  .focus-card-v114,
  .focus-card-v117 {
    padding: 12px 10px !important;
    min-height: 168px !important;
  }

  .focus-title-v114,
  .focus-title-v117 {
    font-size: 17px !important;
  }

  .focus-name-v114 span,
  .focus-name-v117 span {
    font-size: 20px !important;
  }

  .focus-price-v114 span,
  .focus-price-line-v117 span {
    font-size: 30px !important;
  }

  .focus-price-v114 small,
  .focus-price-line-v117 b {
    font-size: 15px !important;
  }

  .v118-head,
  .v118-row,
  .signal-row-v114,
  .signal-row-v117 {
    grid-template-columns: minmax(66px, 1.02fr) minmax(52px, 0.72fr) minmax(78px, 1fr) minmax(60px, 0.76fr) !important;
    column-gap: 6px !important;
  }

  .v118-target b,
  .signal-stock-v114 b,
  .signal-stock-v117 b {
    font-size: 16px !important;
  }

  .v118-price b,
  .signal-price-v114 b,
  .signal-price-v117 b {
    font-size: 16px !important;
  }

  .v118-flow b,
  .signal-flow-v114 b,
  .signal-flow-v117 b {
    font-size: 14px !important;
  }

  .v118-action .pill,
  .signal-action-v114 .pill,
  .signal-action-v117 .pill {
    min-width: 34px !important;
    max-width: 46px !important;
    font-size: 11px !important;
    padding: 0 6px !important;
  }

  .v118-action small,
  .signal-action-v114 small,
  .signal-action-v117 small {
    font-size: 11px !important;
  }
}
'''

# 只保留最後一個 V120 block，避免越疊越亂
if marker in css:
    css = css[:css.index(marker)].rstrip() + "\n" + block + "\n"
else:
    css = css.rstrip() + "\n\n" + block + "\n"

css_path.write_text(css, encoding="utf-8")
print("✅ V120 已加入：修正焦點卡片、明細表格超出、股價截斷、排序列寬度")
