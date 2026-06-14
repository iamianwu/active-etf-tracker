# Fix signalRangeDays V74

修復錯誤：

```text
ReferenceError: signalRangeDays is not defined
```

原因：v73 的今日訊號區間切換 patch 裡，某處使用了 `signalRangeDays`，但 server-side render 時沒有宣告這個變數。

執行：

```bash
python3 tools/fix_signal_range_days_v74.py
```

它會優先在 `frontend/lib/api.ts` 的 `apiGet(path)` function 裡補上安全的：

```ts
const signalRangeDays = ...
```

讓 `/signals` 和 `/signals/[type]` 都不會因為 undefined 直接 500。
