# V103 Signal lots and consensus

今日訊號頁新增：

1. 每列顯示「張數」
2. 每列顯示「多空共識：買賣檔數」
3. 焦點卡同步顯示交易淨額、張數、多空共識
4. 排序新增「張數」與「共識」
5. 重寫 SignalsClient，避免舊版畫面重複訊號區間與欄位擠在一起

注意：
- 張數以 API 傳入的 net_lots / delta_lots 優先。
- 若舊欄位 delta_shares 是股數且數值異常大，會自動除以 1000。
