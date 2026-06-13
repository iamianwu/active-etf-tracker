#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
api_path = ROOT / "frontend/lib/api.ts"
page_path = ROOT / "frontend/app/page.tsx"
signals_page_path = ROOT / "frontend/app/signals/page.tsx"
signals_type_page_path = ROOT / "frontend/app/signals/[type]/page.tsx"
css_path = ROOT / "frontend/app/globals.css"

for p in [api_path, page_path, signals_page_path, signals_type_page_path, css_path]:
    if not p.exists():
        raise SystemExit(f"找不到 {p.relative_to(ROOT)}，請確認你在 repo 根目錄執行。")

api = api_path.read_text(encoding="utf-8")

if "signalWindowPreviousDate_v70" not in api:
    helper = """
// v70: 回傳最新日往前第 N 個可用持股資料日。
// range=1 等於今日訊號：最新日 vs 前一個持股日。
// range=3/5/10/20 等於最新日 vs N 個持股資料日前，做區間淨變動。
function signalWindowPreviousDate_v70(holdings: any[], etfCode: string, date: string, windowInput: any) {
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
    if "\nfunction computeEtfChanges" in api:
        api = api.replace("\nfunction computeEtfChanges", "\n" + helper + "function computeEtfChanges")
    else:
        api += "\n" + helper

api = api.replace(
    "async function getSignals(signalType?: string | null) {",
    "async function getSignals(signalType?: string | null, windowInput?: string | number | null) {"
)
api = api.replace(
    "async function getSignals(signalType?: string | null, windowInput?: string | number | null, windowInput?: string | number | null) {",
    "async function getSignals(signalType?: string | null, windowInput?: string | number | null) {"
)

if "const windowDays = Math.max(1, Math.min(20, Number(windowInput || 1) || 1));" not in api:
    api = api.replace(
        "async function getSignals(signalType?: string | null, windowInput?: string | number | null) {\n  const { holdings, stockQuoteMap } = await loadBaseData();",
        "async function getSignals(signalType?: string | null, windowInput?: string | number | null) {\n  const windowDays = Math.max(1, Math.min(20, Number(windowInput || 1) || 1));\n  const { holdings, stockQuoteMap } = await loadBaseData();"
    )

api = api.replace(
    "const prev = previousDateForEtf(holdings, etf, d);",
    "const prev = signalWindowPreviousDate_v70(holdings, etf, d, windowDays);"
)
api = api.replace(
    "const prev = signalWindowPreviousDate_v68(holdings, etf, d, windowDays);",
    "const prev = signalWindowPreviousDate_v70(holdings, etf, d, windowDays);"
)

if "signal_window_days: windowDays" not in api:
    api = api.replace(
        "return {\n    data_date: dataDate,",
        "return {\n    signal_window_days: windowDays,\n    signal_window_label: windowDays === 1 ? '今日' : `近${windowDays}日`,\n    data_date: dataDate,"
    )

api = api.replace(
    'return getSignals(u.searchParams.get("type"));',
    'return getSignals(u.searchParams.get("type"), u.searchParams.get("range") || u.searchParams.get("window") || u.searchParams.get("days"));'
)
api = api.replace(
    "return getSignals(u.searchParams.get('type'));",
    "return getSignals(u.searchParams.get('type'), u.searchParams.get('range') || u.searchParams.get('window') || u.searchParams.get('days'));"
)

api_path.write_text(api, encoding="utf-8")

page_path.write_text('import Link from \'next/link\';\nimport { apiGet, fmt, fmt0 } from \'@/lib/api\';\nimport SortableSignalTable from \'@/components/SortableSignalTable\';\n\nexport const dynamic = \'force-dynamic\';\nexport const revalidate = 0;\n\nconst ALLOWED = new Set([\'新增\', \'刪除\', \'加碼\', \'減碼\']);\nconst SIGNAL_RANGES = [\'1\', \'3\', \'5\', \'10\', \'20\'];\n\nfunction cleanRange(raw: any) {\n  const r = String(raw || \'1\');\n  return SIGNAL_RANGES.includes(r) ? r : \'1\';\n}\n\nfunction rangeHref(range: string) {\n  return range === \'1\' ? \'/\' : `/?range=${range}`;\n}\n\nfunction signalsRangeHref(range: string) {\n  return range === \'1\' ? \'/signals\' : `/signals?range=${range}`;\n}\n\nfunction typeHref(type: string, range: string) {\n  return range === \'1\' ? `/signals/${type}` : `/signals/${type}?range=${range}`;\n}\n\nfunction rangeTitle(range: string) {\n  return range === \'1\' ? \'今日訊號\' : `近${range}日訊號`;\n}\n\nfunction countFromStatuses(x: any, keyword: string) {\n  if (keyword === \'加碼\' && x.increase_etf_count !== undefined) return Number(x.increase_etf_count || 0);\n  if (keyword === \'減碼\' && x.decrease_etf_count !== undefined) return Number(x.decrease_etf_count || 0);\n  if (keyword === \'買\' && x.buy_etf_count !== undefined) return Number(x.buy_etf_count || 0);\n  if (keyword === \'賣\' && x.sell_etf_count !== undefined) return Number(x.sell_etf_count || 0);\n  return (x.statuses || []).filter((s: string) => String(s).includes(keyword)).length;\n}\n\nfunction sortByMoneyOrSharesDesc(a: any, b: any) {\n  const av = a.delta_value_billion !== null && a.delta_value_billion !== undefined\n    ? Math.abs(Number(a.delta_value_billion || 0))\n    : Math.abs(Number(a.delta_shares || 0));\n\n  const bv = b.delta_value_billion !== null && b.delta_value_billion !== undefined\n    ? Math.abs(Number(b.delta_value_billion || 0))\n    : Math.abs(Number(b.delta_shares || 0));\n\n  return bv - av;\n}\n\nfunction stockMoveValue(x: any) {\n  const v = x?.delta_value_billion;\n\n  if (v !== null && v !== undefined && !Number.isNaN(Number(v)) && Number(v) !== 0) {\n    const prefix = Number(v) > 0 ? \'+\' : \'\';\n    return `${prefix}${fmt(v, 1)} 億`;\n  }\n\n  const lots = Number(x?.delta_shares || 0) / 1000;\n  const prefix = lots > 0 ? \'+\' : \'\';\n  return `${prefix}${fmt0(lots)} 張`;\n}\n\nfunction SignalRangeTabs({ range, base = \'home\' }: { range: string; base?: \'home\' | \'signals\' }) {\n  const items = [\n    { value: \'1\', label: \'即時\' },\n    { value: \'3\', label: \'3日\' },\n    { value: \'5\', label: \'5日\' },\n    { value: \'10\', label: \'10日\' },\n    { value: \'20\', label: \'20日\' },\n  ];\n\n  return (\n    <div className="signals-window-tabs-v70" aria-label="訊號區間">\n      {items.map((item) => (\n        <Link\n          key={item.value}\n          href={base === \'home\' ? rangeHref(item.value) : signalsRangeHref(item.value)}\n          className={range === item.value ? \'active\' : \'\'}\n        >\n          {item.label}\n        </Link>\n      ))}\n    </div>\n  );\n}\n\nfunction FocusCard({\n  title,\n  item,\n  tone,\n  href,\n}: {\n  title: string;\n  item: any;\n  tone: \'red\' | \'green\';\n  href: string;\n}) {\n  const buyCount = countFromStatuses(item || {}, \'買\');\n  const sellCount = countFromStatuses(item || {}, \'賣\');\n\n  return (\n    <Link className={`focus-card ${tone}`} href={href}>\n      <div className="focus-card-title">{title}</div>\n\n      {item ? (\n        <div className="focus-card-body">\n          <div className="focus-stock">\n            <b>{item.stock_name}</b>\n            <span>{item.stock_code}</span>\n          </div>\n\n          <div className="focus-metrics">\n            <div>\n              <span>資金動向：</span>\n              <b>{stockMoveValue(item)}</b>\n            </div>\n            <div>\n              <span>多空共識：</span>\n              <b>買賣檔數 {buyCount}:{sellCount}</b>\n            </div>\n          </div>\n        </div>\n      ) : (\n        <div className="focus-empty">尚無資料</div>\n      )}\n    </Link>\n  );\n}\n\nexport default async function SignalsHomePage({\n  searchParams,\n}: {\n  searchParams?: { range?: string; window?: string; days?: string };\n}) {\n  const range = cleanRange(searchParams?.range || searchParams?.window || searchParams?.days);\n  const data = await apiGet(range === \'1\' ? \'/signals\' : `/signals?range=${range}`);\n\n  const changes = (data.changes || []).filter((x: any) => ALLOWED.has(x.status));\n  const summary = data.summary || {};\n  const agg = (data.aggregate || []).filter((x: any) => x.stock_code);\n\n  const inflow = [...agg]\n    .filter((x: any) => Number(x.delta_shares || 0) > 0)\n    .sort(sortByMoneyOrSharesDesc)[0];\n\n  const outflow = [...agg]\n    .filter((x: any) => Number(x.delta_shares || 0) < 0)\n    .sort(sortByMoneyOrSharesDesc)[0];\n\n  const mostEtfAdd = [...agg]\n    .filter((x: any) => countFromStatuses(x, \'加碼\') > 0)\n    .sort((a: any, b: any) =>\n      countFromStatuses(b, \'加碼\') - countFromStatuses(a, \'加碼\') ||\n      Math.abs(Number(b.delta_shares || 0)) - Math.abs(Number(a.delta_shares || 0))\n    )[0];\n\n  const mostEtfReduce = [...agg]\n    .filter((x: any) => countFromStatuses(x, \'減碼\') > 0)\n    .sort((a: any, b: any) =>\n      countFromStatuses(b, \'減碼\') - countFromStatuses(a, \'減碼\') ||\n      Math.abs(Number(b.delta_shares || 0)) - Math.abs(Number(a.delta_shares || 0))\n    )[0];\n\n  const mmdd = data.data_date_mmdd || \'\';\n  const complete = Number(data.fetched_etf_count || 0) === Number(data.total_etf_count || 0);\n  const title = rangeTitle(range);\n\n  return (\n    <main className="page signals-v3-page signals-window-page-v70">\n      <SignalRangeTabs range={range} base="home" />\n\n      <div className="signals-title-block">\n        <h2>{mmdd ? `${mmdd} ${title}` : title}</h2>\n        <div className={`signals-data-status ${complete ? \'ok\' : \'warn\'}`}>\n          已抓取 {data.fetched_etf_count || 0} / {data.total_etf_count || 0} 檔 ETF\n          {data.data_date ? `，資料日期 ${data.data_date}` : \'\'}\n        </div>\n        <div className="signals-window-note-v70">\n          {range === \'1\'\n            ? \'即時＝最新持股日與前一個持股日比較。\'\n            : `近${range}日＝每檔 ETF 最新持股與 ${range} 個持股資料日前比較，顯示區間淨變動。`}\n        </div>\n      </div>\n\n      <div className="focus-grid">\n        <FocusCard title="資金流入最多" item={inflow} tone="red" href={typeHref(\'increased\', range)} />\n        <FocusCard title="資金流出最多" item={outflow} tone="green" href={typeHref(\'decreased\', range)} />\n        <FocusCard title="最多 ETF 加碼" item={mostEtfAdd} tone="red" href={typeHref(\'increased\', range)} />\n        <FocusCard title="最多 ETF 減碼" item={mostEtfReduce} tone="green" href={typeHref(\'decreased\', range)} />\n      </div>\n\n      <h3>資金交易明細：共 {changes.length} 檔</h3>\n\n      <div className="status-pill-row">\n        <Link className="status-pill add" href={typeHref(\'added\', range)}>\n          <span>新增</span><b>{summary[\'新增\'] || 0}</b>\n        </Link>\n        <Link className="status-pill remove" href={typeHref(\'removed\', range)}>\n          <span>刪除</span><b>{summary[\'刪除\'] || 0}</b>\n        </Link>\n        <Link className="status-pill inc" href={typeHref(\'increased\', range)}>\n          <span>加碼</span><b>{summary[\'加碼\'] || 0}</b>\n        </Link>\n        <Link className="status-pill dec" href={typeHref(\'decreased\', range)}>\n          <span>減碼</span><b>{summary[\'減碼\'] || 0}</b>\n        </Link>\n      </div>\n\n      <SortableSignalTable rows={changes} />\n    </main>\n  );\n}\n', encoding="utf-8")
signals_page_path.write_text('import Link from \'next/link\';\nimport { apiGet, fmt, fmt0 } from \'@/lib/api\';\nimport SortableSignalTable from \'@/components/SortableSignalTable\';\n\nexport const dynamic = \'force-dynamic\';\nexport const revalidate = 0;\n\nconst ALLOWED = new Set([\'新增\', \'刪除\', \'加碼\', \'減碼\']);\nconst SIGNAL_RANGES = [\'1\', \'3\', \'5\', \'10\', \'20\'];\n\nfunction cleanRange(raw: any) {\n  const r = String(raw || \'1\');\n  return SIGNAL_RANGES.includes(r) ? r : \'1\';\n}\n\nfunction rangeHref(range: string) {\n  return range === \'1\' ? \'/\' : `/?range=${range}`;\n}\n\nfunction signalsRangeHref(range: string) {\n  return range === \'1\' ? \'/signals\' : `/signals?range=${range}`;\n}\n\nfunction typeHref(type: string, range: string) {\n  return range === \'1\' ? `/signals/${type}` : `/signals/${type}?range=${range}`;\n}\n\nfunction rangeTitle(range: string) {\n  return range === \'1\' ? \'今日訊號\' : `近${range}日訊號`;\n}\n\nfunction countFromStatuses(x: any, keyword: string) {\n  if (keyword === \'加碼\' && x.increase_etf_count !== undefined) return Number(x.increase_etf_count || 0);\n  if (keyword === \'減碼\' && x.decrease_etf_count !== undefined) return Number(x.decrease_etf_count || 0);\n  if (keyword === \'買\' && x.buy_etf_count !== undefined) return Number(x.buy_etf_count || 0);\n  if (keyword === \'賣\' && x.sell_etf_count !== undefined) return Number(x.sell_etf_count || 0);\n  return (x.statuses || []).filter((s: string) => String(s).includes(keyword)).length;\n}\n\nfunction sortByMoneyOrSharesDesc(a: any, b: any) {\n  const av = a.delta_value_billion !== null && a.delta_value_billion !== undefined\n    ? Math.abs(Number(a.delta_value_billion || 0))\n    : Math.abs(Number(a.delta_shares || 0));\n\n  const bv = b.delta_value_billion !== null && b.delta_value_billion !== undefined\n    ? Math.abs(Number(b.delta_value_billion || 0))\n    : Math.abs(Number(b.delta_shares || 0));\n\n  return bv - av;\n}\n\nfunction stockMoveValue(x: any) {\n  const v = x?.delta_value_billion;\n\n  if (v !== null && v !== undefined && !Number.isNaN(Number(v)) && Number(v) !== 0) {\n    const prefix = Number(v) > 0 ? \'+\' : \'\';\n    return `${prefix}${fmt(v, 1)} 億`;\n  }\n\n  const lots = Number(x?.delta_shares || 0) / 1000;\n  const prefix = lots > 0 ? \'+\' : \'\';\n  return `${prefix}${fmt0(lots)} 張`;\n}\n\nfunction SignalRangeTabs({ range, base = \'home\' }: { range: string; base?: \'home\' | \'signals\' }) {\n  const items = [\n    { value: \'1\', label: \'即時\' },\n    { value: \'3\', label: \'3日\' },\n    { value: \'5\', label: \'5日\' },\n    { value: \'10\', label: \'10日\' },\n    { value: \'20\', label: \'20日\' },\n  ];\n\n  return (\n    <div className="signals-window-tabs-v70" aria-label="訊號區間">\n      {items.map((item) => (\n        <Link\n          key={item.value}\n          href={signalsRangeHref(item.value)}\n          className={range === item.value ? \'active\' : \'\'}\n        >\n          {item.label}\n        </Link>\n      ))}\n    </div>\n  );\n}\n\nfunction FocusCard({\n  title,\n  item,\n  tone,\n  href,\n}: {\n  title: string;\n  item: any;\n  tone: \'red\' | \'green\';\n  href: string;\n}) {\n  const buyCount = countFromStatuses(item || {}, \'買\');\n  const sellCount = countFromStatuses(item || {}, \'賣\');\n\n  return (\n    <Link className={`focus-card ${tone}`} href={href}>\n      <div className="focus-card-title">{title}</div>\n\n      {item ? (\n        <div className="focus-card-body">\n          <div className="focus-stock">\n            <b>{item.stock_name}</b>\n            <span>{item.stock_code}</span>\n          </div>\n\n          <div className="focus-metrics">\n            <div>\n              <span>資金動向：</span>\n              <b>{stockMoveValue(item)}</b>\n            </div>\n            <div>\n              <span>多空共識：</span>\n              <b>買賣檔數 {buyCount}:{sellCount}</b>\n            </div>\n          </div>\n        </div>\n      ) : (\n        <div className="focus-empty">尚無資料</div>\n      )}\n    </Link>\n  );\n}\n\nexport default async function SignalsHomePage({\n  searchParams,\n}: {\n  searchParams?: { range?: string; window?: string; days?: string };\n}) {\n  const range = cleanRange(searchParams?.range || searchParams?.window || searchParams?.days);\n  const data = await apiGet(range === \'1\' ? \'/signals\' : `/signals?range=${range}`);\n\n  const changes = (data.changes || []).filter((x: any) => ALLOWED.has(x.status));\n  const summary = data.summary || {};\n  const agg = (data.aggregate || []).filter((x: any) => x.stock_code);\n\n  const inflow = [...agg]\n    .filter((x: any) => Number(x.delta_shares || 0) > 0)\n    .sort(sortByMoneyOrSharesDesc)[0];\n\n  const outflow = [...agg]\n    .filter((x: any) => Number(x.delta_shares || 0) < 0)\n    .sort(sortByMoneyOrSharesDesc)[0];\n\n  const mostEtfAdd = [...agg]\n    .filter((x: any) => countFromStatuses(x, \'加碼\') > 0)\n    .sort((a: any, b: any) =>\n      countFromStatuses(b, \'加碼\') - countFromStatuses(a, \'加碼\') ||\n      Math.abs(Number(b.delta_shares || 0)) - Math.abs(Number(a.delta_shares || 0))\n    )[0];\n\n  const mostEtfReduce = [...agg]\n    .filter((x: any) => countFromStatuses(x, \'減碼\') > 0)\n    .sort((a: any, b: any) =>\n      countFromStatuses(b, \'減碼\') - countFromStatuses(a, \'減碼\') ||\n      Math.abs(Number(b.delta_shares || 0)) - Math.abs(Number(a.delta_shares || 0))\n    )[0];\n\n  const mmdd = data.data_date_mmdd || \'\';\n  const complete = Number(data.fetched_etf_count || 0) === Number(data.total_etf_count || 0);\n  const title = rangeTitle(range);\n\n  return (\n    <main className="page signals-v3-page signals-window-page-v70">\n      <SignalRangeTabs range={range} base="signals" />\n\n      <div className="signals-title-block">\n        <h2>{mmdd ? `${mmdd} ${title}` : title}</h2>\n        <div className={`signals-data-status ${complete ? \'ok\' : \'warn\'}`}>\n          已抓取 {data.fetched_etf_count || 0} / {data.total_etf_count || 0} 檔 ETF\n          {data.data_date ? `，資料日期 ${data.data_date}` : \'\'}\n        </div>\n        <div className="signals-window-note-v70">\n          {range === \'1\'\n            ? \'即時＝最新持股日與前一個持股日比較。\'\n            : `近${range}日＝每檔 ETF 最新持股與 ${range} 個持股資料日前比較，顯示區間淨變動。`}\n        </div>\n      </div>\n\n      <div className="focus-grid">\n        <FocusCard title="資金流入最多" item={inflow} tone="red" href={typeHref(\'increased\', range)} />\n        <FocusCard title="資金流出最多" item={outflow} tone="green" href={typeHref(\'decreased\', range)} />\n        <FocusCard title="最多 ETF 加碼" item={mostEtfAdd} tone="red" href={typeHref(\'increased\', range)} />\n        <FocusCard title="最多 ETF 減碼" item={mostEtfReduce} tone="green" href={typeHref(\'decreased\', range)} />\n      </div>\n\n      <h3>資金交易明細：共 {changes.length} 檔</h3>\n\n      <div className="status-pill-row">\n        <Link className="status-pill add" href={typeHref(\'added\', range)}>\n          <span>新增</span><b>{summary[\'新增\'] || 0}</b>\n        </Link>\n        <Link className="status-pill remove" href={typeHref(\'removed\', range)}>\n          <span>刪除</span><b>{summary[\'刪除\'] || 0}</b>\n        </Link>\n        <Link className="status-pill inc" href={typeHref(\'increased\', range)}>\n          <span>加碼</span><b>{summary[\'加碼\'] || 0}</b>\n        </Link>\n        <Link className="status-pill dec" href={typeHref(\'decreased\', range)}>\n          <span>減碼</span><b>{summary[\'減碼\'] || 0}</b>\n        </Link>\n      </div>\n\n      <SortableSignalTable rows={changes} />\n    </main>\n  );\n}\n', encoding="utf-8")
signals_type_page_path.write_text('import Link from \'next/link\';\nimport { apiGet } from \'@/lib/api\';\nimport SortableSignalTable from \'@/components/SortableSignalTable\';\n\nexport const dynamic = \'force-dynamic\';\nexport const revalidate = 0;\n\nconst titleMap: any = {\n  added: \'新增清單\',\n  removed: \'刪除清單\',\n  increased: \'加碼清單\',\n  decreased: \'減碼清單\',\n};\n\nconst ALLOWED = new Set([\'新增\', \'刪除\', \'加碼\', \'減碼\']);\nconst SIGNAL_RANGES = [\'1\', \'3\', \'5\', \'10\', \'20\'];\n\nfunction cleanRange(raw: any) {\n  const r = String(raw || \'1\');\n  return SIGNAL_RANGES.includes(r) ? r : \'1\';\n}\n\nfunction backHref(range: string) {\n  return range === \'1\' ? \'/\' : `/?range=${range}`;\n}\n\nexport default async function SignalTypePage({\n  params,\n  searchParams,\n}: {\n  params: { type: string };\n  searchParams?: { range?: string; window?: string; days?: string };\n}) {\n  const range = cleanRange(searchParams?.range || searchParams?.window || searchParams?.days);\n  const data = await apiGet(range === \'1\'\n    ? `/signals?type=${params.type}`\n    : `/signals?type=${params.type}&range=${range}`\n  );\n  const rows = (data.changes || []).filter((x: any) => ALLOWED.has(x.status));\n  const mmdd = data.data_date_mmdd || \'\';\n  const rangeText = range === \'1\' ? \'\' : `近${range}日`;\n  const listTitle = `${rangeText}${titleMap[params.type] || \'訊號清單\'}`;\n\n  return (\n    <main className="page signals-v3-page">\n      <Link className="back" href={backHref(range)}>‹</Link>\n      <div className="signals-title-block">\n        <h2>{mmdd ? `${mmdd} ${listTitle}` : listTitle}：共 {rows.length} 檔</h2>\n        <div className="signals-data-status">\n          已抓取 {data.fetched_etf_count || 0} / {data.total_etf_count || 0} 檔 ETF\n          {data.data_date ? `，資料日期 ${data.data_date}` : \'\'}\n        </div>\n      </div>\n\n      <SortableSignalTable rows={rows} />\n    </main>\n  );\n}\n', encoding="utf-8")

css = css_path.read_text(encoding="utf-8")
css_block = """
/* ===== v70 signals range tabs: 即時 / 3日 / 5日 / 10日 / 20日 ===== */
.signals-window-page-v70 .signals-title-block {
  margin-top: 8px;
}

