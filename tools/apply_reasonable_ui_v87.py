#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
COMP = FRONTEND / "components"
APP = FRONTEND / "app"

if not FRONTEND.exists():
    raise SystemExit("❌ 找不到 frontend 目錄，請在 active-etf-tracker-fix repo 根目錄執行。")
if not COMP.exists():
    raise SystemExit("❌ 找不到 frontend/components 目錄。")

def backup(path: Path):
    if path.exists():
        bak = path.with_suffix(path.suffix + ".bak_v87")
        if not bak.exists():
            bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

def write(path: Path, content: str):
    backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"✅ wrote {path.relative_to(ROOT)}")

signals_client = r"""
'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { codeOf, nameOf, fmt, fmtPct, clsTone, changePctOf, priceOf, n, latestDate, rangeText } from './mobileV86Utils';

type FilterStatus = '新增' | '刪除' | '加碼' | '減碼';

function isUsableStock(r: any) {
  const c = codeOf(r);
  return /^[0-9]{4}$/.test(c) && !!nameOf(r);
}

function flowValue(r: any) {
  const direct =
    r?.amount_billion ??
    r?.flow_billion ??
    r?.capital_flow_billion ??
    r?.delta_amount_billion ??
    r?.money_billion ??
    r?.net_amount_billion ??
    r?.change_amount_billion;
  if (Number.isFinite(Number(direct))) return Number(direct);

  const raw =
    r?.amount ??
    r?.flow_amount ??
    r?.delta_amount ??
    r?.market_value_change ??
    r?.net_amount ??
    r?.change_amount;
  if (Number.isFinite(Number(raw))) return Number(raw) / 100000000;

  const shares = n(r?.delta_shares ?? r?.shares_change ?? r?.change_lots ?? r?.delta_lots, NaN);
  const px = n(priceOf(r), NaN);
  if (Number.isFinite(shares) && Number.isFinite(px)) return shares * px * 1000 / 100000000;

  return NaN;
}

function addCount(r: any) {
  return n(
    r?.buy_etf_count ??
    r?.add_etf_count ??
    r?.etf_add_count ??
    r?.positive_etf_count ??
    r?.buy_count ??
    r?.add_count,
    0
  );
}

function reduceCount(r: any) {
  return n(
    r?.sell_etf_count ??
    r?.reduce_etf_count ??
    r?.etf_reduce_count ??
    r?.negative_etf_count ??
    r?.sell_count ??
    r?.reduce_count,
    0
  );
}

function statusOf(r: any): FilterStatus {
  const st = String(r?.status || r?.action || r?.change_type || '');
  if (st.includes('新增')) return '新增';
  if (st.includes('刪除')) return '刪除';
  if (st.includes('減')) return '減碼';
  if (st.includes('加')) return '加碼';

  const dv = n(r?.delta_shares ?? r?.shares_change ?? r?.change_lots ?? r?.delta_lots, 0);
  if (dv > 0) return '加碼';
  if (dv < 0) return '減碼';
  return '加碼';
}

function FocusCard({ title, item, mode }: { title: string; item: any; mode: 'in' | 'out' }) {
  if (!item) {
    return (
      <div className={`v86-focus-card compact ${mode === 'in' ? 'red' : 'green'} empty`}>
        <div className="v86-focus-title">{title}</div>
        <div className="v86-empty-mini">尚無有效訊號</div>
      </div>
    );
  }

  const c = codeOf(item);
  const name = nameOf(item);
  const pct = changePctOf(item);
  const flow = flowValue(item);
  const isRed = mode === 'in';

  return (
    <Link href={`/stock/${c}?from=signals`} className={`v86-focus-card compact ${isRed ? 'red' : 'green'}`}>
      <div className="v86-focus-title">{title}</div>

      <div className="v87-focus-layout">
        <div className="v87-focus-left">
          <div className="v86-focus-stock">{name}<span>{c}</span></div>
          <div className={clsTone(pct) + ' v86-focus-price'}>{fmt(priceOf(item), 1)} <small>{fmtPct(pct, 2)}</small></div>
        </div>

        <div className="v86-focus-meta">
          <b>資金動向</b>
          <strong className={flow >= 0 ? 'v86-red' : 'v86-green'}>
            {Number.isFinite(flow) ? `${flow >= 0 ? '+' : ''}${fmt(flow, 1)} 億` : '-'}
          </strong>
          <b>多空共識</b>
          <strong>{addCount(item)}:{reduceCount(item)}</strong>
        </div>
      </div>
    </Link>
  );
}

function StatusPill({ label, count, active, onClick }: any) {
  return (
    <button onClick={onClick} className={`v86-status-pill ${active ? 'active' : ''} ${label}`}>
      <span>{label}</span><b>{count}</b>
    </button>
  );
}

export default function SignalsClient(props: any) {
  const data = props?.data || props;
  const rows: any[] = data?.rows || data?.items || data?.signals || [];
  const [selected, setSelected] = useState<FilterStatus[]>(['新增', '刪除', '加碼', '減碼']);

  const range = String(data?.range_days || data?.signalRangeDays || data?.days || 1);

  const computed = useMemo(() => {
    const valid = rows
      .filter(isUsableStock)
      .map((r) => ({ r, flow: flowValue(r), add: addCount(r), reduce: reduceCount(r) }))
      .filter((x) => Number.isFinite(x.flow));

    const inflow = [...valid]
      .filter((x) => x.flow > 0.0001)
      .sort((a, b) => b.flow - a.flow)[0]?.r || null;

    const outflow = [...valid]
      .filter((x) => x.flow < -0.0001)
      .sort((a, b) => a.flow - b.flow)[0]?.r || null;

    const mostAdd = [...valid]
      .filter((x) => x.add > 0)
      .sort((a, b) => b.add - a.add || b.flow - a.flow)[0]?.r || null;

    const mostReduce = [...valid]
      .filter((x) => x.reduce > 0)
      .sort((a, b) => b.reduce - a.reduce || a.flow - b.flow)[0]?.r || null;

    const summary: Record<FilterStatus, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0 };
    rows.forEach((r) => {
      if (isUsableStock(r)) summary[statusOf(r)] += 1;
    });

    return { inflow, outflow, mostAdd, mostReduce, summary };
  }, [rows]);

  const shown = rows
    .filter(isUsableStock)
    .filter((r) => selected.includes(statusOf(r)));

  const fetched = data?.fetched_etf_count ?? data?.fetchedEtfCount ?? data?.complete_etf_count ?? 0;
  const total = data?.total_etf_count ?? data?.totalEtfCount ?? 0;
  const missing = data?.missing_etfs || data?.missingEtfs || [];

  return (
    <main className="page v86-page v87-signals-page">
      <section className="v86-title-block">
        <h1>{rangeText(range)}訊號</h1>
        <div className="v86-data-line">已抓取 {fetched || total || 0} / {total || fetched || 0} 檔 ETF，資料日期 {latestDate(data) || '-'}</div>
        {Array.isArray(missing) && missing.length > 0 && (
          <div className="v86-warn-line">⚠️ {missing.length} 檔資料待補：{missing.slice(0, 4).join('、')}</div>
        )}
      </section>

      <section className="v86-focus-grid">
        <FocusCard title="資金流入最多" item={computed.inflow} mode="in" />
        <FocusCard title="資金流出最多" item={computed.outflow} mode="out" />
        <FocusCard title="最多 ETF 加碼" item={computed.mostAdd} mode="in" />
        <FocusCard title="最多 ETF 減碼" item={computed.mostReduce} mode="out" />
      </section>

      <section className="v86-detail-head">
        <h2>資金交易明細：共 {shown.length} 檔</h2>
      </section>

      <div className="v86-status-row">
        {(['新增', '刪除', '加碼', '減碼'] as FilterStatus[]).map((x) => (
          <StatusPill
            key={x}
            label={x}
            count={computed.summary[x]}
            active={selected.includes(x)}
            onClick={() => setSelected((p) => p.includes(x) ? p.filter((v) => v !== x) : [...p, x])}
          />
        ))}
      </div>

      <section className="v86-list v87-signal-list">
        {shown.slice(0, 120).map((r, idx) => {
          const c = codeOf(r);
          const st = statusOf(r);
          const pct = changePctOf(r);
          const flow = flowValue(r);
          return (
            <Link key={`${c}-${idx}`} className="v86-signal-row" href={`/stock/${c}?from=signals`}>
              <div className="v86-row-left">
                <b>{nameOf(r)}</b>
                <span>{c}</span>
              </div>
              <div className="v86-row-mid">
                <b>{fmt(priceOf(r), 1)}</b>
                <span className={clsTone(pct)}>{fmtPct(pct, 2)}</span>
              </div>
              <div className={`v86-badge ${st}`}>{st}</div>
              <div className={flow >= 0 ? 'v86-red' : 'v86-green'}>
                {Number.isFinite(flow) ? `${flow >= 0 ? '+' : ''}${fmt(flow, 2)} 億` : '-'}
              </div>
            </Link>
          );
        })}
      </section>
    </main>
  );
}
"""

