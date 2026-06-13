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

const TAB_VALUES: Tab[] = ['overview', 'quote', 'operation', 'holdings', 'premium'];

function readTabFromUrl(): Tab | null {
  if (typeof window === 'undefined') return null;
  const t = new URLSearchParams(window.location.search).get('tab');
  return TAB_VALUES.includes(t as Tab) ? (t as Tab) : null;
}

function initialTabFromUrl(): Tab {
  return readTabFromUrl() || 'overview';
}

const ETF_NAV_CODES = [
  '00400A', '00401A', '00403A',
  '00980A', '00981A', '00982A', '00983A', '00984A', '00985A', '00986A',
  '00987A', '00988A', '00989A', '00990A', '00991A', '00992A', '00993A',
  '00994A', '00995A', '00996A', '00997A', '00998A', '00999A',
];

function getEtfNavCodes(data: any) {
  const fromData = data?.nav_codes || data?.etf_codes || data?.all_codes;
  const arr = Array.isArray(fromData) ? fromData : ETF_NAV_CODES;
  return arr.map((x: any) => String(x || '').trim()).filter(Boolean);
}

function getPrevNextEtf(code: any, data: any) {
  const codes = getEtfNavCodes(data);
  const c = String(code || '').trim();
  const idx = codes.indexOf(c);
  if (idx < 0 || codes.length <= 1) return { prevCode: null, nextCode: null };
  return {
    prevCode: codes[(idx - 1 + codes.length) % codes.length],
    nextCode: codes[(idx + 1) % codes.length],
  };
}

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

const OP_STATUS_ORDER = ['新增', '刪除', '加碼', '減碼'];

