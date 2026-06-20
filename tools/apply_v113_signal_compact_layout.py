from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
FRONTEND = ROOT / 'frontend'
if not FRONTEND.exists():
    raise SystemExit('❌ 請在專案根目錄執行，例如：cd ~/Downloads/active-etf-tracker-fix')

now = datetime.now().strftime('%Y%m%d_%H%M%S')

def backup(path: Path):
    if path.exists():
        bak = path.with_suffix(path.suffix + f'.bak_v113_{now}')
        bak.write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
        print(f'備份：{path} -> {bak.name}')

def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    backup(path)
    path.write_text(content.strip() + '\n', encoding='utf-8')
    print(f'✅ 寫入 {path}')

signals_client = """
'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

type AnyRow = Record<string, any>;
type SortKey = 'inflow' | 'outflow' | 'abs_amount' | 'lots' | 'buy' | 'sell' | 'price' | 'pct';
type Status = '新增' | '刪除' | '加碼' | '減碼';

const STATUSES: Status[] = ['新增', '刪除', '加碼', '減碼'];

function num(v: any, fallback = 0): number {
  if (v === null || v === undefined || v === '') return fallback;
  const x = Number(String(v).replace(/,/g, '').replace(/[^\\d.-]/g, ''));
  return Number.isFinite(x) ? x : fallback;
}
function firstNum(row: AnyRow, keys: string[], fallback = 0): number {
  for (const k of keys) {
    if (row && row[k] !== undefined && row[k] !== null && row[k] !== '') {
      const v = num(row[k], NaN);
      if (Number.isFinite(v)) return v;
    }
  }
  return fallback;
}
function rowsOf(data: any): AnyRow[] {
  const src = data?.rows ?? data?.changes ?? data?.aggregate ?? data?.items ?? [];
  return Array.isArray(src) ? src : [];
}
function codeOf(row: AnyRow) { return String(row.stock_code ?? row.code ?? '').trim(); }
function nameOf(row: AnyRow) { return String(row.stock_name ?? row.name ?? row.stockName ?? codeOf(row)).trim(); }
function priceOf(row: AnyRow) {
  const v = firstNum(row, ['price', 'close_price', 'close', 'last_price'], NaN);
  return Number.isFinite(v) ? v : null;
}
function pctOf(row: AnyRow) {
  const v = firstNum(row, ['change_pct', 'pct', 'percent', 'changePercent'], NaN);
  return Number.isFinite(v) ? v : null;
}
function lotsOf(row: AnyRow) {
  return firstNum(row, ['net_lots', 'display_delta_lots', 'change_lots', 'delta_lots', 'lot_change'], 0);
}
function amountOf(row: AnyRow) {
  const direct = firstNum(row, ['net_amount_billion', 'delta_amount_billion', 'flow_billion', 'money_billion', 'amount_billion'], NaN);
  if (Number.isFinite(direct)) return direct;
  const p = priceOf(row);
  return p ? p * lotsOf(row) * 1000 / 100000000 : 0;
}
function statusOf(row: AnyRow): Status {
  const s = String(row.status ?? row.type ?? '').trim();
  if (STATUSES.includes(s as Status)) return s as Status;
  const lots = lotsOf(row);
  if (lots > 0) return '加碼';
  if (lots < 0) return '減碼';
  return '加碼';
}
function buyOf(row: AnyRow) {
  return Math.max(0, Math.round(firstNum(row, ['buy_count', 'buy_etf_count', 'add_etf_count', 'increase_count'], 0)));
}
function sellOf(row: AnyRow) {
  return Math.max(0, Math.round(firstNum(row, ['sell_count', 'sell_etf_count', 'reduce_etf_count', 'decrease_count'], 0)));
}
function mmdd(dateLike: any) {
  const s = String(dateLike ?? '').trim();
  const m = s.match(/(\\d{4})-(\\d{2})-(\\d{2})/);
  if (m) return `${m[2]}-${m[3]}`;
  return s;
}
function fmt0(v: any) {
  const x = num(v, NaN);
  if (!Number.isFinite(x)) return '-';
  return Math.round(x).toLocaleString('zh-TW');
}
function fmtPrice(v: number | null) {
  if (v === null || !Number.isFinite(v)) return '-';
  return v.toLocaleString('zh-TW', { maximumFractionDigits: v >= 100 ? 1 : 2 });
}
function fmtPct(v: number | null) {
  if (v === null || !Number.isFinite(v)) return '-';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}%`;
}
function fmtLots(v: number) {
  if (!Number.isFinite(v)) return '-';
  if (Math.abs(v) < 0.01) return '0張';
  const sign = v > 0 ? '+' : '';
  return `${sign}${Math.round(v).toLocaleString('zh-TW')}張`;
}
function fmtBillion(v: number) {
  if (!Number.isFinite(v)) return '-';
  if (Math.abs(v) < 0.005) return '0億';
  const sign = v > 0 ? '+' : '';
  const abs = Math.abs(v);
  const digits = abs >= 100 ? 1 : abs >= 10 ? 1 : 2;
  return `${sign}${v.toLocaleString('zh-TW', { maximumFractionDigits: digits })}億`;
}
function tone(v: number) { return v > 0 ? 'red' : v < 0 ? 'green' : 'muted'; }
function isLimitUp(row: AnyRow) { const p = pctOf(row); return p !== null && p >= 9.7; }
function isLimitDown(row: AnyRow) { const p = pctOf(row); return p !== null && p <= -9.7; }

function DataQuality({ data }: { data: any }) {
  const total = Number(data?.total_etf_count ?? data?.totalEtfCount ?? 0);
  const today = Number(data?.today_etf_count ?? data?.fetched_etf_count ?? data?.includedEtfCount ?? 0);
  const missing = Number(data?.non_today_etf_count ?? Math.max(0, total - today));
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';
  return (
    <div className="v113-quality">
      <div>資料日 <b>{date ? mmdd(date) : '-'}</b></div>
      <div>已取得今日資料：<b>{today}</b> / <b>{total || today}</b> 檔 ETF</div>
      {missing > 0 && <div className="v113-warn">未更新 {missing} 檔，本頁不混入前一日資料</div>}
    </div>
  );
}

function FocusCard({ title, row, kind }: { title: string; row?: AnyRow | null; kind: 'red' | 'green' }) {
  if (!row) {
    return <div className={`v113-focus-card ${kind}`}><div className="v113-focus-title">{title}</div><div className="v113-empty">尚無有效訊號</div></div>;
  }
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const price = priceOf(row);
  const pct = pctOf(row);
  return (
    <Link href={`/stock/${codeOf(row)}`} className={`v113-focus-card ${kind}`}>
      <div className="v113-focus-title">{title}</div>
      <div className="v113-focus-name"><span>{nameOf(row)}</span><em>{codeOf(row)}</em></div>
      <div className="v113-focus-price"><span>{fmtPrice(price)}</span><b className={tone(pct ?? 0)}>{fmtPct(pct)}</b></div>
      <div className="v113-focus-meta">
        <span>淨額 <b className={tone(amount)}>{fmtBillion(amount)}</b></span>
        <span>張數 <b className={tone(lots)}>{fmtLots(lots)}</b></span>
        <span>買賣 <b>{buyOf(row)}:{sellOf(row)}</b></span>
      </div>
    </Link>
  );
}

function SortPill({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`v113-sort-pill ${active ? 'active' : ''}`}>{label}</button>;
}
function StatusPill({ label, count, active, onClick }: { label: Status; count: number; active: boolean; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`v113-status-pill s-${label} ${active ? 'active' : ''}`}>{label} {count}</button>;
}

function SignalRow({ row }: { row: AnyRow }) {
  const code = codeOf(row);
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const pct = pctOf(row);
  const status = statusOf(row);
  return (
    <Link href={`/stock/${code}`} className="v113-row">
      <div className="v113-r-stock">
        <div className="v113-r-name">{nameOf(row)}</div>
        <div className="v113-r-code">{code}</div>
      </div>
      <div className="v113-r-price">
        <span className={isLimitUp(row) ? 'limit-up' : isLimitDown(row) ? 'limit-down' : ''}>{fmtPrice(priceOf(row))}</span>
        <b className={tone(pct ?? 0)}>{fmtPct(pct)}</b>
      </div>
      <div className="v113-r-flow">
        <b className={tone(amount)}>{fmtBillion(amount)}</b>
        <span className={tone(lots)}>{fmtLots(lots)}</span>
      </div>
      <div className="v113-r-state">
        <span className={`v113-status s-${status}`}>{status}</span>
        <span className="v113-consensus">買賣 {buyOf(row)}:{sellOf(row)}</span>
      </div>
    </Link>
  );
}

export default function SignalsClient(props: any) {
  const data = props?.data ?? props ?? {};
  const sourceRows = rowsOf(data).filter((r) => STATUSES.includes(statusOf(r)) && codeOf(r));
  const [selectedStatuses, setSelectedStatuses] = useState<Status[]>(['新增', '刪除', '加碼', '減碼']);
  const [sortKey, setSortKey] = useState<SortKey>('inflow');

  const statusCount = useMemo(() => {
    const out: Record<Status, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0 };
    for (const r of sourceRows) out[statusOf(r)] += 1;
    return out;
  }, [sourceRows]);

  const rows = useMemo(() => {
    const filtered = sourceRows.filter((r) => selectedStatuses.includes(statusOf(r)));
    const value = (r: AnyRow) => {
      if (sortKey === 'inflow') return amountOf(r);
      if (sortKey === 'outflow') return -amountOf(r);
      if (sortKey === 'abs_amount') return Math.abs(amountOf(r));
      if (sortKey === 'lots') return Math.abs(lotsOf(r));
      if (sortKey === 'buy') return buyOf(r);
      if (sortKey === 'sell') return sellOf(r);
      if (sortKey === 'price') return priceOf(r) ?? -Infinity;
      if (sortKey === 'pct') return pctOf(r) ?? -Infinity;
      return 0;
    };
    return [...filtered].sort((a, b) => value(b) - value(a));
  }, [sourceRows, selectedStatuses, sortKey]);

  const focus = useMemo(() => {
    const pos = sourceRows.filter((r) => amountOf(r) > 0);
    const neg = sourceRows.filter((r) => amountOf(r) < 0);
    const max = (arr: AnyRow[], fn: (r: AnyRow) => number) => arr.length ? [...arr].sort((a, b) => fn(b) - fn(a))[0] : null;
    return {
      inflow: max(pos, amountOf),
      outflow: max(neg, (r) => Math.abs(amountOf(r))),
      mostAdd: max(sourceRows.filter((r) => buyOf(r) > 0), (r) => buyOf(r) * 1000000 + Math.max(0, lotsOf(r))),
      mostReduce: max(sourceRows.filter((r) => sellOf(r) > 0), (r) => sellOf(r) * 1000000 + Math.abs(Math.min(0, lotsOf(r)))),
    };
  }, [sourceRows]);

  function toggleStatus(s: Status) {
    setSelectedStatuses((prev) => prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]);
  }

  return (
    <main className="v113-signals-page">
      <section className="v113-section v113-today-head">
        <h1>今日訊號</h1>
        <DataQuality data={data} />
        <div className="v113-focus-grid">
          <FocusCard title="淨資金流入最多" row={focus.inflow} kind="red" />
          <FocusCard title="淨資金流出最多" row={focus.outflow} kind="green" />
          <FocusCard title="最多 ETF 加碼" row={focus.mostAdd} kind="red" />
          <FocusCard title="最多 ETF 減碼" row={focus.mostReduce} kind="green" />
        </div>
      </section>

      <section className="v113-section v113-list-section">
        <h2>資金交易明細：共 {fmt0(rows.length)} 檔</h2>
        <div className="v113-status-row">
          {STATUSES.map((s) => <StatusPill key={s} label={s} count={statusCount[s]} active={selectedStatuses.includes(s)} onClick={() => toggleStatus(s)} />)}
        </div>
        <div className="v113-sort-row" aria-label="排序">
          <SortPill label="淨流入" active={sortKey === 'inflow'} onClick={() => setSortKey('inflow')} />
          <SortPill label="淨流出" active={sortKey === 'outflow'} onClick={() => setSortKey('outflow')} />
          <SortPill label="絕對金額" active={sortKey === 'abs_amount'} onClick={() => setSortKey('abs_amount')} />
          <SortPill label="張數" active={sortKey === 'lots'} onClick={() => setSortKey('lots')} />
          <SortPill label="買進ETF" active={sortKey === 'buy'} onClick={() => setSortKey('buy')} />
          <SortPill label="賣出ETF" active={sortKey === 'sell'} onClick={() => setSortKey('sell')} />
          <SortPill label="股價" active={sortKey === 'price'} onClick={() => setSortKey('price')} />
          <SortPill label="漲跌幅" active={sortKey === 'pct'} onClick={() => setSortKey('pct')} />
        </div>
        <div className="v113-table-head"><span>標的</span><span>股價</span><span>淨額 / 張數</span><span>狀態 / 共識</span></div>
        <div className="v113-rows">
          {rows.length ? rows.map((row, idx) => <SignalRow row={row} key={`${codeOf(row)}-${idx}`} />) : <div className="v113-no-data">目前沒有符合篩選的今日訊號。</div>}
        </div>
      </section>
    </main>
  );
}
"""

