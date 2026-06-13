# ETF detail mobile v47 compact fit patch

這版針對手機成分股/操作日報表格做更激進的壓縮：

- 移除 v46 的 100vw 列寬，改用容器 100% 百分比欄寬，避免 iPhone WebView 地址列造成視覺溢出。
- 成分股表格與操作日報表格都降低列高與字級。
- 表頭與資料列使用完全相同的 grid-template-columns。
- 說明彈窗開啟時，sticky header 會隱藏。

套用後請用 `?v=47` 測試。
