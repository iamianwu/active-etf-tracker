# V36 ETF Detail Sticky Header + Prev/Next Patch

這版修正 ETF 詳細頁手機版兩個問題：

1. 往下滑時，ETF 代碼 / 名稱 / 左右箭頭 / 分頁列會固定在畫面上方。
2. `‹`、`›` 可以切換上一檔 / 下一檔 ETF，不再只是回 ETF 列表。

預設 ETF 順序：

```text
00400A → 00401A → 00403A → 00980A → 00981A → ... → 00999A
```

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_detail_sticky_nav_v36_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx README_ETF_DETAIL_STICKY_NAV_V36_PATCH.md
git commit -m "Add sticky ETF detail header and prev next navigation"
git push
```

部署完成後，到 `/etf/00981A` 或 `/etf/00403A`：

- 往下滑時，上方 ETF 代碼與 tab 會釘住。
- 左邊 `‹` 切上一檔 ETF。
- 右邊 `›` 切下一檔 ETF。