function statusRank(status: string) {
  const idx = OP_STATUS_ORDER.indexOf(status);
  return idx >= 0 ? idx : 99;
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
  const [tab, setTab] = useState<Tab>(() => initialTabFromUrl());
  const [holdingSort, setHoldingSort] = useState<'weight' | 'value' | 'price' | 'stock'>('weight');
  const [holdingDir, setHoldingDir] = useState<SortDir>('desc');
  const [opFilter, setOpFilter] = useState<string | null>(null);
  const [opSort, setOpSort] = useState<'stock' | 'delta_shares' | 'delta_weight' | 'weight'>('delta_shares');
  const [opDir, setOpDir] = useState<SortDir>('desc');
  const [showChangeInfo, setShowChangeInfo] = useState(false);

  const q = data.quote || {};
  const { prevCode, nextCode } = getPrevNextEtf(data.code, data);
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
      if (!opFilter) {
        const sr = statusRank(a.status) - statusRank(b.status);
        if (sr !== 0) return sr;
      }

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

  function selectTab(nextTab: Tab) {
    setTab(nextTab);
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('tab', nextTab);
      window.history.replaceState(null, '', url.toString());
    }
  }

  function jumpToOperation(status: string) {
    selectTab('operation');
    setOpFilter(status);
  }

  function goToEtf(code: any) {
    if (!code) {
      if (typeof window !== 'undefined') window.location.href = '/etfs';
      return;
    }
    const currentTab = readTabFromUrl() || tab;
    if (typeof window !== 'undefined') {
      window.location.href = `/etf/${code}?tab=${currentTab}`;
    }
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

  function goBackToPreviousPage() {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      window.history.back();
      return;
    }
    if (typeof window !== 'undefined') window.location.href = '/etfs';
  }

  return (
    <main className={showChangeInfo ? "etf-v11-detail modal-open" : "etf-v11-detail"}>
      <div className="etf-v36-sticky-detail-nav">
        <header className="etf-v11-detail-header">
          <button type="button" className="etf-v37-page-back" onClick={goBackToPreviousPage} aria-label="回上一頁">‹</button>
          <button type="button" className="etf-v37-etf-prev" onClick={() => goToEtf(prevCode)} aria-label="上一檔 ETF">◀</button>
          <div className="etf-v37-title">
            <h1>{data.code}</h1>
            <p>{data.name}</p>
          </div>
          <button type="button" className="etf-v37-etf-next" onClick={() => goToEtf(nextCode)} aria-label="下一檔 ETF">▶</button>
          <span className="etf-v37-header-spacer" aria-hidden="true" />
        </header>

        <nav className="etf-v11-tabs">
          <button className={tab === 'overview' ? 'active' : ''} onClick={() => selectTab('overview')}>總覽</button>
          <button className={tab === 'quote' ? 'active' : ''} onClick={() => selectTab('quote')}>即時</button>
          <button className={tab === 'operation' ? 'active' : ''} onClick={() => selectTab('operation')}>操作日報</button>
          <button className={tab === 'holdings' ? 'active' : ''} onClick={() => selectTab('holdings')}>成分股</button>
          <button className={tab === 'premium' ? 'active' : ''} onClick={() => selectTab('premium')}>折溢價</button>
        </nav>
      </div>

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
            <button type="button" onClick={() => selectTab('operation')}>更多 ›</button>
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

          <div className="etf-v41-op-grid" role="table" aria-label="操作日報異動明細">
            <div className="etf-v41-op-head" role="row">
              <div role="columnheader"><SortButton active={opSort === 'stock'} dir={opDir} onClick={() => toggleOpSort('stock')}>標的</SortButton></div>
              <div role="columnheader">狀態</div>
              <div role="columnheader"><SortButton active={opSort === 'delta_shares'} dir={opDir} onClick={() => toggleOpSort('delta_shares')}>持股變動</SortButton></div>
              <div role="columnheader"><SortButton active={opSort === 'delta_weight'} dir={opDir} onClick={() => toggleOpSort('delta_weight')}>變動幅度</SortButton></div>
              <div role="columnheader"><SortButton active={opSort === 'weight'} dir={opDir} onClick={() => toggleOpSort('weight')}>目前權重</SortButton></div>
            </div>

            <div className="etf-v41-op-body" role="rowgroup">
              {filteredChanges.map((r: any) => {
                const prevShares = (num(r.shares) || 0) - (num(r.delta_shares) || 0);
                const mag = prevShares ? ((num(r.delta_shares) || 0) / prevShares) * 100 : null;

                return (
                  <div className="etf-v41-op-row" role="row" key={`${r.stock_code}-${r.status}`}>
                    <div className="etf-v41-op-target" role="cell">
                      <Link href={`/stock/${r.stock_code}`}>
                        <b>{r.stock_name}</b>
                        <small>{r.stock_code}</small>
                      </Link>
                    </div>
                    <div className="etf-v41-op-status" role="cell"><span className={`badge ${statusClass(r.status)}`}>{r.status}</span></div>
                    <div className={`etf-v41-op-shares ${signedClass(r.delta_shares)}`} role="cell">
                      {r.delta_shares > 0 ? '+' : ''}{fmt0((num(r.delta_shares) || 0) / 1000)}
                    </div>
                    <div className="etf-v41-op-mag" role="cell">{changeMagnitudeText(r, mag)}</div>
                    <div className="etf-v41-op-weight" role="cell">
                      <b>{currentWeightMain(r)}</b>
                      <small className={signedClass(r.delta_weight)}>{signedPctMin(r.delta_weight, 2)}</small>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {tab === 'holdings' && (
        <section className="etf-v11-tab-content holdings compact-holdings">
          <div className="etf-v42-distribution-card">
            <div className="etf-v42-distribution-top">
              <div className="etf-v42-seg-tabs" aria-label="成分股模式">
                <button type="button" className="active">成分股</button>
                <button type="button" disabled>產業分布</button>
              </div>
              <div className="etf-v42-update">更新時間<br />{String(data.latest_date || q.updated_at || '-').replaceAll('-', '/')}</div>
            </div>

            <div className="etf-v42-distribution-main">
              <div className="etf-v42-pie">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={topHoldingRows} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="86%" paddingAngle={0}>
                      {topHoldingRows.map((entry, index) => <Cell key={entry.name} fill={entry.color} />)}
                    </Pie>
                    <Tooltip formatter={(v: any) => [`${fmt(v, 2)}%`, '權重']} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="etf-v42-legend">
                {topHoldingRows.map((r, i) => (
                  <div key={r.name}>
                    <span style={{ background: COLORS[i] }} />
                    <b>{r.name}</b>
                    <strong>{fmt(r.value, 2)}%</strong>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="etf-v42-holding-grid" role="table" aria-label="ETF 成分股明細">
            <div className="etf-v42-holding-head" role="row">
              <div role="columnheader"><SortButton active={holdingSort === 'stock'} dir={holdingDir} onClick={() => toggleHoldingSort('stock')}>標的</SortButton></div>
              <div role="columnheader"><SortButton active={holdingSort === 'value'} dir={holdingDir} onClick={() => toggleHoldingSort('value')}>持股市值<br />持股張數</SortButton></div>
              <div role="columnheader"><SortButton active={holdingSort === 'weight'} dir={holdingDir} onClick={() => toggleHoldingSort('weight')}>權重</SortButton></div>
              <div role="columnheader"><SortButton active={holdingSort === 'price'} dir={holdingDir} onClick={() => toggleHoldingSort('price')}>股價<br />漲跌幅</SortButton></div>
            </div>

            <div className="etf-v42-holding-body" role="rowgroup">
              {sortedHoldings.map((r: any) => (
                <div className="etf-v42-holding-row" role="row" key={r.stock_code}>
                  <div className="etf-v42-holding-target" role="cell">
                    <Link href={`/stock/${r.stock_code}`}>
                      <b>{r.stock_name}</b>
                      <small>{r.stock_code}</small>
                    </Link>
                  </div>
                  <div className="etf-v42-holding-value" role="cell">
                    <b>{r.market_value_billion == null ? '-' : `${fmt(r.market_value_billion, 0)} 億`}</b>
                    <small>{fmt0(lots(r.shares))} 張</small>
                  </div>
                  <div className="etf-v42-holding-weight" role="cell">
                    <b>{weightPctMin(r.weight, 2)}</b>
                  </div>
                  <div className="etf-v42-holding-price" role="cell">
                    <b>{r.price == null ? '-' : fmt(r.price, r.price >= 1000 ? 0 : 1)}</b>
                    <small className={signedClass(r.change_pct)}>{signedPct(r.change_pct)}</small>
                  </div>
                </div>
              ))}
            </div>
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

        /* V40：ETF 詳情頁直接隱藏全站 Header，不再只依賴 AppShell path 判斷 */
        header.top,
        .top{
          display:none !important;
          height:0 !important;
          min-height:0 !important;
          overflow:hidden !important;
        }

        .detail-shell,
        .shell.detail-shell{
          padding-top:0 !important;
        }

        .etf-v36-sticky-detail-nav{
          background:#fff;
          border-bottom:1px solid #e5e8ee;
          z-index:60;
        }

        .etf-v37-page-back,
        .etf-v37-etf-prev,
        .etf-v37-etf-next{
          border:0;
          background:transparent;
          text-decoration:none;
          color:#18212d;
          cursor:pointer;
          font-family:inherit;
        }

        .etf-v37-page-back:hover,
        .etf-v37-etf-prev:hover,
        .etf-v37-etf-next:hover{
          color:#4e8ff0;
        }


        /* V43：修正說明彈窗被 sticky 表頭蓋住 */
        .etf-v11-modal-mask{
          position:fixed !important;
          inset:0 !important;
          z-index:99990 !important;
          display:flex !important;
          align-items:center !important;
          justify-content:center !important;
          padding:22px !important;
          background:rgba(15,23,42,.48) !important;
        }

        .etf-v11-modal{
          position:relative !important;
          z-index:99991 !important;
          width:min(520px, calc(100vw - 44px)) !important;
          max-height:calc(100vh - 120px) !important;
          overflow:auto !important;
          border-radius:18px !important;
          background:#fff !important;
          padding:28px 28px 24px !important;
          box-shadow:0 22px 70px rgba(15,23,42,.28) !important;
        }

        .etf-v11-modal h2{
          margin:0 0 18px !important;
          text-align:center !important;
          font-size:26px !important;
          line-height:1.2 !important;
          font-weight:900 !important;
        }

        .etf-v11-modal p{
          margin:0 0 16px !important;
          color:#20252c !important;
          font-size:20px !important;
          line-height:1.7 !important;
          font-weight:800 !important;
        }

        .etf-v11-modal button{
          width:100% !important;
          margin-top:10px !important;
          border:0 !important;
          border-radius:12px !important;
          background:#4e8ff0 !important;
          color:#fff !important;
          font-size:22px !important;
          line-height:1 !important;
          font-weight:900 !important;
          padding:16px 18px !important;
          font-family:inherit !important;
        }

        .etf-v11-detail.modal-open .etf-v41-op-head,
        .etf-v11-detail.modal-open .etf-v42-holding-head{
          z-index:1 !important;
        }

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

          /* V36：手機往下滑時，ETF 代碼區 + 分頁列固定在上方 */
          .etf-v36-sticky-detail-nav{
            position:sticky !important;
            top:0 !important;
            z-index:80 !important;
            background:#fff !important;
            box-shadow:0 2px 10px rgba(15,23,42,.08) !important;
          }

          .etf-v11-detail-header{
            height:56px !important;
            min-height:56px !important;
            padding:5px 4px 5px !important;
            display:grid !important;
            grid-template-columns:42px 34px minmax(0, 1fr) 34px 42px !important;
            align-items:center !important;
            border-bottom:1px solid #edf0f4 !important;
            background:#fff !important;
          }

          .etf-v37-title{
            min-width:0 !important;
            text-align:center !important;
          }

          .etf-v11-detail-header h1{
            font-size:23px !important;
            line-height:1 !important;
            margin:0 !important;
            letter-spacing:.2px !important;
            font-weight:900 !important;
          }

          .etf-v11-detail-header p{
            font-size:15px !important;
            line-height:1.15 !important;
            margin:3px 0 0 !important;
            color:#687180 !important;
            font-weight:800 !important;
            white-space:nowrap !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
          }

          .etf-v37-page-back,
          .etf-v37-etf-prev,
          .etf-v37-etf-next{
            width:100% !important;
            height:46px !important;
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            border:0 !important;
            background:transparent !important;
            text-decoration:none !important;
            -webkit-tap-highlight-color:transparent !important;
          }

          .etf-v37-page-back{
            font-size:40px !important;
            line-height:1 !important;
            font-weight:900 !important;
            color:#121924 !important;
            padding:0 !important;
          }

          .etf-v37-etf-prev,
          .etf-v37-etf-next{
            font-size:20px !important;
            line-height:1 !important;
            font-weight:900 !important;
            color:#8a94a3 !important;
          }

          .etf-v37-header-spacer{
            display:block !important;
            width:42px !important;
            height:1px !important;
          }

          .etf-v11-tabs{
            height:48px !important;
            display:flex !important;
            align-items:flex-end !important;
            gap:0 !important;
            padding:0 0 !important;
            overflow-x:auto !important;
            overflow-y:hidden !important;
            white-space:nowrap !important;
            background:#fff !important;
            border-bottom:0 !important;
            scrollbar-width:none !important;
          }

          .etf-v11-tabs::-webkit-scrollbar{
            display:none !important;
          }

          .etf-v11-tabs button{
            flex:0 0 auto !important;
            min-width:66px !important;
            height:48px !important;
            padding:0 7px 7px !important;
            border:0 !important;
            background:transparent !important;
            color:#565f6b !important;
            font-size:19px !important;
            line-height:1 !important;
            font-weight:900 !important;
            position:relative !important;
          }

          .etf-v11-tabs button.active{
            color:#4e8ff0 !important;
          }

          .etf-v11-tabs button.active::after{
            content:'' !important;
            position:absolute !important;
            left:8px !important;
            right:8px !important;
            bottom:0 !important;
            height:3px !important;
            border-radius:3px 3px 0 0 !important;
            background:#4e8ff0 !important;
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
            border-collapse:separate !important;
            border-spacing:0 !important;
          }

          .etf-v11-op-table th,
          .etf-v11-op-table td{
            padding:8px 4px !important;
            font-size:13px !important;
            line-height:1.2 !important;
            white-space:normal !important;
            word-break:keep-all !important;
            overflow:hidden !important;
            text-overflow:clip !important;
          }

          .etf-v11-op-table thead th{
            position:sticky !important;
            top:104px !important;
            z-index:70 !important;
            background:#f0f1f3 !important;
            color:#20252c !important;
            font-size:13px !important;
            font-weight:900 !important;
            height:40px !important;
            border-bottom:1px solid #dfe3e8 !important;
            box-shadow:0 2px 0 rgba(15,23,42,.04) !important;
          }

          .etf-v11-op-table thead th:first-child{
            z-index:72 !important;
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


          /* V40：iOS Safari table sticky 修正。不要讓每個 th 自己 sticky，改成整列 thead sticky */
          .etf-v11-tab-content.operation .etf-v11-table-wrap{
            overflow-x:hidden !important;
            overflow-y:visible !important;
            width:100% !important;
            max-width:100% !important;
          }

          .etf-v11-op-table,
          .etf-v11-op-table thead,
          .etf-v11-op-table tbody{
            display:block !important;
            width:100% !important;
            min-width:0 !important;
            table-layout:auto !important;
            border-collapse:separate !important;
          }

          .etf-v11-op-table thead{
            position:sticky !important;
            top:100px !important;
            z-index:140 !important;
            background:#f0f1f3 !important;
            box-shadow:0 1px 0 #dfe3e8, 0 3px 10px rgba(15,23,42,.08) !important;
          }

          .etf-v11-op-table tr{
            display:grid !important;
            grid-template-columns:22% 16% 22% 18% 22% !important;
            align-items:center !important;
            width:100% !important;
            min-width:0 !important;
          }

          .etf-v11-op-table thead tr{
            min-height:44px !important;
            background:#f0f1f3 !important;
          }

          .etf-v11-op-table tbody tr{
            min-height:70px !important;
            border-bottom:1px solid #e2e5ea !important;
            background:#fff !important;
          }

          .etf-v11-op-table th,
          .etf-v11-op-table td,
          .etf-v11-op-table thead th,
          .etf-v11-op-table thead th:first-child{
            position:static !important;
            top:auto !important;
            left:auto !important;
            right:auto !important;
            z-index:auto !important;
            display:block !important;
            width:auto !important;
            min-width:0 !important;
            max-width:none !important;
            height:auto !important;
            box-shadow:none !important;
            background:transparent !important;
            overflow:hidden !important;
          }

          .etf-v11-op-table th{
            padding:9px 4px !important;
            font-size:13px !important;
            line-height:1.05 !important;
            color:#20252c !important;
            font-weight:900 !important;
            text-align:center !important;
            white-space:normal !important;
          }

          .etf-v11-op-table th:first-child{
            text-align:left !important;
            padding-left:8px !important;
          }

          .etf-v11-op-table td{
            padding:9px 4px !important;
            font-size:15px !important;
            line-height:1.15 !important;
            text-align:center !important;
            white-space:nowrap !important;
          }

          .etf-v11-op-table td:first-child{
            text-align:left !important;
            padding-left:8px !important;
            background:#fff !important;
          }

          .etf-v11-op-table td:nth-child(3),
          .etf-v11-op-table td:nth-child(4),
          .etf-v11-op-table td:nth-child(5){
            text-align:right !important;
          }

          .etf-v11-op-table td:first-child b{
            font-size:17px !important;
            max-width:100% !important;
          }

          .etf-v11-op-table td:first-child small{
            font-size:13px !important;
          }

          .etf-v11-op-table td:nth-child(3){
            font-size:16px !important;
          }

          .etf-v11-op-table td:nth-child(4){
            font-size:15px !important;
          }

          .etf-v11-op-table td:nth-child(5) b{
            font-size:17px !important;
          }

          .etf-v11-op-table td:nth-child(5) small{
            font-size:13px !important;
          }

          .etf-v11-d-sort{
            font-size:13px !important;
            line-height:1.05 !important;
          }

          /* V41：操作日報改成 div grid，不再用 table sticky，避免 iPhone Safari 表頭浮在列中間 */
          .etf-v41-op-grid{
            width:100% !important;
            max-width:100% !important;
            overflow:visible !important;
            background:#fff !important;
            border-top:1px solid #e4e7eb !important;
            border-bottom:1px solid #e4e7eb !important;
          }

          .etf-v41-op-head,
          .etf-v41-op-row{
            display:grid !important;
            grid-template-columns:22% 16% 22% 18% 22% !important;
            align-items:center !important;
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
          }

          .etf-v41-op-head{
            position:sticky !important;
            top:104px !important;
            z-index:140 !important;
            min-height:42px !important;
            background:#f0f1f3 !important;
            border-bottom:1px solid #dfe3e8 !important;
            box-shadow:0 2px 8px rgba(15,23,42,.08) !important;
          }

          .etf-v41-op-head > div{
            min-width:0 !important;
            padding:8px 3px !important;
            color:#20252c !important;
            font-size:13px !important;
            line-height:1.1 !important;
            font-weight:900 !important;
            text-align:center !important;
            overflow:hidden !important;
            white-space:normal !important;
          }

          .etf-v41-op-head > div:first-child{
            text-align:left !important;
            padding-left:8px !important;
          }

          .etf-v41-op-body{
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
          }

          .etf-v41-op-row{
            min-height:64px !important;
            background:#fff !important;
            border-bottom:1px solid #e6e8ec !important;
          }

          .etf-v41-op-row > div{
            min-width:0 !important;
            padding:8px 3px !important;
            overflow:hidden !important;
          }

          .etf-v41-op-target{
            padding-left:8px !important;
          }

          .etf-v41-op-target a{
            display:block !important;
            color:inherit !important;
            text-decoration:none !important;
            min-width:0 !important;
          }

          .etf-v41-op-target b{
            display:block !important;
            font-size:17px !important;
            line-height:1.08 !important;
            font-weight:900 !important;
            white-space:nowrap !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
          }

          .etf-v41-op-target small{
            display:block !important;
            margin-top:5px !important;
            color:#7e8793 !important;
            font-size:13px !important;
            line-height:1 !important;
            font-weight:800 !important;
          }

          .etf-v41-op-status{
            text-align:center !important;
          }

          .etf-v41-op-status .badge{
            display:inline-flex !important;
            align-items:center !important;
            justify-content:center !important;
            min-width:0 !important;
            padding:6px 7px !important;
            border-radius:12px !important;
            font-size:13px !important;
            line-height:1 !important;
            font-weight:900 !important;
            white-space:nowrap !important;
          }

          .etf-v41-op-shares,
          .etf-v41-op-mag,
          .etf-v41-op-weight{
            text-align:right !important;
            white-space:nowrap !important;
          }

          .etf-v41-op-shares{
            font-size:16px !important;
            font-weight:900 !important;
          }

          .etf-v41-op-mag{
            font-size:15px !important;
            font-weight:800 !important;
            color:#20252c !important;
          }

          .etf-v41-op-weight b{
            display:block !important;
            font-size:17px !important;
            line-height:1.08 !important;
            font-weight:900 !important;
            color:#20252c !important;
          }

          .etf-v41-op-weight small{
            display:block !important;
            margin-top:5px !important;
            font-size:13px !important;
            line-height:1 !important;
            font-weight:800 !important;
          }

          .etf-v41-op-head .etf-v11-d-sort{
            width:100% !important;
            display:inline-flex !important;
            justify-content:center !important;
            align-items:center !important;
            gap:2px !important;
            padding:0 !important;
            font-size:13px !important;
            line-height:1.05 !important;
            background:transparent !important;
            border:0 !important;
            color:inherit !important;
            font-weight:900 !important;
          }

          .etf-v41-op-head > div:first-child .etf-v11-d-sort{
            justify-content:flex-start !important;
          }
        }

        /* V42：成分股頁手機壓縮版。圖表與表格都改成一屏可讀，不再靠橫向寬表格。 */
        .etf-v11-tab-content.holdings.compact-holdings{
          padding:18px 18px 32px;
          overflow-x:hidden;
        }

        .etf-v42-distribution-card{
          border:1px solid #e2e6eb;
          border-radius:18px;
          background:#fff;
          padding:16px 18px;
          margin:0 0 18px;
          box-shadow:0 1px 3px rgba(15,23,42,.03);
        }

        .etf-v42-distribution-top{
          display:grid;
          grid-template-columns:1fr auto;
          align-items:center;
          gap:12px;
          margin-bottom:8px;
        }

        .etf-v42-seg-tabs{
          display:inline-flex;
          align-items:center;
          width:max-content;
          background:#e9edf2;
          border-radius:999px;
          padding:3px;
          gap:2px;
        }

        .etf-v42-seg-tabs button{
          border:0;
          border-radius:999px;
          background:transparent;
          color:#fff;
          font-weight:900;
          font-size:16px;
          line-height:1;
          padding:9px 16px;
          font-family:inherit;
        }

        .etf-v42-seg-tabs button.active{
          background:#fff;
          color:#20252c;
          box-shadow:0 1px 5px rgba(15,23,42,.16);
        }

        .etf-v42-seg-tabs button:disabled{
          opacity:1;
        }

        .etf-v42-update{
          color:#7f8895;
          font-size:15px;
          line-height:1.15;
          font-weight:800;
          text-align:right;
          white-space:nowrap;
        }

        .etf-v42-distribution-main{
          display:grid;
          grid-template-columns:minmax(170px, 38%) 1fr;
          align-items:center;
          gap:18px;
        }

        .etf-v42-pie{
          width:220px;
          max-width:100%;
          height:220px;
          justify-self:center;
        }

        .etf-v42-legend{
          min-width:0;
        }

        .etf-v42-legend > div{
          display:grid;
          grid-template-columns:14px minmax(0, 1fr) 76px;
          align-items:center;
          gap:12px;
          min-height:38px;
          border-bottom:1px solid #e7eaee;
        }

        .etf-v42-legend span{
          display:block;
          width:12px;
          height:12px;
        }

        .etf-v42-legend b{
          min-width:0;
          overflow:hidden;
          white-space:nowrap;
          text-overflow:ellipsis;
          color:#20252c;
          font-weight:900;
          font-size:18px;
        }

        .etf-v42-legend strong{
          color:#20252c;
          font-weight:900;
          font-size:18px;
          text-align:right;
          white-space:nowrap;
        }

        .etf-v42-holding-grid{
          width:100%;
          max-width:100%;
          overflow:hidden;
          background:#fff;
          border-top:1px solid #e5e8ee;
          border-bottom:1px solid #e5e8ee;
        }

        .etf-v42-holding-head,
        .etf-v42-holding-row{
          display:grid;
          grid-template-columns:24% 30% 18% 28%;
          align-items:center;
          width:100%;
          max-width:100%;
          min-width:0;
        }

        .etf-v42-holding-head{
          min-height:54px;
          background:#f0f1f3;
          border-bottom:1px solid #dfe3e8;
        }

        .etf-v42-holding-head > div{
          min-width:0;
          padding:10px 8px;
          color:#20252c;
          font-size:15px;
          line-height:1.1;
          font-weight:900;
          text-align:center;
          overflow:hidden;
        }

        .etf-v42-holding-head > div:first-child{
          text-align:left;
          padding-left:14px;
        }

        .etf-v42-holding-row{
          min-height:72px;
          border-bottom:1px solid #e5e8ee;
        }

        .etf-v42-holding-row > div{
          min-width:0;
          padding:10px 8px;
          overflow:hidden;
        }

        .etf-v42-holding-target{
          padding-left:14px !important;
        }

        .etf-v42-holding-target a{
          display:block;
          color:inherit;
          text-decoration:none;
          min-width:0;
        }

        .etf-v42-holding-target b{
          display:block;
          color:#20252c;
          font-size:19px;
          line-height:1.12;
          font-weight:900;
          white-space:nowrap;
          overflow:hidden;
          text-overflow:ellipsis;
        }

        .etf-v42-holding-target small,
        .etf-v42-holding-value small,
        .etf-v42-holding-price small{
          display:block;
          color:#7f8895;
          font-size:15px;
          line-height:1.08;
          font-weight:800;
          margin-top:6px;
        }

        .etf-v42-holding-value,
        .etf-v42-holding-weight,
        .etf-v42-holding-price{
          text-align:right;
          white-space:nowrap;
        }

        .etf-v42-holding-value b,
        .etf-v42-holding-weight b,
        .etf-v42-holding-price b{
          color:#20252c;
          font-size:19px;
          line-height:1.08;
          font-weight:900;
          white-space:nowrap;
        }

        .etf-v42-holding-price small.red,
        .etf-v42-holding-price small.pos{
          color:#df555b;
        }

        .etf-v42-holding-price small.green,
        .etf-v42-holding-price small.neg{
          color:#2fa982;
        }

        .etf-v42-holding-head .etf-v11-d-sort{
          width:100%;
          display:inline-flex;
          align-items:center;
          justify-content:center;
          gap:3px;
          padding:0;
          border:0;
          background:transparent;
          color:inherit;
          font-size:15px;
          line-height:1.08;
          font-weight:900;
          white-space:normal;
        }

        .etf-v42-holding-head > div:first-child .etf-v11-d-sort{
          justify-content:flex-start;
        }

        @media(max-width:760px){
          .etf-v11-tab-content.holdings.compact-holdings{
            padding:8px 0 24px !important;
            background:#fff !important;
            overflow-x:hidden !important;
          }

          .etf-v42-distribution-card{
            margin:0 8px 10px !important;
            padding:10px 10px 12px !important;
            border-radius:14px !important;
            box-shadow:none !important;
          }

          .etf-v42-distribution-top{
            grid-template-columns:1fr auto !important;
            gap:8px !important;
            margin-bottom:8px !important;
          }

          .etf-v42-seg-tabs{
            padding:2px !important;
          }

          .etf-v42-seg-tabs button{
            padding:7px 13px !important;
            font-size:16px !important;
          }

          .etf-v42-update{
            font-size:14px !important;
            line-height:1.12 !important;
          }

          .etf-v42-distribution-main{
            grid-template-columns:42% 58% !important;
            gap:4px !important;
          }

          .etf-v42-pie{
            width:148px !important;
            height:148px !important;
            justify-self:center !important;
          }

          .etf-v42-legend > div{
            grid-template-columns:10px minmax(0, 1fr) 56px !important;
            gap:7px !important;
            min-height:30px !important;
          }

          .etf-v42-legend span{
            width:9px !important;
            height:9px !important;
          }

          .etf-v42-legend b{
            font-size:16px !important;
            line-height:1.05 !important;
          }

          .etf-v42-legend strong{
            font-size:16px !important;
            line-height:1.05 !important;
          }

          .etf-v42-holding-grid{
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            overflow:hidden !important;
            border-radius:0 !important;
          }

          .etf-v42-holding-head,
          .etf-v42-holding-row{
            grid-template-columns:24% 29% 18% 29% !important;
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
          }

          .etf-v42-holding-head{
            position:sticky !important;
            top:104px !important;
            z-index:135 !important;
            min-height:42px !important;
            box-shadow:0 2px 8px rgba(15,23,42,.08) !important;
          }

          .etf-v42-holding-head > div{
            padding:7px 3px !important;
            font-size:13px !important;
            line-height:1.03 !important;
          }

          .etf-v42-holding-head > div:first-child{
            padding-left:8px !important;
          }

          .etf-v42-holding-row{
            min-height:58px !important;
          }

          .etf-v42-holding-row > div{
            padding:7px 3px !important;
          }

          .etf-v42-holding-target{
            padding-left:8px !important;
          }

          .etf-v42-holding-target b{
            font-size:17px !important;
            line-height:1.08 !important;
          }

          .etf-v42-holding-target small,
          .etf-v42-holding-value small,
          .etf-v42-holding-price small{
            font-size:13px !important;
            line-height:1 !important;
            margin-top:4px !important;
          }

          .etf-v42-holding-value b,
          .etf-v42-holding-weight b,
          .etf-v42-holding-price b{
            font-size:17px !important;
            line-height:1.05 !important;
          }

          .etf-v42-holding-head .etf-v11-d-sort{
            font-size:13px !important;
            line-height:1.03 !important;
            gap:1px !important;
          }

          .etf-v42-holding-value,
          .etf-v42-holding-weight,
          .etf-v42-holding-price{
            text-align:right !important;
          }
        }


        /* V43：iPhone Safari 會讓 grid sticky header 漂到資料列中間。
           手機版先改成正常表頭，避免錯位與遮住第一列。 */
        @media(max-width:760px){
          .etf-v11-detail .etf-v41-op-head,
          .etf-v11-detail .etf-v42-holding-head{
            position:static !important;
            top:auto !important;
            z-index:1 !important;
            box-shadow:none !important;
            transform:none !important;
          }

          .etf-v11-detail.modal-open .etf-v41-op-head,
          .etf-v11-detail.modal-open .etf-v42-holding-head{
            visibility:hidden !important;
          }

          .etf-v11-modal-mask{
            padding:18px !important;
          }

          .etf-v11-modal{
            width:calc(100vw - 36px) !important;
            max-height:calc(100vh - 110px) !important;
            padding:24px 24px 20px !important;
            border-radius:16px !important;
          }

          .etf-v11-modal h2{
            font-size:24px !important;
          }

          .etf-v11-modal p{
            font-size:19px !important;
            line-height:1.75 !important;
          }
        }


        /* V44：手機版下方表格重新啟用 sticky header，並用同一組 grid 欄寬讓表頭與資料列完全對齊。
           重點：不要讓 table 或 grid 產生自己的橫向捲動；表頭只在整頁往下滑時固定。 */
        @media(max-width:760px){
          .etf-v11-detail{
            --etf-detail-sticky-top:104px;
            overflow-x:hidden !important;
          }

          .etf-v41-op-grid,
          .etf-v42-holding-grid{
            position:relative !important;
            display:block !important;
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            overflow:visible !important;
            background:#fff !important;
            isolation:isolate !important;
            transform:none !important;
          }

          .etf-v41-op-grid{
            --op-grid-cols:22% 16% 22% 18% 22%;
          }

          .etf-v42-holding-grid{
            --holding-grid-cols:24% 29% 18% 29%;
          }

          .etf-v41-op-head,
          .etf-v41-op-row{
            display:grid !important;
            grid-template-columns:var(--op-grid-cols) !important;
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            box-sizing:border-box !important;
          }

          .etf-v42-holding-head,
          .etf-v42-holding-row{
            display:grid !important;
            grid-template-columns:var(--holding-grid-cols) !important;
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            box-sizing:border-box !important;
          }

          .etf-v41-op-head,
          .etf-v42-holding-head{
            position:sticky !important;
            top:var(--etf-detail-sticky-top) !important;
            z-index:260 !important;
            transform:translateZ(0) !important;
            -webkit-transform:translateZ(0) !important;
            background:#f0f1f3 !important;
            border-top:1px solid #e2e5ea !important;
            border-bottom:1px solid #dfe3e8 !important;
            box-shadow:0 2px 8px rgba(15,23,42,.08) !important;
            overflow:hidden !important;
          }

          .etf-v41-op-head > div,
          .etf-v42-holding-head > div,
          .etf-v41-op-row > div,
          .etf-v42-holding-row > div{
            box-sizing:border-box !important;
            min-width:0 !important;
            max-width:100% !important;
            overflow:hidden !important;
          }

          .etf-v41-op-row,
          .etf-v42-holding-row{
            position:relative !important;
            z-index:1 !important;
            background:#fff !important;
          }

          .etf-v41-op-body,
          .etf-v42-holding-body{
            position:relative !important;
            z-index:1 !important;
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            overflow:visible !important;
          }

          .etf-v41-op-head .etf-v11-d-sort,
          .etf-v42-holding-head .etf-v11-d-sort{
            display:inline-flex !important;
            max-width:100% !important;
            white-space:normal !important;
            overflow:hidden !important;
            text-overflow:clip !important;
          }

          .etf-v11-detail.modal-open .etf-v41-op-head,
          .etf-v11-detail.modal-open .etf-v42-holding-head{
            visibility:hidden !important;
            z-index:1 !important;
          }
        }


        /* V45：最後覆蓋手機版表格。修正 iPhone Safari 中 sticky header 與資料列欄位不同步、第一欄偏移、欄距過寬問題。 */
        @media(max-width:760px){
          .etf-v11-detail{
            --etf-v45-nav-top:104px;
            width:100% !important;
            max-width:100vw !important;
            overflow-x:hidden !important;
          }

          .etf-v11-tab-content.operation,
          .etf-v11-tab-content.holdings.compact-holdings{
            width:100% !important;
            max-width:100vw !important;
            overflow-x:hidden !important;
          }

          /* 取消任何舊版 left sticky / 寬表格殘留 */
          .etf-v41-op-grid,
          .etf-v42-holding-grid,
          .etf-v41-op-head,
          .etf-v42-holding-head,
          .etf-v41-op-body,
          .etf-v42-holding-body,
          .etf-v41-op-row,
          .etf-v42-holding-row,
          .etf-v41-op-grid > *,
          .etf-v42-holding-grid > *,
          .etf-v41-op-row > *,
          .etf-v42-holding-row > *,
          .etf-v41-op-head > *,
          .etf-v42-holding-head > *{
            box-sizing:border-box !important;
            min-width:0 !important;
            max-width:100% !important;
            transform:none !important;
            -webkit-transform:none !important;
          }

          .etf-v41-op-grid,
          .etf-v42-holding-grid{
            display:block !important;
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            overflow:visible !important;
            background:#fff !important;
            border-radius:0 !important;
            border-top:1px solid #e2e5ea !important;
            border-bottom:1px solid #e2e5ea !important;
          }

          .etf-v41-op-body,
          .etf-v42-holding-body{
            display:block !important;
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            overflow:visible !important;
          }

          /* 操作日報：全部 5 欄固定塞進單一手機頁寬 */
          .etf-v41-op-head,
          .etf-v41-op-row{
            display:grid !important;
            grid-template-columns:22% 17% 21% 18% 22% !important;
            column-gap:0 !important;
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            margin:0 !important;
          }

          /* 成分股：全部 4 欄固定塞進單一手機頁寬 */
          .etf-v42-holding-head,
          .etf-v42-holding-row{
            display:grid !important;
            grid-template-columns:24% 28% 18% 30% !important;
            column-gap:0 !important;
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            margin:0 !important;
          }

          .etf-v41-op-head,
          .etf-v42-holding-head{
            position:sticky !important;
            top:var(--etf-v45-nav-top) !important;
            z-index:300 !important;
            min-height:42px !important;
            background:#f0f1f3 !important;
            border-top:1px solid #e2e5ea !important;
            border-bottom:1px solid #d7dce3 !important;
            box-shadow:0 2px 7px rgba(15,23,42,.08) !important;
            overflow:hidden !important;
          }

          .etf-v41-op-row,
          .etf-v42-holding-row{
            position:relative !important;
            z-index:1 !important;
            min-height:60px !important;
            background:#fff !important;
            border-bottom:1px solid #e6e8ec !important;
            align-items:center !important;
            overflow:hidden !important;
          }

          .etf-v41-op-head > div,
          .etf-v42-holding-head > div{
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            width:100% !important;
            min-width:0 !important;
            padding:7px 2px !important;
            overflow:hidden !important;
            text-align:center !important;
            color:#20252c !important;
            font-size:13px !important;
            line-height:1.04 !important;
            font-weight:900 !important;
            white-space:normal !important;
          }

          .etf-v41-op-head > div:first-child,
          .etf-v42-holding-head > div:first-child{
            justify-content:flex-start !important;
            text-align:left !important;
            padding-left:8px !important;
            padding-right:2px !important;
          }

          .etf-v41-op-head .etf-v11-d-sort,
          .etf-v42-holding-head .etf-v11-d-sort{
            width:100% !important;
            max-width:100% !important;
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            gap:1px !important;
            padding:0 !important;
            margin:0 !important;
            border:0 !important;
            background:transparent !important;
            color:inherit !important;
            font-size:13px !important;
            line-height:1.04 !important;
            font-weight:900 !important;
            white-space:normal !important;
            overflow:hidden !important;
            text-align:center !important;
          }

          .etf-v41-op-head > div:first-child .etf-v11-d-sort,
          .etf-v42-holding-head > div:first-child .etf-v11-d-sort{
            justify-content:flex-start !important;
            text-align:left !important;
          }

          .etf-v11-d-sort .sort-arrows,
          .sort-arrows{
            flex:0 0 auto !important;
            display:inline-flex !important;
            flex-direction:column !important;
            gap:0 !important;
            margin-left:1px !important;
            font-size:9px !important;
            line-height:.72 !important;
          }

          .etf-v41-op-row > div,
          .etf-v42-holding-row > div{
            width:100% !important;
            min-width:0 !important;
            max-width:100% !important;
            padding:7px 3px !important;
            overflow:hidden !important;
          }

          .etf-v41-op-target,
          .etf-v42-holding-target{
            padding-left:8px !important;
            padding-right:2px !important;
            text-align:left !important;
          }

          .etf-v41-op-target a,
          .etf-v42-holding-target a{
            display:block !important;
            width:100% !important;
            min-width:0 !important;
            overflow:hidden !important;
            color:inherit !important;
            text-decoration:none !important;
          }

          .etf-v41-op-target b,
          .etf-v42-holding-target b{
            display:block !important;
            width:100% !important;
            max-width:100% !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
            white-space:nowrap !important;
            color:#20252c !important;
            font-size:17px !important;
            line-height:1.08 !important;
            font-weight:900 !important;
          }

          .etf-v41-op-target small,
          .etf-v42-holding-target small,
          .etf-v42-holding-value small,
          .etf-v42-holding-price small{
            display:block !important;
            margin-top:4px !important;
            color:#7f8895 !important;
            font-size:13px !important;
            line-height:1 !important;
            font-weight:800 !important;
          }

          .etf-v41-op-status,
          .etf-v41-op-shares,
          .etf-v41-op-mag,
          .etf-v41-op-weight,
          .etf-v42-holding-value,
          .etf-v42-holding-weight,
          .etf-v42-holding-price{
            text-align:right !important;
            white-space:nowrap !important;
          }

          .etf-v41-op-status{
            text-align:center !important;
          }

          .etf-v41-op-status .badge{
            display:inline-flex !important;
            align-items:center !important;
            justify-content:center !important;
            padding:6px 7px !important;
            border-radius:999px !important;
            font-size:13px !important;
            line-height:1 !important;
            font-weight:900 !important;
            white-space:nowrap !important;
          }

          .etf-v41-op-shares,
          .etf-v42-holding-value b,
          .etf-v42-holding-weight b,
          .etf-v42-holding-price b{
            font-size:17px !important;
            line-height:1.05 !important;
            font-weight:900 !important;
          }

          .etf-v41-op-mag{
            font-size:15px !important;
            line-height:1.05 !important;
            font-weight:800 !important;
            color:#20252c !important;
          }

          .etf-v41-op-weight b{
            display:block !important;
            font-size:17px !important;
            line-height:1.05 !important;
            font-weight:900 !important;
            color:#20252c !important;
          }

          .etf-v41-op-weight small{
            display:block !important;
            margin-top:4px !important;
            font-size:13px !important;
            line-height:1 !important;
            font-weight:800 !important;
          }

          .etf-v42-holding-value,
          .etf-v42-holding-weight,
          .etf-v42-holding-price{
            padding-left:2px !important;
            padding-right:8px !important;
          }

          .etf-v42-holding-value{
            padding-right:4px !important;
          }

          .etf-v42-holding-weight{
            text-align:center !important;
            padding-right:2px !important;
          }

          .etf-v42-holding-head > div:nth-child(2),
          .etf-v42-holding-head > div:nth-child(4){
            justify-content:flex-end !important;
            text-align:right !important;
            padding-right:8px !important;
          }

          .etf-v42-holding-head > div:nth-child(3){
            justify-content:center !important;
            text-align:center !important;
          }

          .etf-v41-op-head > div:nth-child(3),
          .etf-v41-op-head > div:nth-child(4),
          .etf-v41-op-head > div:nth-child(5){
            justify-content:flex-end !important;
            text-align:right !important;
            padding-right:6px !important;
          }

          .etf-v11-detail.modal-open .etf-v41-op-head,
          .etf-v11-detail.modal-open .etf-v42-holding-head{
            visibility:hidden !important;
            pointer-events:none !important;
          }

          /* 更窄螢幕再微調字級，避免最後一欄被 Safari 工具列壓住 */
          @media(max-width:390px){
            .etf-v41-op-head,
            .etf-v41-op-row{ grid-template-columns:22% 17% 21% 18% 22% !important; }
            .etf-v42-holding-head,
            .etf-v42-holding-row{ grid-template-columns:24% 28% 18% 30% !important; }
            .etf-v41-op-target b,
            .etf-v42-holding-target b,
            .etf-v41-op-shares,
            .etf-v42-holding-value b,
            .etf-v42-holding-weight b,
            .etf-v42-holding-price b,
            .etf-v41-op-weight b{ font-size:16px !important; }
            .etf-v41-op-head .etf-v11-d-sort,
            .etf-v42-holding-head .etf-v11-d-sort,
            .etf-v41-op-head > div,
            .etf-v42-holding-head > div{ font-size:12px !important; }
          }
        }



        /* V46：手機版表格硬性對齊版
           目的：不要再讓 Safari 依內容自動放寬欄位；表頭與每一列使用完全相同的 viewport 欄寬。
           成分股：標的 23vw / 市值 29vw / 權重 18vw / 股價 30vw = 100vw
           操作日報：標的 22vw / 狀態 15vw / 變動 23vw / 幅度 18vw / 權重 22vw = 100vw
        */
        @media(max-width:760px){
          html, body{
            overflow-x:hidden !important;
            max-width:100vw !important;
          }

          .etf-v11-detail{
            width:100vw !important;
            max-width:100vw !important;
            overflow-x:hidden !important;
            --etf-v46-sticky-top:104px;
          }

          .etf-v11-tab-content.operation,
          .etf-v11-tab-content.holdings.compact-holdings{
            width:100vw !important;
            max-width:100vw !important;
            margin-left:calc(50% - 50vw) !important;
            margin-right:calc(50% - 50vw) !important;
            overflow-x:hidden !important;
            box-sizing:border-box !important;
          }

          .etf-v11-tab-content.operation{
            padding-left:16px !important;
            padding-right:16px !important;
          }

          .etf-v41-op-grid{
            width:calc(100vw - 32px) !important;
            max-width:calc(100vw - 32px) !important;
            margin-left:0 !important;
            margin-right:0 !important;
            overflow:hidden !important;
            border-radius:0 !important;
            background:#fff !important;
          }

          .etf-v42-holding-grid{
            width:100vw !important;
            max-width:100vw !important;
            margin-left:0 !important;
            margin-right:0 !important;
            overflow:hidden !important;
            border-radius:0 !important;
            background:#fff !important;
          }

          .etf-v41-op-head,
          .etf-v41-op-row,
          .etf-v42-holding-head,
          .etf-v42-holding-row{
            display:grid !important;
            column-gap:0 !important;
            box-sizing:border-box !important;
            min-width:0 !important;
            max-width:none !important;
            margin:0 !important;
            padding:0 !important;
            align-items:center !important;
          }

          .etf-v41-op-head,
          .etf-v41-op-row{
            grid-template-columns:22% 15% 23% 18% 22% !important;
            width:100% !important;
          }

          .etf-v42-holding-head,
          .etf-v42-holding-row{
            grid-template-columns:23vw 29vw 18vw 30vw !important;
            width:100vw !important;
          }

          .etf-v41-op-head,
          .etf-v42-holding-head{
            position:sticky !important;
            top:var(--etf-v46-sticky-top) !important;
            z-index:420 !important;
            background:#f0f1f3 !important;
            min-height:42px !important;
            border-top:1px solid #e4e7ec !important;
            border-bottom:1px solid #d7dce3 !important;
            box-shadow:0 2px 7px rgba(15,23,42,.07) !important;
            overflow:hidden !important;
          }

          .etf-v41-op-row,
          .etf-v42-holding-row{
            min-height:58px !important;
            background:#fff !important;
            border-bottom:1px solid #e7e9ee !important;
            overflow:hidden !important;
          }

          .etf-v41-op-head > div,
          .etf-v42-holding-head > div,
          .etf-v41-op-row > div,
          .etf-v42-holding-row > div{
            min-width:0 !important;
            max-width:100% !important;
            width:100% !important;
            box-sizing:border-box !important;
            overflow:hidden !important;
            transform:none !important;
            -webkit-transform:none !important;
          }

          .etf-v41-op-head > div,
          .etf-v42-holding-head > div{
            padding:7px 2px !important;
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            font-size:12.5px !important;
            line-height:1.02 !important;
            font-weight:900 !important;
            color:#20252c !important;
            white-space:normal !important;
            text-align:center !important;
          }

          .etf-v41-op-head > div:first-child,
          .etf-v42-holding-head > div:first-child{
            justify-content:flex-start !important;
            padding-left:8px !important;
            text-align:left !important;
          }

          .etf-v41-op-row > div,
          .etf-v42-holding-row > div{
            padding:6px 3px !important;
          }

          .etf-v41-op-target,
          .etf-v42-holding-target{
            padding-left:8px !important;
            padding-right:2px !important;
            text-align:left !important;
          }

          .etf-v41-op-target a,
          .etf-v42-holding-target a{
            display:block !important;
            width:100% !important;
            min-width:0 !important;
            overflow:hidden !important;
            text-decoration:none !important;
            color:inherit !important;
          }

          .etf-v41-op-target b,
          .etf-v42-holding-target b{
            display:block !important;
            width:100% !important;
            max-width:100% !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
            white-space:nowrap !important;
            font-size:16px !important;
            line-height:1.05 !important;
            font-weight:900 !important;
            color:#20252c !important;
          }

          .etf-v41-op-target small,
          .etf-v42-holding-target small,
          .etf-v42-holding-value small,
          .etf-v42-holding-price small{
            display:block !important;
            margin-top:4px !important;
            font-size:12.5px !important;
            line-height:1 !important;
            font-weight:800 !important;
            color:#7f8895 !important;
            white-space:nowrap !important;
          }

          .etf-v41-op-status,
          .etf-v41-op-shares,
          .etf-v41-op-mag,
          .etf-v41-op-weight,
          .etf-v42-holding-value,
          .etf-v42-holding-weight,
          .etf-v42-holding-price{
            white-space:nowrap !important;
            text-align:right !important;
          }

          .etf-v41-op-status{
            text-align:center !important;
          }

          .etf-v41-op-status .badge{
            display:inline-flex !important;
            align-items:center !important;
            justify-content:center !important;
            padding:5px 6px !important;
            border-radius:999px !important;
            font-size:12.5px !important;
            line-height:1 !important;
            font-weight:900 !important;
            white-space:nowrap !important;
          }

          .etf-v41-op-shares,
          .etf-v42-holding-value b,
          .etf-v42-holding-weight b,
          .etf-v42-holding-price b,
          .etf-v41-op-weight b{
            display:block !important;
            font-size:16px !important;
            line-height:1.04 !important;
            font-weight:900 !important;
            color:#20252c;
            white-space:nowrap !important;
          }

          .etf-v41-op-mag{
            font-size:14px !important;
            line-height:1.04 !important;
            font-weight:800 !important;
            color:#20252c !important;
          }

          .etf-v41-op-weight small{
            display:block !important;
            margin-top:4px !important;
            font-size:12.5px !important;
            line-height:1 !important;
            font-weight:800 !important;
          }

          .etf-v42-holding-value{
            padding-left:2px !important;
            padding-right:4px !important;
            text-align:right !important;
          }

          .etf-v42-holding-weight{
            padding-left:0 !important;
            padding-right:0 !important;
            text-align:center !important;
          }

          .etf-v42-holding-price{
            padding-left:2px !important;
            padding-right:8px !important;
            text-align:right !important;
          }

          .etf-v42-holding-head > div:nth-child(2),
          .etf-v42-holding-head > div:nth-child(4){
            justify-content:flex-end !important;
            text-align:right !important;
            padding-right:8px !important;
          }

          .etf-v42-holding-head > div:nth-child(3){
            justify-content:center !important;
            text-align:center !important;
          }

          .etf-v41-op-head > div:nth-child(3),
          .etf-v41-op-head > div:nth-child(4),
          .etf-v41-op-head > div:nth-child(5){
            justify-content:flex-end !important;
            text-align:right !important;
            padding-right:5px !important;
          }

          .etf-v41-op-head .etf-v11-d-sort,
          .etf-v42-holding-head .etf-v11-d-sort{
            width:100% !important;
            max-width:100% !important;
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            gap:1px !important;
            padding:0 !important;
            margin:0 !important;
            border:0 !important;
            background:transparent !important;
            color:inherit !important;
            font-size:12.5px !important;
            line-height:1.02 !important;
            font-weight:900 !important;
            white-space:normal !important;
            text-align:center !important;
            overflow:hidden !important;
          }

          .etf-v41-op-head > div:first-child .etf-v11-d-sort,
          .etf-v42-holding-head > div:first-child .etf-v11-d-sort{
            justify-content:flex-start !important;
            text-align:left !important;
          }

          .etf-v11-d-sort .sort-arrows,
          .sort-arrows{
            flex:0 0 auto !important;
            display:inline-flex !important;
            flex-direction:column !important;
            margin-left:1px !important;
            gap:0 !important;
            font-size:8.5px !important;
            line-height:.68 !important;
          }

          /* 說明彈窗開啟時，所有表格表頭一律退到背景，避免蓋到彈窗文字。 */
          .etf-v11-detail.modal-open .etf-v41-op-head,
          .etf-v11-detail.modal-open .etf-v42-holding-head{
            opacity:0 !important;
            visibility:hidden !important;
            pointer-events:none !important;
            z-index:1 !important;
          }

          @media(max-width:390px){
            .etf-v41-op-grid{ width:calc(100vw - 24px) !important; max-width:calc(100vw - 24px) !important; }
            .etf-v11-tab-content.operation{ padding-left:12px !important; padding-right:12px !important; }
            .etf-v41-op-target b,
            .etf-v42-holding-target b,
            .etf-v41-op-shares,
            .etf-v42-holding-value b,
            .etf-v42-holding-weight b,
            .etf-v42-holding-price b,
            .etf-v41-op-weight b{ font-size:15px !important; }
            .etf-v41-op-head > div,
            .etf-v42-holding-head > div,
            .etf-v41-op-head .etf-v11-d-sort,
            .etf-v42-holding-head .etf-v11-d-sort{ font-size:11.5px !important; }
          }
        }


        /* V47：手機版再縮小 + 改回容器百分比欄寬。
           重點：
           1. 不再用 100vw 當每一列寬度，避免 iPhone WebView / Safari 地址列造成視覺溢出。
           2. 成分股與操作日報都改成更小字級與更低列高，接近 App 圖 2/圖 4 的資訊密度。
           3. 表頭與資料列使用同一組 grid-template-columns，避免 sticky header 與內容錯位。
        */
        @media(max-width:760px){
          .etf-v11-detail{
            width:100% !important;
            max-width:100% !important;
            overflow-x:hidden !important;
            --etf-v47-sticky-top:104px;
          }

          .etf-v11-tab-content.operation,
          .etf-v11-tab-content.holdings.compact-holdings{
            width:100% !important;
            max-width:100% !important;
            margin-left:0 !important;
            margin-right:0 !important;
            overflow-x:hidden !important;
            box-sizing:border-box !important;
          }

          /* 成分股上方圓餅區再壓小一點，讓下方表格更快出現 */
          .etf-v11-tab-content.holdings.compact-holdings{
            padding:6px 0 22px !important;
          }

          .etf-v42-distribution-card{
            margin:0 8px 8px !important;
            padding:8px 8px 9px !important;
            border-radius:13px !important;
            overflow:hidden !important;
          }

          .etf-v42-distribution-top{
            margin-bottom:6px !important;
          }

          .etf-v42-seg-tabs button{
            font-size:14px !important;
            padding:6px 11px !important;
          }

          .etf-v42-update{
            font-size:12.5px !important;
            line-height:1.08 !important;
          }

          .etf-v42-distribution-main{
            grid-template-columns:39% 61% !important;
            gap:0 !important;
            align-items:center !important;
          }

          .etf-v42-pie{
            width:126px !important;
            height:126px !important;
          }

          .etf-v42-legend > div{
            grid-template-columns:8px minmax(0, 1fr) 50px !important;
            min-height:26px !important;
            gap:5px !important;
          }

          .etf-v42-legend span{
            width:8px !important;
            height:8px !important;
          }

          .etf-v42-legend b,
          .etf-v42-legend strong{
            font-size:14px !important;
            line-height:1.02 !important;
          }

          /* 成分股表格：百分比欄寬，完整塞進目前容器 */
          .etf-v42-holding-grid{
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            margin:0 !important;
            overflow:hidden !important;
            border-radius:0 !important;
            background:#fff !important;
          }

          .etf-v42-holding-head,
          .etf-v42-holding-row{
            display:grid !important;
            grid-template-columns:23% 28% 17% 32% !important;
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            column-gap:0 !important;
            box-sizing:border-box !important;
            align-items:center !important;
          }

          .etf-v42-holding-head{
            position:sticky !important;
            top:var(--etf-v47-sticky-top) !important;
            z-index:430 !important;
            min-height:38px !important;
            background:#f0f1f3 !important;
            border-top:1px solid #e4e7ec !important;
            border-bottom:1px solid #d7dce3 !important;
            box-shadow:0 2px 7px rgba(15,23,42,.06) !important;
          }

          .etf-v42-holding-row{
            min-height:50px !important;
            border-bottom:1px solid #e7e9ee !important;
            background:#fff !important;
          }

          .etf-v42-holding-head > div,
          .etf-v42-holding-row > div{
            min-width:0 !important;
            max-width:100% !important;
            width:100% !important;
            overflow:hidden !important;
            box-sizing:border-box !important;
          }

          .etf-v42-holding-head > div{
            padding:5px 2px !important;
            font-size:11.5px !important;
            line-height:1.02 !important;
            font-weight:900 !important;
          }

          .etf-v42-holding-row > div{
            padding:5px 2px !important;
          }

          .etf-v42-holding-target{
            padding-left:6px !important;
            padding-right:1px !important;
          }

          .etf-v42-holding-target b{
            font-size:14.5px !important;
            line-height:1.03 !important;
            letter-spacing:-.2px !important;
          }

          .etf-v42-holding-target small,
          .etf-v42-holding-value small,
          .etf-v42-holding-price small{
            font-size:11.5px !important;
            line-height:1 !important;
            margin-top:3px !important;
          }

          .etf-v42-holding-value b,
          .etf-v42-holding-weight b,
          .etf-v42-holding-price b{
            font-size:14.5px !important;
            line-height:1.03 !important;
            letter-spacing:-.2px !important;
          }

          .etf-v42-holding-value{
            padding-right:3px !important;
          }

          .etf-v42-holding-weight{
            text-align:center !important;
            padding-left:0 !important;
            padding-right:0 !important;
          }

          .etf-v42-holding-price{
            padding-right:6px !important;
          }

          .etf-v42-holding-head .etf-v11-d-sort{
            font-size:11.5px !important;
            line-height:1.02 !important;
            gap:1px !important;
          }

          /* 操作日報同樣縮小，避免再出現橫向滑動 */
          .etf-v11-tab-content.operation{
            padding-left:12px !important;
            padding-right:12px !important;
          }

          .etf-v41-op-grid{
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            margin:0 !important;
            overflow:hidden !important;
            border-radius:0 !important;
            background:#fff !important;
          }

          .etf-v41-op-head,
          .etf-v41-op-row{
            display:grid !important;
            grid-template-columns:22% 15% 23% 18% 22% !important;
            width:100% !important;
            max-width:100% !important;
            min-width:0 !important;
            column-gap:0 !important;
            box-sizing:border-box !important;
            align-items:center !important;
          }

          .etf-v41-op-head{
            position:sticky !important;
            top:var(--etf-v47-sticky-top) !important;
            z-index:430 !important;
            min-height:38px !important;
            background:#f0f1f3 !important;
            border-top:1px solid #e4e7ec !important;
            border-bottom:1px solid #d7dce3 !important;
            box-shadow:0 2px 7px rgba(15,23,42,.06) !important;
          }

          .etf-v41-op-row{
            min-height:50px !important;
            border-bottom:1px solid #e7e9ee !important;
            background:#fff !important;
          }

          .etf-v41-op-head > div,
          .etf-v41-op-row > div{
            min-width:0 !important;
            max-width:100% !important;
            width:100% !important;
            overflow:hidden !important;
            box-sizing:border-box !important;
          }

          .etf-v41-op-head > div{
            padding:5px 2px !important;
            font-size:11.5px !important;
            line-height:1.02 !important;
            font-weight:900 !important;
          }

          .etf-v41-op-row > div{
            padding:5px 2px !important;
          }

          .etf-v41-op-target{
            padding-left:6px !important;
            padding-right:1px !important;
          }

          .etf-v41-op-target b{
            font-size:14.5px !important;
            line-height:1.03 !important;
            letter-spacing:-.2px !important;
          }

          .etf-v41-op-target small,
          .etf-v41-op-weight small{
            font-size:11.5px !important;
            line-height:1 !important;
            margin-top:3px !important;
          }

          .etf-v41-op-status .badge{
            font-size:11.5px !important;
            padding:4px 5px !important;
          }

          .etf-v41-op-shares,
          .etf-v41-op-weight b{
            font-size:14.5px !important;
            line-height:1.03 !important;
            letter-spacing:-.2px !important;
          }

          .etf-v41-op-mag{
            font-size:13px !important;
            line-height:1.03 !important;
            letter-spacing:-.2px !important;
          }

          .etf-v41-op-head .etf-v11-d-sort{
            font-size:11.5px !important;
            line-height:1.02 !important;
            gap:1px !important;
          }

          .etf-v11-d-sort .sort-arrows,
          .sort-arrows{
            font-size:7.5px !important;
            line-height:.64 !important;
            margin-left:1px !important;
          }

          .etf-v11-detail.modal-open .etf-v41-op-head,
          .etf-v11-detail.modal-open .etf-v42-holding-head{
            opacity:0 !important;
            visibility:hidden !important;
            pointer-events:none !important;
            z-index:1 !important;
          }
        }

      `}</style>
    </main>
  );
}
