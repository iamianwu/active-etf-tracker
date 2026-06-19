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

def backup(path: Path, tag="v90"):
    if path.exists():
        bak = path.with_suffix(path.suffix + f".bak_{tag}")
        if not bak.exists():
            bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

def write(path: Path, content: str):
    backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"✅ wrote {path.relative_to(ROOT)}")

def has_external_range_tabs():
    targets = [
        APP / "signals" / "page.tsx",
        APP / "signals" / "[type]" / "page.tsx",
    ]
    for p in targets:
        if p.exists():
            s = p.read_text(encoding="utf-8")
            if "訊號區間" in s or "signal-range" in s or "range-tabs" in s:
                return True
    return False

hide_internal_range = has_external_range_tabs()
print(f"訊號區間是否已由 page 提供：{'是，SignalsClient 會隱藏內建區間' if hide_internal_range else '否，SignalsClient 會保留內建區間'}")

range_render = "" if hide_internal_range else "<RangeTabs current={range} />"

signals_client_template = r'''
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

function usable(r: any) {
  return isStockCode(stockCode(r)) && !!stockName(r);
}

function lotsDelta(r: any) {
  return num(r?.delta_lots ?? r?.change_lots ?? r?.shares_change ?? r?.delta_shares ?? r?.deltaShares ?? r?.changeShares, 0);
}

function SortButton({ label, k, sortKey, sortDir, onClick }: any) {
  const active = sortKey === k;
  return <button className={active ? 'active' : ''} onClick={onClick}>{label}<span>{active ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}</span></button>;
}

function RangeTabs({ current }: { current: string }) {
  const tabs = [
    ['1', '今日', '/signals'],
    ['5', '5日', '/signals?days=5'],
    ['10', '10日', '/signals?days=10'],
    ['20', '20日', '/signals?days=20'],
  ];
  return (
    <section className="v89-range-card">
      <div className="v89-range-title">訊號區間</div>
      <div className="v89-segment four">
        {tabs.map(([v, label, href]) => <Link key={v} href={href} className={String(current) === v ? 'active' : ''}>{label}</Link>)}
      </div>
    </section>
  );
}

function FocusCard({ title, item, tone }: { title: string; item: any; tone: 'red' | 'green' }) {
  if (!item) return <div className={`v89-focus ${tone}`}><h3>{title}</h3><div className="v89-empty">尚無有效訊號</div></div>;
  const code = stockCode(item);
  const flow = flowBillionOf(item);
  const add = addEtfCount(item);
  const reduce = reduceEtfCount(item);
  const delta = lotsDelta(item);
  const consensus = add || reduce ? `${add}:${reduce}` : (delta ? `張數 ${fmtSigned(delta, 0)}` : '0:0');

  return (
    <Link href={`/stock/${code}?from=signals`} className={`v89-focus ${tone}`}>
      <h3>{title}</h3>
      <div className="v89-focus-grid">
        <div>
          <div className="v89-focus-name">{stockName(item)} <span>{code}</span></div>
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
  const rows = rowsOf(data).filter(usable);
  const [enabled, setEnabled] = useState<Status[]>(['新增', '刪除', '加碼', '減碼', '異動']);
  const [sortKey, setSortKey] = useState<SortKey>('flow');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const range = String(data?.range_days || data?.signalRangeDays || data?.days || 1);

  const { summary, focus } = useMemo(() => {
    const summary: Record<Status, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0, 異動: 0 };
    rows.forEach((r) => { summary[statusOf(r) as Status] += 1; });

    const withFlow = rows.map((r) => ({
      r,
      flow: flowBillionOf(r),
      add: addEtfCount(r),
      reduce: reduceEtfCount(r),
      status: statusOf(r),
      delta: lotsDelta(r),
    }));

    const validFlow = withFlow.filter((x) => Number.isFinite(x.flow));
    const addPoolByCount = withFlow.filter((x) => x.add > 0);
    const reducePoolByCount = withFlow.filter((x) => x.reduce > 0);
    const addPoolFallback = withFlow.filter((x) => x.status === '加碼' || x.delta > 0);
    const reducePoolFallback = withFlow.filter((x) => x.status === '減碼' || x.delta < 0);

    const mostAdd =
      [...addPoolByCount].sort((a, b) => b.add - a.add || Math.abs(b.flow || 0) - Math.abs(a.flow || 0))[0]?.r ||
      [...addPoolFallback].sort((a, b) => Math.abs(b.flow || 0) - Math.abs(a.flow || 0) || Math.abs(b.delta) - Math.abs(a.delta))[0]?.r ||
      null;

    const mostReduce =
      [...reducePoolByCount].sort((a, b) => b.reduce - a.reduce || Math.abs(b.flow || 0) - Math.abs(a.flow || 0))[0]?.r ||
      [...reducePoolFallback].sort((a, b) => Math.abs(b.flow || 0) - Math.abs(a.flow || 0) || Math.abs(b.delta) - Math.abs(a.delta))[0]?.r ||
      null;

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
      return stockName(r);
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
      __RANGE_RENDER__

      <section className="v89-title">
        <h1>{range === '1' ? '今日訊號' : `${range}日訊號`}</h1>
        <p>已抓取 {fetched || total || 0} / {total || fetched || 0} 檔 ETF，資料日期 {shortDate(latestDateOf(data))}</p>
      </section>

      <section className="v89-focus-wrap">
        <FocusCard title="資金流入最多" item={focus.inflow} tone="red" />
        <FocusCard title="資金流出最多" item={focus.outflow} tone="green" />
        <FocusCard title="最多 ETF 加碼" item={focus.mostAdd} tone="red" />
        <FocusCard title="最多 ETF 減碼" item={focus.mostReduce} tone="green" />
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
              <div className="v89-name-cell"><b>{stockName(r)}</b><span>{code}</span></div>
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
signals_client = signals_client_template.replace("__RANGE_RENDER__", range_render)
write(COMP / "SignalsClient.tsx", signals_client)

stock_detail = r'''
'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { rowsOf, quoteOf, stockCode, stockName, etfCode, etfName, fmtFree, fmtPct, fmtSigned, priceOf, changePctOf, marketValueBillionOf, sharesLotsOf, allHoldingHistory, trendRowsFromAny, dateOf, shortDate, sortRows, toneClass, num, toggleFavorite, favoriteExists, type SortDir } from './mobileV89Utils';

