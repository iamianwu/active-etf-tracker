# V44 ETF Detail Mobile Sticky Header Alignment Patch

這版修正 ETF 詳情頁手機版下方表格：

- 操作日報表格：重新啟用 sticky header，並固定使用同一組 grid 欄寬，讓「標的 / 狀態 / 持股變動 / 變動幅度 / 目前權重」與資料列完全對齊。
- 成分股表格：重新啟用 sticky header，並固定使用同一組 grid 欄寬，讓「標的 / 持股市值持股張數 / 權重 / 股價漲跌幅」與資料列完全對齊。
- 防止表格自己產生橫向捲動，避免手機版欄位被切開或表頭漂移。
- 保留 V43 的彈窗修正；開啟「變動說明」時，sticky header 會隱藏，不會蓋住彈窗。

套用：

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud
unzip -o ~/Downloads/active_etf_detail_mobile_v44_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx README_ETF_DETAIL_MOBILE_V44_PATCH.md
git commit -m "Fix ETF detail mobile table header alignment"
git push
```

測試頁面：

```text
/etf/00994A?tab=operation
/etf/00994A?tab=holdings
/etf/00992A?tab=holdings
```
