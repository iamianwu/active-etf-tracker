# V84 App-like Speed Patch

讓切換頁面比較像 app 的第一層優化：

1. 預抓主要路由
   - `/signals`
   - `/holdings`
   - `/etfs`
   - `/search`

2. 加入 60 秒頁面快取
   - 移除 root layout 的 `force-dynamic` / `revalidate = 0`
   - 主要頁面加入 `export const revalidate = 60`
   - 同一頁 60 秒內不會每次都重新跑完整 Supabase 查詢

3. 加入 loading skeleton
   - 切換時會立即有畫面，不會白等

注意：
- 這是「速度體感」改善。
- 真正做到 native app 感，要下一步做瀏覽器資料快取/SWR：舊資料秒開，背景更新。