type Tab = 'overview' | 'whale' | 'rank' | 'detail';
type SortKey = 'lots' | 'value' | 'delta5' | 'delta20' | 'delta60' | 'weight' | 'code';
type RankDays = 5 | 20 | 60;

function useBack() {
  return () => {
    if (typeof window !== 'undefined' && window.history.length > 1) window.history.back();
    else window.location.href = '/holdings';
  };
}

function axisTick(v: any) {
  const n = Number(v);
  if (!Number.isFinite(n)) return '';
  const abs = Math.abs(n);
  if (abs >= 10000) return `${(n / 10000).toFixed(abs >= 100000 ? 0 : 1)}萬`;
  if (abs >= 1000) return `${(n / 1000).toFixed(abs >= 10000 ? 0 : 1)}K`;
  return `${Math.round(n)}`;
}

function Header({ code, name }: any) {
  const back = useBack();
  const [fav, setFav] = useState(false);
  return (
    <header className="v89-detail-header">
      <button onClick={back} className="back">‹</button>
      <div><b>{code}</b><span>{name}</span></div>
      <button className="star" onClick={() => setFav(toggleFavorite({ code, name, type: 'stock' }))}>{fav || favoriteExists(code, 'stock') ? '★' : '☆'}</button>
    </header>
  );
}

function Tabs({ tab, setTab }: any) {
  const tabs: [Tab, string][] = [['overview', '總覽'], ['whale', 'ETF持股變化'], ['rank', '加減碼排行'], ['detail', '持股明細']];
  return <nav className="v89-detail-tabs">{tabs.map(([k, label]) => <button key={k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)}>{label}</button>)}</nav>;
}

