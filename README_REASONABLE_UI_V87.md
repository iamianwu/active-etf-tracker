# V87 Reasonability Fixes

修正 v86 目前不合理的地方：

1. 今日訊號「訊號區間」重複顯示  
   - SignalsClient 不再另外渲染區間切換，避免跟 page-level tabs 重複。

2. 今日訊號重點卡片不要亂抓 fallback  
   - 資金流入：只取 flow > 0 的有效個股  
   - 資金流出：只取 flow < 0 的有效個股  
   - 最多 ETF 加碼：必須 addCount > 0  
   - 最多 ETF 減碼：必須 reduceCount > 0  
   - 如果沒有有效訊號，顯示「尚無有效訊號」，不要硬塞台積電 0:0。

3. 卡片太大、字太大、內容太散  
   - 今日訊號改成 2 欄小卡  
   - 明細列、ETF 卡片、資金持股卡片縮小字級與 padding  
   - 手機小螢幕仍自動變 1 欄。

4. 明細 row 過度巨大  
   - 壓縮 row 高度與欄寬，降低滑動負擔。
