#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
component_path = ROOT / "frontend/components/SignalRangeTabsV75.tsx"
layout_path = ROOT / "frontend/app/signals/layout.tsx"
page_path = ROOT / "frontend/app/signals/page.tsx"
type_page_path = ROOT / "frontend/app/signals/[type]/page.tsx"
css_path = ROOT / "frontend/app/globals.css"

if not (ROOT / "frontend").exists():
    raise SystemExit("找不到 frontend，請在 repo 根目錄執行。")

component_code = """'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';

const OPTIONS = [
  { label: '今日', days: '1' },
  { label: '5日', days: '5' },
  { label: '10日', days: '10' },
  { label: '20日', days: '20' },
];

export default function SignalRangeTabsV75() {
  const pathname = usePathname() || '/signals';
  const searchParams = useSearchParams();

  const activeDays =
    searchParams.get('days') ||
    searchParams.get('rangeDays') ||
    searchParams.get('signalRangeDays') ||
    '1';

  const makeHref = (days: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('days', days);
    params.delete('rangeDays');
    params.delete('signalRangeDays');
    return `${pathname}?${params.toString()}`;
  };

  return (
    <div className="signal-range-wrap-v75">
      <div className="signal-range-title-v75">訊號區間</div>
      <div className="signal-range-tabs-v75" aria-label="今日訊號區間切換">
        {OPTIONS.map((opt) => {
          const active = String(activeDays) === opt.days;
          return (
            <Link
              key={opt.days}
              href={makeHref(opt.days)}
              className={`signal-range-tab-v75 ${active ? 'active' : ''}`}
            >
              {opt.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
"""

layout_code = """import SignalRangeTabsV75 from '@/components/SignalRangeTabsV75';

export default function SignalsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <SignalRangeTabsV75 />
      {children}
    </>
  );
}
"""

component_path.parent.mkdir(parents=True, exist_ok=True)
component_path.write_text(component_code, encoding="utf-8")

# Add /signals layout. If it already exists, inject component safely.
if layout_path.exists():
    text = layout_path.read_text(encoding="utf-8")
    if "SignalRangeTabsV75" not in text:
        text = "import SignalRangeTabsV75 from '@/components/SignalRangeTabsV75';\n" + text
        text = text.replace("{children}", "<SignalRangeTabsV75 />\n      {children}", 1)
        layout_path.write_text(text, encoding="utf-8")
else:
    layout_path.write_text(layout_code, encoding="utf-8")

page_code = """import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

const VALID_SIGNAL_DAYS = [1, 5, 10, 20];

function normalizeSignalDays(searchParams?: { days?: string; rangeDays?: string; signalRangeDays?: string }) {
  const raw =
    searchParams?.days ||
    searchParams?.rangeDays ||
    searchParams?.signalRangeDays ||
    '1';

  const n = Number(raw);
  return VALID_SIGNAL_DAYS.includes(n) ? n : 1;
}

export default async function SignalsPage({
  searchParams,
}: {
  searchParams?: { days?: string; rangeDays?: string; signalRangeDays?: string };
}) {
  const days = normalizeSignalDays(searchParams);
  const data = await apiGet(`/signals?days=${days}`);

  return (
    <SignalsClient
      data={{
        ...data,
        rangeDays: days,
        signalRangeDays: days,
      }}
    />
  );
}
"""

if page_path.exists():
    page_path.write_text(page_code, encoding="utf-8")

type_page_code = """import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

const VALID_SIGNAL_DAYS = [1, 5, 10, 20];

function normalizeSignalDays(searchParams?: { days?: string; rangeDays?: string; signalRangeDays?: string }) {
  const raw =
    searchParams?.days ||
    searchParams?.rangeDays ||
    searchParams?.signalRangeDays ||
    '1';

  const n = Number(raw);
  return VALID_SIGNAL_DAYS.includes(n) ? n : 1;
}

export default async function SignalTypePage({
  params,
  searchParams,
}: {
  params: { type: string };
  searchParams?: { days?: string; rangeDays?: string; signalRangeDays?: string };
}) {
  const days = normalizeSignalDays(searchParams);
  const type = params.type;
  const data = await apiGet(`/signals?type=${type}&days=${days}`);

  return (
    <SignalsClient
      data={{
        ...data,
        activeType: type,
        selectedType: type,
        rangeDays: days,
        signalRangeDays: days,
      }}
    />
  );
}
"""

if type_page_path.exists():
    type_page_path.write_text(type_page_code, encoding="utf-8")

css_block = """
/* ===== v75 visible signal range tabs ===== */
.signal-range-wrap-v75 {
  width: min(100%, 1180px);
  margin: 22px auto 0;
  padding: 0 24px;
  box-sizing: border-box;
}

.signal-range-title-v75 {
  margin: 0 0 10px;
  color: #7b8492;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.signal-range-tabs-v75 {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px;
  border-radius: 999px;
  background: #eef2f7;
  border: 1px solid #e3e8ef;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
}

.signal-range-tab-v75 {
  min-width: 86px;
  padding: 12px 18px;
  border-radius: 999px;
  text-align: center;
  color: #64748b;
  font-size: 20px;
  font-weight: 900;
  text-decoration: none;
  line-height: 1;
  -webkit-tap-highlight-color: transparent;
}

.signal-range-tab-v75.active {
  color: #2f6fcf;
  background: #ffffff;
  box-shadow: 0 3px 10px rgba(42, 96, 180, 0.16);
}

.signal-range-tab-v75:active {
  transform: scale(0.98);
}

@media (max-width: 620px) {
  .signal-range-wrap-v75 {
    margin: 14px auto 0;
    padding: 0 16px;
  }

  .signal-range-title-v75 {
    font-size: 16px;
    margin-bottom: 8px;
  }

  .signal-range-tabs-v75 {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    width: 100%;
    gap: 6px;
    padding: 6px;
  }

  .signal-range-tab-v75 {
    min-width: 0;
    padding: 11px 0;
    font-size: 17px;
  }
}
"""

if css_path.exists():
    css = css_path.read_text(encoding="utf-8")
    if "v75 visible signal range tabs" not in css:
        css += "\n" + css_block
    css_path.write_text(css, encoding="utf-8")

print("✅ v75 已強制加入 今日｜5日｜10日｜20日 訊號區間切換。")
print("已建立/更新：")
print(" - frontend/components/SignalRangeTabsV75.tsx")
print(" - frontend/app/signals/layout.tsx")
print(" - frontend/app/signals/page.tsx")
print(" - frontend/app/signals/[type]/page.tsx")
print(" - frontend/app/globals.css")
print("\n請接著 npm run build，然後 commit / push。")
