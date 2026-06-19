#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
COMP = FRONTEND / "components"
APP = FRONTEND / "app"

if not FRONTEND.exists():
    raise SystemExit("❌ 找不到 frontend 目錄，請在 repo 根目錄執行。")
if not COMP.exists():
    raise SystemExit("❌ 找不到 frontend/components 目錄。")

def backup(path: Path, tag="v91"):
    if path.exists():
        bak = path.with_suffix(path.suffix + f".bak_{tag}")
        if not bak.exists():
            bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

def write(path: Path, content: str):
    backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"✅ wrote {path.relative_to(ROOT)}")

signals_client = r'''
'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import {
  rowsOf, latestDateOf, shortDate, stockCode, stockName, fmt, fmtPct, fmtSigned,
  priceOf, changePctOf, flowBillionOf, addEtfCount, reduceEtfCount,
  statusOf, sortRows, toneClass, isStockCode, num, type SortDir
} from './mobileV89Utils';

type Status = '新增' | '刪除' | '加碼' | '減碼' | '異動';
type SortKey = 'flow' | 'price' | 'pct' | 'status' | 'name';

const statusOrder: Record<string, number> = { 新增: 4, 加碼: 3, 減碼: 2, 刪除: 1, 異動: 0 };

const STOCK_NAME_FIX: Record<string, string> = {
  '2330': '台積電',
  '2327': '國巨',
  '2454': '聯發科',
  '2383': '台光電',
  '2382': '廣達',
  '2303': '聯電',
  '3711': '日月光投控',
  '2317': '鴻海',
  '6223': '旺矽',
  '3037': '欣興',
  '2308': '台達電',
  '2345': '智邦',
  '3017': '奇鋐',
  '6669': '緯穎',
};

function fixedStockName(r: any) {
  const c = stockCode(r);
  return STOCK_NAME_FIX[c] || stockName(r);
}

function usable(r: any) {
  return isStockCode(stockCode(r)) && !!stockName(r);
}

function rawLotsDelta(r: any) {
  return num(
    r?.delta_lots ?? r?.change_lots ?? r?.lots_delta ?? r?.deltaLots ??
    r?.shares_change_lots ?? r?.delta_shares_lots ??
    r?.shares_change ?? r?.delta_shares ?? r?.deltaShares ?? r?.changeShares,
    0
  );
}

function normalizeLotsDelta(v: number) {
  if (!Number.isFinite(v)) return 0;
  // 後端有些欄位是「股」，前端要顯示「張」；避免出現 +3,400,000 這種不合理文字
  if (Math.abs(v) >= 100000) return v / 1000;
  return v;
}

function rowAddCount(r: any) {
  const direct = addEtfCount(r);
  if (Number.isFinite(direct) && direct > 0) return direct;
  const s = statusOf(r);
  return s === '新增' || s === '加碼' ? 1 : 0;
}

function rowReduceCount(r: any) {
  const direct = reduceEtfCount(r);
  if (Number.isFinite(direct) && direct > 0) return direct;
  const s = statusOf(r);
  return s === '刪除' || s === '減碼' ? 1 : 0;
}

function combinedStatus(add: number, reduce: number, statuses: string[]) {
  if (statuses.includes('新增') && !statuses.includes('刪除') && !statuses.includes('減碼')) return '新增';
  if (statuses.includes('刪除') && !statuses.includes('新增') && !statuses.includes('加碼')) return '刪除';
  if (add > reduce) return '加碼';
  if (reduce > add) return '減碼';
  if (statuses.includes('加碼')) return '加碼';
  if (statuses.includes('減碼')) return '減碼';
  return '異動';
}

function mergeSignalRows(rows: any[]) {
  const groups: Record<string, any[]> = {};
  rows.forEach((r) => {
    const c = stockCode(r);
    if (!c) return;
    if (!groups[c]) groups[c] = [];
    groups[c].push(r);
  });

  return Object.entries(groups).map(([code, list]) => {
    // 以資訊最完整的 row 當底；數值再重新彙總
    const base =
      [...list].sort((a, b) =>
        Math.abs(flowBillionOf(b) || 0) - Math.abs(flowBillionOf(a) || 0)
      )[0] || list[0];

    const flow = list.reduce((sum, r) => {
      const v = flowBillionOf(r);
      return sum + (Number.isFinite(v) ? v : 0);
    }, 0);

    const add = list.reduce((sum, r) => sum + rowAddCount(r), 0);
    const reduce = list.reduce((sum, r) => sum + rowReduceCount(r), 0);
    const deltaLots = list.reduce((sum, r) => sum + normalizeLotsDelta(rawLotsDelta(r)), 0);
    const statuses = list.map((r) => statusOf(r));

    const status = combinedStatus(add, reduce, statuses);

    return {
      ...base,
      stock_code: code,
      code,
      stock_name: fixedStockName(base),
      name: fixedStockName(base),
      flow_billion: flow,
      money_billion: flow,
      amount_billion: flow,
      delta_amount_billion: flow,
      delta_value_billion: flow,
      add_etf_count: add,
      add_count: add,
      buy_etf_count: add,
      reduce_etf_count: reduce,
      reduce_count: reduce,
      sell_etf_count: reduce,
      delta_lots: deltaLots,
      change_lots: deltaLots,
      status,
      _merged_count: list.length,
    };
  });
}

function SortButton({ label, k, sortKey, sortDir, onClick }: any) {
  const active = sortKey === k;
  return <button className={active ? 'active' : ''} onClick={onClick}>{label}<span>{active ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}</span></button>;
}

function FocusCard({ title, item, tone, countMode = false }: { title: string; item: any; tone: 'red' | 'green'; countMode?: boolean }) {
  if (!item) {
    return <div className={`v89-focus ${tone}`}><h3>{title}</h3><div className="v89-empty">目前沒有明顯訊號</div></div>;
  }

  const code = stockCode(item);
  const flow = flowBillionOf(item);
  const add = addEtfCount(item);
  const reduce = reduceEtfCount(item);
  const delta = normalizeLotsDelta(rawLotsDelta(item));

  const consensus = countMode
    ? `買賣檔數 ${add || 0}:${reduce || 0}`
    : (add || reduce ? `買賣檔數 ${add}:${reduce}` : (delta ? `張數 ${fmtSigned(delta, 0)}` : '張數 -'));

  return (
    <Link href={`/stock/${code}?from=signals`} className={`v89-focus ${tone}`}>
      <h3>{title}</h3>
      <div className="v89-focus-grid">
        <div>
          <div className="v89-focus-name">{fixedStockName(item)} <span>{code}</span></div>
          <div className={toneClass(changePctOf(item)) + ' v89-focus-price'}>{fmt(priceOf(item), 1)} <small>{fmtPct(changePctOf(item), 2)}</small></div>
        </div>
        <div className="v89-focus-info">
          <span>資金動向</span><b className={flow >= 0 ? 'v89-red' : 'v89-green'}>{Number.isFinite(flow) ? fmtSigned(flow, 1, ' 億') : '-'}</b>
          <span>多空共識</span><b>{consensus}</b>
        </div>
      </div>
    </Link>
  );
}

function StatusPill({ status, count, active, onClick }: any) {
  return <button className={`v89-status-pill ${status} ${active ? 'active' : ''}`} onClick={onClick}><span>{status}</span><b>{count}</b></button>;
}

export default function SignalsClient(props: any) {
  const data = props?.data || props;

  // v91：只用 page.tsx 的區間切換；這裡不再渲染 RangeTabs，避免畫面出現兩組「訊號區間」
  const rawRows = rowsOf(data).filter(usable);
  const rows = useMemo(() => mergeSignalRows(rawRows), [rawRows]);

  const [enabled, setEnabled] = useState<Status[]>(['新增', '刪除', '加碼', '減碼', '異動']);
  const [sortKey, setSortKey] = useState<SortKey>('flow');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const range = String(data?.range_days || data?.signalRangeDays || data?.days || 1);

  const { summary, focus } = useMemo(() => {
    const summary: Record<Status, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0, 異動: 0 };
    rows.forEach((r) => { summary[statusOf(r) as Status] += 1; });

    const validFlow = rows
      .map((r) => ({ r, flow: flowBillionOf(r), add: addEtfCount(r), reduce: reduceEtfCount(r), delta: normalizeLotsDelta(rawLotsDelta(r)) }))
      .filter((x) => Number.isFinite(x.flow));

    const mostAdd = [...validFlow]
      .filter((x) => x.add > 0)
      .sort((a, b) => b.add - a.add || Math.abs(b.flow) - Math.abs(a.flow))[0]?.r || null;

    const mostReduce = [...validFlow]
      .filter((x) => x.reduce > 0)
      .sort((a, b) => b.reduce - a.reduce || Math.abs(b.flow) - Math.abs(a.flow))[0]?.r || null;

    return {
      summary,
      focus: {
        inflow: [...validFlow].filter((x) => x.flow > 0).sort((a, b) => b.flow - a.flow)[0]?.r || null,
        outflow: [...validFlow].filter((x) => x.flow < 0).sort((a, b) => a.flow - b.flow)[0]?.r || null,
        mostAdd,
        mostReduce,
      }
    };
  }, [rows]);

  const filtered = rows.filter((r) => enabled.includes(statusOf(r) as Status));
  const sorted = useMemo(() => {
    return sortRows(filtered, (r: any) => {
      if (sortKey === 'flow') return flowBillionOf(r);
      if (sortKey === 'price') return priceOf(r);
      if (sortKey === 'pct') return changePctOf(r);
      if (sortKey === 'status') return statusOrder[statusOf(r)] || 0;
      return fixedStockName(r);
    }, sortDir);
  }, [filtered, sortKey, sortDir]);

  function toggleSort(k: SortKey) {
    if (sortKey === k) setSortDir((d) => d === 'desc' ? 'asc' : 'desc');
    else { setSortKey(k); setSortDir('desc'); }
  }

  const fetched = data?.fetched_etf_count ?? data?.fetchedEtfCount ?? data?.complete_etf_count ?? 0;
  const total = data?.total_etf_count ?? data?.totalEtfCount ?? 0;

  return (
    <main className="page v89-page">
      <section className="v89-title">
        <h1>{range === '1' ? '今日訊號' : `${range}日訊號`}</h1>
        <p>已抓取 {fetched || total || 0} / {total || fetched || 0} 檔 ETF，資料日期 {shortDate(latestDateOf(data))}</p>
      </section>

      <section className="v89-focus-wrap">
        <FocusCard title="資金流入最多" item={focus.inflow} tone="red" />
        <FocusCard title="資金流出最多" item={focus.outflow} tone="green" />
        <FocusCard title="最多 ETF 加碼" item={focus.mostAdd} tone="red" countMode />
        <FocusCard title="最多 ETF 減碼" item={focus.mostReduce} tone="green" countMode />
      </section>

      <section className="v89-table-head"><h2>資金交易明細：共 {sorted.length} 檔</h2></section>

      <div className="v89-status-row">
        {(['新增', '刪除', '加碼', '減碼'] as Status[]).map((s) => (
          <StatusPill key={s} status={s} count={summary[s]} active={enabled.includes(s)} onClick={() => setEnabled((old) => old.includes(s) ? old.filter((x) => x !== s) : [...old, s])} />
        ))}
      </div>

      <div className="v89-sort-row">
        <SortButton label="金額" k="flow" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('flow')} />
        <SortButton label="股價" k="price" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('price')} />
        <SortButton label="漲跌幅" k="pct" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('pct')} />
        <SortButton label="狀態" k="status" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('status')} />
      </div>

      <section className="v89-dense-list">
        {sorted.slice(0, 180).map((r, i) => {
          const s = statusOf(r);
          const code = stockCode(r);
          const flow = flowBillionOf(r);
          return (
            <Link href={`/stock/${code}?from=signals`} className="v89-signal-row" key={`${code}-${i}`}>
              <div className="v89-name-cell"><b>{fixedStockName(r)}</b><span>{code}</span></div>
              <div className="v89-num-cell"><b>{fmt(priceOf(r), 1)}</b><span className={toneClass(changePctOf(r))}>{fmtPct(changePctOf(r), 2)}</span></div>
              <div className={`v89-pill ${s}`}>{s}</div>
              <div className={flow >= 0 ? 'v89-red v89-flow' : 'v89-green v89-flow'}>{Number.isFinite(flow) ? fmtSigned(flow, 2, ' 億') : '-'}</div>
            </Link>
          );
        })}
      </section>
    </main>
  );
}
'''

