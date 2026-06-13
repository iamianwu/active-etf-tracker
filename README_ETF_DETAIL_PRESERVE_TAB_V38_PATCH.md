# V38 ETF Detail Preserve Tab Patch

修正 V37 的分頁切換問題：

- 在「操作日報」按下一檔 ETF，下一檔會維持在「操作日報」。
- 在「成分股」按下一檔 ETF，下一檔會維持在「成分股」。
- 左側 `‹` 保持為回上一頁；ETF 代碼左右的 `◀` / `▶` 才是切換 ETF。

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_detail_preserve_tab_v38_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx README_ETF_DETAIL_PRESERVE_TAB_V38_PATCH.md
git commit -m "Preserve ETF detail tab when switching ETFs"
git push
```

測試：

1. 打開 `/etf/00981A`
2. 點「操作日報」
3. 按右側 `▶`
4. 下一檔應仍然停在「操作日報」
