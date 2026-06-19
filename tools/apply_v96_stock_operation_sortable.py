#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
COMP = FRONTEND / "components"
APP = FRONTEND / "app"
TARGET = COMP / "StockDetailClient.tsx"
CSS = APP / "globals.css"

if not FRONTEND.exists():
    raise SystemExit("❌ 找不到 frontend 目錄，請在 repo 根目錄執行。")
if not TARGET.exists():
    raise SystemExit("❌ 找不到 frontend/components/StockDetailClient.tsx")
if not CSS.exists():
    raise SystemExit("❌ 找不到 frontend/app/globals.css")

def backup(path: Path, tag="v96"):
    bak = path.with_suffix(path.suffix + f".bak_{tag}")
    if not bak.exists():
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

backup(TARGET)
backup(CSS)

s = TARGET.read_text(encoding="utf-8")

# 確保 React import 有 useState
if "from 'react'" in s:
    s = re.sub(
        r"import\s+\{([^}]+)\}\s+from\s+'react';",
        lambda m: "import {" + (m.group(1).strip() if "useState" in m.group(1) else m.group(1).strip() + ", useState") + "} from 'react';",
        s,
        count=1
    )

usage = "<StockRecentOperationPanel data={data} etfRows={etfRows} />"
if usage not in s:
    patterns = [
        r"(<TopEtfPreview[\s\S]*?onMore=\{\(\) => setTab\('detail'\)\}\s*/>)",
        r"(<TopEtfPreview[\s\S]*?/>)",
        r"(<h2>前五大持有 ETF</h2>[\s\S]*?</TopEtfPreview>)",
    ]
    done = False
    for pat in patterns:
        s2, n = re.subn(pat, r"\1\n        <StockRecentOperationPanel data={data} etfRows={etfRows} />", s, count=1)
        if n:
            s = s2
            done = True
            break
    if not done:
        raise SystemExit("❌ 找不到前五大持有 ETF 區塊，請貼 StockDetailClient.tsx 中 TopEtfPreview 附近內容。")

