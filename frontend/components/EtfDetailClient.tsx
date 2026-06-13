'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fmt, fmt0, num, signedClass } from '@/lib/etfData';

type Tab = 'overview' | 'quote' | 'operation' | 'holdings' | 'premium';
type SortDir = 'asc' | 'desc';

const COLORS = ['#ffa83d', '#1aaed8', '#4f85d8', '#c878ed', '#cfcfcf'];

function mmdd(date: any) {
  const s = String(date || '');
  if (!s) return '';
  return s.slice(5).replace('-', '/');
}

function signedPct(v: any, digits = 2) {
  const x = num(v);
  if (x === null) return '-';
  return `${x > 0 ? '+' : ''}${fmt(x, digits)}%`;
}

function signedPctMin(v: any, digits = 2) {
  const x = num(v);
  if (x === null) return '-';
  if (x === 0) return `0.${'0'.repeat(digits)}%`;
  if (Math.abs(x) < 0.01) return `${x > 0 ? '+' : '-'}<0.01%`;
  return `${x > 0 ? '+' : ''}${fmt(x, digits)}%`;
}

function weightPctMin(v: any, digits = 2) {
  const x = num(v);
  if (x === null || x <= 0) return '-';
  if (x < 0.01) return '<0.01%';
  return `${fmt(x, digits)}%`;
}

function currentWeightMain(r: any) {
  if (r?.status === '刪除') return '-';
  return weightPctMin(r?.weight, 2);
}

function changeMagnitudeText(r: any, mag: number | null) {
  if (r?.status === '新增') return '100%';
  if (mag === null) return '-';
  if (mag === 0) return '0.0%';
  if (Math.abs(mag) < 0.01) return `${mag > 0 ? '+' : '-'}<0.01%`;
  if (Math.abs(mag) > 300) return mag > 0 ? '>3倍' : '<-3倍';
  return `${fmt(mag, 1)}%`;
}

function signedNum(v: any, digits = 2) {
  const x = num(v);
  if (x === null) return '-';
  return `${x > 0 ? '+' : ''}${fmt(Math.abs(x), digits)}`;
}

function lots(shares: any) {
  return (num(shares) || 0) / 1000;
}

function amountTextB(v: any, digits = 0) {
  const x = num(v);
  if (x === null) return '-';
  return `${fmt(x, digits)} 億`;
}

function yearFromInception(date: string | null | undefined) {
  if (!date) return '-';
  const d = new Date(date);
  if (Number.isNaN(d.getTime())) return '-';
  const years = (Date.now() - d.getTime()) / (365.25 * 24 * 60 * 60 * 1000);
  return `${fmt(years, 1)} 年`;
}

function statusClass(status: string) {
  if (status === '加碼') return 'red';
  if (status === '減碼') return 'green';
  if (status === '新增') return 'gold';
  return '';
}

function changeSummaryTitle(data: any) {
  const d = mmdd(data.latest_date);
  return `${d} 持股異動：新增 ${data.change_summary?.added || 0} 檔｜刪除 ${data.change_summary?.removed || 0} 檔`;
}

function previewNames(rows: any[], limit = 3) {
  const names = (rows || [])
    .slice(0, limit)
    .map((r) => String(r.stock_name || r.stock_code || '').trim())
    .filter(Boolean);

  if (!names.length) return '-';
  if ((rows || []).length > limit) return `${names.join('、')} 等 ${(rows || []).length} 檔`;
  return names.join('、');
}

function sortChangePreviewRows(rows: any[]) {
  return [...(rows || [])].sort((a, b) => Math.abs(num(b.delta_shares) || 0) - Math.abs(num(a.delta_shares) || 0));
}

function computeReturn(rows: any[], days: number) {
  const arr = (rows || []).filter((x) => num(x.close ?? x.price) !== null);
  if (arr.length < 2) return null;
  const latest = num(arr[arr.length - 1].close ?? arr[arr.length - 1].price);
  const base = num(arr[Math.max(0, arr.length - 1 - days)].close ?? arr[Math.max(0, arr.length - 1 - days)].price);
  if (!latest || !base) return null;
  return (latest / base - 1) * 100;
}

function latestPriceFromHistory(rows: any[]) {
  const arr = (rows || []).filter((x) => num(x.close ?? x.price) !== null);
  if (!arr.length) return null;
  return num(arr[arr.length - 1].close ?? arr[arr.length - 1].price);
}

function latestNav(rows: any[]) {
  const arr = (rows || []).filter((x) => num(x.nav) !== null || num(x.premium_pct) !== null);
  if (!arr.length) return null;
  return arr[arr.length - 1];
}

