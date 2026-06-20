# V111 Signal consensus fix

修正今日訊號的「多空共識」邏輯。

問題：
- 舊版在缺少 buy/sell count 時，會 fallback 到 `etf_count` / `count`。
- 這會把「持有這檔股票的 ETF 總數」誤當成「今天買賣的 ETF 數」。
- 例如聯發科 2454 在 06/18 只有 1 檔 ETF 減碼，卻顯示 `0:18`。

修正：
- API row 明確輸出：`buy_count`、`sell_count`、`add_etf_count`、`reduce_etf_count`。
- 前端 getBuyCount/getSellCount 優先讀 API 的實際買賣檔數。
- 若沒有欄位，改從 `changed_etfs` 計算。
- 最後保底最多只顯示 1，不再使用 `etf_count/count` 當共識數。

預期：
- 2454 若 06/18 只有一檔 ETF 賣，應顯示 `0:1`，不會再是 `0:18`。
