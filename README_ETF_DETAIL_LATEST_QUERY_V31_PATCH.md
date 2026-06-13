# V31 ETF Detail Latest Holdings Query Fix

問題：

ETF 詳細頁顯示 06/08，但 Supabase 查詢確認 00981A 已有 06/12 完整資料。

原因：

Supabase 前端查詢預設最多回傳 1000 筆。  
原本 ETF detail 用：

```ts
selectMaybe('holdings', (q) => q.eq('etf_code', normalizedCode))
```

沒有排序，當單一 ETF 的歷史持股資料超過 1000 筆時，前端不一定拿到最新日期，所以可能只看到 06/08。

V31 修正：

```ts
selectMaybe('holdings', (q) =>
  q
    .eq('etf_code', normalizedCode)
    .order('data_date', { ascending: false })
    .limit(1000)
)
```

這樣會強制先拿最新日期資料，再從這批資料裡計算：

- latest_date
- previous_date
- 新增 / 刪除 / 加碼 / 減碼
- 成分股權重
- 操作日報

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_etf_detail_latest_query_v31_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/lib/etfData.ts README_ETF_DETAIL_LATEST_QUERY_V31_PATCH.md
git commit -m "Fix ETF detail holdings query ordering"
git push
```

Vercel 部署完成後，重新打開：

```text
/etf/00981A
```

應該會顯示：

```text
06/12 持股異動
```

如果手機還顯示舊日期，請用無痕模式或清除瀏覽器快取後再看。
