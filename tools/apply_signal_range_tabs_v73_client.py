#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path.cwd()
api_path = ROOT / "frontend/lib/api.ts"
signals_page_path = ROOT / "frontend/app/signals/page.tsx"
signals_type_path = ROOT / "frontend/app/signals/[type]/page.tsx"
client_path = ROOT / "frontend/components/SignalsClient.tsx"
css_path = ROOT / "frontend/app/globals.css"

paths = [api_path, signals_page_path, signals_type_path, client_path, css_path]
for p in paths:
    if not p.exists():
        raise SystemExit(f"找不到 {p.relative_to(ROOT)}，請確認你在 repo 根目錄執行。")

api = api_path.read_text(encoding="utf-8")
signals_page = signals_page_path.read_text(encoding="utf-8")
signals_type = signals_type_path.read_text(encoding="utf-8")
client = client_path.read_text(encoding="utf-8")
css = css_path.read_text(encoding="utf-8")

# ---------------------------
# Preflight: verify current structure BEFORE writing.
# ---------------------------
required_api = [
    "async function getSignals(signalType?: string | null) {",
    "  const { holdings, stockQuoteMap } = await loadBaseData();",
    "    const prev = previousDateForEtf(holdings, etf, d);",
    '    return getSignals(u.searchParams.get("type"));',
]
for needle in required_api:
    if needle not in api and "signalPreviousDateByRangeV73" not in api:
        raise SystemExit(f"api.ts 找不到預期文字：{needle}")

expected_signals_page = """import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

export default async function SignalsPage() {
  const data = await apiGet('/signals');
  return <SignalsClient data={data} />;
}
"""
if signals_page.strip() != expected_signals_page.strip() and "signalRange={range}" not in signals_page:
    raise SystemExit("frontend/app/signals/page.tsx 不是目前預期的簡短版本，停止。")

expected_type_page = """import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

const statusMap: any = {
  added: '新增',
  removed: '刪除',
  increased: '加碼',
  decreased: '減碼',
};

export default async function SignalTypePage({ params }: { params: { type: string } }) {
  const data = await apiGet('/signals');
  return <SignalsClient data={data} initialFilter={statusMap[params.type] || null} />;
}
"""
if signals_type.strip() != expected_type_page.strip() and "signalRange={range}" not in signals_type:
    raise SystemExit("frontend/app/signals/[type]/page.tsx 不是目前預期版本，停止。")

required_client = [
    "const STATUS_LIST = ['新增', '刪除', '加碼', '減碼'] as const;",
    "export default function SignalsClient({ data, initialFilter = null }: { data: any; initialFilter?: FilterStatus | null }) {",
    "  const defaultStatuses: FilterStatus[] = initialFilter ? [initialFilter] : ['新增', '刪除', '加碼', '減碼'];",
    '    <main className="page signals-v7-page">',
    "<h2>{mmdd ? `${mmdd} 今日訊號` : '今日訊號'}</h2>",
    '<FocusCard title="資金流入最多" item={inflow} tone="red" />',
    '<FocusCard title="資金流出最多" item={outflow} tone="green" />',
    '<FocusCard title="最多 ETF 加碼" item={mostEtfAdd} tone="red" />',
    '<FocusCard title="最多 ETF 減碼" item={mostEtfReduce} tone="green" />',
]
for needle in required_client:
    if needle not in client and "SignalRangeTabsV73" not in client:
        raise SystemExit(f"SignalsClient.tsx 找不到預期文字：{needle}")

# ---------------------------
# api.ts
# ---------------------------
if "signalPreviousDateByRangeV73" not in api:
    api = api.replace("\nasync function getSignals", """
function signalPreviousDateByRangeV73(holdings: any[], etfCode: string, date: string, rangeInput: any) {
  const rangeDays = Math.max(1, Math.min(20, Number(rangeInput || 1) || 1));

  if (rangeDays <= 1) {
    return previousDateForEtf(holdings, etfCode, date);
  }

  const dates = Array.from(new Set(
    holdings
      .filter((h) => h.etf_code === etfCode)
      .map((h) => String(h.data_date))
      .filter((d) => d && d < String(date))
  )).sort();

  if (!dates.length) return null;

  const idx = Math.max(0, dates.length - rangeDays);
  return dates[idx] || dates[0] || null;
}

async function getSignals""", 1)

api = api.replace(
    "async function getSignals(signalType?: string | null) {",
    "async function getSignals(signalType?: string | null, signalRange?: string | number | null) {",
    1,
)

