# Signals Window Tabs V70 Force Home

v69 如果仍然看不到即時 / 3日 / 5日 / 10日 / 20日，代表首頁沒有吃到 `/signals/page.tsx` 的 re-export。

v70 會直接覆寫：

- `frontend/app/page.tsx`
- `frontend/app/signals/page.tsx`
- `frontend/app/signals/[type]/page.tsx`

讓首頁 `/` 和 `/signals` 都出現同一個區間切換。

測試：

```text
https://active-etf-tracker.vercel.app/?v=70
https://active-etf-tracker.vercel.app/?range=3&v=70
https://active-etf-tracker.vercel.app/?range=5&v=70
```
