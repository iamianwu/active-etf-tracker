# Header icons v63 force patch

這版比 v62 更強制，會直接把 layout.tsx 裡的舊 emoji：

- 👤 改成 bell SVG mask
- 🔍 改成 search SVG mask

並加入 CSS：

- `.header-icon-bell-v63`
- `.header-icon-search-v63`

使用方式：

```bash
python3 tools/apply_header_icons_v63_force.py
```

執行後它會印出 layout.tsx 是否仍然含有舊 emoji。
