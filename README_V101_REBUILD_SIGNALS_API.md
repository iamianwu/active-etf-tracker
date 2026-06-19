# V101 Rebuild Signals API

修正 v100 套錯檔案的問題。

v100 去找 `frontend/lib/etfData.ts` 的 `getSignalsData()`，但目前專案的今日訊號資料來源是在 `frontend/lib/api.ts` 的 `getSignals()`。

V101 直接替換 `api.ts/getSignals()`：

- 從 holdings 計算每檔 ETF 最新有效日 vs 前一有效日。
- 使用 `delta_shares / 1000` 當張數。
- 交易淨額 = 淨張數 × 1000 × 股價 / 1e8。
- 回傳 `rows` 與 `aggregate` 皆為同一份淨變動資料。
- 避免明細是減碼、焦點卡卻顯示淨流入。
