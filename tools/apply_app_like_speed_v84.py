#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
frontend = ROOT / "frontend"
if not frontend.exists():
    raise SystemExit("找不到 frontend 目錄，請確認你在 repo 根目錄執行。")

components = frontend / "components"
components.mkdir(parents=True, exist_ok=True)

(components / "RoutePrefetcherV84.tsx").write_text("""'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

const CORE_ROUTES = ['/signals', '/holdings', '/etfs', '/search'];

export default function RoutePrefetcherV84() {
  const router = useRouter();

  useEffect(() => {
    const prefetchAll = () => {
      for (const route of CORE_ROUTES) {
        try {
          router.prefetch(route);
        } catch {}
      }
    };

    const timer = window.setTimeout(prefetchAll, 300);
    const onVisible = () => {
      if (document.visibilityState === 'visible') prefetchAll();
    };

    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [router]);

  return null;
}
""", encoding="utf-8")

layout = frontend / "app/layout.tsx"
if layout.exists():
    text = layout.read_text(encoding="utf-8")
    text = re.sub(r"export\s+const\s+dynamic\s*=\s*['\"]force-dynamic['\"]\s*;?\n?", "", text)
    text = re.sub(r"export\s+const\s+revalidate\s*=\s*0\s*;?\n?", "", text)

    if "RoutePrefetcherV84" not in text:
        lines = text.splitlines()
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("import "):
                insert_at = i + 1
        lines.insert(insert_at, "import RoutePrefetcherV84 from '@/components/RoutePrefetcherV84';")
        text = "\n".join(lines) + "\n"

    if "<RoutePrefetcherV84 />" not in text:
        text = re.sub(r"(<body[^>]*>)", r"\1\n        <RoutePrefetcherV84 />", text, count=1)

    layout.write_text(text, encoding="utf-8")
    print("✅ layout 已加入 route prefetcher，並移除 force-dynamic / revalidate 0")

page_files = [
    frontend / "app/page.tsx",
    frontend / "app/signals/page.tsx",
    frontend / "app/signals/[type]/page.tsx",
    frontend / "app/holdings/page.tsx",
    frontend / "app/etfs/page.tsx",
    frontend / "app/etf/[code]/page.tsx",
    frontend / "app/stock/[code]/page.tsx",
]

changed = []
for path in page_files:
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("'use client'") or text.lstrip().startswith('"use client"'):
        continue

    text = re.sub(r"export\s+const\s+dynamic\s*=\s*['\"]force-dynamic['\"]\s*;?\n?", "", text)
    text = re.sub(r"export\s+const\s+revalidate\s*=\s*0\s*;?\n?", "", text)

    if "export const revalidate" not in text:
        text = "export const revalidate = 60;\n\n" + text

    path.write_text(text, encoding="utf-8")
    changed.append(str(path.relative_to(ROOT)))

print("✅ 已替主要頁面加入 60 秒快取：")
for x in changed:
    print(" -", x)

(frontend / "app/loading.tsx").write_text("""export default function Loading() {
  return (
    <main className="page route-loading-v84">
      <div className="loading-line-v84 w60" />
      <div className="loading-card-v84" />
      <div className="loading-card-v84" />
      <div className="loading-line-v84 w40" />
      <div className="loading-table-v84">
        <div />
        <div />
        <div />
        <div />
      </div>
    </main>
  );
}
""", encoding="utf-8")

css = frontend / "app/globals.css"
if css.exists():
    c = css.read_text(encoding="utf-8")
    block = """
/* ===== v84 app-like navigation loading ===== */
.route-loading-v84 { padding-top: 24px; }

.loading-line-v84,
.loading-card-v84,
.loading-table-v84 div {
  background: linear-gradient(90deg, #f1f5f9 0%, #e5eaf2 45%, #f1f5f9 100%);
  background-size: 220% 100%;
  animation: shimmer-v84 1.1s ease-in-out infinite;
}

.loading-line-v84 {
  height: 34px;
  border-radius: 12px;
  margin: 18px 0;
}

.loading-line-v84.w60 { width: 60%; }
.loading-line-v84.w40 { width: 40%; }

.loading-card-v84 {
  height: 118px;
  border-radius: 18px;
  margin: 14px 0;
}

.loading-table-v84 {
  margin-top: 20px;
  display: grid;
  gap: 10px;
}

.loading-table-v84 div {
  height: 62px;
  border-radius: 12px;
}

@keyframes shimmer-v84 {
  0% { background-position: 140% 0; }
  100% { background-position: -140% 0; }
}
"""
    if "route-loading-v84" not in c:
        css.write_text(c + "\n" + block, encoding="utf-8")
        print("✅ 已加入 loading skeleton CSS")

print("")
print("v84 完成。接著：cd frontend && npm run build")
