#!/usr/bin/env python3
from pathlib import Path

layout = Path("frontend/app/layout.tsx")
if not layout.exists():
    raise SystemExit("找不到 frontend/app/layout.tsx，請確認在 repo 根目錄執行")

text = layout.read_text(encoding="utf-8")

metadata = """export const metadata = {
  title: '主動式 ETF',
  description: '主動式 ETF 追蹤',
  applicationName: '主動式 ETF',
  manifest: '/manifest.json',
  icons: {
    icon: [
      { url: '/favicon.ico' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: [
      { url: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
    shortcut: ['/favicon.ico'],
  },
};

export const viewport = {
  themeColor: '#173B68',
};
"""

def replace_export_const_object(src: str, export_name: str, replacement: str):
    key = f"export const {export_name}"
    start = src.find(key)
    if start < 0:
        return src, False
    eq = src.find("=", start)
    if eq < 0:
        return src, False
    brace = src.find("{", eq)
    if brace < 0:
        return src, False
    depth = 0
    end = None
    in_str = None
    esc = False
    for i in range(brace, len(src)):
        ch = src[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in ('"', "'", '`'):
            in_str = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return src, False
    # include trailing semicolon and whitespace/newline immediately after object
    j = end
    while j < len(src) and src[j].isspace():
        j += 1
    if j < len(src) and src[j] == ";":
        j += 1
    while j < len(src) and src[j] in " \t\r\n":
        j += 1
    return src[:start] + replacement + src[j:], True

# Remove old viewport first to avoid duplicate export error
text, _ = replace_export_const_object(text, "viewport", "")
text, found = replace_export_const_object(text, "metadata", metadata)

if not found:
    # insert after last import block
    lines = text.splitlines(True)
    insert_at = 0
    for idx, line in enumerate(lines):
        if line.startswith("import ") or line.strip() == "":
            insert_at = idx + 1
        elif insert_at:
            break
    lines.insert(insert_at, "\n" + metadata + "\n")
    text = "".join(lines)

layout.write_text(text, encoding="utf-8")
print("OK: patched frontend/app/layout.tsx metadata/icons")
