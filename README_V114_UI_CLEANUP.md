# V114 UI Cleanup

本 patch 會修改：

- `frontend/app/signals/page.tsx`
- `frontend/components/SignalsClient.tsx`
- `frontend/app/globals.css`

改善內容：

1. 今日訊號只保留一組「訊號區間」。
2. 今日資料完整度固定顯示 27 檔總數。
3. 未更新 ETF 會清楚提示，不混入前一日資料。
4. 四張重點卡改成摘要式。
5. 資金交易明細改成更穩定的表格式列。
6. 保留排序與篩選，排序名稱更清楚。
7. 每列可以點擊進入個股頁。
8. 漲停 / 跌停會在股價上亮燈。
