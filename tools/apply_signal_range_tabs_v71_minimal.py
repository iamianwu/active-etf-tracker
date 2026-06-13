#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path.cwd()

api_path = ROOT / "frontend/lib/api.ts"
signals_page = ROOT / "frontend/app/signals/page.tsx"
signals_type_page = ROOT / "frontend/app/signals/[type]/page.tsx"
css_path = ROOT / "frontend/app/globals.css"

for p in [api_path, signals_page, signals_type_page, css_path]:
    if not p.exists():
        raise SystemExit(f"找不到 {p.relative_to(ROOT)}，請確認你在 repo 根目錄執行。")


def patch_api() -> None:
    api = api_path.read_text(encoding="utf-8")

    # 1. Add helper before getSignals only once.
    if "signalWindowPreviousDate_v71" not in api:
        helper = """
function signalWindowPreviousDate_v71(holdings: any[], etfCode: string, date: string, windowInput: any) {
  const windowDays = Math.max(1, Math.min(20, Number(windowInput || 1) || 1));
  const dates = Array.from(new Set(
    holdings
      .filter((h) => h.etf_code === etfCode)
      .map((h) => String(h.data_date))
      .filter((d) => d && d < String(date))
  )).sort();

  if (!dates.length) return null;
  const idx = Math.max(0, dates.length - windowDays);
  return dates[idx] || dates[0] || null;
}

"""
        if "\nasync function getSignals" not in api:
            raise SystemExit("找不到 async function getSignals，api.ts 沒有被修改。")
        api = api.replace("\nasync function getSignals", "\n" + helper + "async function getSignals", 1)

    # 2. Change getSignals signature.
    api = api.replace(
        "async function getSignals(signalType?: string | null) {",
        "async function getSignals(signalType?: string | null, signalRange?: string | number | null) {",
        1,
    )

    # 3. Add range variable after loadBaseData.
    target = "  const { holdings, stockQuoteMap } = await loadBaseData();"
    insert = target + "\n  const signalWindowDays = Math.max(1, Math.min(20, Number(signalRange || 1) || 1));"
    if "const signalWindowDays = Math.max(1, Math.min(20, Number(signalRange || 1) || 1));" not in api:
        if target not in api:
            raise SystemExit("找不到 loadBaseData 那行，api.ts 沒有被修改。")
        api = api.replace(target, insert, 1)

    # 4. Use window previous date in the for-loop. Keep 即時 = original previousDateForEtf.
    old = "    const prev = previousDateForEtf(holdings, etf, d);"
    new = "    const prev = signalWindowDays <= 1 ? previousDateForEtf(holdings, etf, d) : signalWindowPreviousDate_v71(holdings, etf, d, signalWindowDays);"
    if new not in api:
        if old not in api:
            raise SystemExit("找不到 previousDateForEtf 那行，api.ts 沒有被修改。")
        api = api.replace(old, new, 1)

    # 5. Pass range query to getSignals inside apiGet.
    # Support both quote styles and exact existing dispatch.
    replacements = [
        (
            'return getSignals(u.searchParams.get("type"));',
            'return getSignals(u.searchParams.get("type"), u.searchParams.get("range") || u.searchParams.get("window") || u.searchParams.get("days"));',
        ),
        (
            "return getSignals(u.searchParams.get('type'));",
            "return getSignals(u.searchParams.get('type'), u.searchParams.get('range') || u.searchParams.get('window') || u.searchParams.get('days'));",
        ),
    ]

    changed_dispatch = False
    for a, b in replacements:
        if a in api:
            api = api.replace(a, b)
            changed_dispatch = True

    # Fallback: if already replaced, ok. If not found, fail loudly so we do not silently deploy a no-op.
    if "getSignals(u.searchParams.get(\"type\"), u.searchParams.get(\"range\")" not in api and \
       "getSignals(u.searchParams.get('type'), u.searchParams.get('range')" not in api:
        if not changed_dispatch:
            raise SystemExit("找不到 apiGet 裡的 getSignals dispatch，api.ts 沒有被修改。")

    api_path.write_text(api, encoding="utf-8")


def add_tabs_component(text: str) -> str:
    if "SignalRangeTabs_v71" in text:
        return text

    component = """
const SIGNAL_RANGES_V71 = ['1', '3', '5', '10', '20'];

function cleanSignalRange_v71(raw: any) {
  const r = String(raw || '1');
  return SIGNAL_RANGES_V71.includes(r) ? r : '1';
}

function signalRangeHref_v71(range: string) {
  return range === '1' ? '/signals' : `/signals?range=${range}`;
}

function SignalRangeTabs_v71({ range }: { range: string }) {
  const items = [
    { value: '1', label: '即時' },
    { value: '3', label: '3日' },
    { value: '5', label: '5日' },
    { value: '10', label: '10日' },
    { value: '20', label: '20日' },
  ];

  return (
    <div className="signals-window-tabs-v71" aria-label="訊號區間">
      {items.map((item) => (
        <Link
          key={item.value}
          href={signalRangeHref_v71(item.value)}
          className={range === item.value ? 'active' : ''}
        >
          {item.label}
        </Link>
      ))}
    </div>
  );
}

"""
    # Put after imports. Need Link import already exists in this file.
    m = list(re.finditer(r"^import .+?;\n", text, flags=re.M))
    if not m:
        raise SystemExit("signals/page.tsx 找不到 import 區塊。")
    pos = m[-1].end()
    return text[:pos] + "\n" + component + text[pos:]


