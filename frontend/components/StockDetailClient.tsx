'use client';

import Link from 'next/link';
import {useMemo, useState} from 'react';
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
        <h2>前五大持有 ETF</h2>
        <TopEtfPreview
          rows={[...etfRows].sort((a: any, b: any) => (Number.isFinite(b.value) ? b.value : 0) - (Number.isFinite(a.value) ? a.value : 0)).slice(0, 5)}
          totalValue={totalValue}
          onMore={() => setTab('detail')}
        />
        <StockRecentOperationPanel data={data} etfRows={etfRows} />
        <StockRecentOperationRecords data={data} etfRows={etfRows} />
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




type StockOpSortKey = 'date' | 'etf' | 'lots' | 'pct' | 'status';
type StockOpSortDir = 'asc' | 'desc';

function stockOpPick(obj: any, keys: string[]): any {
  for (const k of keys) {
    if (obj && obj[k] !== undefined && obj[k] !== null && obj[k] !== '') return obj[k];
  }
  return undefined;
}

function stockOpNum(v: any): number {
  if (typeof num === 'function') return num(v);
  const n = Number(String(v ?? '').replace(/,/g, ''));
  return Number.isFinite(n) ? n : NaN;
}

function stockOpLotsFromAny(v: any): number {
  const n = stockOpNum(v);
  if (!Number.isFinite(n)) return NaN;
  return Math.abs(n) >= 100000 ? n / 1000 : n;
}

function stockOpDate(r: any): string {
  return String(stockOpPick(r, ['data_date', 'date', 'trade_date', 'updated_date', 'dt']) || '');
}

function stockOpCode(r: any): string {
  return String(stockOpPick(r, ['etf_code', 'etfCode', 'code', 'fund_code', 'fundCode']) || '');
}

function stockOpName(r: any, etfMap: Record<string, any>): string {
  const code = stockOpCode(r);
  return String(
    stockOpPick(r, ['etf_name', 'etfName', 'name', 'fund_name', 'fundName']) ||
    etfMap[code]?.name ||
    etfMap[code]?.etf_name ||
    etfMap[code]?.fund_name ||
    ''
  );
}

function stockOpHoldingLots(r: any): number {
  return stockOpLotsFromAny(stockOpPick(r, ['shares', 'shares_lots', 'lots', 'holding_lots', 'quantity', 'qty', 'position_lots']));
}

function stockOpFormatMmdd(v: string): string {
  const s = String(v || '');
  if (!s) return '-';
  const m = s.match(/(\d{4})[-/](\d{2})[-/](\d{2})/);
  if (m) return `${m[2]}/${m[3]}`;
  const m2 = s.match(/(\d{2})[-/](\d{2})/);
  if (m2) return `${m2[1]}/${m2[2]}`;
  return s;
}

function stockOpFormatLotsSigned(v: number): string {
  if (!Number.isFinite(v)) return '-';
  const abs = Math.abs(v);
  if (abs > 0 && abs < 1) return `${v > 0 ? '+' : '-'}<1張`;
  const rounded = Math.round(abs * 100) / 100;
  const integerLike = Math.abs(rounded - Math.round(rounded)) < 1e-8;
  const body = integerLike ? Math.round(rounded).toLocaleString() : rounded.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return `${v > 0 ? '+' : '-'}${body}張`;
}

function stockOpFormatPct(v: number): string {
  if (!Number.isFinite(v)) return '-';
  const abs = Math.abs(v);
  if (abs > 100) {
    const times = Math.min(10, Math.floor(abs / 100));
    if (times >= 1) return `${v > 0 ? '>' : '-'}${times}倍`;
  }
  const digits = abs >= 10 ? 1 : 2;
  const text = abs.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: 0 });
  return `${v > 0 ? '+' : '-'}${text}%`;
}

