# V109 Today-only signals

修正今日訊號邏輯：

- 全站使用同一個 targetDate = holdings 最大 data_date。
- 今日訊號只納入 targetDate 有 holdings 且有前一可比較資料的 ETF。
- 不再把前一天 ETF 的最新資料混入今日訊號。
- 回傳 includedEtfCount / total_etf_count / missing_today_etf_codes / today_holding_rows / signal_count，讓前端可以說清楚納入幾檔與排除原因。
- 交易淨額使用有方向的 signed amount；淨流入只取正值，淨流出只取負值。
- delta_shares 以「張」為單位，避免 600 張顯示成 600,000 張。
