# V45 ETF detail mobile table alignment patch

這版專門修正 V44 仍會在 iPhone Safari / 手機瀏覽器出現的兩個問題：

1. 操作日報表格 sticky header 和資料列欄位沒有完全對齊。
2. 成分股表格 sticky header 第一欄偏移，導致圖表下方表格看起來很誇張。

修正方式：

- 操作日報與成分股表格都用固定 CSS grid 欄寬。
- header 與 row 共用同一組 grid-template-columns。
- 移除舊版 table / left sticky / 橫向寬表格殘留樣式。
- 第一欄「標的」強制靠左，與下方股票名稱同起點。
- 其他數值欄依照圖示靠右或置中。
- 彈窗開啟時隱藏 sticky table header，避免蓋在 modal 上。

套用方式：

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud
unzip -o ~/Downloads/active_etf_detail_mobile_v45_alignment_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx README_ETF_DETAIL_MOBILE_V45_PATCH.md
git commit -m "Fix ETF detail mobile grid alignment v45"
git push
```

測試頁面：

```text
/etf/00400A?tab=operation
/etf/00400A?tab=holdings
/etf/00994A?tab=operation
/etf/00994A?tab=holdings
```

如果手機 Safari 還看到舊畫面，先重新整理兩次，或在網址後加 `?v=45` 測試快取。
