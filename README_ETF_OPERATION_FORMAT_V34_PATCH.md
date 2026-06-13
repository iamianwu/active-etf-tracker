# V34 ETF Operation Format Patch

這版修正 ETF 詳細頁「操作日報」的顯示規則：

1. 新增標的的「變動幅度」固定顯示 `100%`
2. 刪除標的的「目前權重」主數字顯示 `-`
3. 權重或變動百分比只要大於 0、但小於 0.01%，顯示 `<0.01%`
4. 若是很小的正負變動，會保留方向：
   - `+<0.01%`
   - `-<0.01%`

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_operation_format_v34_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx README_ETF_OPERATION_FORMAT_V34_PATCH.md
git commit -m "Format ETF operation change values"
git push
```

部署完成後，手機看 `/etf/00991A` → 操作日報：

- 新增：變動幅度會是 `100%`
- 刪除：目前權重會是 `-`
- 小於 0.01% 的變動會顯示 `<0.01%`
