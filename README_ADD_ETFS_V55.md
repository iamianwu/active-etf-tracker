# Add ETFs v55 Patch

新增下列主動式 ETF 到 `backend/app/config.py`，並同步更新手機 ETF 詳情頁左右切換順序 `ETF_NAV_CODES`：

- 00402A 主動安聯美國科技
- 00404A 主動聯博動能50
- 00405A 主動富邦台灣龍耀
- 00406A 主動中信台灣收益
- 00998A 主動復華金融股息
- 00980D 主動聯博投等入息
- 00981D 主動中信非投等債
- 00982D 主動富邦動態入息
- 00983D 主動富邦複合收益
- 00984D 主動聯博全球非投
- 00985D 主動貝萊德優投等
- 00986D 主動復華金融債息

執行：

```bash
python3 tools/add_active_etfs_v55.py
```

推上 GitHub 後，請到 GitHub Actions 手動執行 `Update ETF Data`，建議 `dt_range=120` 先把新 ETF 的持股資料補進 Supabase。