function MiniArea({ rows, color = 'red', height = 210 }: any) {
  if (!Array.isArray(rows) || rows.length < 2) return <div className="v89-empty-box">目前沒有足夠的歷史資料</div>;
  return (
    <div className="v89-chart-box">
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={rows} margin={{ top: 8, right: 10, left: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="4 4" vertical={false} />
          <XAxis dataKey="date" tickFormatter={(v) => shortDate(v)} minTickGap={20} />
          <YAxis width={54} tickFormatter={axisTick} domain={['auto', 'auto']} />
          <Tooltip formatter={(v: any) => [fmtFree(v, 0), '張數']} labelFormatter={(v) => `日期：${v}`} />
          <Area type="monotone" dataKey="value" stroke={color === 'red' ? '#df555d' : '#27a575'} fill={color === 'red' ? '#fff1f2' : '#ecfdf5'} strokeWidth={2.2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function buildEtfRows(data: any, currentRows: any[]) {
  const hist = allHoldingHistory(data);
  const currentMap: Record<string, any> = {};
  currentRows.forEach((r) => { if (etfCode(r)) currentMap[etfCode(r)] = r; });

  if (!hist.length) {
    return currentRows
      .map((r) => ({
        raw: r,
        code: etfCode(r),
        name: etfName(r),
        lots: sharesLotsOf(r),
        value: marketValueBillionOf(r),
        weight: num(r?.weight),
        delta5: NaN,
        delta20: NaN,
        delta60: NaN,
        latestDate: dateOf(r),
      }))
      .filter((x) => x.code);
  }

  const groups: Record<string, any[]> = {};
  hist.forEach((r) => {
    const c = etfCode(r);
    if (!groups[c]) groups[c] = [];
    groups[c].push(r);
  });

  return Object.entries(groups).map(([code, list]) => {
    const sorted = [...list].sort((a, b) => dateOf(a).localeCompare(dateOf(b)));
    const latest = sorted[sorted.length - 1];
    const prev5 = sorted[Math.max(0, sorted.length - 6)];
    const prev20 = sorted[Math.max(0, sorted.length - 21)];
    const prev60 = sorted[Math.max(0, sorted.length - 61)];
    const lots = sharesLotsOf(latest);
    const cur = currentMap[code] || latest;
    return {
      raw: cur,
      code,
      name: etfName(cur) || etfName(latest),
      lots,
      value: marketValueBillionOf(cur),
      weight: num(cur?.weight ?? latest?.weight),
      delta5: sorted.length >= 2 ? lots - sharesLotsOf(prev5) : NaN,
      delta20: sorted.length >= 2 ? lots - sharesLotsOf(prev20) : NaN,
      delta60: sorted.length >= 2 ? lots - sharesLotsOf(prev60) : NaN,
      latestDate: dateOf(latest),
    };
  });
}

function totalHoldingTrend(data: any) {
  const hist = allHoldingHistory(data);
  if (!hist.length) return [];
  const map: Record<string, number> = {};
  hist.forEach((r) => {
    const d = dateOf(r);
    const v = sharesLotsOf(r);
    if (d && Number.isFinite(v)) map[d] = (map[d] || 0) + v;
  });
  return Object.entries(map).sort(([a], [b]) => a.localeCompare(b)).map(([date, value]) => ({ date, value })).slice(-180);
}

function SortButton({ label, k, sortKey, sortDir, onClick }: any) {
  const active = sortKey === k;
  return <button className={active ? 'active' : ''} onClick={onClick}>{label}<span>{active ? (sortDir === 'desc' ? '↓' : '↑') : '↕'}</span></button>;
}

export default function StockDetailClient(props: any) {
  const data = props?.data || props;
  const quote = quoteOf(data);
  const code = stockCode(quote) || data?.stock_code || data?.code;
  const name = stockName(quote) || data?.stock_name || data?.name;
  const [tab, setTab] = useState<Tab>('overview');
  const [sortKey, setSortKey] = useState<SortKey>('value');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [rankDays, setRankDays] = useState<RankDays>(20);

  const currentRows = rowsOf(data);
  const etfRows = useMemo(() => buildEtfRows(data, currentRows), [data, currentRows]);
  const totalLots = etfRows.reduce((a, r) => a + (Number.isFinite(r.lots) ? r.lots : 0), 0);
  const totalValue = etfRows.reduce((a, r) => a + (Number.isFinite(r.value) ? r.value : 0), 0);
  const delta5 = etfRows.reduce((a, r) => a + (Number.isFinite(r.delta5) ? r.delta5 : 0), 0);
  const delta20 = etfRows.reduce((a, r) => a + (Number.isFinite(r.delta20) ? r.delta20 : 0), 0);
  const delta60 = etfRows.reduce((a, r) => a + (Number.isFinite(r.delta60) ? r.delta60 : 0), 0);

  const holdingTrend = useMemo(() => totalHoldingTrend(data), [data]);
  const priceTrend = trendRowsFromAny(data);

  const sortedEtfRows = useMemo(() => sortRows(etfRows, (r: any) => {
    if (sortKey === 'lots') return r.lots;
    if (sortKey === 'delta5') return r.delta5;
    if (sortKey === 'delta20') return r.delta20;
    if (sortKey === 'delta60') return r.delta60;
    if (sortKey === 'weight') return r.weight;
    if (sortKey === 'code') return r.code;
    return r.value;
  }, sortDir), [etfRows, sortKey, sortDir]);

  function toggleSort(k: SortKey) {
    if (sortKey === k) setSortDir((d) => d === 'desc' ? 'asc' : 'desc');
    else { setSortKey(k); setSortDir('desc'); }
  }

  const rankKey = rankDays === 5 ? 'delta5' : rankDays === 60 ? 'delta60' : 'delta20';
  const addRank = [...etfRows].filter((r: any) => Number.isFinite(r[rankKey]) && r[rankKey] > 0).sort((a: any, b: any) => b[rankKey] - a[rankKey]).slice(0, 5);
  const reduceRank = [...etfRows].filter((r: any) => Number.isFinite(r[rankKey]) && r[rankKey] < 0).sort((a: any, b: any) => a[rankKey] - b[rankKey]).slice(0, 5);

  return (
    <main className="v89-detail-page">
      <Header code={code} name={name} />
      <Tabs tab={tab} setTab={setTab} />

      {tab === 'overview' && <section className="v89-section">
        <div className="v89-stock-quote">
          <div><span>股價</span><b className={toneClass(changePctOf(quote))}>{fmtFree(priceOf(quote), 1)}</b><small>{fmtPct(changePctOf(quote), 2)}</small></div>
          <div><span>主動 ETF 持股熱度</span><b>{fmtFree(etfRows.length, 0)} 檔</b><small>總市值 {fmtFree(totalValue, 2)} 億</small></div>
        </div>
        <div className="v89-kpi-grid four">
          <div><span>持有 ETF</span><b>{fmtFree(etfRows.length, 0)}</b><small>檔</small></div>
          <div><span>總持股張數</span><b>{fmtFree(totalLots, 0)}</b><small>張</small></div>
          <div><span>近5日變化</span><b className={toneClass(delta5)}>{fmtSigned(delta5, 0)}</b><small>張</small></div>
          <div><span>近20日變化</span><b className={toneClass(delta20)}>{fmtSigned(delta20, 0)}</b><small>張</small></div>
        </div>
        <div className={`v89-insight ${delta20 >= 0 ? 'red' : 'green'}`}>
          <b>🎯 主動 ETF 近期{delta20 >= 0 ? '偏加碼' : '偏減碼'}</b>
          <span>近20日淨變化 {fmtSigned(delta20, 0, ' 張')}</span>
        </div>
        <h2>主動 ETF 總持股趨勢</h2>
        <MiniArea rows={holdingTrend.length ? holdingTrend : priceTrend} color={delta20 >= 0 ? 'red' : 'green'} />
        <h2>持有 ETF 明細</h2>
        <EtfHoldingList rows={sortedEtfRows.slice(0, 8)} />
      </section>}

      {tab === 'whale' && <section className="v89-section">
        <h1>ETF 大戶持股總覽</h1>
        <div className="v89-kpi-grid four">
          <div><span>持有 ETF 檔數</span><b>{fmtFree(etfRows.length, 0)}</b></div>
          <div><span>總持股張數</span><b>{fmtFree(totalLots, 0)}</b></div>
          <div><span>總持股市值</span><b>{fmtFree(totalValue, 2)}</b><small>億</small></div>
          <div><span>近20日變化</span><b className={toneClass(delta20)}>{fmtSigned(delta20, 0)}</b><small>張</small></div>
        </div>
        <h2>總持股趨勢</h2>
        <MiniArea rows={holdingTrend} color={delta20 >= 0 ? 'red' : 'green'} />
      </section>}

      {tab === 'rank' && <section className="v89-section">
        <div className="v89-range-mini">
          {[5, 20, 60].map((d) => <button key={d} className={rankDays === d ? 'active' : ''} onClick={() => setRankDays(d as RankDays)}>近{d}日</button>)}
        </div>
        <RankCard title={`近${rankDays}日加碼 TOP5`} rows={addRank} keyName={rankKey} positive />
        <RankCard title={`近${rankDays}日減碼 TOP5`} rows={reduceRank} keyName={rankKey} positive={false} />
        {addRank.length + reduceRank.length === 0 && <div className="v89-empty-box">目前沒有足夠的 ETF 歷史持股變動資料</div>}
      </section>}

      {tab === 'detail' && <section className="v89-section">
        <div className="v89-sort-row sticky">
          <SortButton label="市值" k="value" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('value')} />
          <SortButton label="張數" k="lots" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('lots')} />
          <SortButton label="近5日" k="delta5" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('delta5')} />
          <SortButton label="近20日" k="delta20" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('delta20')} />
          <SortButton label="近60日" k="delta60" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('delta60')} />
        </div>
        <EtfHoldingList rows={sortedEtfRows} />
      </section>}
    </main>
  );
}