if "const signalRangeDays = Math.max(1, Math.min(20, Number(signalRange || 1) || 1));" not in api:
    api = api.replace(
        "  const { holdings, stockQuoteMap } = await loadBaseData();",
        "  const { holdings, stockQuoteMap } = await loadBaseData();\n  const signalRangeDays = Math.max(1, Math.min(20, Number(signalRange || 1) || 1));",
        1,
    )

api = api.replace(
    "    const prev = previousDateForEtf(holdings, etf, d);",
    "    const prev = signalPreviousDateByRangeV73(holdings, etf, d, signalRangeDays);",
    1,
)

if "signal_range_days: signalRangeDays" not in api:
    api = api.replace(
        "  return {\n    data_date: dataDate,",
        "  return {\n    signal_range_days: signalRangeDays,\n    data_date: dataDate,",
        1,
    )

api = api.replace(
    '    return getSignals(u.searchParams.get("type"));\n',
    '    return getSignals(u.searchParams.get("type"), u.searchParams.get("range") || u.searchParams.get("window") || u.searchParams.get("days"));\n',
    1,
)

# ---------------------------
# signals/page.tsx
# ---------------------------
signals_page = """import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

const ALLOWED_SIGNAL_RANGES_V73 = new Set(['1', '3', '5', '10', '20']);

function cleanSignalRangeV73(raw: any) {
  const r = String(raw || '1');
  return ALLOWED_SIGNAL_RANGES_V73.has(r) ? r : '1';
}

export default async function SignalsPage({
  searchParams,
}: {
  searchParams?: { range?: string; window?: string; days?: string };
}) {
  const range = cleanSignalRangeV73(searchParams?.range || searchParams?.window || searchParams?.days);
  const data = await apiGet(range === '1' ? '/signals' : `/signals?range=${range}`);
  return <SignalsClient data={data} signalRange={range} />;
}
"""

# ---------------------------
# signals/[type]/page.tsx
# ---------------------------
signals_type = """import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

const statusMap: any = {
  added: '新增',
  removed: '刪除',
  increased: '加碼',
  decreased: '減碼',
};

const ALLOWED_SIGNAL_RANGES_V73 = new Set(['1', '3', '5', '10', '20']);

function cleanSignalRangeV73(raw: any) {
  const r = String(raw || '1');
  return ALLOWED_SIGNAL_RANGES_V73.has(r) ? r : '1';
}

export default async function SignalTypePage({
  params,
  searchParams,
}: {
  params: { type: string };
  searchParams?: { range?: string; window?: string; days?: string };
}) {
  const range = cleanSignalRangeV73(searchParams?.range || searchParams?.window || searchParams?.days);
  const data = await apiGet(range === '1' ? '/signals' : `/signals?range=${range}`);
  return <SignalsClient data={data} initialFilter={statusMap[params.type] || null} signalRange={range} />;
}
"""

# ---------------------------
# SignalsClient.tsx
# ---------------------------
if "SIGNAL_RANGE_OPTIONS_V73" not in client:
    client = client.replace(
        "const STATUS_LIST = ['新增', '刪除', '加碼', '減碼'] as const;\n",
        """const STATUS_LIST = ['新增', '刪除', '加碼', '減碼'] as const;
const SIGNAL_RANGE_OPTIONS_V73 = [
  { value: '1', label: '即時' },
  { value: '3', label: '3日' },
  { value: '5', label: '5日' },
  { value: '10', label: '10日' },
  { value: '20', label: '20日' },
] as const;

function signalRangeHrefV73(range: string) {
  return range === '1' ? '/signals' : `/signals?range=${range}`;
}

function signalTypeHrefV73(type: string, range: string) {
  return range === '1' ? `/signals/${type}` : `/signals/${type}?range=${range}`;
}

function signalRangeTitleV73(range: string) {
  return range === '1' ? '今日訊號' : `近${range}日訊號`;
}

function SignalRangeTabsV73({ activeRange }: { activeRange: string }) {
  return (
    <div className="signals-window-tabs-v73" aria-label="訊號區間">
      {SIGNAL_RANGE_OPTIONS_V73.map((item) => (
        <Link
          key={item.value}
          href={signalRangeHrefV73(item.value)}
          className={activeRange === item.value ? 'active' : ''}
        >
          {item.label}
        </Link>
      ))}
    </div>
  );
}

""",
        1,
    )

client = client.replace(
    "export default function SignalsClient({ data, initialFilter = null }: { data: any; initialFilter?: FilterStatus | null }) {",
    "export default function SignalsClient({ data, initialFilter = null, signalRange = '1' }: { data: any; initialFilter?: FilterStatus | null; signalRange?: string }) {",
    1,
)

