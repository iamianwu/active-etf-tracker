# V32 ETF Detail Change Preview

這版修正 ETF 詳細頁「總覽」：

原本只有：

```text
06/12 持股異動：新增 1 檔｜刪除 1 檔
```

V32 會在下方加上像 App 圖片的提示卡：

```text
新增標的：臻鼎-KY
刪除標的：南亞塑膠
```

如果有多檔，會顯示前 3 檔，例如：

```text
新增標的：A、B、C 等 5 檔
```

點卡片會直接切到「操作日報」並篩選該狀態。

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_etf_detail_change_preview_v32_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx README_ETF_DETAIL_CHANGE_PREVIEW_V32_PATCH.md
git commit -m "Show added and removed holdings in ETF overview"
git push
```

Vercel 部署完成後，到：

```text
/etf/00991A
```

總覽應該會出現：

```text
新增標的：臻鼎-KY
刪除標的：南亞塑膠
```
