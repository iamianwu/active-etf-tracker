# Active ETF Mobile Layout V13 Patch

這版針對你最新的手機畫面問題：

## 修正內容

1. 今日訊號首頁
   - 四張焦點卡片改成 2 欄 compact 版
   - 字體、padding、卡片高度都縮小
   - 比較接近你參考圖 2，不會一張卡佔太多高度

2. 資金持股頁
   - 股票欄縮窄
   - 股票欄 sticky 固定在左側
   - 右側欄位可以像 App 一樣水平滑動
   - 避免第一欄佔太大 width

3. ETF 列表
   - ETF 列表標題與「即時 / 報酬 / 基本」放在同一列
   - 第一欄股票欄縮窄
   - 第一欄 sticky 固定
   - 右側股價、漲跌幅、成交量欄位可水平滑動
   - 更接近你參考圖 6 的排版

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_mobile_layout_v13_patch.zip -d .

cat frontend/app/globals.css.addon.mobile-v13.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend/components/EtfListClient.tsx frontend/app/globals.css frontend/app/globals.css.addon.mobile-v13.css README_MOBILE_LAYOUT_V13_PATCH.md
git commit -m "Refine mobile table layout and ETF list header"
git push
```

部署後請用手機 Safari 開無痕或重新整理一次，避免舊 CSS 快取。
