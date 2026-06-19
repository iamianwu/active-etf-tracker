# V98 Fix Stock Operation Reference

修正個股頁 client-side exception：

`ReferenceError: StockRecentOperationRecords is not defined`

原因是 JSX 還在呼叫不存在的 `StockRecentOperationRecords`，實際 component 是 `StockRecentOperationPanel`。