write(COMP / "SignalsClient.tsx", signals_client)

css_path = APP / "globals.css"
if not css_path.exists():
    raise SystemExit("❌ 找不到 frontend/app/globals.css")

css = r"""

/* ===== V87 reasonability fixes ===== */

.v87-signals-page .v86-range-block {
  display: none !important;
}

.v86-focus-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 10px !important;
}

.v86-focus-card.compact {
  min-height: 142px;
  padding: 11px 12px !important;
}

.v87-focus-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.v86-focus-title {
  font-size: 16px !important;
  margin-bottom: 8px !important;
}

.v86-focus-stock {
  font-size: 17px !important;
  line-height: 1.15 !important;
  white-space: normal !important;
}

.v86-focus-stock span {
  font-size: 13px !important;
  margin-left: 5px !important;
}

.v86-focus-price {
  font-size: 25px !important;
  line-height: 1.05 !important;
}

.v86-focus-price small {
  font-size: 13px !important;
}

.v86-focus-meta {
  grid-template-columns: auto 1fr;
  column-gap: 6px;
  row-gap: 1px;
  font-size: 11.5px !important;
}

.v86-focus-meta strong {
  font-size: 12.5px !important;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.v86-empty-mini {
  color: #8a95a6;
  font-weight: 900;
  font-size: 14px;
  padding-top: 12px;
}

.v86-title-block h1,
.v86-list-head h1 {
  font-size: 28px !important;
}

.v86-status-pill {
  padding: 8px 12px !important;
  font-size: 16px !important;
}

.v86-signal-row {
  grid-template-columns: minmax(86px, 1fr) 78px 62px 80px !important;
  min-height: 68px !important;
  gap: 6px !important;
  padding: 10px 4px !important;
}

.v86-row-left b,
.v86-holding-row b,
.v86-etf-holding-row b {
  font-size: 17px !important;
}

.v86-row-left span,
.v86-holding-row span,
.v86-etf-holding-row span {
  font-size: 13px !important;
}

.v86-row-mid b {
  font-size: 18px !important;
}

.v86-row-mid span {
  font-size: 13px !important;
}

.v86-badge {
  font-size: 13px !important;
  padding: 4px 9px !important;
}

.v86-etf-card,
.v86-stock-card {
  padding: 10px 11px !important;
  border-radius: 13px !important;
  margin-bottom: 9px !important;
}

.v86-etf-top b,
.v86-stock-card b {
  font-size: 19px !important;
}

.v86-etf-price strong,
.v86-stock-price strong {
  font-size: 20px !important;
}

.v86-etf-metrics {
  gap: 4px !important;
  margin-top: 8px !important;
}

.v86-etf-metrics span {
  font-size: 11.5px !important;
}

.v86-badge-row {
  margin-top: 8px !important;
}

.v86-badge-row span {
  font-size: 11.5px !important;
  padding: 3px 7px !important;
}

.v86-search-line input {
  height: 42px !important;
  font-size: 15px !important;
}

@media (max-width: 390px) {
  .v86-focus-grid {
    grid-template-columns: 1fr !important;
  }

  .v86-signal-row {
    grid-template-columns: minmax(78px, 1fr) 72px 56px 72px !important;
  }
}
"""