function SortArrows({ active, dir }: { active: boolean; dir: SortDir }) {
  return (
    <span className="sort-arrows">
      <span className={active && dir === 'asc' ? 'on' : ''}>▲</span>
      <span className={active && dir === 'desc' ? 'on' : ''}>▼</span>
    </span>
  );
}

function SortButton({ active, dir, onClick, children }: any) {
  return (
    <button type="button" className={`etf-v11-d-sort ${active ? 'active' : ''}`} onClick={onClick}>
      <span>{children}</span>
      <SortArrows active={active} dir={dir} />
    </button>
  );
}

export default function EtfDetailClient({ data }: { data: any }) {
  const [tab, setTab] = useState<Tab>('overview');
  const [holdingSort, setHoldingSort] = useState<'weight' | 'value' | 'price' | 'stock'>('weight');
  const [holdingDir, setHoldingDir] = useState<SortDir>('desc');
  const [opFilter, setOpFilter] = useState<string | null>(null);
  const [opSort, setOpSort] = useState<'stock' | 'delta_shares' | 'delta_weight' | 'weight'>('delta_shares');
  const [opDir, setOpDir] = useState<SortDir>('desc');
  const [showChangeInfo, setShowChangeInfo] = useState(false);

  const q = data.quote || {};
  const priceHistory = data.price_history || [];
  const navHistory = data.nav_history || [];
  const latestNavRow = latestNav(navHistory);

  const price = num(q.price) ?? latestPriceFromHistory(priceHistory);
  const changePct = num(q.change_pct);
  const change = num(q.change);
  const totalReturn = num(q.total_return) ?? computeReturn(priceHistory, priceHistory.length - 1);
  const stockWeight = num(data.summary?.stock_weight);
  const premiumPct = num(q.premium_pct) ?? num(latestNavRow?.premium_pct);
  const nav = num(q.nav) ?? num(latestNavRow?.nav);

  const chartRows = (priceHistory || []).slice(-120);
  const chartUp = (computeReturn(chartRows, Math.min(60, chartRows.length - 1)) || 0) >= 0;

  const topHoldingRows = useMemo(() => {
    const rows = [...(data.holdings || [])];
    rows.sort((a, b) => (num(b.weight) || 0) - (num(a.weight) || 0));

    const top = rows.slice(0, 4).map((r, idx) => ({
      name: r.stock_name,
      value: num(r.weight) || 0,
      color: COLORS[idx],
    }));
    const other = Math.max(0, 100 - top.reduce((s, r) => s + r.value, 0));

    return [...top, { name: '其他', value: other, color: COLORS[4] }];
  }, [data.holdings]);

  const sortedHoldings = useMemo(() => {
    const rows = [...(data.holdings || [])];

    rows.sort((a, b) => {
      let av: any;
      let bv: any;

      if (holdingSort === 'stock') {
        av = `${a.stock_code}${a.stock_name}`;
        bv = `${b.stock_code}${b.stock_name}`;
        const cmp = String(av).localeCompare(String(bv), 'zh-Hant');
        return holdingDir === 'asc' ? cmp : -cmp;
      }

      if (holdingSort === 'weight') {
        av = num(a.weight) || 0;
        bv = num(b.weight) || 0;
      } else if (holdingSort === 'value') {
        av = num(a.market_value_billion) || 0;
        bv = num(b.market_value_billion) || 0;
      } else {
        av = num(a.change_pct) || 0;
        bv = num(b.change_pct) || 0;
      }

      return holdingDir === 'asc' ? av - bv : bv - av;
    });

    return rows;
  }, [data.holdings, holdingSort, holdingDir]);

  const filteredChanges = useMemo(() => {
    let rows = [...(data.changes || [])];

    if (opFilter) rows = rows.filter((r) => r.status === opFilter);

    rows.sort((a, b) => {
      let av: any;
      let bv: any;

      if (opSort === 'stock') {
        av = `${a.stock_code}${a.stock_name}`;
        bv = `${b.stock_code}${b.stock_name}`;
        const cmp = String(av).localeCompare(String(bv), 'zh-Hant');
        return opDir === 'asc' ? cmp : -cmp;
      }

      if (opSort === 'delta_shares') {
        av = Math.abs(num(a.delta_shares) || 0);
        bv = Math.abs(num(b.delta_shares) || 0);
      } else if (opSort === 'delta_weight') {
        av = Math.abs(num(a.delta_weight) || 0);
        bv = Math.abs(num(b.delta_weight) || 0);
      } else {
        av = num(a.weight) || 0;
        bv = num(b.weight) || 0;
      }

      return opDir === 'asc' ? av - bv : bv - av;
    });

    return rows;
  }, [data.changes, opFilter, opSort, opDir]);

  const addedPreviewRows = useMemo(
    () => sortChangePreviewRows((data.changes || []).filter((r: any) => r.status === '新增')),
    [data.changes]
  );

  const removedPreviewRows = useMemo(
    () => sortChangePreviewRows((data.changes || []).filter((r: any) => r.status === '刪除')),
    [data.changes]
  );

  function jumpToOperation(status: string) {
    setTab('operation');
    setOpFilter(status);
  }

  function toggleHoldingSort(key: any) {
    if (holdingSort === key) setHoldingDir(holdingDir === 'asc' ? 'desc' : 'asc');
    else {
      setHoldingSort(key);
      setHoldingDir(key === 'stock' ? 'asc' : 'desc');
    }
  }

  function toggleOpSort(key: any) {
    if (opSort === key) setOpDir(opDir === 'asc' ? 'desc' : 'asc');
    else {
      setOpSort(key);
      setOpDir(key === 'stock' ? 'asc' : 'desc');
    }
  }

  return (
    <main className="etf-v11-detail">
      <header className="etf-v11-detail-header">
        <Link href="/etfs" className="etf-v11-back">‹</Link>
        <div>
          <h1>{data.code}</h1>
          <p>{data.name}</p>
        </div>
        <Link href="/etfs" className="etf-v11-next">›</Link>
      </header>

      <nav className="etf-v11-tabs">
        <button className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}>總覽</button>
        <button className={tab === 'quote' ? 'active' : ''} onClick={() => setTab('quote')}>即時</button>
        <button className={tab === 'operation' ? 'active' : ''} onClick={() => setTab('operation')}>操作日報</button>
        <button className={tab === 'holdings' ? 'active' : ''} onClick={() => setTab('holdings')}>成分股</button>
        <button className={tab === 'premium' ? 'active' : ''} onClick={() => setTab('premium')}>折溢價</button>
      </nav>

      {tab === 'overview' && (
        <section className="etf-v11-tab-content">
          <div className="etf-v11-overview-stats">
            <div>
              <span>股價</span>
              <b className={signedClass(changePct)}>{price == null ? '-' : fmt(price, 2)}</b>
              <small className={signedClass(changePct)}>
                {change == null ? '' : `${change > 0 ? '▲' : change < 0 ? '▼' : ''} ${fmt(Math.abs(change), 2)} `}
                {signedPct(changePct)}
              </small>
            </div>

            <div>
              <span>年化報酬（成立以來）</span>
              <b className={signedClass(totalReturn)}>{signedPct(totalReturn)}</b>
            </div>
          </div>

          <div className="etf-v11-change-strip">
            <span>{changeSummaryTitle(data)}</span>
            <button type="button" onClick={() => setTab('operation')}>更多 ›</button>
          </div>

          {(addedPreviewRows.length > 0 || removedPreviewRows.length > 0) && (
            <div className="etf-v32-change-preview">
              {addedPreviewRows.length > 0 && (
                <button
                  type="button"
                  className="etf-v32-preview-card added"
                  onClick={() => jumpToOperation('新增')}
                >
                  <span>新增標的：</span>
                  <b>{previewNames(addedPreviewRows)}</b>
                </button>
              )}

              {removedPreviewRows.length > 0 && (
                <button
                  type="button"
                  className="etf-v32-preview-card removed"
                  onClick={() => jumpToOperation('刪除')}
                >
                  <span>刪除標的：</span>
                  <b>{previewNames(removedPreviewRows)}</b>
                </button>
              )}
            </div>
          )}

          <section className="etf-v11-card">
            <h3>股價走勢</h3>
            {chartRows.length >= 2 ? (
              <div className="etf-v11-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartRows}>
                    <defs>
                      <linearGradient id="etfV11PriceFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={chartUp ? '#f2b4b4' : '#bce8d7'} stopOpacity={0.85} />
                        <stop offset="95%" stopColor={chartUp ? '#f2b4b4' : '#bce8d7'} stopOpacity={0.08} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="4 4" />
                    <XAxis dataKey="trade_date" tickFormatter={mmdd} />
                    <YAxis domain={['auto', 'auto']} />
                    <Tooltip formatter={(v: any) => [fmt(v, 2), '股價']} labelFormatter={(v) => `日期：${v}`} />
                    <Area type="monotone" dataKey="close" stroke={chartUp ? '#db5555' : '#35a77f'} fill="url(#etfV11PriceFill)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="etf-v11-empty">尚無足夠股價歷史資料，請先跑 Update Pocket ETF Market Data。</div>
            )}

            <div className="etf-v11-period-row">
              <button>1月</button><button>3月</button><button>6月</button><button>1年</button><button>歷史</button>
            </div>
          </section>

          <section className="etf-v11-card">
            <h3>基本資料</h3>
            <div className="etf-v11-info-list">
              <div><span>資產規模</span><b>{q.aum_billion ? `${fmt0(q.aum_billion)} 億` : '-'}</b></div>
              <div><span>成立年數</span><b>{yearFromInception(q.inception_date)}{q.inception_date ? `（${String(q.inception_date).slice(0, 7).replace('-', '/')} 上市）` : ''}</b></div>
              <div><span>內扣費用</span><b>{q.expense_ratio == null ? '-' : `${fmt(q.expense_ratio, 2)}%`}</b></div>
              <div><span>持股人數</span><b>{q.holder_count == null ? '-' : `${fmt0(q.holder_count)} 人`}</b></div>
              <div><span>配息週期</span><b>{q.dividend_frequency || '-'}</b></div>
              <div><span>基金名稱</span><b>{q.full_name || q.etf_name || data.name}</b></div>
              <div><span>經理人</span><b>{q.manager || '-'}</b></div>
              <div><span>投信公司</span><b>{q.company || '-'}</b></div>
              <div><span>保管銀行</span><b>{q.custodian || '-'}</b></div>
            </div>
          </section>
        </section>
      )}

      {tab === 'quote' && (
        <section className="etf-v11-tab-content">
          <div className="etf-v11-overview-stats">
            <div>
              <span>股價</span>
              <b className={signedClass(changePct)}>{price == null ? '-' : fmt(price, 2)}</b>
              <small className={signedClass(changePct)}>{signedPct(changePct)}</small>
            </div>
            <div>
              <span>成交量</span>
              <b>{q.volume == null ? '-' : fmt0(q.volume)}</b>
              <small>{q.amount == null ? '-' : `${fmt(q.amount / 100000000, 2)} 億`}</small>
            </div>
          </div>

          <section className="etf-v11-card">
            <h3>即時行情</h3>
            <div className="etf-v11-info-list">
              <div><span>最新股價</span><b>{price == null ? '-' : fmt(price, 2)}</b></div>
              <div><span>漲跌</span><b className={signedClass(change)}>{change == null ? '-' : signedNum(change)}</b></div>
              <div><span>漲跌幅</span><b className={signedClass(changePct)}>{signedPct(changePct)}</b></div>
              <div><span>成交量</span><b>{q.volume == null ? '-' : fmt0(q.volume)}</b></div>
              <div><span>成交金額</span><b>{q.amount == null ? '-' : `${fmt(q.amount / 100000000, 2)} 億`}</b></div>
              <div><span>更新時間</span><b>{q.updated_at || '-'}</b></div>
            </div>
          </section>
        </section>
      )}

      {tab === 'operation' && (
        <section className="etf-v11-tab-content operation">
          <h2>{mmdd(data.latest_date)} 操作日報</h2>

          <div className="etf-v11-op-card-grid">
            <div className="etf-v11-op-top-card">
              <span>基金規模</span>
              <b>{q.aum_billion ? `${fmt(q.aum_billion, 1)} 億` : '-'}</b>
              <small className="red">較前日 +0.02%</small>
            </div>
            <div className="etf-v11-op-top-card">
              <span>折溢價</span>
              <b className={signedClass(premiumPct)}>{premiumPct == null ? '-' : signedPct(premiumPct, 2)}</b>
              <small>股價 {price ?? '-'}｜淨值 {nav ?? '-'}</small>
            </div>
          </div>

          <div className="etf-v11-op-filter-row">
            <button className={`gold ${opFilter === '新增' ? 'active' : ''}`} onClick={() => setOpFilter(opFilter === '新增' ? null : '新增')}>
              <span>新增</span><b>{data.change_summary?.added || 0}</b><em>檔</em>
            </button>
            <button className={`gray ${opFilter === '刪除' ? 'active' : ''}`} onClick={() => setOpFilter(opFilter === '刪除' ? null : '刪除')}>
              <span>刪除</span><b>{data.change_summary?.removed || 0}</b><em>檔</em>
            </button>
            <button className={`red ${opFilter === '加碼' ? 'active' : ''}`} onClick={() => setOpFilter(opFilter === '加碼' ? null : '加碼')}>
              <span>加碼</span><b>{data.change_summary?.increased || 0}</b><em>檔</em>
            </button>
            <button className={`green ${opFilter === '減碼' ? 'active' : ''}`} onClick={() => setOpFilter(opFilter === '減碼' ? null : '減碼')}>
              <span>減碼</span><b>{data.change_summary?.decreased || 0}</b><em>檔</em>
            </button>
          </div>

          <div className="etf-v11-op-subtitle">
            <span>共 {filteredChanges.length} 檔異動</span>
            <button onClick={() => setShowChangeInfo(true)}>變動說明 ⓘ</button>
          </div>

          <div className="etf-v11-table-wrap">
            <table className="etf-v11-op-table">
              <thead>
                <tr>
                  <th><SortButton active={opSort === 'stock'} dir={opDir} onClick={() => toggleOpSort('stock')}>標的</SortButton></th>
                  <th>狀態</th>
                  <th><SortButton active={opSort === 'delta_shares'} dir={opDir} onClick={() => toggleOpSort('delta_shares')}>持股變動</SortButton></th>
                  <th><SortButton active={opSort === 'delta_weight'} dir={opDir} onClick={() => toggleOpSort('delta_weight')}>變動幅度</SortButton></th>
                  <th><SortButton active={opSort === 'weight'} dir={opDir} onClick={() => toggleOpSort('weight')}>目前權重</SortButton></th>
                </tr>
              </thead>
              <tbody>
                {filteredChanges.map((r: any) => {
                  const prevShares = (num(r.shares) || 0) - (num(r.delta_shares) || 0);
                  const mag = prevShares ? ((num(r.delta_shares) || 0) / prevShares) * 100 : null;

                  return (
                    <tr key={`${r.stock_code}-${r.status}`}>
                      <td><Link href={`/stock/${r.stock_code}`}><b>{r.stock_name}</b><small>{r.stock_code}</small></Link></td>
                      <td><span className={`badge ${statusClass(r.status)}`}>{r.status}</span></td>
                      <td className={signedClass(r.delta_shares)}>{r.delta_shares > 0 ? '+' : ''}{fmt0((num(r.delta_shares) || 0) / 1000)}<span className="etf-v33-unit"> 張</span></td>
                      <td>{changeMagnitudeText(r, mag)}</td>
                      <td>
                        <b>{currentWeightMain(r)}</b>
                        <small className={signedClass(r.delta_weight)}>{signedPctMin(r.delta_weight, 2)}</small>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === 'holdings' && (
        <section className="etf-v11-tab-content">
          <div className="etf-v11-distribution-card">
            <div className="etf-v11-pie">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={topHoldingRows} dataKey="value" nameKey="name" innerRadius={70} outerRadius={115} paddingAngle={0}>
                    {topHoldingRows.map((entry, index) => <Cell key={entry.name} fill={entry.color} />)}
                  </Pie>
                  <Tooltip formatter={(v: any) => [`${fmt(v, 2)}%`, '權重']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="etf-v11-legend">
              <div className="etf-v11-update">更新時間<br />{data.latest_date || q.updated_at || '-'}</div>
              {topHoldingRows.map((r, i) => (
                <div key={r.name}>
                  <span style={{ background: COLORS[i] }} />
                  <b>{r.name}</b>
                  <strong>{fmt(r.value, 2)}%</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="etf-v11-table-wrap">
            <table className="etf-v11-holding-table">
              <thead>
                <tr>
                  <th><SortButton active={holdingSort === 'stock'} dir={holdingDir} onClick={() => toggleHoldingSort('stock')}>標的</SortButton></th>
                  <th><SortButton active={holdingSort === 'value'} dir={holdingDir} onClick={() => toggleHoldingSort('value')}>持股市值<br />持股張數</SortButton></th>
                  <th><SortButton active={holdingSort === 'weight'} dir={holdingDir} onClick={() => toggleHoldingSort('weight')}>權重</SortButton></th>
                  <th><SortButton active={holdingSort === 'price'} dir={holdingDir} onClick={() => toggleHoldingSort('price')}>股價<br />漲跌幅</SortButton></th>
                </tr>
              </thead>
              <tbody>
                {sortedHoldings.map((r: any) => (
                  <tr key={r.stock_code}>
                    <td><Link href={`/stock/${r.stock_code}`}><b>{r.stock_name}</b><small>{r.stock_code}</small></Link></td>
                    <td><b>{r.market_value_billion == null ? '-' : `${fmt(r.market_value_billion, 0)} 億`}</b><small>{fmt0(lots(r.shares))} 張</small></td>
                    <td><b>{weightPctMin(r.weight, 2)}</b></td>
                    <td><b>{r.price == null ? '-' : fmt(r.price, r.price >= 1000 ? 0 : 1)}</b><small className={signedClass(r.change_pct)}>{signedPct(r.change_pct)}</small></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === 'premium' && (
        <section className="etf-v11-tab-content">
          {navHistory.length >= 2 ? (
            <>
              <div className="etf-v11-premium-chart">
                <h3>折溢價 (%)</h3>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={navHistory.slice(-45)}>
                    <CartesianGrid strokeDasharray="4 4" />
                    <XAxis dataKey="trade_date" tickFormatter={mmdd} />
                    <YAxis />
                    <Tooltip formatter={(v: any) => [`${fmt(v, 2)}%`, '折溢價']} />
                    <Bar dataKey="premium_pct">
                      {navHistory.slice(-45).map((r: any) => <Cell key={r.trade_date} fill={(num(r.premium_pct) || 0) >= 0 ? '#db5555' : '#35a77f'} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="etf-v11-premium-chart">
                <h3>股價 / 淨值</h3>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={navHistory.slice(-45)}>
                    <CartesianGrid strokeDasharray="4 4" />
                    <XAxis dataKey="trade_date" tickFormatter={mmdd} />
                    <YAxis domain={['auto', 'auto']} />
                    <Tooltip />
                    <Line type="monotone" dataKey="price" name="股價" stroke="#db5555" dot={false} strokeWidth={2} />
                    <Line type="monotone" dataKey="nav" name="淨值" stroke="#4c8bef" dot={false} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="etf-v11-table-wrap">
                <table className="etf-v11-premium-table">
                  <thead><tr><th>日期</th><th>股價</th><th>淨值</th><th>折溢價 (%)</th></tr></thead>
                  <tbody>
                    {[...navHistory].reverse().slice(0, 30).map((r: any) => (
                      <tr key={r.trade_date}>
                        <td>{r.trade_date}</td>
                        <td>{fmt(r.price, 2)}</td>
                        <td>{fmt(r.nav, 2)}</td>
                        <td className={signedClass(r.premium_pct)}>{signedPct(r.premium_pct, 2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="etf-v11-card">
              <h3>折溢價</h3>
              <div className="etf-v11-mini-grid">
                <div><span>折溢價</span><b className={signedClass(premiumPct)}>{premiumPct == null ? '-' : signedPct(premiumPct, 2)}</b></div>
                <div><span>淨值</span><b>{nav == null ? '-' : fmt(nav, 2)}</b></div>
              </div>
              <p className="muted">尚無足夠折溢價歷史，請先跑 Update Pocket ETF Market Data。</p>
            </div>
          )}
        </section>
      )}

      {showChangeInfo && (
        <div className="etf-v11-modal-mask" onClick={() => setShowChangeInfo(false)}>
          <div className="etf-v11-modal" onClick={(e) => e.stopPropagation()}>
            <h2>變動資料說明</h2>
            <p>持股變動以 1 張為最小顯示單位；未滿 1 張的零股變動將無條件捨去。</p>
            <p>變動幅度用來衡量加減碼強度。當原持股基數很小時，倍數會被放大，請搭配「持股變動」判讀。</p>
            <button onClick={() => setShowChangeInfo(false)}>我知道了</button>
          </div>
        </div>
      )}

      <style>{`
        .etf-v32-change-preview{
          display:grid;
          grid-template-columns:1fr 1fr;
          gap:14px;
          margin:-4px 0 18px;
        }

        .etf-v32-preview-card{
          border:0;
          border-radius:16px;
          padding:16px 18px;
          text-align:left;
          font-size:18px;
          font-weight:900;
          cursor:pointer;
          display:flex;
          align-items:center;
          gap:6px;
          min-height:64px;
        }

        .etf-v32-preview-card.added{
          background:#fff9df;
          color:#a38a00;
        }

        .etf-v32-preview-card.removed{
          background:#f4f5f6;
          color:#5d6570;
        }

        .etf-v32-preview-card span{
          flex:0 0 auto;
        }

        .etf-v32-preview-card b{
          color:#5d6570;
          font-weight:900;
          overflow:hidden;
          text-overflow:ellipsis;
          white-space:nowrap;
        }

        @media(max-width:760px){
          .etf-v32-change-preview{
            grid-template-columns:1fr;
            gap:10px;
            margin:-2px 0 16px;
          }

          .etf-v32-preview-card{
            min-height:64px;
            padding:14px 18px;
            font-size:22px;
            border-radius:14px;
          }

          /* V33 操作日報手機版：整體縮小，盡量一屏顯示 */
          .etf-v11-page{
            overflow-x:hidden !important;
          }

          .etf-v11-tab-content.operation{
            padding:14px 16px 26px !important;
            background:#f6f6f7 !important;
            overflow-x:hidden !important;
          }

          .etf-v11-tab-content.operation h2{
            font-size:20px !important;
            line-height:1.2 !important;
            margin:4px 0 12px !important;
            color:#7f8895 !important;
            font-weight:800 !important;
          }

          .etf-v11-op-card-grid{
            display:grid !important;
            grid-template-columns:1fr 1fr !important;
            gap:8px !important;
            margin:0 0 12px !important;
          }

          .etf-v11-op-top-card{
            min-height:0 !important;
            padding:14px 14px 16px !important;
            border-radius:10px !important;
            background:#fff !important;
            box-shadow:none !important;
          }

          .etf-v11-op-top-card span{
            display:block !important;
            font-size:17px !important;
            line-height:1.2 !important;
            margin-bottom:8px !important;
            color:#666f7a !important;
            font-weight:800 !important;
          }

          .etf-v11-op-top-card b{
            display:block !important;
            font-size:30px !important;
            line-height:1.05 !important;
            letter-spacing:-0.5px !important;
            white-space:nowrap !important;
          }

          .etf-v11-op-top-card small{
            display:block !important;
            font-size:15px !important;
            line-height:1.2 !important;
            margin-top:7px !important;
            white-space:normal !important;
          }

          /* 新增 / 刪除 / 加碼 / 減碼：改成四格小卡片 */
          .etf-v11-op-filter-row{
            display:grid !important;
            grid-template-columns:repeat(4, minmax(0, 1fr)) !important;
            gap:8px !important;
            margin:0 0 14px !important;
            overflow:visible !important;
          }

          .etf-v11-op-filter-row button{
            width:100% !important;
            height:70px !important;
            min-width:0 !important;
            border-radius:10px !important;
            padding:8px 8px !important;
            display:grid !important;
            grid-template-columns:auto 1fr auto !important;
            grid-template-rows:auto 1fr !important;
            align-items:center !important;
            justify-items:start !important;
            gap:0 3px !important;
            box-shadow:none !important;
            background:#fff !important;
            font-size:18px !important;
            line-height:1 !important;
            font-weight:900 !important;
          }

          .etf-v11-op-filter-row button::after{
            content:'✓';
            grid-column:3;
            grid-row:1;
            width:18px;
            height:18px;
            border-radius:999px;
            display:flex;
            align-items:center;
            justify-content:center;
            color:#fff;
            font-size:12px;
            font-weight:900;
          }

          .etf-v11-op-filter-row button.gold::after{background:#a89200;}
          .etf-v11-op-filter-row button.gray::after{background:#687079;}
          .etf-v11-op-filter-row button.red::after{background:#df555b;}
          .etf-v11-op-filter-row button.green::after{background:#3fb092;}

          .etf-v11-op-filter-row button:not(.active){
            opacity:.72 !important;
            background:#fff !important;
          }

          .etf-v11-op-filter-row button:not(.active)::after{
            opacity:.55;
          }

          .etf-v11-op-filter-row button span{
            grid-column:1 / 3;
            grid-row:1;
            font-size:18px !important;
            line-height:1.1 !important;
          }

          .etf-v11-op-filter-row button b{
            grid-column:1 / 3;
            grid-row:2;
            font-size:28px !important;
            line-height:1 !important;
            margin-top:6px !important;
          }

          .etf-v11-op-filter-row button em{
            grid-column:3;
            grid-row:2;
            font-style:normal !important;
            font-size:15px !important;
            align-self:end !important;
            padding-bottom:2px !important;
          }

          .etf-v11-op-filter-row button.gold{
            border:1.5px solid #b59b00 !important;
            background:#fffbe8 !important;
            color:#a89200 !important;
          }

          .etf-v11-op-filter-row button.gray{
            border:1.5px solid #9da4ad !important;
            background:#f6f7f8 !important;
            color:#687079 !important;
          }

          .etf-v11-op-filter-row button.red{
            border:1.5px solid #df555b !important;
            background:#fff0f1 !important;
            color:#df555b !important;
          }

          .etf-v11-op-filter-row button.green{
            border:1.5px solid #41ad90 !important;
            background:#eaf8f4 !important;
            color:#28a985 !important;
          }

          .etf-v11-op-subtitle{
            display:flex !important;
            align-items:center !important;
            justify-content:space-between !important;
            margin:0 0 6px !important;
            font-size:18px !important;
            color:#7f8895 !important;
          }

          .etf-v11-op-subtitle span{
            font-size:20px !important;
            font-weight:800 !important;
          }

          .etf-v11-op-subtitle button{
            font-size:18px !important;
            font-weight:800 !important;
            color:#8b94a1 !important;
          }

          /* 操作日報表格：取消橫向寬度，全部壓進手機畫面 */
          .etf-v11-table-wrap{
            width:100% !important;
            max-width:100% !important;
            overflow-x:visible !important;
            border-radius:0 !important;
            box-shadow:none !important;
          }

          .etf-v11-op-table{
            width:100% !important;
            min-width:0 !important;
            table-layout:fixed !important;
            border-collapse:collapse !important;
          }

          .etf-v11-op-table th,
          .etf-v11-op-table td{
            padding:9px 4px !important;
            font-size:14px !important;
            line-height:1.2 !important;
            white-space:normal !important;
            word-break:keep-all !important;
            overflow:hidden !important;
            text-overflow:clip !important;
          }

          .etf-v11-op-table thead th{
            position:sticky !important;
            top:0 !important;
            z-index:3 !important;
            background:#f0f1f3 !important;
            color:#20252c !important;
            font-size:14px !important;
            font-weight:900 !important;
            height:42px !important;
          }

          .etf-v11-op-table th:nth-child(1),
          .etf-v11-op-table td:nth-child(1){
            width:23% !important;
            position:static !important;
            left:auto !important;
            box-shadow:none !important;
          }

          .etf-v11-op-table th:nth-child(2),
          .etf-v11-op-table td:nth-child(2){
            width:16% !important;
            text-align:center !important;
          }

          .etf-v11-op-table th:nth-child(3),
          .etf-v11-op-table td:nth-child(3){
            width:21% !important;
            text-align:right !important;
          }

          .etf-v11-op-table th:nth-child(4),
          .etf-v11-op-table td:nth-child(4){
            width:18% !important;
            text-align:right !important;
          }

          .etf-v11-op-table th:nth-child(5),
          .etf-v11-op-table td:nth-child(5){
            width:22% !important;
            text-align:right !important;
          }

          .etf-v11-op-table td:first-child a{
            display:block !important;
            min-width:0 !important;
            color:inherit !important;
          }

          .etf-v11-op-table td:first-child b{
            display:block !important;
            font-size:18px !important;
            line-height:1.15 !important;
            font-weight:900 !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
            white-space:nowrap !important;
          }

          .etf-v11-op-table td:first-child small{
            display:block !important;
            font-size:14px !important;
            line-height:1.1 !important;
            margin-top:5px !important;
            color:#7e8793 !important;
            font-weight:800 !important;
          }

          .etf-v11-op-table .badge{
            display:inline-flex !important;
            min-width:0 !important;
            padding:6px 7px !important;
            border-radius:12px !important;
            font-size:14px !important;
            line-height:1 !important;
            font-weight:900 !important;
            white-space:nowrap !important;
          }

          .etf-v11-op-table td:nth-child(3){
            font-size:17px !important;
            font-weight:800 !important;
          }

          .etf-v11-op-table td:nth-child(4){
            font-size:16px !important;
            font-weight:700 !important;
          }

          .etf-v11-op-table td:nth-child(5) b{
            display:block !important;
            font-size:18px !important;
            line-height:1.1 !important;
          }

          .etf-v11-op-table td:nth-child(5) small{
            display:block !important;
            font-size:14px !important;
            line-height:1.1 !important;
            margin-top:4px !important;
          }

          .etf-v11-d-sort{
            display:inline-flex !important;
            align-items:center !important;
            justify-content:center !important;
            gap:2px !important;
            padding:0 !important;
            font-size:14px !important;
            line-height:1.05 !important;
            white-space:normal !important;
          }

          .etf-v11-d-sort span{
            white-space:normal !important;
          }

          .etf-v33-unit{
            display:none !important;
          }

          .etf-v11-op-table td:nth-child(4),
          .etf-v11-op-table td:nth-child(5) b,
          .etf-v11-op-table td:nth-child(5) small{
            white-space:nowrap !important;
          }
        }
      `}</style>
    </main>
  );
}