component = '\ntype StockOpSortKey = \'date\' | \'etf\' | \'lots\' | \'pct\' | \'status\';\ntype StockOpSortDir = \'asc\' | \'desc\';\n\nfunction stockOpPick(obj: any, keys: string[]): any {\n  for (const k of keys) {\n    if (obj && obj[k] !== undefined && obj[k] !== null && obj[k] !== \'\') return obj[k];\n  }\n  return undefined;\n}\n\nfunction stockOpNum(v: any): number {\n  if (typeof num === \'function\') return num(v);\n  const n = Number(String(v ?? \'\').replace(/,/g, \'\'));\n  return Number.isFinite(n) ? n : NaN;\n}\n\nfunction stockOpLotsFromAny(v: any): number {\n  const n = stockOpNum(v);\n  if (!Number.isFinite(n)) return NaN;\n  return Math.abs(n) >= 100000 ? n / 1000 : n;\n}\n\nfunction stockOpDate(r: any): string {\n  return String(stockOpPick(r, [\'data_date\', \'date\', \'trade_date\', \'updated_date\', \'dt\']) || \'\');\n}\n\nfunction stockOpCode(r: any): string {\n  return String(stockOpPick(r, [\'etf_code\', \'etfCode\', \'code\', \'fund_code\', \'fundCode\']) || \'\');\n}\n\nfunction stockOpName(r: any, etfMap: Record<string, any>): string {\n  const code = stockOpCode(r);\n  return String(\n    stockOpPick(r, [\'etf_name\', \'etfName\', \'name\', \'fund_name\', \'fundName\']) ||\n    etfMap[code]?.name ||\n    etfMap[code]?.etf_name ||\n    etfMap[code]?.fund_name ||\n    \'\'\n  );\n}\n\nfunction stockOpHoldingLots(r: any): number {\n  return stockOpLotsFromAny(stockOpPick(r, [\'shares\', \'shares_lots\', \'lots\', \'holding_lots\', \'quantity\', \'qty\', \'position_lots\']));\n}\n\nfunction stockOpFormatMmdd(v: string): string {\n  const s = String(v || \'\');\n  if (!s) return \'-\';\n  const m = s.match(/(\\d{4})[-/](\\d{2})[-/](\\d{2})/);\n  if (m) return `${m[2]}/${m[3]}`;\n  const m2 = s.match(/(\\d{2})[-/](\\d{2})/);\n  if (m2) return `${m2[1]}/${m2[2]}`;\n  return s;\n}\n\nfunction stockOpFormatLotsSigned(v: number): string {\n  if (!Number.isFinite(v)) return \'-\';\n  const abs = Math.abs(v);\n  if (abs > 0 && abs < 1) return `${v > 0 ? \'+\' : \'-\'}<1張`;\n  const rounded = Math.round(abs * 100) / 100;\n  const integerLike = Math.abs(rounded - Math.round(rounded)) < 1e-8;\n  const body = integerLike ? Math.round(rounded).toLocaleString() : rounded.toLocaleString(undefined, { maximumFractionDigits: 2 });\n  return `${v > 0 ? \'+\' : \'-\'}${body}張`;\n}\n\nfunction stockOpFormatPct(v: number): string {\n  if (!Number.isFinite(v)) return \'-\';\n  const abs = Math.abs(v);\n  if (abs > 100) {\n    const times = Math.min(10, Math.floor(abs / 100));\n    if (times >= 1) return `${v > 0 ? \'>\' : \'-\'}${times}倍`;\n  }\n  const digits = abs >= 10 ? 1 : 2;\n  const text = abs.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: 0 });\n  return `${v > 0 ? \'+\' : \'-\'}${text}%`;\n}\n\nfunction buildStockRecentOperationRows(data: any, etfRows: any[]) {\n  const etfMap: Record<string, any> = {};\n  for (const e of etfRows || []) etfMap[String(e?.code || e?.etf_code || e?.fund_code || \'\')] = e;\n\n  const raw = ([] as any[]).concat(\n    Array.isArray(data?.operation_records) ? data.operation_records : [],\n    Array.isArray(data?.operationRecords) ? data.operationRecords : [],\n    Array.isArray(data?.recent_operations) ? data.recent_operations : [],\n    Array.isArray(data?.recentOperations) ? data.recentOperations : [],\n    Array.isArray(data?.stock_operation_records) ? data.stock_operation_records : [],\n    Array.isArray(data?.stockOperationRecords) ? data.stockOperationRecords : []\n  );\n\n  let rows: any[] = [];\n\n  if (raw.length) {\n    rows = raw.map((r: any) => {\n      const lots = stockOpLotsFromAny(stockOpPick(r, [\n        \'delta_lots\', \'change_lots\', \'deltaLots\', \'changeLots\',\n        \'shares_change\', \'delta_shares\', \'sharesChange\', \'deltaShares\',\n        \'change_shares\', \'changeShares\', \'delta\', \'change\'\n      ]));\n      const pct = stockOpNum(stockOpPick(r, [\'change_pct\', \'delta_pct\', \'changePct\', \'deltaPct\', \'change_percent\', \'percent_change\', \'pct\']));\n      return {\n        date: stockOpDate(r),\n        code: stockOpCode(r),\n        name: stockOpName(r, etfMap),\n        lots,\n        pct,\n        status: String(stockOpPick(r, [\'status\', \'action\']) || (lots >= 0 ? \'加碼\' : \'減碼\')),\n      };\n    }).filter((r) => r.code && Number.isFinite(r.lots) && r.lots !== 0);\n  }\n\n  if (!rows.length) {\n    const hist = ([] as any[]).concat(\n      Array.isArray(data?.holding_history) ? data.holding_history : [],\n      Array.isArray(data?.holdingHistory) ? data.holdingHistory : [],\n      Array.isArray(data?.historyRows) ? data.historyRows : [],\n      Array.isArray(data?.history) ? data.history : []\n    );\n\n    const grouped: Record<string, any[]> = {};\n    for (const r of hist) {\n      const code = stockOpCode(r);\n      const date = stockOpDate(r);\n      if (!code || !date) continue;\n      if (!grouped[code]) grouped[code] = [];\n      grouped[code].push(r);\n    }\n\n    for (const code of Object.keys(grouped)) {\n      const list = grouped[code].sort((a, b) => stockOpDate(a).localeCompare(stockOpDate(b)));\n      for (let i = 1; i < list.length; i++) {\n        const prevLots = stockOpHoldingLots(list[i - 1]);\n        const currLots = stockOpHoldingLots(list[i]);\n        if (!Number.isFinite(prevLots) || !Number.isFinite(currLots)) continue;\n        const delta = currLots - prevLots;\n        if (Math.abs(delta) < 0.0001) continue;\n        rows.push({\n          date: stockOpDate(list[i]),\n          code,\n          name: stockOpName(list[i], etfMap),\n          lots: delta,\n          pct: prevLots ? (delta / Math.abs(prevLots)) * 100 : NaN,\n          status: delta >= 0 ? \'加碼\' : \'減碼\',\n        });\n      }\n    }\n  }\n\n  const seen = new Set<string>();\n  return rows.filter((r) => {\n    const key = [r.date, r.code, r.status, Math.round((r.lots || 0) * 1000)].join(\'|\');\n    if (seen.has(key)) return false;\n    seen.add(key);\n    return true;\n  });\n}\n\nfunction StockRecentOperationPanel({ data, etfRows }: { data: any; etfRows: any[] }) {\n  const baseRows = buildStockRecentOperationRows(data, etfRows);\n  const [openInfo, setOpenInfo] = useState(false);\n  const [sortKey, setSortKey] = useState<StockOpSortKey>(\'date\');\n  const [sortDir, setSortDir] = useState<StockOpSortDir>(\'desc\');\n\n  if (!baseRows.length) return null;\n\n  function toggleSort(key: StockOpSortKey) {\n    if (sortKey === key) {\n      setSortDir(sortDir === \'asc\' ? \'desc\' : \'asc\');\n      return;\n    }\n    setSortKey(key);\n    setSortDir(key === \'etf\' || key === \'status\' ? \'asc\' : \'desc\');\n  }\n\n  function sortValue(row: any, key: StockOpSortKey): any {\n    if (key === \'date\') return String(row.date || \'\');\n    if (key === \'etf\') return String(row.code || \'\');\n    if (key === \'lots\') return Math.abs(Number(row.lots || 0));\n    if (key === \'pct\') return Math.abs(Number(row.pct || 0));\n    if (key === \'status\') return String(row.status || \'\');\n    return \'\';\n  }\n\n  const rows = [...baseRows]\n    .sort((a, b) => {\n      const av = sortValue(a, sortKey);\n      const bv = sortValue(b, sortKey);\n      let cmp = 0;\n      if (typeof av === \'number\' && typeof bv === \'number\') cmp = av - bv;\n      else cmp = String(av).localeCompare(String(bv));\n      return sortDir === \'asc\' ? cmp : -cmp;\n    })\n    .slice(0, 30);\n\n  const SortBtn = ({ k, children, right = false }: { k: StockOpSortKey; children: React.ReactNode; right?: boolean }) => (\n    <button type="button" className={`v96-op-head-btn ${right ? \'right\' : \'\'} ${sortKey === k ? \'active\' : \'\'}`} onClick={() => toggleSort(k)}>\n      <span>{children}</span>\n      <em>{sortKey === k ? (sortDir === \'asc\' ? \'▲\' : \'▼\') : \'↕\'}</em>\n    </button>\n  );\n\n  return (\n    <section className="v96-op-panel">\n      <div className="v96-op-title-row">\n        <h2>近30日操作記錄</h2>\n        <button type="button" className="v96-op-info-btn" onClick={() => setOpenInfo(true)} aria-label="變動資料說明">i</button>\n      </div>\n\n      <div className="v96-op-table">\n        <div className="v96-op-head">\n          <SortBtn k="date">日期</SortBtn>\n          <SortBtn k="etf">ETF</SortBtn>\n          <SortBtn k="lots" right>變動張數<br />變動幅度</SortBtn>\n          <SortBtn k="status" right>狀態</SortBtn>\n        </div>\n\n        {rows.map((r: any, idx: number) => {\n          const isAdd = r.lots >= 0;\n          return (\n            <div className="v96-op-row" key={`${r.date}-${r.code}-${idx}`}>\n              <div className="v96-op-date">{stockOpFormatMmdd(r.date)}</div>\n              <div className="v96-op-etf">\n                <b>{r.code}</b>\n                <span>{r.name || \'-\'}</span>\n              </div>\n              <div className={`v96-op-change ${isAdd ? \'up\' : \'down\'}`}>\n                <b>{stockOpFormatLotsSigned(r.lots)}</b>\n                <span>{stockOpFormatPct(r.pct)}</span>\n              </div>\n              <div className={`v96-op-status ${isAdd ? \'up\' : \'down\'}`}>{r.status || (isAdd ? \'加碼\' : \'減碼\')}</div>\n            </div>\n          );\n        })}\n      </div>\n\n      {openInfo && (\n        <div className="v96-op-modal-mask" onClick={() => setOpenInfo(false)}>\n          <div className="v96-op-modal" onClick={(e) => e.stopPropagation()}>\n            <h3>變動資料說明</h3>\n            <ul>\n              <li><b>變動張數：</b>以 1 張為最小顯示單位，未滿 1 張的零股變動不顯示。</li>\n              <li><b>變動幅度：</b>用於衡量加減碼強度。當變動幅度超過 100% 時，以倍數顯示（如 &gt;1倍、&gt;2倍），最多顯示 10 倍，快速識別大幅異動。</li>\n              <li><b>判讀提醒：</b>變動幅度過大，可能源於原始持股基數較小，請搭配變動張數判讀。</li>\n            </ul>\n            <button type="button" onClick={() => setOpenInfo(false)}>我知道了</button>\n          </div>\n        </div>\n      )}\n    </section>\n  );\n}\n'

