from pathlib import Path

css = Path("frontend/app/globals.css")
text = css.read_text(encoding="utf-8")

marker = "/* V119 signal mobile fit hard override */"

block = r'''

/* V119 signal mobile fit hard override
   目的：
   1. 修正股價欄被截斷成 30... / 23...
   2. 修正狀態 chip 與篩選 chip 超出手機寬度
   3. 改成更像表格、較緊湊、不使用過大的卡片排版
*/

.v118-page {
  max-width: 480px !important;
  width: 100% !important;
  padding-left: 14px !important;
  padding-right: 14px !important;
  overflow-x: hidden !important;
}

/* 四個狀態 chip 不再橫向切掉 */
.v118-status-tabs {
  display: grid !important;
  grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  gap: 8px !important;
  overflow: visible !important;
  padding-bottom: 8px !important;
}

.v118-status-tabs button {
  min-width: 0 !important;
  width: 100% !important;
  padding: 8px 4px !important;
  font-size: 15px !important;
  line-height: 1 !important;
  white-space: nowrap !important;
}

/* 明細排序按鈕可橫向滑動，但不撐破頁面 */
.v118-detail {
  overflow: hidden !important;
}

.v118-table {
  width: 100% !important;
  max-width: 100% !important;
  overflow: visible !important;
}

/* 手機版固定四欄，但壓縮欄寬與字級 */
.v118-head,
.v118-row {
  width: 100% !important;
  max-width: 100% !important;
  display: grid !important;
  grid-template-columns:
    minmax(72px, 1.05fr)
    minmax(70px, .85fr)
    minmax(90px, 1.05fr)
    minmax(58px, .72fr) !important;
  column-gap: 5px !important;
  align-items: center !important;
}

.v118-head {
  min-height: 44px !important;
  padding: 0 6px !important;
  border-radius: 0 !important;
}

.v118-head button {
  min-width: 0 !important;
  font-size: 13px !important;
  line-height: 1.15 !important;
  white-space: normal !important;
  word-break: keep-all !important;
}

.v118-row {
  min-height: 74px !important;
  padding: 10px 6px !important;
}

/* 標的 */
.v118-stock b {
  font-size: 18px !important;
  line-height: 1.1 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.v118-stock span {
  font-size: 13px !important;
}

/* 股價：取消紅底 pill 截斷，漲停改用下方小標籤 */
.v118-price b {
  display: block !important;
  max-width: none !important;
  width: auto !important;
  overflow: visible !important;
  text-overflow: clip !important;
  white-space: nowrap !important;
  font-size: 19px !important;
  line-height: 1.05 !important;
  padding: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: #111827 !important;
}

.v118-price b.limit-up {
  color: #d95561 !important;
  background: transparent !important;
}

.v118-price b.limit-down {
  color: #27a575 !important;
  background: transparent !important;
}

.v118-price span {
  font-size: 13px !important;
  line-height: 1.15 !important;
}

.limit-tag {
  display: inline-block !important;
  margin-top: 3px !important;
  padding: 2px 6px !important;
  border-radius: 999px !important;
  font-size: 11px !important;
  line-height: 1 !important;
  color: #fff !important;
  background: #d95561 !important;
}

.limit-tag.green {
  background: #27a575 !important;
}

/* 淨額 / 張數 */
.v118-flow {
  text-align: right !important;
}

.v118-flow b {
  font-size: 17px !important;
  line-height: 1.12 !important;
  white-space: nowrap !important;
}

.v118-flow span {
  font-size: 13px !important;
  line-height: 1.15 !important;
  white-space: nowrap !important;
}

/* 狀態 / 異動 */
.v118-action {
  text-align: right !important;
  display: grid !important;
  justify-items: end !important;
  gap: 4px !important;
}

.v118-action .pill {
  min-width: 44px !important;
  max-width: 56px !important;
  padding: 5px 6px !important;
  font-size: 13px !important;
  line-height: 1 !important;
  white-space: nowrap !important;
}

.v118-action span {
  font-size: 12px !important;
  line-height: 1.1 !important;
  white-space: nowrap !important;
}

/* 排序列不要過大 */
.v118-detail h2 {
  font-size: 30px !important;
  line-height: 1.12 !important;
  margin-bottom: 12px !important;
}

/* focus cards 稍微縮小，避免上方也擠出 */
.v118-focus-card {
  min-height: 150px !important;
  padding: 13px 12px !important;
}

.v118-focus-title {
  font-size: 18px !important;
}

.v118-focus-name b {
  font-size: 20px !important;
}

.v118-focus-price strong {
  font-size: 30px !important;
}

.v118-focus-price em {
  font-size: 15px !important;
}

.v118-focus-meta {
  font-size: 14px !important;
}

@media (max-width: 390px) {
  .v118-head,
  .v118-row {
    grid-template-columns:
      minmax(68px, 1fr)
      minmax(66px, .82fr)
      minmax(82px, .98fr)
      minmax(52px, .68fr) !important;
    column-gap: 4px !important;
  }

  .v118-row {
    padding-left: 4px !important;
    padding-right: 4px !important;
  }

  .v118-stock b {
    font-size: 17px !important;
  }

  .v118-price b {
    font-size: 18px !important;
  }

  .v118-flow b {
    font-size: 16px !important;
  }

  .v118-action .pill {
    min-width: 40px !important;
    font-size: 12px !important;
  }
}
'''

if marker not in text:
    css.write_text(text + "\n" + block, encoding="utf-8")
    print("✅ V119 已加入：修正手機版明細表格、股價截斷、chip 超出問題")
else:
    print("ℹ️ V119 已存在，未重複加入")
