# V43 ETF 詳情頁手機修正

修正項目：

1. 成分股頁手機版表頭 sticky 錯位：手機版先改為正常表頭，避免表頭漂到第一列資料中間。
2. 操作日報表頭 sticky 錯位：手機版同樣改為正常表頭，避免與股票列重疊。
3. 變動說明彈窗被表頭蓋住：提高 modal z-index，並在彈窗開啟時隱藏背景表頭。

套用：

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud
unzip -o ~/Downloads/active_etf_detail_mobile_v43_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx README_ETF_DETAIL_MOBILE_V43_PATCH.md
git commit -m "Fix ETF detail mobile sticky header and modal"
git push
```

測試：

- `/etf/00992A?tab=holdings`
- `/etf/00992A?tab=operation`
- 在操作日報點「變動說明」