function buildStockRecentOperationRows(data: any, etfRows: any[]) {
  const etfMap: Record<string, any> = {};
  for (const e of etfRows || []) etfMap[String(e?.code || e?.etf_code || e?.fund_code || '')] = e;

  const raw = ([] as any[]).concat(
    Array.isArray(data?.operation_records) ? data.operation_records : [],
    Array.isArray(data?.operationRecords) ? data.operationRecords : [],
    Array.isArray(data?.recent_operations) ? data.recent_operations : [],
    Array.isArray(data?.recentOperations) ? data.recentOperations : [],
    Array.isArray(data?.stock_operation_records) ? data.stock_operation_records : [],
    Array.isArray(data?.stockOperationRecords) ? data.stockOperationRecords : []
  );

  let rows: any[] = [];

  if (raw.length) {
    rows = raw.map((r: any) => {
      const lots = stockOpLotsFromAny(stockOpPick(r, [
        'delta_lots', 'change_lots', 'deltaLots', 'changeLots',
        'shares_change', 'delta_shares', 'sharesChange', 'deltaShares',
        'change_shares', 'changeShares', 'delta', 'change'
      ]));
      const pct = stockOpNum(stockOpPick(r, ['change_pct', 'delta_pct', 'changePct', 'deltaPct', 'change_percent', 'percent_change', 'pct']));
      return {
        date: stockOpDate(r),
        code: stockOpCode(r),
        name: stockOpName(r, etfMap),
        lots,
        pct,
        status: String(stockOpPick(r, ['status', 'action']) || (lots >= 0 ? '加碼' : '減碼')),
      };
    }).filter((r) => r.code && Number.isFinite(r.lots) && r.lots !== 0);
  }

  if (!rows.length) {
    const hist = ([] as any[]).concat(
      Array.isArray(data?.holding_history) ? data.holding_history : [],
      Array.isArray(data?.holdingHistory) ? data.holdingHistory : [],
      Array.isArray(data?.historyRows) ? data.historyRows : [],
      Array.isArray(data?.history) ? data.history : []
    );

    const grouped: Record<string, any[]> = {};
    for (const r of hist) {
      const code = stockOpCode(r);
      const date = stockOpDate(r);
      if (!code || !date) continue;
      if (!grouped[code]) grouped[code] = [];
      grouped[code].push(r);
    }

    for (const code of Object.keys(grouped)) {
      const list = grouped[code].sort((a, b) => stockOpDate(a).localeCompare(stockOpDate(b)));
      for (let i = 1; i < list.length; i++) {
        const prevLots = stockOpHoldingLots(list[i - 1]);
        const currLots = stockOpHoldingLots(list[i]);
        if (!Number.isFinite(prevLots) || !Number.isFinite(currLots)) continue;
        const delta = currLots - prevLots;
        if (Math.abs(delta) < 0.0001) continue;
        rows.push({
          date: stockOpDate(list[i]),
          code,
          name: stockOpName(list[i], etfMap),
          lots: delta,
          pct: prevLots ? (delta / Math.abs(prevLots)) * 100 : NaN,
          status: delta >= 0 ? '加碼' : '減碼',
        });
      }
    }
  }

  const seen = new Set<string>();
  return rows.filter((r) => {
    const key = [r.date, r.code, r.status, Math.round((r.lots || 0) * 1000)].join('|');
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function StockRecentOperationPanel({ data, etfRows }: { data: any; etfRows: any[] }) {
  const baseRows = buildStockRecentOperationRows(data, etfRows);
  const [openInfo, setOpenInfo] = useState(false);
  const [sortKey, setSortKey] = useState<StockOpSortKey>('date');
  const [sortDir, setSortDir] = useState<StockOpSortDir>('desc');

  if (!baseRows.length) return null;

  function toggleSort(key: StockOpSortKey) {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
      return;
    }
    setSortKey(key);
    setSortDir(key === 'etf' || key === 'status' ? 'asc' : 'desc');
  }

  function sortValue(row: any, key: StockOpSortKey): any {
    if (key === 'date') return String(row.date || '');
    if (key === 'etf') return String(row.code || '');
    if (key === 'lots') return Math.abs(Number(row.lots || 0));
    if (key === 'pct') return Math.abs(Number(row.pct || 0));
    if (key === 'status') return String(row.status || '');
    return '';
  }

  const rows = [...baseRows]
    .sort((a, b) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);
      let cmp = 0;
      if (typeof av === 'number' && typeof bv === 'number') cmp = av - bv;
      else cmp = String(av).localeCompare(String(bv));
      return sortDir === 'asc' ? cmp : -cmp;
    })
    .slice(0, 30);

  const SortBtn = ({ k, children, right = false }: { k: StockOpSortKey; children: React.ReactNode; right?: boolean }) => (
    <button type="button" className={`v96-op-head-btn ${right ? 'right' : ''} ${sortKey === k ? 'active' : ''}`} onClick={() => toggleSort(k)}>
      <span>{children}</span>
      <em>{sortKey === k ? (sortDir === 'asc' ? '▲' : '▼') : '↕'}</em>
    </button>
  );

  return (
    <section className="v96-op-panel">
      <div className="v96-op-title-row">
        <h2>近30日操作記錄</h2>
        <button type="button" className="v96-op-info-btn" onClick={() => setOpenInfo(true)} aria-label="變動資料說明">i</button>
      </div>

      <div className="v96-op-table">
        <div className="v96-op-head">
          <SortBtn k="date">日期</SortBtn>
          <SortBtn k="etf">ETF</SortBtn>
          <SortBtn k="lots" right>變動張數<br />變動幅度</SortBtn>
          <SortBtn k="status" right>狀態</SortBtn>
        </div>

        {rows.map((r: any, idx: number) => {
          const isAdd = r.lots >= 0;
          return (
            <div className="v96-op-row" key={`${r.date}-${r.code}-${idx}`}>
              <div className="v96-op-date">{stockOpFormatMmdd(r.date)}</div>
              <div className="v96-op-etf">
                <b>{r.code}</b>
                <span>{r.name || '-'}</span>
              </div>
              <div className={`v96-op-change ${isAdd ? 'up' : 'down'}`}>
                <b>{stockOpFormatLotsSigned(r.lots)}</b>
                <span>{stockOpFormatPct(r.pct)}</span>
              </div>
              <div className={`v96-op-status ${isAdd ? 'up' : 'down'}`}>{r.status || (isAdd ? '加碼' : '減碼')}</div>
            </div>
          );
        })}
      </div>

      {openInfo && (
        <div className="v96-op-modal-mask" onClick={() => setOpenInfo(false)}>
          <div className="v96-op-modal" onClick={(e) => e.stopPropagation()}>
            <h3>變動資料說明</h3>
            <ul>
              <li><b>變動張數：</b>以 1 張為最小顯示單位，未滿 1 張的零股變動不顯示。</li>
              <li><b>變動幅度：</b>用於衡量加減碼強度。當變動幅度超過 100% 時，以倍數顯示（如 &gt;1倍、&gt;2倍），最多顯示 10 倍，快速識別大幅異動。</li>
              <li><b>判讀提醒：</b>變動幅度過大，可能源於原始持股基數較小，請搭配變動張數判讀。</li>
            </ul>
            <button type="button" onClick={() => setOpenInfo(false)}>我知道了</button>
          </div>
        </div>
      )}
    </section>
  );
}