css = """
/* ===== V113 signal compact layout cleanup ===== */
html,body{max-width:100%;overflow-x:hidden;}
.v113-signals-page{width:100%;max-width:760px;margin:0 auto;padding:22px 16px 80px;color:#111827;overflow:hidden;}
.v113-section{margin:0 0 26px;}
.v113-section h1{font-size:42px;line-height:1.05;margin:0 0 10px;font-weight:1000;letter-spacing:-.04em;}
.v113-section h2{font-size:34px;line-height:1.08;margin:0 0 14px;font-weight:1000;letter-spacing:-.04em;}
.v113-quality{margin:0 0 16px;color:#778397;font-size:17px;font-weight:900;line-height:1.45;}
.v113-quality b{color:#111827;}
.v113-warn{color:#b7791f;}
.v113-focus-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.v113-focus-card{display:block;text-decoration:none;border-radius:18px;padding:15px 15px 14px;border:1.5px solid #e5eaf2;min-height:150px;color:#111827;background:#fff;overflow:hidden;}
.v113-focus-card.red{background:#fff8f8;border-color:#f7cbd1;}
.v113-focus-card.green{background:#f2fffa;border-color:#bfeedd;}
.v113-focus-title{font-size:21px;font-weight:1000;margin-bottom:8px;line-height:1.1;}
.v113-focus-card.red .v113-focus-title{color:#df5361;}
.v113-focus-card.green .v113-focus-title{color:#22a879;}
.v113-focus-name{display:flex;align-items:baseline;gap:7px;flex-wrap:wrap;font-size:24px;font-weight:1000;line-height:1.08;margin-bottom:3px;}
.v113-focus-name em{font-style:normal;font-size:17px;color:#8995a8;font-weight:900;}
.v113-focus-price{display:flex;align-items:baseline;gap:7px;margin-bottom:6px;min-width:0;}
.v113-focus-price span{font-size:34px;font-weight:1000;letter-spacing:-.03em;color:#111827;line-height:1;}
.v113-focus-price b{font-size:19px;font-weight:1000;white-space:nowrap;}
.v113-focus-meta{font-size:16px;line-height:1.38;color:#7b8798;font-weight:900;display:grid;gap:1px;}
.v113-focus-meta b{font-size:17px;}
.v113-empty{font-size:18px;color:#8390a2;font-weight:900;margin-top:18px;}
.v113-status-row,.v113-sort-row{display:flex;gap:10px;overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;scrollbar-width:none;padding:0 18px 8px 0;margin-right:-16px;}
.v113-status-row::-webkit-scrollbar,.v113-sort-row::-webkit-scrollbar{display:none;}
.v113-status-pill,.v113-sort-pill{border:2px solid #cbd5e1;background:#fff;border-radius:999px;padding:9px 15px;font-size:19px;font-weight:1000;color:#667386;white-space:nowrap;flex:0 0 auto;}
.v113-status-pill.active.s-新增{border-color:#c9ab00;color:#b59b00;background:#fffdf0;}
.v113-status-pill.active.s-刪除{border-color:#a9b2bf;color:#6b7280;background:#f8fafc;}
.v113-status-pill.active.s-加碼{border-color:#df5361;color:#df5361;background:#fff8f8;}
.v113-status-pill.active.s-減碼{border-color:#22a879;color:#22a879;background:#f2fffa;}
.v113-sort-pill.active{border-color:#bfdbfe;background:#eff6ff;color:#2765bd;}
.v113-table-head{display:grid;grid-template-columns:1.05fr .72fr 1fr .88fr;gap:8px;background:#f3f6fa;color:#667386;font-size:15px;font-weight:1000;padding:10px 12px;border-radius:14px 14px 0 0;margin-top:4px;}
.v113-rows{border-top:1px solid #e5eaf2;}
.v113-row{display:grid;grid-template-columns:1.05fr .72fr 1fr .88fr;gap:8px;align-items:center;text-decoration:none;color:#111827;padding:15px 12px;border-bottom:1px solid #e5eaf2;}
.v113-r-stock,.v113-r-price,.v113-r-flow,.v113-r-state{min-width:0;}
.v113-r-name{font-size:22px;font-weight:1000;line-height:1.08;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.v113-r-code{font-size:17px;color:#8995a8;font-weight:900;margin-top:2px;}
.v113-r-price span{font-size:23px;font-weight:1000;line-height:1.1;white-space:nowrap;}
.v113-r-price b{display:block;font-size:16px;font-weight:1000;margin-top:2px;white-space:nowrap;}
.v113-r-flow b{display:block;font-size:21px;font-weight:1000;line-height:1.05;white-space:nowrap;text-align:right;}
.v113-r-flow span{display:block;font-size:17px;font-weight:1000;margin-top:4px;white-space:nowrap;text-align:right;}
.v113-r-state{display:flex;flex-direction:column;align-items:flex-end;gap:6px;}
.v113-status{border-radius:999px;padding:4px 9px;font-size:16px;font-weight:1000;line-height:1;white-space:nowrap;}
.v113-status.s-新增{background:#fff5c2;color:#b59b00;}
.v113-status.s-加碼{background:#ffe8ec;color:#df5361;}
.v113-status.s-減碼,.v113-status.s-刪除{background:#dcfce7;color:#22a879;}
.v113-consensus{font-size:16px;font-weight:1000;color:#64748b;white-space:nowrap;}
.limit-up{display:inline-block;background:#df5361!important;color:#fff!important;border-radius:8px;padding:1px 6px;}.limit-down{display:inline-block;background:#22a879!important;color:#fff!important;border-radius:8px;padding:1px 6px;}
.red{color:#df5361!important;}.green{color:#22a879!important;}.muted{color:#8995a8!important;}
.v113-no-data{padding:24px;text-align:center;color:#8390a2;font-size:18px;font-weight:900;}
@media (max-width:520px){
  .v113-signals-page{padding:18px 16px 70px;}
  .v113-section h1{font-size:40px;}
  .v113-section h2{font-size:32px;}
  .v113-focus-grid{gap:10px;}
  .v113-focus-card{padding:13px 12px;min-height:156px;}
  .v113-focus-title{font-size:20px;}
  .v113-focus-name{font-size:22px;}
  .v113-focus-price span{font-size:31px;}
  .v113-focus-price b{font-size:17px;}
  .v113-focus-meta{font-size:15px;}
  .v113-table-head{grid-template-columns:1.05fr .66fr .94fr .74fr;font-size:14px;padding:9px 8px;gap:5px;}
  .v113-row{grid-template-columns:1.05fr .66fr .94fr .74fr;padding:14px 8px;gap:5px;}
  .v113-r-name{font-size:20px;}
  .v113-r-code{font-size:16px;}
  .v113-r-price span{font-size:21px;}
  .v113-r-price b{font-size:15px;}
  .v113-r-flow b{font-size:19px;}
  .v113-r-flow span{font-size:15px;}
  .v113-status{font-size:15px;padding:4px 8px;}
  .v113-consensus{font-size:15px;}
}
@media (max-width:380px){
  .v113-signals-page{padding-left:13px;padding-right:13px;}
  .v113-focus-card{padding:12px 10px;}
  .v113-focus-title{font-size:19px;}
  .v113-focus-price span{font-size:29px;}
  .v113-table-head{grid-template-columns:1.03fr .62fr .92fr .72fr;}
  .v113-row{grid-template-columns:1.03fr .62fr .92fr .72fr;}
  .v113-r-name{font-size:19px;}
}
/* ===== end V113 ===== */
"""

