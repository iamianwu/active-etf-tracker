# V40 ETF detail mobile header/table patch

修正項目：

1. ETF 詳情頁直接用頁面內 CSS 隱藏全站 Header，不再只依賴 AppShell 的 path 判斷。
2. 修正手機版操作日報表格在 iOS Safari 會出現「標的」表頭與其他表頭分離、重疊股票列的問題。
3. 操作日報表格改成手機固定 5 欄 grid：標的 / 狀態 / 持股變動 / 變動幅度 / 目前權重，避免橫向滑動與表頭錯位。

套用：

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud
unzip -o ~/Downloads/active_etf_detail_mobile_header_table_v40_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx frontend/components/AppShell.tsx frontend/app/layout.tsx README_ETF_DETAIL_MOBILE_HEADER_TABLE_V40_PATCH.md
git commit -m "Fix ETF detail mobile header and sticky operation table"
git push
```

測試：

- /etf/00403A?tab=operation
- 手機往下滑操作日報表格，表頭不應再與股票列重疊。
- ETF 詳情頁不應再顯示全站 Header：🎯 主動式 ETF / 今日訊號 / 資金持股 / ETF列表。