def patch_signals_page() -> None:
    text = signals_page.read_text(encoding="utf-8")
    text = add_tabs_component(text)

    # Add searchParams to default function.
    if "cleanSignalRange_v71(searchParams" not in text:
        text = re.sub(
            r"export\s+default\s+async\s+function\s+SignalsPage\s*\(\s*\)\s*\{",
            "export default async function SignalsPage({ searchParams }: { searchParams?: { range?: string; window?: string; days?: string } }) {",
            text,
            count=1,
        )

        text = re.sub(
            r"export\s+default\s+async\s+function\s+Page\s*\(\s*\)\s*\{",
            "export default async function Page({ searchParams }: { searchParams?: { range?: string; window?: string; days?: string } }) {",
            text,
            count=1,
        )

        marker = "const data = await apiGet('/signals');"
        if marker in text:
            replacement = "const range = cleanSignalRange_v71(searchParams?.range || searchParams?.window || searchParams?.days);\n  const data = await apiGet(range === '1' ? '/signals' : `/signals?range=${range}`);"
            text = text.replace(marker, replacement, 1)
        else:
            marker2 = 'const data = await apiGet("/signals");'
            if marker2 in text:
                replacement = 'const range = cleanSignalRange_v71(searchParams?.range || searchParams?.window || searchParams?.days);\n  const data = await apiGet(range === \'1\' ? \'/signals\' : `/signals?range=${range}`);'
                text = text.replace(marker2, replacement, 1)
            else:
                raise SystemExit("signals/page.tsx 找不到 const data = await apiGet('/signals');")

    # Insert tabs after main opening.
    if "<SignalRangeTabs_v71 range={range} />" not in text:
        text = re.sub(
            r'(<main\s+className="[^"]*signals-v3-page[^"]*"[^>]*>)',
            r'\1\n      <SignalRangeTabs_v71 range={range} />',
            text,
            count=1,
        )

    if "<SignalRangeTabs_v71 range={range} />" not in text:
        raise SystemExit("signals/page.tsx 沒有成功插入 SignalRangeTabs_v71。")

    signals_page.write_text(text, encoding="utf-8")


def patch_signals_type_page() -> None:
    text = signals_type_page.read_text(encoding="utf-8")

    # Add range parsing helper if not exists.
    if "cleanSignalRange_v71" not in text:
        helper = """
const SIGNAL_RANGES_V71 = ['1', '3', '5', '10', '20'];

function cleanSignalRange_v71(raw: any) {
  const r = String(raw || '1');
  return SIGNAL_RANGES_V71.includes(r) ? r : '1';
}

function signalBackHref_v71(range: string) {
  return range === '1' ? '/signals' : `/signals?range=${range}`;
}

"""
        m = list(re.finditer(r"^import .+?;\n", text, flags=re.M))
        if m:
            text = text[:m[-1].end()] + "\n" + helper + text[m[-1].end():]
        else:
            text = helper + text

    # Add searchParams to function signature if it only has params.
    if "searchParams?: { range?: string; window?: string; days?: string }" not in text:
        text = text.replace(
            "}: { params: { type: string } }) {",
            "}: { params: { type: string }; searchParams?: { range?: string; window?: string; days?: string } }) {",
        )

    # Add range and api URL.
    if "const range = cleanSignalRange_v71" not in text:
        # Insert before apiGet line.
        text = re.sub(
            r"(const\s+data\s*=\s*await\s+apiGet\()(`?/signals\?type=\$\{params\.type\}`?|['\"]/signals\?type=.*?['\"])(\);)",
            r"const range = cleanSignalRange_v71(searchParams?.range || searchParams?.window || searchParams?.days);\n  \1range === '1' ? `/signals?type=${params.type}` : `/signals?type=${params.type}&range=${range}`\3",
            text,
            count=1,
        )

    # Back link preserves range.
    text = re.sub(
        r'href=(["\'])/signals\1',
        r'href={signalBackHref_v71(range)}',
        text,
    )

    signals_type_page.write_text(text, encoding="utf-8")


def patch_css() -> None:
    css = css_path.read_text(encoding="utf-8")
    block = """
/* ===== v71 signal range tabs: 即時 / 3日 / 5日 / 10日 / 20日 ===== */
.signals-window-tabs-v71 {
  display: inline-grid;
  grid-template-columns: repeat(5, minmax(70px, 1fr));
  gap: 6px;
  padding: 6px;
  margin: 0 0 18px;
  background: #eef2f7;
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.16);
}

.signals-window-tabs-v71 a {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 16px;
  border-radius: 999px;
  color: #64748b;
  text-decoration: none;
  font-weight: 900;
  font-size: 18px;
  letter-spacing: 0.01em;
  white-space: nowrap;
  -webkit-tap-highlight-color: transparent;
}

.signals-window-tabs-v71 a.active {
  background: #fff;
  color: #3b82f6;
  box-shadow:
    0 2px 8px rgba(15, 23, 42, 0.10),
    inset 0 0 0 1px rgba(203, 213, 225, 0.76);
}

@media (max-width: 720px) {
  .signals-window-tabs-v71 {
    width: 100%;
    grid-template-columns: repeat(5, 1fr);
    gap: 4px;
    padding: 5px;
    margin: 0 0 14px;
  }

  .signals-window-tabs-v71 a {
    min-height: 40px;
    padding: 0;
    font-size: 16px;
  }
}
"""
    if "v71 signal range tabs" not in css:
        css += "\n" + block
    css_path.write_text(css, encoding="utf-8")


def main() -> None:
    patch_api()
    patch_signals_page()
    patch_signals_type_page()
    patch_css()

    print("✅ v71 已用最小修改加入今日訊號區間切換。")
    print("這版不會修改 frontend/app/page.tsx，所以首頁仍維持 redirect('/signals')。")
    print("請接著 npm run build，成功後再 commit / push。")


if __name__ == "__main__":
    main()