function TopEtfPreview({ rows, totalValue, onMore }: { rows: any[]; totalValue: number; onMore: () => void }) {
  if (!rows?.length) return <div className="v89-empty-box">目前沒有 ETF 持股資料</div>;
  const maxValue = Math.max(...rows.map((r) => Number.isFinite(r.value) ? r.value : 0), 1);

  return (
    <section className="v92-top-etf-preview">
      <div className="v92-preview-note">依目前持股市值排序。完整清單與近 5 / 20 / 60 日排序請到「持股明細」。</div>
      {rows.map((r) => {
        const pct = totalValue > 0 && Number.isFinite(r.value) ? (r.value / totalValue) * 100 : NaN;
        const width = Math.max(8, Math.min(100, ((Number.isFinite(r.value) ? r.value : 0) / maxValue) * 100));
        return (
          <Link key={r.code} href={`/etf/${r.code}?from=stock`} className="v92-top-etf-row">
            <div className="v92-top-etf-main">
              <b>{r.code}</b>
              <span>{r.name}</span>
            </div>
            <div className="v92-top-etf-value">
              <b>{fmtFree(r.value, 2)} 億</b>
              <span>{fmtFree(r.lots, 0)} 張{Number.isFinite(pct) ? `｜占 ${fmtFree(pct, 1)}%` : ''}</span>
            </div>
            <div className="v92-top-etf-bar"><i style={{ width: `${width}%` }} /></div>
          </Link>
        );
      })}
      <button className="v92-more-btn" onClick={onMore}>查看完整持股明細與排序 ›</button>
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
