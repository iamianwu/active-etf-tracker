# Active ETF List UI V9 Patch

這版修改「ETF 列表」頁，讓它更接近你附圖的 ETF app。

## 修改內容

1. ETF 列表改成三個模式：
   - 即時
   - 報酬
   - 基本

2. 即時模式欄位：
   - 股票
   - 股價
   - 漲跌幅
   - 今成交量 / 成交金額

3. 報酬模式欄位：
   - 股票
   - 1週報酬
   - 總報酬（成立以來）
   - 殖利率

4. 基本模式欄位：
   - 股票
   - 資產規模
   - 內扣費用
   - 投資區域

5. 每個欄位都有 ▲▼ 排序。

6. 股票欄左邊加入類似附圖的紅 / 綠 K 棒提示。

7. 漲停 / 跌停亮燈：
   - 漲跌幅 >= 9.5%：股價紅底
   - 漲跌幅 <= -9.5%：股價綠底

8. live quotes job 同時補：
   - stock_quotes
   - etf_quotes

因此 ETF 列表的股價、漲跌幅、成交量會補進來。

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_list_ui_v9_patch.zip -d .

cat frontend/app/globals.css.addon.etf-v9.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend backend .github README_ETF_LIST_UI_V9_PATCH.md
git commit -m "Improve ETF list UI and quotes"
git push
```

## 補 ETF 股價

部署後到 GitHub：

```text
Actions → Update Live Quotes → Run workflow
```

跑完後 ETF 列表的股價、漲跌幅、成交量會更新。

如果 ETF 價格仍是 `-`，代表 Yahoo Finance 暫時沒有回傳該 ETF 代號。
