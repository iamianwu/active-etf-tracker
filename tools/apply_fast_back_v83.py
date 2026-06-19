#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()

TARGETS = [
    ROOT / "frontend/components/EtfDetailClient.tsx",
    ROOT / "frontend/components/StockDetailClient.tsx",
]

def ensure_use_router_import(text: str) -> str:
    if "useRouter" in text and "next/navigation" in text:
        return text

    m = re.search(r'import\s+\{([^}]+)\}\s+from\s+[\'"]next/navigation[\'"];?', text)
    if m:
        names = [x.strip() for x in m.group(1).split(",")]
        if "useRouter" not in names:
            names.append("useRouter")
        return text[:m.start()] + f"import {{ {', '.join(names)} }} from 'next/navigation';" + text[m.end():]

    if text.startswith("'use client';"):
        return text.replace("'use client';", "'use client';\n\nimport { useRouter } from 'next/navigation';", 1)
    if text.startswith('"use client";'):
        return text.replace('"use client";', '"use client";\n\nimport { useRouter } from \'next/navigation\';', 1)

    return "import { useRouter } from 'next/navigation';\n" + text


def insert_fast_back_helper(text: str, component_name: str) -> str:
    if "handleFastBackV83" in text:
        return text

    pattern = re.compile(rf'(export\s+default\s+function\s+{re.escape(component_name)}\s*\([^)]*\)\s*\{{)')
    m = pattern.search(text)

    if not m:
        pattern = re.compile(rf'(function\s+{re.escape(component_name)}\s*\([^)]*\)\s*\{{)')
        m = pattern.search(text)

    if not m:
        print(f"⚠️ 找不到 {component_name} function，略過 helper 插入")
        return text

    helper = '''

  const routerV83 = useRouter();

  function handleFastBackV83(e?: any) {
    if (e?.preventDefault) e.preventDefault();

    if (typeof window !== 'undefined') {
      const ref = document.referrer || '';
      const sameSiteRef = ref.includes(window.location.host);

      // 最快：回到瀏覽器上一頁，不重新 push 到 /signals /holdings /etfs。
      // 這樣從今日訊號、資金持股、ETF列表點進來，再按左上角 <，通常會直接回到原頁與原捲動位置。
      if (window.history.length > 1 && sameSiteRef) {
        window.history.back();
        return;
      }

      const params = new URLSearchParams(window.location.search);
      const from = params.get('from') || params.get('src') || params.get('source') || '';

      if (from === 'signals' || from === 'signal') {
        routerV83.push('/signals');
        return;
      }
      if (from === 'holdings' || from === 'funds') {
        routerV83.push('/holdings');
        return;
      }
      if (from === 'search') {
        routerV83.push('/search');
        return;
      }
    }

    routerV83.push('/etfs');
  }
'''
    return text[:m.end()] + helper + text[m.end():]


def add_onclick_to_back_links(text: str) -> tuple[str, int]:
    count = 0

    def repl_tag(m):
        nonlocal count
        tag = m.group(0)
        if "handleFastBackV83" in tag:
            return tag
        if re.search(r'className=\{?["`][^"`}]*(back|return|prev|arrow-left|left-arrow)[^"`}]*["`]\}?', tag, re.I):
            count += 1
            return tag[:-1] + " onClick={handleFastBackV83}>"
        if re.search(r'href=\{?(backHref|returnHref|prevHref|sourceHref|fallbackHref)\}?', tag):
            count += 1
            return tag[:-1] + " onClick={handleFastBackV83}>"
        return tag

    text = re.sub(r'<(?:Link|a)\b[^>]*>', repl_tag, text)

    replacements = [
        ("router.push(backHref)", "handleFastBackV83()"),
        ("router.replace(backHref)", "handleFastBackV83()"),
        ("router.push(returnHref)", "handleFastBackV83()"),
        ("router.replace(returnHref)", "handleFastBackV83()"),
        ("router.push(prevHref)", "handleFastBackV83()"),
        ("router.replace(prevHref)", "handleFastBackV83()"),
        ("router.push(sourceHref)", "handleFastBackV83()"),
        ("router.replace(sourceHref)", "handleFastBackV83()"),
        ("router.push('/etfs')", "handleFastBackV83()"),
        ('router.push("/etfs")', "handleFastBackV83()"),
    ]
    for old, new in replacements:
        if old in text:
            text = text.replace(old, new)
            count += 1

    if count == 0:
        pattern = re.compile(r'(<(?:button|Link|a)\b(?![^>]*handleFastBackV83)[^>]*>)(\s*(?:‹|&lt;|←|<|◀|ChevronLeft)[\s\S]{0,120}</(?:button|Link|a)>)')
        def repl_arrow(m):
            nonlocal count
            count += 1
            first = m.group(1)
            if "onClick=" in first:
                first = re.sub(r'onClick=\{[^}]*\}', 'onClick={handleFastBackV83}', first, count=1)
                return first + m.group(2)
            return first[:-1] + " onClick={handleFastBackV83}>" + m.group(2)
        text = pattern.sub(repl_arrow, text, count=1)

    return text, count


for path in TARGETS:
    if not path.exists():
        print(f"⚠️ 找不到 {path}，略過")
        continue

    text = path.read_text(encoding="utf-8")

    if "'use client'" in text or '"use client"' in text:
        component_name = path.stem
        text = ensure_use_router_import(text)
        text = insert_fast_back_helper(text, component_name)
        text, c = add_onclick_to_back_links(text)

        path.write_text(text, encoding="utf-8")
        print(f"✅ {path}: 已套用 fast back，替換/掛載 {c} 個返回入口")
    else:
        print(f"⚠️ {path} 不是 client component，略過")

print("")
print("請接著執行：cd frontend && npm run build")
print("如果 build 成功，再 git add / commit / push。")
