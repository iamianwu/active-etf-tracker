# V119 Missing ETF Real List

修正內容：

1. 未更新 ETF modal 不再只顯示「API 尚未回傳清單」。
2. 若 `/signals` 沒有 `non_today_etfs`，前端會在打開彈窗時直接查 Supabase `holdings`，找出 27 檔 ETF 各自最新 `data_date`。
3. 彈窗會列出：ETF 代號、ETF 名稱、最新資料日。
4. 手機版彈窗字級與列表間距縮小，避免過大與看不懂。

注意：本機若要測試彈窗查詢，`frontend/.env.local` 需要有：

```env
NEXT_PUBLIC_SUPABASE_URL=你的 Supabase URL
NEXT_PUBLIC_SUPABASE_ANON_KEY=你的 anon public key
```

Vercel 已有這兩個環境變數就可以正常運作。
