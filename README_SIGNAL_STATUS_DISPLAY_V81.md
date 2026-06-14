# V81 Signal Status Display Fix

v80 後若今日訊號出現：

`已抓取 25 / 25 檔 ETF，資料日期 2026-06-12` : ''}`

代表前一次自動替換 JSX 時，多留了一段 literal 字串。

v81 只修：

- `frontend/components/SignalsClient.tsx`
- signals-data-status 區塊
- 不改資料邏輯
- 不改 ETF 數量