.signals-window-tabs-v70 {
  display: inline-grid;
  grid-template-columns: repeat(5, minmax(78px, 1fr));
  gap: 6px;
  padding: 6px;
  margin: 0 0 18px;
  background: #eef2f7;
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.16);
}

.signals-window-tabs-v70 a {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 18px;
  border-radius: 999px;
  color: #64748b;
  text-decoration: none;
  font-weight: 900;
  font-size: 18px;
  letter-spacing: 0.01em;
  white-space: nowrap;
  -webkit-tap-highlight-color: transparent;
}

.signals-window-tabs-v70 a.active {
  background: #fff;
  color: #3b82f6;
  box-shadow:
    0 2px 8px rgba(15, 23, 42, 0.10),
    inset 0 0 0 1px rgba(203, 213, 225, 0.76);
}

.signals-window-note-v70 {
  margin-top: 6px;
  color: #94a3b8;
  font-size: 14px;
  font-weight: 700;
}

@media (max-width: 720px) {
  .signals-window-page-v70 {
    padding-left: 14px;
    padding-right: 14px;
  }

  .signals-window-tabs-v70 {
    width: 100%;
    grid-template-columns: repeat(5, 1fr);
    gap: 4px;
    padding: 5px;
    margin: 0 0 14px;
  }

  .signals-window-tabs-v70 a {
    min-height: 40px;
    padding: 0;
    font-size: 16px;
  }

  .signals-window-note-v70 {
    font-size: 12px;
    line-height: 1.45;
  }
}
"""
if "v70 signals range tabs" not in css:
    css += "\n" + css_block

css_path.write_text(css, encoding="utf-8")

print("✅ v70 已強制改首頁 frontend/app/page.tsx，今日訊號區間切換應該會出現在首頁。")
print("請確認這幾個檔案有變更：")
print("- frontend/app/page.tsx")
print("- frontend/app/signals/page.tsx")
print("- frontend/app/signals/[type]/page.tsx")
print("- frontend/lib/api.ts")
print("- frontend/app/globals.css")