write(COMP / "SignalsClient.tsx", signals_client)

css_path = APP / "globals.css"
if css_path.exists():
    backup(css_path)
    old = css_path.read_text(encoding="utf-8")
    patch_css = r'''
/* ===== V91 signal cleanup ===== */
.v89-page .v89-title { margin-top: 18px; }
.v89-page > .v89-range-card { display: none !important; }
.v89-focus-grid { gap: 8px; }
.v89-focus-info b { line-height: 1.15; }
.v89-focus-name span { margin-left: 4px; }
.v89-signal-row .v89-name-cell b {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
  display: block;
}
@media(max-width:390px){
  .v89-focus-info { font-size: 12px; }
  .v89-focus-price small { font-size: 13px; }
  .v89-signal-row { grid-template-columns: 1.08fr .84fr .58fr .78fr; }
}
'''
    if "V91 signal cleanup" not in old:
        css_path.write_text(old + "\n\n" + patch_css, encoding="utf-8")
        print("✅ appended V91 CSS")
    else:
        print("ℹ️ V91 CSS already exists")

readme = r'''
# V91 Signal Cleanup

修正畫面不合理之處：

1. 今日訊號重複出現兩組「訊號區間」
   - SignalsClient 不再產生自己的區間切換，保留 page 上面那組。

2. 同一股票重複出現
   - 依 stock_code 彙總，避免 2330 同時出現「台灣積體」與「台灣積體電路製造」。

3. 張數單位錯誤
   - 若後端給的是股數，前端會自動除以 1000 轉成張，避免顯示 +3,400,000。

4. 股票名稱修正
   - 常見代號改成較直覺名稱，例如 2330 → 台積電。

5. 最多 ETF 加碼 / 減碼
   - 改成以 ETF 檔數邏輯為主，不再用很寬鬆的 fallback 造成怪訊號。
'''
write(ROOT / "README_V91_SIGNAL_CLEANUP.md", readme)

print("\n✅ V91 已套用。下一步：")
print("cd frontend")
print("[ -d node_modules ] || npm install")
print("npm run build")