readme = """
# V113 今日訊號排版修正

修正內容：

1. 移除 V112 自己新增的「訊號區間」，避免和原本頁面上的訊號區間重複。
2. 資金交易明細改成固定四欄：標的 / 股價 / 淨額張數 / 狀態共識。
3. 移除每列第二行雜亂資訊，避免「漲停」標籤與買賣共識擠在一起。
4. 保留排序與篩選功能。
5. 每列仍可點進個股頁。
6. 限價燈號保留在股價欄，不會再跑到狀態欄。
"""

write(FRONTEND / 'components' / 'SignalsClient.tsx', signals_client)

css_path = FRONTEND / 'app' / 'globals.css'
backup(css_path)
old = css_path.read_text(encoding='utf-8') if css_path.exists() else ''
for start, end in [
    ('/* ===== V112 signal logic + mobile UI cleanup ===== */', '/* ===== end V112 ===== */'),
    ('/* ===== V113 signal compact layout cleanup ===== */', '/* ===== end V113 ===== */'),
]:
    while start in old and end in old:
        before = old.split(start)[0]
        after = old.split(end, 1)[1]
        old = before.rstrip() + '\n' + after.lstrip()
new = old.rstrip() + '\n' + css.strip() + '\n'
css_path.write_text(new, encoding='utf-8')
print(f'✅ 更新 {css_path}')

write(ROOT / 'README_V113_SIGNAL_COMPACT_LAYOUT.md', readme)
print('\n✅ V113 已完成：移除重複訊號區間，並重排交易明細為固定四欄。')
