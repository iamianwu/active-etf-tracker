# V110 Signal metadata display fix

修正今日訊號顯示邏輯：

- 不再顯示錯誤的 `18 / 18`。
- 改成顯示：`今日有資料 19 / 27 檔 ETF`。
- 另外顯示：`可計算訊號 18 檔；未納入 9 檔（8 檔非今日資料、1 檔缺前日比較）`。
- API metadata 分清楚：
  - `total_etf_count`: ETF 清單總數，例如 27。
  - `today_etf_count`: targetDate 當天有 holdings 的 ETF，例如 19。
  - `includedEtfCount` / `comparable_etf_count`: 有今日資料且有前日可比較的 ETF，例如 18。
