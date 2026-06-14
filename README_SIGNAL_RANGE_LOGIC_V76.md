# Signal Range Logic V76

修正兩個問題：

1. 點 `5日｜10日｜20日` 很慢  
   原本 `/signals` 會載入整個 holdings 歷史。v76 改成：
   - 先查 holdings 的 `etf_code,data_date`
   - 找出每檔 ETF 的 latest date 與 N 個交易日前日期
   - 只載入那些日期的 holdings

2. 點 5日/10日/20日 跟今日沒什麼差別  
   原本資料邏輯可能仍用「最新日 vs 前一日」。v76 改成：
   - 今日 = 最新日 vs 前 1 個交易日
   - 5日 = 最新日 vs 前 5 個交易日
   - 10日 = 最新日 vs 前 10 個交易日
   - 20日 = 最新日 vs 前 20 個交易日

使用：

```bash
python3 tools/apply_signal_range_logic_v76.py
```
