#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
COMP = FRONTEND / "components"
APP = FRONTEND / "app"

signals = COMP / "SignalsClient.tsx"
css = APP / "globals.css"

if not FRONTEND.exists():
    raise SystemExit("❌ 找不到 frontend 目錄，請在 repo 根目錄執行。")
if not signals.exists():
    raise SystemExit("❌ 找不到 frontend/components/SignalsClient.tsx。")

def backup(path: Path, tag="v99"):
    if path.exists():
        bak = path.with_suffix(path.suffix + f".bak_{tag}")
        if not bak.exists():
            bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

backup(signals)

signals_code = r'''
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
  '8210': '勤誠',
  '4105': '東洋',
};

function fixedStockName(r: any) {
  const c = stockCode(r);
  return STOCK_NAME_FIX[c] || stockName(r);
}

function usable(r: any) {
  return isStockCode(stockCode(r)) && !!fixedStockName(r);
}

function rawLotsDelta(r: any) {
  return num(
    r?.net_delta_lots ??
    r?.delta_lots ??
    r?.change_lots ??
    r?.lots_delta ??
    r?.deltaLots ??
    r?.shares_change_lots ??
    r?.delta_shares_lots ??
    r?.shares_change ??
    r?.delta_shares ??
    r?.deltaShares ??
    r?.changeShares,
    NaN
  );
}

function normalizeLotsDelta(v: number) {
  if (!Number.isFinite(v)) return NaN;
  // 後端有時給「股」，前端需要顯示「張」。
  // 例如 +3,400,000 應該是 +3,400 張。
  if (Math.abs(v) >= 100000) return v / 1000;
  return v;
}

function rowNetLots(r: any) {
  const v = normalizeLotsDelta(rawLotsDelta(r));
  return Number.isFinite(v) ? v : 0;
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

function statusFromNet(netLots: number, add: number, reduce: number, statuses: string[]): Status {
  // v99 核心修正：
  // 只要有淨張數，就用淨張數決定方向，避免「明細減碼，但焦點卡顯示流入」。
  if (netLots > 0) {
    if (statuses.includes('新增') && !statuses.includes('刪除') && !statuses.includes('減碼')) return '新增';
    return '加碼';
  }
  if (netLots < 0) {
    if (statuses.includes('刪除') && !statuses.includes('新增') && !statuses.includes('加碼')) return '刪除';
    return '減碼';
  }

  if (add > reduce) return '加碼';
  if (reduce > add) return '減碼';
  if (statuses.includes('新增') && !statuses.includes('刪除')) return '新增';
  if (statuses.includes('刪除') && !statuses.includes('新增')) return '刪除';
  return '異動';
}

function tradeAmountBillionFromLots(lots: number, price: number) {
  if (!Number.isFinite(lots) || !Number.isFinite(price) || lots === 0) return NaN;
  return lots * 1000 * price / 100000000;
}

function signalAmountBillion(r: any) {
  const lots = rowNetLots(r);
  const px = priceOf(r);
  const computed = tradeAmountBillionFromLots(lots, px);
  if (Number.isFinite(computed)) return computed;

  // fallback：如果沒有張數，只能用原本 flow，但要依 status 修正方向。
  const raw = flowBillionOf(r);
  if (!Number.isFinite(raw)) return NaN;
  const s = statusOf(r);
  if (s === '減碼' || s === '刪除') return -Math.abs(raw);
  if (s === '加碼' || s === '新增') return Math.abs(raw);
  return raw;
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
    const base =
      [...list].sort((a, b) =>
        Math.abs(signalAmountBillion(b) || 0) - Math.abs(signalAmountBillion(a) || 0)
      )[0] || list[0];

    const netLots = list.reduce((sum, r) => sum + rowNetLots(r), 0);
    const add = list.reduce((sum, r) => sum + rowAddCount(r), 0);
    const reduce = list.reduce((sum, r) => sum + rowReduceCount(r), 0);
    const statuses = list.map((r) => statusOf(r));
    const status = statusFromNet(netLots, add, reduce, statuses);
    const px = priceOf(base);
    const computedAmount = tradeAmountBillionFromLots(netLots, px);

    let fallbackFlow = list.reduce((sum, r) => {
      const v = flowBillionOf(r);
      return sum + (Number.isFinite(v) ? v : 0);
    }, 0);

    if (!Number.isFinite(fallbackFlow)) fallbackFlow = 0;

    const amount = Number.isFinite(computedAmount)
      ? computedAmount
      : (
          status === '減碼' || status === '刪除'
            ? -Math.abs(fallbackFlow)
            : status === '加碼' || status === '新增'
              ? Math.abs(fallbackFlow)
              : fallbackFlow
        );

    return {
      ...base,
      stock_code: code,
      code,
      stock_name: fixedStockName(base),
      name: fixedStockName(base),

      // v99：下面所有 flow 欄位都改成「交易淨額」，不是持股市值因股價波動造成的變化。
      flow_billion: amount,
      money_billion: amount,
      amount_billion: amount,
      delta_amount_billion: amount,
      delta_value_billion: amount,
      net_amount_billion: amount,

      add_etf_count: add,
      add_count: add,
      buy_etf_count: add,
      buy_count: add,
      reduce_etf_count: reduce,
      reduce_count: reduce,
      sell_etf_count: reduce,
      sell_count: reduce,

      delta_lots: netLots,
      change_lots: netLots,
      net_delta_lots: netLots,
      status,
      _merged_count: list.length,
    };
  });
}

function isPositiveStatus(r: any) {
  const s = statusOf(r);
  return s === '新增' || s === '加碼';
}

function isNegativeStatus(r: any) {
  const s = statusOf(r);
  return s === '刪除' || s === '減碼';
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
  const flow = signalAmountBillion(item);
  const add = addEtfCount(item);
  const reduce = reduceEtfCount(item);
  const deltaLots = rowNetLots(item);

  const consensus = countMode
    ? `買賣檔數 ${add || 0}:${reduce || 0}`
    : (Number.isFinite(deltaLots) && deltaLots !== 0 ? `淨張數 ${fmtSigned(deltaLots, 0)}` : `買賣檔數 ${add || 0}:${reduce || 0}`);

  return (
    <Link href={`/stock/${code}?from=signals`} className={`v89-focus ${tone}`}>
      <h3>{title}</h3>
      <div className="v89-focus-grid">
        <div>
          <div className="v89-focus-name">{fixedStockName(item)} <span>{code}</span></div>
          <div className={toneClass(changePctOf(item)) + ' v89-focus-price'}>{fmt(priceOf(item), 1)} <small>{fmtPct(changePctOf(item), 2)}</small></div>
        </div>
        <div className="v89-focus-info">
          <span>交易淨額</span><b className={flow >= 0 ? 'v89-red' : 'v89-green'}>{Number.isFinite(flow) ? fmtSigned(flow, 1, ' 億') : '-'}</b>
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

  // 只保留 page.tsx 的區間切換；SignalsClient 不再自己產生第二組 range tabs。
  const rawRows = rowsOf(data).filter(usable);
  const rows = useMemo(() => mergeSignalRows(rawRows), [rawRows]);

  const [enabled, setEnabled] = useState<Status[]>(['新增', '刪除', '加碼', '減碼', '異動']);
  const [sortKey, setSortKey] = useState<SortKey>('flow');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const range = String(data?.range_days || data?.signalRangeDays || data?.days || 1);

  const { summary, focus } = useMemo(() => {
    const summary: Record<Status, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0, 異動: 0 };
    rows.forEach((r) => {
      const s = statusOf(r) as Status;
      summary[s] = (summary[s] || 0) + 1;
    });

    const withNet = rows
      .map((r) => ({ r, amount: signalAmountBillion(r), add: addEtfCount(r), reduce: reduceEtfCount(r), lots: rowNetLots(r) }))
      .filter((x) => Number.isFinite(x.amount));

    return {
      summary,
      focus: {
        // v99 核心：焦點卡必須與下方明細方向一致
        inflow: [...withNet]
          .filter((x) => x.amount > 0 && isPositiveStatus(x.r))
          .sort((a, b) => b.amount - a.amount || b.add - a.add)[0]?.r || null,

        outflow: [...withNet]
          .filter((x) => x.amount < 0 && isNegativeStatus(x.r))
          .sort((a, b) => a.amount - b.amount || b.reduce - a.reduce)[0]?.r || null,

        mostAdd: [...withNet]
          .filter((x) => isPositiveStatus(x.r) && x.add > 0)
          .sort((a, b) => b.add - a.add || b.amount - a.amount)[0]?.r || null,

        mostReduce: [...withNet]
          .filter((x) => isNegativeStatus(x.r) && x.reduce > 0)
          .sort((a, b) => b.reduce - a.reduce || Math.abs(b.amount) - Math.abs(a.amount))[0]?.r || null,
      }
    };
  }, [rows]);

  const filtered = rows.filter((r) => enabled.includes(statusOf(r) as Status));

  const sorted = useMemo(() => {
    return sortRows(filtered, (r: any) => {
      if (sortKey === 'flow') return signalAmountBillion(r);
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
        <FocusCard title="淨資金流入最多" item={focus.inflow} tone="red" />
        <FocusCard title="淨資金流出最多" item={focus.outflow} tone="green" />
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
          const flow = signalAmountBillion(r);
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

signals.write_text(signals_code.strip() + "\n", encoding="utf-8")
print("✅ wrote frontend/components/SignalsClient.tsx")

if css.exists():
    backup(css)
    c = css.read_text(encoding="utf-8")
    patch_css = r'''
