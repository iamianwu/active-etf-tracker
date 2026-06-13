#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
layout_path = ROOT / "frontend/app/layout.tsx"
css_path = ROOT / "frontend/app/globals.css"

if not layout_path.exists():
    raise SystemExit("找不到 frontend/app/layout.tsx，請確認你在專案根目錄執行。")

if not css_path.exists():
    raise SystemExit("找不到 frontend/app/globals.css，請確認你在專案根目錄執行。")

layout = layout_path.read_text(encoding="utf-8")

# Ensure Link import exists
if "from 'next/link'" not in layout and 'from \"next/link\"' not in layout:
    layout = "import Link from 'next/link';\n" + layout

new_icons = (
    '<div className="top-icons header-icons-v62">'
    '<span className="header-icon-v62 header-icon-bell-v62" aria-label="通知" title="通知" />'
    '<Link href="/search" className="header-icon-link-v62" aria-label="搜尋" title="搜尋">'
    '<span className="header-icon-v62 header-icon-search-v62" />'
    '</Link>'
    '</div>'
)

changed = False

# Case 1: original simple layout
if "👤 🔍" in layout or "👤&nbsp;🔍" in layout:
    layout = layout.replace("<div>👤 🔍</div>", new_icons)
    layout = layout.replace("<div>👤&nbsp;🔍</div>", new_icons)
    changed = True

# Case 2: existing top-icons block
pattern_top_icons = re.compile(
    r'<div\s+className=(["\'])top-icons\1>.*?</div>',
    flags=re.DOTALL
)
if pattern_top_icons.search(layout):
    layout = pattern_top_icons.sub(new_icons, layout, count=1)
    changed = True

# Case 3: existing v62 block
pattern_v62_icons = re.compile(
    r'<div\s+className=(["\'])top-icons header-icons-v62\1>.*?</div>',
    flags=re.DOTALL
)
if pattern_v62_icons.search(layout):
    layout = pattern_v62_icons.sub(new_icons, layout, count=1)
    changed = True

# Case 4: replace remaining emoji icons
if "👤" in layout or "🔍" in layout:
    layout = re.sub(
        r'<span([^>]*)>\s*👤\s*</span>',
        r'<span className="header-icon-v62 header-icon-bell-v62" aria-label="通知" title="通知" />',
        layout
    )
    layout = re.sub(
        r'(<Link[^>]*href=(["\'])/search\2[^>]*>)\s*🔍\s*(</Link>)',
        r'\1<span className="header-icon-v62 header-icon-search-v62" />\3',
        layout
    )
    layout = layout.replace("👤", '<span className="header-icon-v62 header-icon-bell-v62" aria-label="通知" title="通知" />')
    layout = layout.replace("🔍", '<span className="header-icon-v62 header-icon-search-v62" />')
    changed = True

# Case 5: if there is a brand row with logo but no icon block was patched, insert after logo div
if not changed:
    pattern_logo = re.compile(r'(<div\s+className=(["\'])logo\2>.*?</div>)', flags=re.DOTALL)
    if pattern_logo.search(layout):
        layout = pattern_logo.sub(r'\1' + new_icons, layout, count=1)
        changed = True

if not changed:
    raise SystemExit(
        "沒有自動找到右上角 icon 區塊。請把 frontend/app/layout.tsx 的 header 片段貼給我，我再幫你精準修。"
    )

layout_path.write_text(layout, encoding="utf-8")

css = css_path.read_text(encoding="utf-8")
css_block = """
/* ===== v62 header icons: bell + search ===== */
.header-icons-v62,
.top-icons.header-icons-v62 {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 18px;
  flex: 0 0 auto;
}

.header-icon-link-v62 {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  text-decoration: none;
  color: inherit;
  -webkit-tap-highlight-color: transparent;
}

.header-icon-v62 {
  display: inline-block;
  width: 30px;
  height: 30px;
  background-color: #64748b;
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: 30px 30px;
  mask-size: 30px 30px;
  flex: 0 0 auto;
}

.header-icon-bell-v62 {
  -webkit-mask-image: url('/icons/header-bell.svg');
  mask-image: url('/icons/header-bell.svg');
}

.header-icon-search-v62 {
  -webkit-mask-image: url('/icons/header-search.svg');
  mask-image: url('/icons/header-search.svg');
}

.header-icon-link-v62:active .header-icon-v62,
.header-icon-v62:active {
  background-color: #173b68;
  transform: scale(0.96);
}

@media (max-width: 620px) {
  .header-icons-v62,
  .top-icons.header-icons-v62 {
    gap: 14px;
  }

  .header-icon-link-v62 {
    width: 30px;
    height: 30px;
  }

  .header-icon-v62 {
    width: 28px;
    height: 28px;
    -webkit-mask-size: 28px 28px;
    mask-size: 28px 28px;
  }
}
"""

if "v62 header icons" not in css:
    css += "\n" + css_block
else:
    css = re.sub(
        r'/\* ===== v62 header icons: bell \+ search ===== \*/.*?(?=\n/\* =====|\Z)',
        css_block.strip() + "\n",
        css,
        flags=re.DOTALL
    )

css_path.write_text(css, encoding="utf-8")

print("Done: 已更新右上角 icon：人頭 → 小鈴鐺，搜尋 → 你提供的新 search icon。")
