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

# Ensure Link import exists.
if "from 'next/link'" not in layout and 'from "next/link"' not in layout:
    layout = "import Link from 'next/link';\n" + layout

bell = '<span className="header-icon-v63 header-icon-bell-v63" aria-label="通知" title="通知" />'
search_inner = '<span className="header-icon-v63 header-icon-search-v63" />'
search_link = '<Link href="/search" className="header-icon-link-v63" aria-label="搜尋" title="搜尋">' + search_inner + '</Link>'

# 1) Replace the exact emoji pair if it exists.
layout = layout.replace("<div>👤 🔍</div>", '<div className="top-icons header-icons-v63">' + bell + search_link + "</div>")
layout = layout.replace("<div>👤&nbsp;🔍</div>", '<div className="top-icons header-icons-v63">' + bell + search_link + "</div>")

# 2) Replace simple span emoji blocks.
layout = re.sub(r'<span[^>]*>\s*👤\s*</span>', bell, layout)
layout = re.sub(r'<span[^>]*>\s*🔍\s*</span>', search_inner, layout)

# 3) Replace search emoji inside Link href="/search".
layout = re.sub(
    r'(<Link\b[^>]*href=(["\'])/search\2[^>]*>)\s*🔍\s*(</Link>)',
    r'\1' + search_inner + r'\3',
    layout,
    flags=re.DOTALL
)

# 4) Replace bare remaining emojis.
layout = layout.replace("👤", bell)
layout = layout.replace("🔍", search_link)

# 5) If header still has old top-icons class without our v63 class, upgrade wrapper class.
layout = layout.replace('className="top-icons"', 'className="top-icons header-icons-v63"')

# 6) If no v63 wrapper exists but the two icons now exist close together, wrap likely simple div.
# Keep this conservative; most layouts already have top-icons.
if "header-icons-v63" not in layout and "header-icon-bell-v63" in layout:
    layout = re.sub(
        r'<div([^>]*)>\s*(' + re.escape(bell) + r')\s*(' + re.escape(search_link) + r')\s*</div>',
        r'<div className="top-icons header-icons-v63">\2\3</div>',
        layout,
        count=1
    )

layout_path.write_text(layout, encoding="utf-8")

css = css_path.read_text(encoding="utf-8")
css_block = """
/* ===== v63 force header icons: bell + search ===== */
.header-icons-v63,
.top-icons.header-icons-v63 {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 18px !important;
  flex: 0 0 auto !important;
}

.header-icon-link-v63 {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 34px !important;
  height: 34px !important;
  text-decoration: none !important;
  -webkit-tap-highlight-color: transparent !important;
}

.header-icon-v63 {
  display: inline-block !important;
  width: 31px !important;
  height: 31px !important;
  background-color: #64748b !important;
  color: transparent !important;
  font-size: 0 !important;
  line-height: 0 !important;
  -webkit-mask-repeat: no-repeat !important;
  mask-repeat: no-repeat !important;
  -webkit-mask-position: center !important;
  mask-position: center !important;
  -webkit-mask-size: 31px 31px !important;
  mask-size: 31px 31px !important;
  flex: 0 0 auto !important;
}

.header-icon-bell-v63 {
  -webkit-mask-image: url('/icons/header-bell.svg') !important;
  mask-image: url('/icons/header-bell.svg') !important;
}

.header-icon-search-v63 {
  -webkit-mask-image: url('/icons/header-search.svg') !important;
  mask-image: url('/icons/header-search.svg') !important;
}

.header-icon-link-v63:active .header-icon-v63,
.header-icon-v63:active {
  background-color: #173b68 !important;
  transform: scale(0.96);
}

@media (max-width: 620px) {
  .header-icons-v63,
  .top-icons.header-icons-v63 {
    gap: 14px !important;
  }

  .header-icon-link-v63 {
    width: 30px !important;
    height: 30px !important;
  }

  .header-icon-v63 {
    width: 28px !important;
    height: 28px !important;
    -webkit-mask-size: 28px 28px !important;
    mask-size: 28px 28px !important;
  }
}
"""

if "v63 force header icons" not in css:
    css += "\n" + css_block

css_path.write_text(css, encoding="utf-8")

# Verify
layout2 = layout_path.read_text(encoding="utf-8")
remaining = []
if "👤" in layout2:
    remaining.append("👤")
if "🔍" in layout2:
    remaining.append("🔍")

print("已套用 v63 header icons。")
print("layout.tsx 是否仍有舊 emoji：", "有 " + ",".join(remaining) if remaining else "沒有")
print("請接著 git status / commit / push。")