function RankCard({ title, rows, keyName, positive }: any) {
  return (
    <section className={`v89-rank-card ${positive ? 'red' : 'green'}`}>
      <h2>{title}</h2>
      {rows.length === 0 && <div className="v89-empty-box small">目前沒有資料</div>}
      {rows.map((r: any, i: number) => (
        <Link href={`/etf/${r.code}?from=stock`} className="v89-rank-item" key={r.code}>
          <span>{i + 1}</span>
          <div><b>{r.code}</b><small>{r.name}</small></div>
          <strong>{fmtSigned(r[keyName], 0, ' 張')}</strong>
        </Link>
      ))}
    </section>
  );
}

function EtfHoldingList({ rows }: { rows: any[] }) {
  if (!rows.length) return <div className="v89-empty-box">目前沒有 ETF 持股資料</div>;
  return (
    <div className="v89-etf-holding-list">
      {rows.map((r) => (
        <Link key={r.code} href={`/etf/${r.code}?from=stock`} className="v89-etf-holding-row">
          <div><b>{r.code}</b><span>{r.name}</span></div>
          <div><b>{fmtFree(r.lots, 0)} 張</b><span>{fmtFree(r.value, 2)} 億</span></div>
          <div><b className={toneClass(r.delta5)}>{Number.isFinite(r.delta5) ? fmtSigned(r.delta5, 0) : '-'}</b><span>近5日</span></div>
          <div><b className={toneClass(r.delta20)}>{Number.isFinite(r.delta20) ? fmtSigned(r.delta20, 0) : '-'}</b><span>近20日</span></div>
        </Link>
      ))}
    </div>
  );
}
'''
write(COMP / "StockDetailClient.tsx", stock_detail)

css_path = APP / "globals.css"
if css_path.exists():
    backup(css_path)
    old = css_path.read_text(encoding="utf-8")
    patch_css = r'''
