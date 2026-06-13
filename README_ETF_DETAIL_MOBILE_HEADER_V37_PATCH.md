# V37 ETF Detail Mobile Header Patch

這版修正：

1. 手機版 ETF 詳情頁的上方固定列改成更接近 App：
   - 最左邊 `‹`：回上一頁
   - ETF 代號左右的 `◀` / `▶`：切換上一檔 / 下一檔 ETF
2. 切換上一檔 / 下一檔 ETF 時，會保留目前分頁：
   - 例如在「操作日報」按下一檔，下一檔也會停在「操作日報」
   - 在「成分股」按下一檔，下一檔也會停在「成分股」
3. 手機版 ETF 標題列與 tab 字體縮小，避免像之前一樣太大。

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_detail_mobile_header_v37_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx README_ETF_DETAIL_MOBILE_HEADER_V37_PATCH.md
git commit -m "Improve ETF detail mobile header navigation"
git push
```

測試方式：

1. 開 `/etf/00981A`
2. 點「操作日報」
3. 按右側 `▶`
4. 下一檔 ETF 應該仍然停在「操作日報」
5. 最左側 `‹` 應可回上一頁
