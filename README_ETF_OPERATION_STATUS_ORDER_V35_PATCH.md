# V35 ETF Operation Status Order Patch

這版修正 ETF 詳細頁「操作日報」表格排序。

當沒有單獨篩選狀態時，表格會先依照上方四個框框的順序排列：

```text
新增 → 刪除 → 加碼 → 減碼
```

同一個狀態裡面，仍會沿用目前選到的排序欄位，例如：
- 持股變動
- 變動幅度
- 目前權重
- 標的

所以預設會比較接近 App 的邏輯：先看新增、刪除，再看加碼、減碼。

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_operation_status_order_v35_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx README_ETF_OPERATION_STATUS_ORDER_V35_PATCH.md
git commit -m "Sort ETF operation rows by status order"
git push
```

部署完成後，到：

```text
/etf/00403A
```

操作日報的表格順序應該會變成：

```text
新增
刪除
加碼
減碼
```
