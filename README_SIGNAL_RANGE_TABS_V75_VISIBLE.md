# Signal Range Tabs V75 Visible

用途：強制讓 `/signals` 與 `/signals/[type]` 顯示：

```text
今日｜5日｜10日｜20日
```

v73/v74 已經修過資料邏輯與 undefined 問題，但畫面上沒有看到 tabs。  
v75 會把 tabs 放在 `/signals/layout.tsx`，因此只要進入今日訊號頁就一定會顯示。

同時會把：

```text
/signals?days=5
/signals?days=10
/signals?days=20
```

傳進 `apiGet()`，讓後端/前端資料邏輯可以依 days 切換。
