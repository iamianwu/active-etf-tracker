# V83 Fast Back Button

問題：
ETF 詳情頁左上角 `<` 若用 `router.push('/signals')`、`router.push('/holdings')` 或 `/etfs`，會重新跑該頁資料查詢，所以手機上看起來要等很久。

v83 修正：
- 在 `EtfDetailClient.tsx` / `StockDetailClient.tsx` 加入 `handleFastBackV83`
- 優先使用 `window.history.back()`
- 這會盡量回到上一頁的原畫面與原捲動位置
- 如果沒有同站歷史紀錄，才依 `from` fallback 到 `/signals`、`/holdings`、`/search` 或 `/etfs`
