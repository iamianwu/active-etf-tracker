# ETF Detail Mobile V46 Hard Fit Patch

這版是針對 iPhone Safari / ChatGPT 內建瀏覽器的 ETF 詳情頁手機表格對齊修正。

重點：

1. v45 已經在 main 的話，重新套 v45 會顯示 `nothing to commit`，因此不會有任何變化。
2. v46 在 `EtfDetailClient.tsx` 最後新增一組更強的 mobile CSS override。
3. 成分股表格使用固定 viewport 欄寬：標的 23vw / 持股市值 29vw / 權重 18vw / 股價 30vw。
4. 操作日報表格使用固定百分比欄寬：標的 22% / 狀態 15% / 持股變動 23% / 變動幅度 18% / 目前權重 22%。
5. 說明彈窗開啟時，sticky table header 會隱藏，避免蓋住彈窗文字。

套用後請等 Vercel 部署完成，再用網址加 `?tab=holdings&v=46` 或 `?tab=operation&v=46` 測試。