/* ===== V99 signal net logic / duplicate range guard ===== */
.signals-v7-page .signal-range-block + .signal-range-block,
.signals-v7-page .signals-range-block + .signals-range-block,
.signals-v7-page .v75-range-block + .v75-range-block,
.signals-v7-page .signal-range-tabs-wrap + .signal-range-tabs-wrap,
.v89-page .v89-range-card {
  display: none !important;
}
'''
    if "V99 signal net logic" not in c:
        css.write_text(c + "\n\n" + patch_css, encoding="utf-8")
        print("✅ appended V99 CSS")

readme = ROOT / "README_V99_SIGNAL_NET_LOGIC.md"
readme.write_text(
    "# V99 Signal Net Logic\n\n"
    "修正今日訊號焦點卡與明細方向不一致的問題。\n\n"
    "核心修正：\n"
    "1. 先依 stock_code 合併同一檔股票。\n"
    "2. 用淨張數 net lots 決定方向：正數為加碼，負數為減碼。\n"
    "3. 金額改用「淨張數 × 股價」估算交易淨額，不再把股價上漲造成的市值變化誤判為資金流入。\n"
    "4. 焦點卡只能從方向一致的股票挑選：流入只挑加碼/新增，流出只挑減碼/刪除。\n"
    "5. 保留排序功能。\n",
    encoding="utf-8",
)
print("✅ wrote README_V99_SIGNAL_NET_LOGIC.md")

print("\n下一步：git status / commit / push，並等 Vercel Ready。")
