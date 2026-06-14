# Signal Range Schema V77

v76 修了 5日 / 10日 / 20日比較邏輯，但回傳格式少了舊版 `SignalsClient` 需要的欄位，導致：

- 顯示 `已抓取 0 / 0 檔 ETF`
- 資料日期不見
- 明細表股價、金額變成 `-`
- 多空共識可能變成 0:0

v77 不改 UI，只修 `frontend/lib/api.ts` 的 `getSignals()` 回傳格式，補回多種命名 alias：

- `includedEtfCount` / `included_etf_count`
- `totalEtfCount` / `total_etf_count`
- `latestDataDate` / `data_date`
- `price` / `stock_price`
- `change_pct`
- `delta_value_billion` / `amount_billion`
- `buy_etf_count` / `sell_etf_count`
