# V41 操作日報手機表格修正

這版把 ETF 詳情頁「操作日報」下方異動明細，從 `<table>` 改成 div grid。

修正重點：

1. 避免 iPhone Safari 把 table sticky header 浮在資料列中間。
2. 手機版固定 5 欄：標的｜狀態｜持股變動｜變動幅度｜目前權重。
3. 不再需要左右滑，欄位會壓在同一個手機畫面內。
4. 表頭仍可 sticky，但改用單一 div header，比 table th sticky 穩定。

套用：

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud
unzip -o ~/Downloads/active_etf_operation_grid_v41_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx README_ETF_OPERATION_GRID_V41_PATCH.md
git commit -m "Fix ETF operation mobile table with grid layout"
git push
```