if "const activeSignalRangeV73 = String(data?.signal_range_days || signalRange || '1');" not in client:
    client = client.replace(
        "  const defaultStatuses: FilterStatus[] = initialFilter ? [initialFilter] : ['新增', '刪除', '加碼', '減碼'];",
        "  const defaultStatuses: FilterStatus[] = initialFilter ? [initialFilter] : ['新增', '刪除', '加碼', '減碼'];\n  const activeSignalRangeV73 = String(data?.signal_range_days || signalRange || '1');\n  const signalTitleV73 = signalRangeTitleV73(activeSignalRangeV73);",
        1,
    )

client = client.replace(
    """function FocusCard({
  title,
  item,
  tone,
}: {
  title: string;
  item: any;
  tone: 'red' | 'green';
}) {""",
    """function FocusCard({
  title,
  item,
  tone,
  href,
}: {
  title: string;
  item: any;
  tone: 'red' | 'green';
  href: string;
}) {""",
    1,
)

client = client.replace(
    "    <Link className={`focus-card ${cardTone}`} href={tone === 'red' ? '/signals/increased' : '/signals/decreased'}>",
    "    <Link className={`focus-card ${cardTone}`} href={href}>",
    1,
)

client = client.replace(
    '    <main className="page signals-v7-page">',
    '    <main className="page signals-v7-page">\n      <SignalRangeTabsV73 activeRange={activeSignalRangeV73} />',
    1,
)

client = client.replace(
    "<h2>{mmdd ? `${mmdd} 今日訊號` : '今日訊號'}</h2>",
    "<h2>{mmdd ? `${mmdd} ${signalTitleV73}` : signalTitleV73}</h2>",
    1,
)

client = client.replace(
    '<FocusCard title="資金流入最多" item={inflow} tone="red" />',
    "<FocusCard title=\"資金流入最多\" item={inflow} tone=\"red\" href={signalTypeHrefV73('increased', activeSignalRangeV73)} />",
    1,
)
client = client.replace(
    '<FocusCard title="資金流出最多" item={outflow} tone="green" />',
    "<FocusCard title=\"資金流出最多\" item={outflow} tone=\"green\" href={signalTypeHrefV73('decreased', activeSignalRangeV73)} />",
    1,
)
client = client.replace(
    '<FocusCard title="最多 ETF 加碼" item={mostEtfAdd} tone="red" />',
    "<FocusCard title=\"最多 ETF 加碼\" item={mostEtfAdd} tone=\"red\" href={signalTypeHrefV73('increased', activeSignalRangeV73)} />",
    1,
)
client = client.replace(
    '<FocusCard title="最多 ETF 減碼" item={mostEtfReduce} tone="green" />',
    "<FocusCard title=\"最多 ETF 減碼\" item={mostEtfReduce} tone=\"green\" href={signalTypeHrefV73('decreased', activeSignalRangeV73)} />",
    1,
)

# ---------------------------
# CSS
# ---------------------------
css_block = """
/* ===== v73 今日訊號區間切換：即時 / 3日 / 5日 / 10日 / 20日 ===== */
.signals-window-tabs-v73 {
  display: inline-grid;
  grid-template-columns: repeat(5, minmax(70px, 1fr));
  gap: 6px;
  padding: 6px;
  margin: 0 0 18px;
  background: #eef2f7;
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.16);
}

.signals-window-tabs-v73 a {
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

.signals-window-tabs-v73 a.active {
  background: #fff;
  color: #2563eb;
  box-shadow:
    0 2px 8px rgba(15, 23, 42, 0.10),
    inset 0 0 0 1px rgba(203, 213, 225, 0.76);
}

@media (max-width: 720px) {
  .signals-window-tabs-v73 {
    width: 100%;
    grid-template-columns: repeat(5, 1fr);
    gap: 4px;
    padding: 5px;
    margin: 0 0 14px;
  }

  .signals-window-tabs-v73 a {
    min-height: 40px;
    padding: 0;
    font-size: 16px;
  }
}
"""
if "v73 今日訊號區間切換" not in css:
    css = css + "\n" + css_block

# ---------------------------
# Write all files only after all patches completed.
# ---------------------------
api_path.write_text(api, encoding="utf-8")
signals_page_path.write_text(signals_page, encoding="utf-8")
signals_type_path.write_text(signals_type, encoding="utf-8")
client_path.write_text(client, encoding="utf-8")
css_path.write_text(css, encoding="utf-8")

print("✅ v73 已加入今日訊號區間切換。")
print("接著請執行：cd frontend && npm run build")
