# Signal Range Tabs V71 Minimal Patch

v70 造成 server-side exception，原因是直接覆寫首頁 page。

v71 採用最小修改：

- 不修改 `frontend/app/page.tsx`
- 保留目前首頁 `redirect('/signals')`
- 只修改：
  - `frontend/lib/api.ts`
  - `frontend/app/signals/page.tsx`
  - `frontend/app/signals/[type]/page.tsx`
  - `frontend/app/globals.css`

功能：

```text
即時 / 3日 / 5日 / 10日 / 20日
```

邏輯：

- 即時：最新持股日 vs 前一個持股日
- 3日：最新持股日 vs 3 個持股資料日前
- 5日：最新持股日 vs 5 個持股資料日前
- 10日：最新持股日 vs 10 個持股資料日前
- 20日：最新持股日 vs 20 個持股資料日前

測試網址：

```text
/signals
/signals?range=3
/signals?range=5
/signals?range=10
/signals?range=20
```
