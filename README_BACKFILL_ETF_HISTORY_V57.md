# v57 Backfill ETF History Batches

這版新增一個專門回補歷史資料的 GitHub Actions workflow：

- `.github/workflows/backfill-etf-history-batches.yml`
- `backend/app/jobs/backfill_selected_etfs.py`

用途：避免 `DT_RANGE=9999` 一次跑 34 檔 ETF 導致 GitHub Actions timeout / canceled。

## 建議設定

到 GitHub Actions 手動執行：

`Backfill ETF History Batches`

輸入：

- `dt_range`: `9999`
- `batch_size`: `2`
- `sleep_sec`: `0.8`
- `update_quotes`: `true`

這會把 ETF 分成多個 batch，每個 job 只跑 2 檔，且最多同時跑 2 個 jobs。

若還是太慢或 Pocket 卡住，改成：

- `batch_size`: `1`

## 為什麼不要用原本 Update ETF Data + DT_RANGE=9999？

原本 workflow 會一次跑全部 ETF。現在 ETF 已經增加到 34 檔，其中 00400A、00401A 歷史資料非常多，所以跑到第 5 檔附近就容易被 GitHub Actions 取消。

這個 v57 workflow 是專門給完整回補用的。日常更新仍可用原本 `Update ETF Data`，建議 `dt_range=1` 或 `120`。
