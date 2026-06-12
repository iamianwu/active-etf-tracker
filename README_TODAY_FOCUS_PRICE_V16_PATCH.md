# Active ETF Today Focus Price V16 Patch

這版修正你剛剛指出的兩件事：

1. 今日訊號焦點卡片沒有顯示股價
2. 資金動向要改成：
   資金動向：+/-XX億 (+/-XX張)

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_today_focus_price_v16_patch.zip -d .

cat frontend/app/globals.css.addon.today-focus-v16.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend/components/SignalsClient.tsx frontend/app/globals.css frontend/app/globals.css.addon.today-focus-v16.css README_TODAY_FOCUS_PRICE_V16_PATCH.md
git commit -m "Show price and amount on today focus cards"
git push
```

## 顯示邏輯

焦點卡會顯示：

```text
股票名稱 代號
股價（漲跌幅）

資金動向：+11.5 億 (+1,700張)
多空共識：買賣檔數 5:0
```

如果沒有股價，無法換算金額，會顯示：

```text
資金動向：- 億 (+1,000張)
```

如果該股票漲幅 >= 9.5%，股價會亮紅底。
如果跌幅 <= -9.5%，股價會亮綠底。
