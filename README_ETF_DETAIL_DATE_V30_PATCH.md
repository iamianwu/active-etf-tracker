# V30 ETF Detail Date Fix

你查到 00981A 的 holdings 已經有 2026-06-12：

```text
2026-06-12 row_count=54 stock_count=51 stock_weight=96.91
2026-06-11 row_count=53 stock_count=50 stock_weight=96.05
```

所以資料庫沒問題。ETF 詳細頁還顯示 06/09，通常是前端頁面被 Next/Vercel 靜態快取，或日期選擇邏輯沒有避開舊資料。

V30 修正：

1. `frontend/app/etf/[code]/page.tsx` 加上：

```ts
export const dynamic = 'force-dynamic';
export const revalidate = 0;
```

2. `frontend/lib/etfData.ts` 改成選「有效持股日期」：

```text
4碼股票檔數 >= 20
股票權重合計 >= 30%
```

再用最新有效日期和前一個有效日期計算新增 / 刪除 / 加碼 / 減碼。

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_etf_detail_date_v30_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/lib/etfData.ts 'frontend/app/etf/[code]/page.tsx' README_ETF_DETAIL_DATE_V30_PATCH.md
git commit -m "Fix ETF detail latest holding date"
git push
```

## 驗證

Vercel 部署完成後，重新打開：

```text
/etf/00981A
```

應該要顯示：

```text
06/12 持股異動
```

如果手機仍顯示舊資料，請先強制重新整理或用無痕模式開啟。
