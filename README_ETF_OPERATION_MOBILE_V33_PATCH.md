# V33 ETF Operation Mobile Layout Patch

這版主要修手機版 ETF 詳細頁的「操作日報」。

改善內容：

1. 手機版整體比例縮小，接近你參考圖，可以一屏看到更多內容。
2. 「新增 / 刪除 / 加碼 / 減碼」改成四格卡片樣式，像 App 圖 2。
3. 「共 N 檔異動」下方表格取消橫向大寬度，壓成手機單頁寬度。
4. 手機版操作日報表格欄位仍保留：
   - 標的
   - 狀態
   - 持股變動
   - 變動幅度
   - 目前權重
5. 表頭 sticky，往下滑時欄位標題會釘住。
6. 手機版隱藏「張」單位，讓表格更窄，但數值仍代表張數。

## 套用

```bash
cd ~/Downloads/pocket_etf_cloud_postgres_ready/pocket_etf_cloud

unzip -o ~/Downloads/active_etf_operation_mobile_v33_patch.zip -d .

cd frontend
npm run build
cd ..

git add frontend/components/EtfDetailClient.tsx README_ETF_OPERATION_MOBILE_V33_PATCH.md
git commit -m "Improve ETF operation mobile layout"
git push
```

部署完成後，到手機看：

```text
/etf/00991A
```

應該會比原本圖 1 更接近你想要的圖 2。
