# Active ETF V11 App Style Rebuild

這包是 ETF List + ETF Detail 的大整理版，目標是讓畫面更接近你參考的 App。

## 這版主要改善

### ETF 列表
- 即時 / 報酬 / 基本 三模式
- ETF 行情不再靠 Yahoo，改用 Pocket ETF API
- price 為 0 時顯示 `-`，避免出現 0.00 / 0.00%
- 顯示 K 棒、股價、漲跌幅、成交量、成交金額
- 欄位都有排序 ▲▼

### ETF 詳情頁
重做 5 個 tab：

1. 總覽
   - 股價
   - 年化 / 成立以來報酬
   - 持股異動
   - 股價走勢圖
   - 基本資料

2. 即時
   - 最新股價
   - 漲跌
   - 漲跌幅
   - 成交量
   - 成交金額
   - 更新時間

3. 操作日報
   - 基金規模卡
   - 折溢價卡
   - 新增 / 刪除 / 加碼 / 減碼卡片
   - 異動表
   - 變動說明 popup

4. 成分股
   - 環圈圖
   - Top holdings legend
   - 持股市值 / 持股張數
   - 權重
   - 股價 / 漲跌幅

5. 折溢價
   - 折溢價柱狀圖
   - 股價 vs 淨值折線圖
   - 折溢價歷史表

### 後端
新增 / 強化：
- `backend/app/services/pocket_etf_market.py`
- `backend/app/jobs/update_etf_market.py`
- `.github/workflows/update-etf-market.yml`

會建立並更新：
- `etf_quotes`
- `etf_price_history`
- `etf_nav_history`
- `etf_basic_info`

## 套用方式

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_v11_app_style_rebuild.zip -d .

cat frontend/app/globals.css.addon.v11.css >> frontend/app/globals.css

cd frontend
npm run build
cd ..

git add frontend backend .github README_ACTIVE_ETF_V11_APP_STYLE_REBUILD.md
git commit -m "Rebuild ETF pages in app style"
git push
```

## 套用後一定要跑一次資料更新

到 GitHub：

```text
Actions → Update Pocket ETF Market Data → Run workflow
```

跑完後到 Supabase 查：

```sql
select etf_code, price, change_pct, volume, amount, nav, premium_pct, aum_billion, expense_ratio, updated_at
from etf_quotes
order by etf_code;

select count(*) from etf_price_history;
select count(*) from etf_nav_history;
select count(*) from etf_basic_info;
```

如果 `etf_price_history` 有資料，ETF 詳情頁的總覽圖表會開始出現。

## 注意

Pocket API 欄位名稱如果和目前解析不同，可能某些欄位仍會是 `-`。
但這版已把架構拆好，之後只要微調 `pocket_etf_market.py` 的欄位 mapping 就能補齊，不用再改整個前端。