start_markers = [
    "type StockOpSortKey",
    "function stockOpPick",
    "function pickObjValue",
]
start_pos = -1
for m in start_markers:
    p = s.find(m)
    if p != -1:
        start_pos = p
        break

if start_pos != -1:
    end_pos = -1
    for m in ["\nfunction TopEtfPreview", "\nfunction EtfHoldingList", "\nfunction HoldingEtfList", "\nexport default function"]:
        p = s.find(m, start_pos + 1)
        if p != -1:
            end_pos = p
            break
    if end_pos == -1:
        raise SystemExit("❌ 找到舊 component 起點，但找不到結束點。")
    s = s[:start_pos] + component + s[end_pos:]
else:
    marker = "\nfunction TopEtfPreview"
    if marker not in s:
        marker = "\nfunction EtfHoldingList"
    if marker not in s:
        raise SystemExit("❌ 找不到可插入 component 的位置。")
    s = s.replace(marker, "\n" + component + marker, 1)

TARGET.write_text(s, encoding="utf-8")

css = CSS.read_text(encoding="utf-8")
if "V96 stock operation sortable table override" not in css:
    css += '\n/* ===== V96 stock operation sortable table override ===== */\n.v95-op-panel,\n.v94-op-section {\n  display: none !important;\n}\n.v96-op-panel {\n  margin: 18px 0 28px;\n  overflow: visible;\n}\n.v96-op-title-row {\n  display: flex;\n  align-items: center;\n  gap: 8px;\n  margin: 0 0 12px;\n}\n.v96-op-title-row h2 {\n  margin: 0;\n  font-size: clamp(26px, 6vw, 36px);\n  line-height: 1.15;\n}\n.v96-op-info-btn {\n  width: 28px;\n  height: 28px;\n  border-radius: 999px;\n  border: 2px solid #9aa5b5;\n  background: #fff;\n  color: #7b8797;\n  font-size: 16px;\n  font-weight: 950;\n  line-height: 1;\n}\n.v96-op-table {\n  width: 100%;\n  background: #fff;\n  border: 1px solid #e7edf5;\n  border-radius: 16px;\n  overflow: hidden;\n}\n.v96-op-head,\n.v96-op-row {\n  display: grid;\n  grid-template-columns: 64px minmax(0, 1fr) 112px 64px;\n  column-gap: 8px;\n  align-items: center;\n}\n.v96-op-head {\n  padding: 12px 12px;\n  background: #f5f7fa;\n  border-bottom: 1px solid #e7edf5;\n}\n.v96-op-head-btn {\n  appearance: none;\n  border: 0;\n  background: transparent;\n  padding: 0;\n  display: flex;\n  align-items: flex-start;\n  gap: 4px;\n  color: #4b5563;\n  font-size: 14px;\n  font-weight: 950;\n  line-height: 1.2;\n  text-align: left;\n}\n.v96-op-head-btn.right {\n  justify-content: flex-end;\n  text-align: right;\n}\n.v96-op-head-btn em {\n  font-style: normal;\n  color: #98a2b3;\n  font-size: 12px;\n  line-height: 1;\n  margin-top: 1px;\n}\n.v96-op-head-btn.active {\n  color: #2468c9;\n}\n.v96-op-head-btn.active em {\n  color: #2468c9;\n}\n.v96-op-row {\n  padding: 14px 12px;\n  min-height: 86px;\n  border-top: 1px solid #eef2f7;\n}\n.v96-op-row:first-of-type {\n  border-top: 0;\n}\n.v96-op-date {\n  font-size: 16px;\n  font-weight: 900;\n  color: #27303c;\n}\n.v96-op-etf {\n  min-width: 0;\n}\n.v96-op-etf b {\n  display: block;\n  color: #182030;\n  font-size: 20px;\n  font-weight: 950;\n  line-height: 1.08;\n  letter-spacing: .2px;\n}\n.v96-op-etf span {\n  display: -webkit-box;\n  margin-top: 4px;\n  color: #667085;\n  font-size: 14px;\n  font-weight: 800;\n  line-height: 1.22;\n  overflow: hidden;\n  -webkit-line-clamp: 2;\n  -webkit-box-orient: vertical;\n}\n.v96-op-change,\n.v96-op-status {\n  text-align: right;\n}\n.v96-op-change b {\n  display: block;\n  font-size: 17px;\n  font-weight: 950;\n  line-height: 1.15;\n  white-space: nowrap;\n}\n.v96-op-change span {\n  display: block;\n  margin-top: 5px;\n  color: #5f6978;\n  font-size: 15px;\n  font-weight: 850;\n}\n.v96-op-status {\n  font-size: 17px;\n  font-weight: 950;\n  white-space: nowrap;\n}\n.v96-op-change.up,\n.v96-op-status.up {\n  color: #e15661;\n}\n.v96-op-change.down,\n.v96-op-status.down {\n  color: #2fa67c;\n}\n.v96-op-modal-mask {\n  position: fixed;\n  inset: 0;\n  z-index: 9999;\n  background: rgba(15, 23, 42, .35);\n  display: flex;\n  align-items: center;\n  justify-content: center;\n  padding: 22px;\n}\n.v96-op-modal {\n  width: min(560px, 100%);\n  max-height: 84vh;\n  overflow: auto;\n  border-radius: 18px;\n  background: #fff;\n  padding: 22px;\n  box-shadow: 0 20px 60px rgba(15, 23, 42, .25);\n}\n.v96-op-modal h3 {\n  margin: 0 0 18px;\n  text-align: center;\n  font-size: 24px;\n  line-height: 1.2;\n}\n.v96-op-modal ul {\n  margin: 0;\n  padding-left: 24px;\n}\n.v96-op-modal li {\n  margin: 16px 0;\n  font-size: 17px;\n  line-height: 1.75;\n  font-weight: 650;\n}\n.v96-op-modal button {\n  width: 100%;\n  margin-top: 18px;\n  border: 0;\n  border-radius: 14px;\n  background: #5d8fe0;\n  color: #fff;\n  padding: 14px 16px;\n  font-size: 19px;\n  font-weight: 950;\n}\n@media (max-width: 430px) {\n  .v96-op-head,\n  .v96-op-row {\n    grid-template-columns: 54px minmax(0, 1fr) 94px 50px;\n    column-gap: 6px;\n  }\n  .v96-op-head,\n  .v96-op-row {\n    padding-left: 10px;\n    padding-right: 10px;\n  }\n  .v96-op-row {\n    min-height: 78px;\n  }\n  .v96-op-etf b {\n    font-size: 18px;\n  }\n  .v96-op-etf span {\n    font-size: 13px;\n  }\n  .v96-op-change b,\n  .v96-op-status {\n    font-size: 15px;\n  }\n  .v96-op-change span,\n  .v96-op-date,\n  .v96-op-head-btn {\n    font-size: 13px;\n  }\n}\n'
CSS.write_text(css, encoding="utf-8")

readme = ROOT / "README_V96_STOCK_OPERATION_SORTABLE.md"
readme.write_text(
    "# V96 Stock Operation Sortable Table\n\n"
    "修正個股頁「近30日操作記錄」：\n"
    "- 加入可點排序：日期、ETF、變動張數、狀態\n"
    "- 修正手機版欄寬，避免 ETF 名稱與狀態擠在一起\n"
    "- 保留 i 說明彈窗\n"
    "- 隱藏舊 v94/v95 操作記錄區塊，避免重複顯示\n",
    encoding="utf-8"
)

print("✅ V96 已完成：近30日操作記錄加入排序，並修正手機版排版")