/* ===== V90 refinement: no duplicate gaps, better mobile charts ===== */
.v89-page > .v89-range-card + .v89-range-card { display: none !important; }
.v89-page .v89-range-card { margin-top: 10px; margin-bottom: 14px; }
.v89-focus { min-height: 134px; }
.v89-focus-price { font-size: 22px; }
.v89-focus-info b { white-space: normal; }
.v89-chart-box .recharts-yAxis .recharts-cartesian-axis-tick-value {
  font-size: 12px;
  font-weight: 700;
}
.v89-range-mini {
  margin: 4px 0 12px;
}
.v89-range-mini button {
  min-width: 76px;
}
@media(max-width:390px){
  .v89-focus-wrap{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
  .v89-focus{padding:10px;min-height:126px}
  .v89-focus h3{font-size:15px}
  .v89-focus-name{font-size:15px}
  .v89-focus-price{font-size:20px}
}
'''
    if "V90 refinement" not in old:
        css_path.write_text(old + "\n\n" + patch_css, encoding="utf-8")
        print("✅ appended V90 CSS")
    else:
        print("ℹ️ V90 CSS already exists")

readme = r'''
# V90 Refinement Patch

修正內容：
1. 今日訊號區間重複問題：如果 page 已經提供區間切換，SignalsClient 不再重複顯示。
2. 今日訊號「最多 ETF 加碼 / 減碼」：
   - 優先使用 add_etf_count / reduce_etf_count。
   - 若沒有這些欄位，改用 status=加碼 / 減碼 與資金流向、張數變化 fallback，不再直接顯示「尚無有效訊號」。
3. 個股詳情 ETF 持股趨勢圖：
   - Y 軸加寬。
   - 數字改成 K / 萬 格式，避免 12000 被截成 2000。
4. 個股加減碼排行：
   - 加入近 5 日 / 20 日 / 60 日切換。
5. 持股明細：
   - 保留排序，並補近 60 日排序。
'''
write(ROOT / "README_V90_REFINEMENT.md", readme)

print("\n✅ V90 refinement 已套用。下一步：")
print("cd frontend")
print("[ -d node_modules ] || npm install")
print("npm run build")
