# V117 Missing ETF List Modal

修正內容：

1. 未更新 ETF modal 不再顯示 ETF 1 / ETF 2 假資料。
2. 若 /signals API 沒有回傳 non_today_etfs，前端會在打開 modal 時從 Supabase holdings 查各 ETF 最新 data_date，列出未更新清單。
3. 壓低資料完整度文字與 modal 字級，避免手機上過大。
4. 嘗試移除 SignalsClient 內重複的訊號區間入口，並用 CSS 防止連續重複顯示。

注意：如果本機 npm run build 出現 supabaseUrl is required，代表本機 frontend/.env.local 沒有 NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY；Vercel 有環境變數則仍可部署。
