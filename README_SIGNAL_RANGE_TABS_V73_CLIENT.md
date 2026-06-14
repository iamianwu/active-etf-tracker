# v73 今日訊號區間切換

v72 失敗原因：目前 `SignalsClient.tsx` 的 main class 是：

```tsx
<main className="page signals-v7-page">
```

v73 已改用正確位置。

新增：

```text
即時 / 3日 / 5日 / 10日 / 20日
```

注意：務必先 `npm run build` 成功再 commit / push。
