# Header Icons V67 Global Replace

如果 v63 後網站仍顯示舊的 👤 / 🔍，代表 icon 不在 `layout.tsx`，而是在其他 component。

這版會掃整個 `frontend/**/*.tsx` / `frontend/**/*.jsx`，把：

- `👤` 改成小鈴鐺 SVG mask
- `🔍` 改成 search SVG mask，並連到 `/search`

執行：

```bash
python3 tools/replace_all_header_icons_v67.py
```

執行後它會列出已修改檔案，並確認 frontend 裡是否還有舊 emoji。
