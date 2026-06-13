# ETF Detail Mobile V49 Patch

這版針對手機版 ETF 詳情頁「表頭看起來與資料欄沒有對齊」再修正。

重點：
- v48 已讓表頭與資料列使用同一個 grid parent。
- v49 進一步把數字欄位的表頭改成與資料一樣右靠。
- 成分股表：標的左靠、持股市值右靠、權重置中、股價右靠。
- 操作日報表：標的左靠、狀態置中、持股變動/變動幅度/目前權重右靠。

測試網址建議加 cache busting：
- /etf/00400A?tab=holdings&v=49
- /etf/00400A?tab=operation&v=49