old_css = css_path.read_text(encoding="utf-8")
if "V87 reasonability fixes" not in old_css:
    css_path.write_text(old_css + css, encoding="utf-8")
    print("✅ appended V87 CSS")
else:
    print("ℹ️ V87 CSS already exists")

readme = r"""
# V87 Reasonability Fixes

修正 v86 目前不合理的地方：

1. 今日訊號「訊號區間」重複顯示  
   - SignalsClient 不再另外渲染區間切換，避免跟 page-level tabs 重複。

2. 今日訊號重點卡片不要亂抓 fallback  
   - 資金流入：只取 flow > 0 的有效個股  
   - 資金流出：只取 flow < 0 的有效個股  
   - 最多 ETF 加碼：必須 addCount > 0  
   - 最多 ETF 減碼：必須 reduceCount > 0  
   - 如果沒有有效訊號，顯示「尚無有效訊號」，不要硬塞台積電 0:0。

3. 卡片太大、字太大、內容太散  
   - 今日訊號改成 2 欄小卡  
   - 明細列、ETF 卡片、資金持股卡片縮小字級與 padding  
   - 手機小螢幕仍自動變 1 欄。

4. 明細 row 過度巨大  
   - 壓縮 row 高度與欄寬，降低滑動負擔。
"""

write(ROOT / "README_REASONABLE_UI_V87.md", readme)

print("\n✅ v87 已套用。請執行：")
print("cd frontend")
print("[ -d node_modules ] || npm install")
print("npm run build")
