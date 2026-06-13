# Remove D-class ETFs V66

這版會把 D 類 ETF 從網站與更新清單移除：

```text
00980D
00981D
00982D
00983D
00984D
00985D
00986D
```

會修改：

- `backend/app/config.py`
  - 從 `ETF_CODES` 移除 D 類 ETF
  - 從 `ETF_NAMES` 移除 D 類 ETF 名稱
- 前端 `ETF_NAV_CODES` / 搜尋熱點 / 靜態清單中如有 D 類 ETF，也會移除
- workflow 裡若有 D 類 ETF 文字，也會清掉

## 重要

這只會改程式清單。  
如果 Supabase 裡已經有 D 類 ETF 的資料，還要手動刪掉，網站才不會從資料庫又撈出來。

請到 Supabase SQL Editor 跑：

```sql
do $$
declare
  t text;
begin
  foreach t in array array[
    'holdings',
    'etf_quotes',
    'etf_price_history',
    'etf_daily_quotes',
    'etf_history',
    'fund_quotes'
  ]
  loop
    if to_regclass('public.' || t) is not null then
      execute format(
        'delete from %I where etf_code in (''00980D'',''00981D'',''00982D'',''00983D'',''00984D'',''00985D'',''00986D'')',
        t
      );
    end if;
  end loop;
end $$;
```

如果只確定有這兩張表，也可以只跑：

```sql
delete from holdings
where etf_code in ('00980D','00981D','00982D','00983D','00984D','00985D','00986D');

delete from etf_quotes
where etf_code in ('00980D','00981D','00982D','00983D','00984D','00985D','00986D');
```

## 使用方式

```bash
python3 tools/remove_d_etfs_v66.py
```
