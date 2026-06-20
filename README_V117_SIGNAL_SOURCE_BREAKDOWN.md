# V117 Signal Source Breakdown

本版修正今日訊號容易誤判的問題：

- 今日訊號列表仍顯示全部 ETF 合計後的淨額 / 張數。
- 不再把 generic buy_count / sell_count 誤當作今日買賣共識，避免把「持有 ETF 檔數」顯示成「買賣 14:0」。
- 點摘要卡或明細列的淨額 / 張數，可以查看來源 ETF 明細；若 API 尚未回傳來源 ETF，會明確提示。
- 明細排序改回 ▲ / ▼ / ↕ 形式。
- 明細表改成較緊湊的 4 欄版面，避免文字超出頁面。
- 保留點股票名稱 / 股價進入個股頁。

注意：若 /signals API 尚未回傳 source_rows / detail_rows / operation_records，前端只能顯示合計值，無法列出 ETF 來源清單。下一步可在 API 補回每檔股票的來源 ETF 明細。
