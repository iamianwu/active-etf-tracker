# V117 Compact Signals Table

這版把今日訊號改成較接近資料表的高資訊密度 UI，但不完全仿照參考圖。

重點：
- 移除重複的「訊號區間」，只保留一組。
- 明細改成精簡表格式，不再用大卡片。
- 排序改回 ▲ / ▼ / ↕ 的欄位式操作。
- 支援：淨流入、淨流出、絕對金額、張數、共識、股價排序。
- 每列可點進個股頁。
- 漲停 / 跌停只用小型提示，不讓整列過度變大。
- 未更新 ETF modal 不再顯示 ETF 1、ETF 2 假資料；若 API 有清單就顯示清單，沒有就顯示說明。
- 內容避免超出手機寬度。

套用後建議先在 Vercel 觀看，因本機 build 需要 NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY。
