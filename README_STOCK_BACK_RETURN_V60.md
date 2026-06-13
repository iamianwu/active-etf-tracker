# v60 Stock back return source fix

修正：

- 從「資金持股」點進個股頁後，個股頁左上角 `<` 應回到「資金持股」，不應回到搜尋頁。
- 個股頁底下「持股主動式 ETF」連結也會延續同一個 return source。

原因：

StockDetailClient 的返回按鈕原本 hard-code 到 `/search`，所以即使從 `/holdings` 進來，按 `<` 也會跑到搜尋頁。

這版：

1. holdings 頁點股票時補上 `from=holdings&returnTo=/holdings`。
2. StockDetailClient 的 `<` 改成讀 URL 的 `returnTo`。
3. 若沒有 `returnTo`，預設回 `/holdings`，不再回 `/search`。
