# V102 Stable Signals API

修正 V101 造成 `/signals` server-side exception 的問題。

V102 重點：

1. 不再依賴舊 signal helper，直接從 `holdings` 與 `stock_quotes` 計算今日訊號。
2. 所有「張數」欄位統一回傳「張」，避免前端把股數誤顯示成張數。
3. 焦點卡與明細共用同一份 rows，避免明細減碼、焦點卡卻顯示流入。
4. 加入 try/catch fallback，避免 server component 直接白畫面。
5. 金額 = 淨股數 × 股價 / 1e8，單位為「億」。

套用後請推上 Vercel，等 Ready 後重新整理 `/signals`。
