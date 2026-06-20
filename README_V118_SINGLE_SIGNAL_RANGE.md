# V118 Single Signal Range

修正：

1. 首頁 `/` 與 `/signals` 統一由 `SignalsClient` 顯示「訊號區間」。
2. 移除 page.tsx 端重複的訊號區間，避免點 5 日後出現兩組。
3. RangeSwitch 會依目前路徑產生連結，避免 `/` 與 `/signals` 版面來源不一致。
4. 加保險 CSS，避免舊版 range 元件殘留時重複顯示。

套用後請 commit：

```bash
git add frontend/app/page.tsx frontend/app/signals/page.tsx frontend/components/SignalsClient.tsx frontend/app/globals.css tools/apply_v118_single_signal_range.py README_V118_SINGLE_SIGNAL_RANGE.md
git commit -m "Fix duplicated signal range tabs v118"
git push origin main
```
