# V80 ETF List and Signal Count Fix

v79 還是 22 檔的主因通常是：

`frontend/lib/etfData.ts` 用 `selectMaybe('holdings')` 只拿到 Supabase 預設前 1000 rows，
新 ETF 的 holdings 沒被掃到，所以 ETF 列表仍是 22 檔。

v80 修正：

1. ETF 列表
   - holdings 改成分頁抓取
   - 用 `ETF_CODES + etf_quotes + holdings` 聯集
   - 排除 D 類 ETF

2. 今日訊號
   - `已抓取 X/Y` 增加 fallback
   - 如果 API 沒回傳 fetched count，就用 changes rows 中的 unique ETF count
   - 不再顯示 `0 / 25`
