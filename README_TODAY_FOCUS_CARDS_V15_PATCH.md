# Active ETF Today Focus Cards V15 Patch

這版是針對「今日訊號」上方四張焦點卡片的手機 / 桌機排版調整。

## 目標

你的目前畫面像：

- 卡片太大
- 股票名稱、代號、資金動向分散
- 沒有像 App 那樣顯示股價 / 漲跌幅
- 漲停 / 跌停沒有亮燈

這版 CSS 會先把卡片改成更接近 App 的樣式：

- 標題左側紅 / 綠色直條
- 股票名稱 + 代號同列
- 右側資金動向與多空共識
- 手機版更緊湊
- 支援 `.focus-price`、`.limit-up`、`.limit-down`

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_today_focus_cards_v15_patch.zip -d .

cat frontend/app/globals.css.addon.today-focus-v15.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend/app/globals.css frontend/app/globals.css.addon.today-focus-v15.css README_TODAY_FOCUS_CARDS_V15_PATCH.md
git commit -m "Restyle today focus cards"
git push
```

## 重要：若要顯示股價 / 漲跌幅

CSS 已經做好 `.focus-price` 樣式，但你的 Today Signal component 需要真的輸出這段 HTML：

```tsx
<div className="focus-stock">
  <b>{item.stock_name}</b>
  <span>{item.stock_code}</span>
  <FocusPrice price={item.price} changePct={item.change_pct} />
</div>
```

我也附了一個 helper 檔：

```text
frontend/components/FocusPriceHelper.v15.tsx
```

你可以把裡面的 `V15FocusPrice` 貼到今日訊號的 component 裡。

如果你不知道今日訊號 component 檔案是哪個，執行：

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud
grep -R "focus-card" -n frontend
```

找到有 `focus-card` 的檔案，把結果貼給我，我可以下一包直接幫你改到 component。
