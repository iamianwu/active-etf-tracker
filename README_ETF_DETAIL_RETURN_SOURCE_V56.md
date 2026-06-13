# ETF detail back navigation v56

這版修正 ETF 詳情頁左上角返回 `<` 的行為：

- 從今日訊號進來：返回今日訊號
- 從資金持股進來：返回資金持股
- 從 ETF 列表進來：返回 ETF 列表
- 在 ETF 詳情頁用左右箭頭切換 ETF 後，仍保留原本來源
- 切換 tab 後，返回來源不會被 tab 或上一檔 / 下一檔干擾

技術：

- 優先讀 URL 的 `returnTo` 或 `from`
- 其次讀同站 `document.referrer`
- 再其次讀 `sessionStorage`
- 最後 fallback 到 `/etfs`

支援範例：

- `/etf/00403A?from=signals`
- `/etf/00403A?from=holdings`
- `/etf/00403A?from=etfs`
- `/etf/00403A?returnTo=%2Fholdings`
