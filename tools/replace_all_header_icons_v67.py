#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
CSS = ROOT / "frontend/app/globals.css"

if not FRONTEND.exists():
    raise SystemExit("找不到 frontend，請在 repo 根目錄執行。")
if not CSS.exists():
    raise SystemExit("找不到 frontend/app/globals.css，請在 repo 根目錄執行。")

bell = '<span className="header-icon-v67 header-icon-bell-v67" aria-label="通知" title="通知" />'
search_a = '<a href="/search" className="header-icon-link-v67" aria-label="搜尋" title="搜尋"><span className="header-icon-v67 header-icon-search-v67" /></a>'
search_span = '<span className="header-icon-v67 header-icon-search-v67" />'

patched_files = []

# Patch every JSX/TSX file, because the header might not be in layout.tsx.
for path in list(FRONTEND.rglob("*.tsx")) + list(FRONTEND.rglob("*.jsx")):
    text = path.read_text(encoding="utf-8")
    original = text

    # Replace exact old pair first.
    text = text.replace("<div>👤 🔍</div>", f'<div className="top-icons header-icons-v67">{bell}{search_a}</div>')
    text = text.replace("<div>👤&nbsp;🔍</div>", f'<div className="top-icons header-icons-v67">{bell}{search_a}</div>')

    # Replace user emoji in span.
    text = re.sub(r'<span([^>]*)>\s*👤\s*</span>', bell, text)

    # Replace search emoji inside existing Link or a tag, keeping the original href wrapper.
    text = re.sub(
        r'(<Link\b[^>]*href=(["\'])/search\2[^>]*>)\s*🔍\s*(</Link>)',
        r'\1' + search_span + r'\3',
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r'(<a\b[^>]*href=(["\'])/search\2[^>]*>)\s*🔍\s*(</a>)',
        r'\1' + search_span + r'\3',
        text,
        flags=re.DOTALL,
    )

    # Bare emojis: replace user with bell, search with clickable anchor.
    text = text.replace("👤", bell)
    text = text.replace("🔍", search_a)

    # If a div now contains both icons but no flex class, try to upgrade any existing top-icons class.
    text = text.replace('className="top-icons"', 'className="top-icons header-icons-v67"')

    if text != original:
        path.write_text(text, encoding="utf-8")
        patched_files.append(str(path.relative_to(ROOT)))

# Patch CSS.
css = CSS.read_text(encoding="utf-8")
css_block = """
/* ===== v67 global header icons: bell + search ===== */
.header-icons-v67,
.top-icons.header-icons-v67 {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 18px !important;
  flex: 0 0 auto !important;
}

.header-icon-link-v67 {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 34px !important;
  height: 34px !important;
  text-decoration: none !important;
  -webkit-tap-highlight-color: transparent !important;
}

.header-icon-v67 {
  display: inline-block !important;
  width: 31px !important;
  height: 31px !important;
  background-color: #64748b !important;
  color: transparent !important;
  font-size: 0 !important;
  line-height: 0 !important;
  vertical-align: middle !important;
  -webkit-mask-repeat: no-repeat !important;
  mask-repeat: no-repeat !important;
  -webkit-mask-position: center !important;
  mask-position: center !important;
  -webkit-mask-size: 31px 31px !important;
  mask-size: 31px 31px !important;
  flex: 0 0 auto !important;
}

.header-icon-bell-v67 {
  -webkit-mask-image: url('/icons/header-bell.svg') !important;
  mask-image: url('/icons/header-bell.svg') !important;
}

.header-icon-search-v67 {
  -webkit-mask-image: url('/icons/header-search.svg') !important;
  mask-image: url('/icons/header-search.svg') !important;
}

.header-icon-link-v67:active .header-icon-v67,
.header-icon-v67:active {
  background-color: #173b68 !important;
  transform: scale(0.96);
}

@media (max-width: 620px) {
  .header-icons-v67,
  .top-icons.header-icons-v67 {
    gap: 14px !important;
  }

  .header-icon-link-v67 {
    width: 30px !important;
    height: 30px !important;
  }

  .header-icon-v67 {
    width: 28px !important;
    height: 28px !important;
    -webkit-mask-size: 28px 28px !important;
    mask-size: 28px 28px !important;
  }
}
"""
if "v67 global header icons" not in css:
    CSS.write_text(css + "\n" + css_block, encoding="utf-8")

# Final scan
remaining = []
for path in list(FRONTEND.rglob("*.tsx")) + list(FRONTEND.rglob("*.jsx")):
    text = path.read_text(encoding="utf-8")
    if "👤" in text or "🔍" in text:
        remaining.append(str(path.relative_to(ROOT)))

print("✅ v67 已完成全 frontend 掃描替換。")
print("已修改檔案：")
for p in patched_files:
    print(" -", p)
if not patched_files:
    print(" - 沒有找到可替換的 JSX/TSX 檔案，代表目前 repo 可能已經沒有舊 emoji。")

if remaining:
    print("\n⚠️ 仍有舊 emoji 的檔案：")
    for p in remaining:
        print(" -", p)
else:
    print("\nfrontend 內已找不到舊 emoji：👤 或 🔍")

print("\n請接著 git status / commit / push，並等 Vercel Ready。")
