# Active ETF Mobile Compact Sticky V12 Patch

這版針對最新回饋：

1. 手機版表格整體 scale 太大  
   → 字體、padding、卡片高度、表格列高全部縮小。

2. 圖 1/2/3 的「標的 / 股票」欄太寬  
   → 手機版縮小第一欄寬度。

3. 往右滑時希望第一欄釘選  
   → 今日訊號、資金持股、ETF列表、ETF詳情內表格都加上 sticky first column。

4. 參考圖 6 的方式  
   → 第一欄固定在左邊，右邊欄位可水平滑動。

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_mobile_compact_sticky_v12_patch.zip -d .

cat frontend/app/globals.css.addon.mobile-v12.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend/app/globals.css frontend/app/globals.css.addon.mobile-v12.css README_MOBILE_COMPACT_STICKY_V12_PATCH.md
git commit -m "Compact mobile tables and pin first column"
git push
```

## 影響頁面

- 今日訊號
- 資金持股
- ETF列表
- ETF詳情頁內：
  - 操作日報
  - 成分股
  - 折溢價表格

## 注意

這版是 CSS patch，不改資料邏輯。  
如果 Vercel 部署後看起來沒變，請手機瀏覽器重新整理或開無痕視窗查看。
