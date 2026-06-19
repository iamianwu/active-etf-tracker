# V97 Fix Stock Detail Client Exception and Signal Stability

修正內容：
1. 修正 V96 在個股頁插入 `data={{data}}` / `etfRows={{etfRows}}` 造成的 client-side exception。
2. StockRecentOperationPanel 加入防呆，避免 props 型態錯誤時整頁崩潰。
3. 隱藏重複的訊號區間 selector。
4. 今日訊號排序加入穩定 tie-breaker，避免同分資料重新整理時順序漂移。
