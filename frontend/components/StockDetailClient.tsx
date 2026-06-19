'use client';

import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fmt, fmt0, signedClass } from '@/lib/api';

type EtfSortKey = 'etf' | 'value' | 'weight';
type SortDir = 'asc' | 'desc';

function shortDate(s: string) {
  if (!s) return '';
  return String(s).slice(5).replace('-', '/');
}

function lots(shares: any) {
  return Number(shares || 0) / 1000;
}

function asNumber(v: any): number | null {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function buildHoldingHistory(rows: any[] = []) {
  const map = new Map<string, { date: string; shares_lots: number; weight_sum: number }>();

  for (const r of rows) {
    const d = String(r.data_date || '');
    if (!d) continue;

    if (!map.has(d)) {
      map.set(d, { date: d, shares_lots: 0, weight_sum: 0 });
    }

    const x = map.get(d)!;
    x.shares_lots += lots(r.shares);
    x.weight_sum += Number(r.weight || 0);
  }

  return [...map.values()].sort((a, b) => a.date.localeCompare(b.date)).slice(-90);
}

function calcReturnByTradingDays(priceHistory: any[], days: number) {
  const arr = (priceHistory || []).filter((x: any) => asNumber(x?.close) !== null);
  if (arr.length < 2) return null;

  const latest = asNumber(arr[arr.length - 1]?.close);
  const baseIndex = Math.max(0, arr.length - 1 - days);
  const base = asNumber(arr[baseIndex]?.close);

  if (!latest || !base) return null;
  return ((latest - base) / base) * 100;
}

function calcFullPeriodReturn(priceHistory: any[]) {
  const arr = (priceHistory || []).filter((x: any) => asNumber(x?.close) !== null);
  if (arr.length < 2) return null;

  const latest = asNumber(arr[arr.length - 1]?.close);
  const first = asNumber(arr[0]?.close);

  if (!latest || !first) return null;
  return ((latest - first) / first) * 100;
}

function calcPriceChange(priceHistory: any[], quote: any) {
  const qChange = asNumber(quote?.change ?? quote?.change_amount ?? quote?.price_change);
  if (qChange !== null) return qChange;

  const arr = (priceHistory || []).filter((x: any) => asNumber(x?.close) !== null);
  if (arr.length < 2) return null;

  const latest = asNumber(arr[arr.length - 1]?.close);
  const prev = asNumber(arr[arr.length - 2]?.close);

  if (latest === null || prev === null) return null;
  return latest - prev;
}

function calcPriceChangePct(priceHistory: any[], quote: any) {
  const qPct = asNumber(quote?.change_pct);
  if (qPct !== null) return qPct;

  const arr = (priceHistory || []).filter((x: any) => asNumber(x?.close) !== null);
  if (arr.length < 2) return null;

  const latest = asNumber(arr[arr.length - 1]?.close);
  const prev = asNumber(arr[arr.length - 2]?.close);

  if (!latest || !prev) return null;
  return ((latest - prev) / prev) * 100;
}

function calcVolumeChangePct(priceHistory: any[], quote: any) {
  const qPct = asNumber(quote?.volume_change_pct ?? quote?.volume_pct ?? quote?.volume_change);
  if (qPct !== null) return qPct;

  const arr = (priceHistory || []).filter((x: any) => asNumber(x?.volume) !== null);
  if (arr.length < 2) return null;

  const latest = asNumber(arr[arr.length - 1]?.volume);
  const prev = asNumber(arr[arr.length - 2]?.volume);

  if (!latest || !prev) return null;
  return ((latest - prev) / prev) * 100;
}

function signedNumber(v: number | null, digits = 0) {
  if (v === null || Number.isNaN(v)) return '-';
  const prefix = v > 0 ? '+' : v < 0 ? '-' : '';
  return `${prefix}${Math.abs(v).toLocaleString('zh-TW', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  })}`;
}

function signedPct(v: number | null, digits = 1) {
  if (v === null || Number.isNaN(v)) return '-';
  const prefix = v > 0 ? '+' : '';
  return `${prefix}${v.toFixed(digits)}%`;
}

function toneClass(v: number | null) {
  if (v === null || Number.isNaN(v)) return 'flat';
  if (v > 0) return 'up';
  if (v < 0) return 'down';
  return 'flat';
}

function sumInstitutionalByDate(rows: any[] = []) {
  const map = new Map<string, any>();

  for (const r of rows) {
    const d = String(r.trade_date || '');
    if (!d) continue;

    if (!map.has(d)) {
      map.set(d, {
        trade_date: d,
        foreign_net: 0,
        investment_trust_net: 0,
        dealer_net: 0,
        total_net: 0,
      });
    }

    const x = map.get(d)!;
    x.foreign_net += Number(r.foreign_net || 0);
    x.investment_trust_net += Number(r.investment_trust_net || 0);
    x.dealer_net += Number(r.dealer_net || 0);
    x.total_net += Number(r.total_net || 0);
  }

  return [...map.values()].sort((a, b) => String(b.trade_date).localeCompare(String(a.trade_date))).slice(0, 20);
}

export default function StockDetailClient({ data }: { data: any }) {

  const routerV83 = useRouter();

  function handleFastBackV83(e?: any) {
    if (e?.preventDefault) e.preventDefault();

    if (typeof window !== 'undefined') {
      const ref = document.referrer || '';
      const sameSiteRef = ref.includes(window.location.host);

      // 最快：回到瀏覽器上一頁，不重新 push 到 /signals /holdings /etfs。
      // 這樣從今日訊號、資金持股、ETF列表點進來，再按左上角 <，通常會直接回到原頁與原捲動位置。
      if (window.history.length > 1 && sameSiteRef) {
        window.history.back();
        return;
      }

      const params = new URLSearchParams(window.location.search);
      const from = params.get('from') || params.get('src') || params.get('source') || '';

      if (from === 'signals' || from === 'signal') {
        routerV83.push('/signals');
        return;
      }
      if (from === 'holdings' || from === 'funds') {
        routerV83.push('/holdings');
        return;
      }
      if (from === 'search') {
        routerV83.push('/search');
        return;
      }
    }

    routerV83.push('/etfs');
  }

  const searchParams = useSearchParams();

  function resolveStockBackHref() {
    const returnToParam = searchParams.get('returnTo') || '';
    const fromParam = searchParams.get('from') || '';

    if (returnToParam) return returnToParam;
    if (fromParam === 'holdings') return '/holdings';
    if (fromParam === 'signals') return '/signals';
    if (fromParam === 'etfs') return '/etfs';
    if (fromParam === 'search') return '/search';

    if (typeof window !== 'undefined') {
      const storedReturnTo =
        window.sessionStorage.getItem('stockReturnTo') ||
        window.sessionStorage.getItem('activeEtfReturnTo') ||
        window.sessionStorage.getItem('activeEtfOriginReturnTo') ||
        '';
      const storedFrom =
        window.sessionStorage.getItem('stockFrom') ||
        window.sessionStorage.getItem('activeEtfFrom') ||
        '';

      if (storedReturnTo) return storedReturnTo;
      if (storedFrom === 'holdings') return '/holdings';
      if (storedFrom === 'signals') return '/signals';
      if (storedFrom === 'etfs') return '/etfs';
      if (storedFrom === 'search') return '/search';
    }

    // 個股頁最常見入口是資金持股；不要再 fallback 到搜尋頁。
    return '/holdings';
  }

  const stockBackHref = resolveStockBackHref();


  function buildEtfHrefFromStock(etfCode: string) {
    const returnTo = stockBackHref || '/holdings';
    const from = returnTo.startsWith('/holdings') ? 'holdings'
      : returnTo.startsWith('/signals') ? 'signals'
      : returnTo.startsWith('/etfs') ? 'etfs'
      : returnTo.startsWith('/search') ? 'search'
      : 'holdings';

    if (typeof window !== 'undefined') {
      window.sessionStorage.setItem('activeEtfReturnTo', returnTo);
      window.sessionStorage.setItem('activeEtfOriginReturnTo', returnTo);
      window.sessionStorage.setItem('activeEtfFrom', from);
    }

    const params = new URLSearchParams();
    params.set('from', from);
    params.set('returnTo', returnTo);
    return `/etf/${etfCode}?${params.toString()}`;
  }
  const [showInfo, setShowInfo] = useState(false);
  const [chartMode, setChartMode] = useState<'price' | 'holding'>('price');
  const [etfSortKey, setEtfSortKey] = useState<EtfSortKey>('value');
  const [etfSortDir, setEtfSortDir] = useState<SortDir>('desc');

  const quote = data.quote || {};
  const priceChart = useMemo(() => (data.price_history || []).slice(-90), [data.price_history]);
  const holdingChart = useMemo(() => buildHoldingHistory(data.history || []), [data.history]);
  const institutionalRows = useMemo(() => sumInstitutionalByDate(data.institutional || []), [data.institutional]);

  const latestPriceRow = priceChart.length ? priceChart[priceChart.length - 1] : null;
  const latestClose = asNumber(quote.price) ?? asNumber(latestPriceRow?.close);
  const priceChange = calcPriceChange(priceChart, quote);
  const priceChangePct = calcPriceChangePct(priceChart, quote);
  const volume = asNumber(quote.volume) ?? asNumber(latestPriceRow?.volume);
  const volumeChangePct = calcVolumeChangePct(priceChart, quote);

  const priceTone = toneClass(priceChangePct ?? priceChange);
  const volumeTone = toneClass(volumeChangePct);

  const return5d = calcReturnByTradingDays(priceChart, 5);
  const return1m = calcReturnByTradingDays(priceChart, 20);
  const return3m = calcReturnByTradingDays(priceChart, 60);
  const periodReturn = calcFullPeriodReturn(priceChart);

  const chartIsUp = (periodReturn ?? priceChangePct ?? 0) >= 0;
  const chartStroke = chartIsUp ? '#db5555' : '#35a77f';
  const chartFill = chartIsUp ? '#f5c6c6' : '#c7eadc';

  const totalLots = lots(data.summary?.total_shares);
  const totalValue = data.summary?.market_value_billion;
  const totalWeight = data.summary?.total_weight;

  const hasPriceChart = priceChart.length >= 2;
  const hasHoldingChart = holdingChart.length >= 2;

  const etfs = useMemo(() => {
    return [...(data.etfs || [])].sort((a, b) => {
      let av: any;
      let bv: any;

      if (etfSortKey === 'etf') {
        av = String(a.etf_code || '');
        bv = String(b.etf_code || '');
        const cmp = av.localeCompare(bv);
        return etfSortDir === 'asc' ? cmp : -cmp;
      }

      if (etfSortKey === 'value') {
        av = Number(a.market_value_billion || 0);
        bv = Number(b.market_value_billion || 0);
      } else {
        av = Number(a.weight || 0);
        bv = Number(b.weight || 0);
      }

      return etfSortDir === 'asc' ? av - bv : bv - av;
    });
  }, [data.etfs, etfSortKey, etfSortDir]);

  function toggleEtfSort(key: EtfSortKey) {
    if (etfSortKey === key) {
      setEtfSortDir(etfSortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setEtfSortKey(key);
      setEtfSortDir(key === 'etf' ? 'asc' : 'desc');
    }
  }

  function SortHead({ id, children }: { id: EtfSortKey; children: React.ReactNode }) {
    const active = etfSortKey === id;
    return (
      <button type="button" className={`sort-head stock-sort-head ${active ? 'active' : ''}`} onClick={() => toggleEtfSort(id)}>
        <span>{children}</span>
        <span className="sort-arrows">
          <span className={active && etfSortDir === 'asc' ? 'on' : ''}>▲</span>
          <span className={active && etfSortDir === 'desc' ? 'on' : ''}>▼</span>
        </span>
      </button>
    );
  }

  return (
    <main className="stock-v6-page">
      <header className="stock-v6-header">
        <Link className="stock-v6-back" href={stockBackHref} onClick={handleFastBackV83}>‹</Link>
        <div className="stock-v6-title">
          <div className="stock-v6-code">{data.stock_code}</div>
          <div className="stock-v6-name">{data.stock_name}</div>
        </div>
        <div style={{ width: 44 }} />
      </header>

      <section className="stock-v6-top-stats">
        <div className="stock-v6-top-card">
          <div className="stock-v6-top-label">今日股價</div>
          <div className={`stock-v6-top-price ${priceTone}`}>
            {latestClose == null ? '-' : fmt(latestClose, latestClose >= 1000 ? 0 : 1)}
          </div>
          <div className={`stock-v6-top-sub ${priceTone}`}>
            {priceChange && priceChange > 0 ? '▲' : priceChange && priceChange < 0 ? '▼' : ''}
            {' '}
            {signedNumber(priceChange, latestClose && latestClose >= 1000 ? 0 : 1)}
            <span className="stock-v6-chip">{signedPct(priceChangePct, 2)}</span>
          </div>
        </div>

        <div className="stock-v6-divider" />

        <div className="stock-v6-top-card">
          <div className="stock-v6-top-label">成交量</div>
          <div className="stock-v6-top-price volume">
            {volume == null ? '-' : fmt0(volume)}
          </div>
          <div className={`stock-v6-top-sub ${volumeTone}`}>
            量{volumeChangePct == null ? '-' : volumeChangePct > 0 ? '增' : volumeChangePct < 0 ? '減' : '平'}
            {volumeChangePct == null ? '' : ` ${Math.abs(volumeChangePct).toFixed(0)}%`}
          </div>
        </div>
      </section>

      <section className="stock-v6-section">
        <div className="stock-v6-section-head">
          <h3>近三月股價走勢與報酬</h3>
          <div className="stock-v6-segment">
            <button className={chartMode === 'price' ? 'active' : ''} onClick={() => setChartMode('price')}>
              股價
            </button>
            <button className={chartMode === 'holding' ? 'active' : ''} onClick={() => setChartMode('holding')}>
              持股
            </button>
          </div>
        </div>

        <div className="stock-v6-chart-card">
          {chartMode === 'price' && hasPriceChart ? (
            <>
              <div className="stock-v6-chart-box">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={priceChart}>
                    <defs>
                      <linearGradient id="stockV6Fill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={chartFill} stopOpacity={0.85} />
                        <stop offset="95%" stopColor={chartFill} stopOpacity={0.12} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="4 4" />
                    <XAxis dataKey="trade_date" tickFormatter={shortDate} tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} domain={['auto', 'auto']} />
                    <Tooltip
                      formatter={(value: any) => [fmt(value), '收盤價']}
                      labelFormatter={(label) => `日期：${label}`}
                    />
                    <Area type="monotone" dataKey="close" stroke={chartStroke} fill="url(#stockV6Fill)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="stock-v6-return-row">
                <div className="stock-v6-return-item">
                  <div className="stock-v6-return-label">近 5 日報酬</div>
                  <div className={toneClass(return5d)}>{signedPct(return5d, 1)}</div>
                </div>
                <div className="stock-v6-return-item">
                  <div className="stock-v6-return-label">近 1 月報酬</div>
                  <div className={toneClass(return1m)}>{signedPct(return1m, 1)}</div>
                </div>
                <div className="stock-v6-return-item">
                  <div className="stock-v6-return-label">近 3 月報酬</div>
                  <div className={toneClass(return3m)}>{signedPct(return3m, 1)}</div>
                </div>
              </div>
            </>
          ) : chartMode === 'holding' && hasHoldingChart ? (
            <>
              <div className="stock-v6-chart-summary">
                <div>
                  <span>期末張數</span>
                  <b>{fmt0(holdingChart[holdingChart.length - 1]?.shares_lots)} 張</b>
                </div>
                <div>
                  <span>期初張數</span>
                  <b>{fmt0(holdingChart[0]?.shares_lots)} 張</b>
                </div>
              </div>

              <div className="stock-v6-chart-box">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={holdingChart}>
                    <CartesianGrid strokeDasharray="4 4" />
                    <XAxis dataKey="date" tickFormatter={shortDate} tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} domain={['auto', 'auto']} />
                    <Tooltip
                      formatter={(value: any) => [`${fmt0(value)} 張`, 'ETF 持股']}
                      labelFormatter={(label) => `日期：${label}`}
                    />
                    <Line type="monotone" dataKey="shares_lots" stroke="#4c8bef" strokeWidth={2.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          ) : (
            <div className="stock-v6-empty">
              {chartMode === 'price' ? '尚無股價歷史資料，請先跑 GitHub Actions 更新 market data。' : '尚未有足夠 holdings 歷史資料。'}
            </div>
          )}
        </div>
      </section>

      <section className="stock-v6-section">
        <div className="stock-v6-section-head">
          <div className="stock-v6-info-title">
            <h3>持股主動式 ETF</h3>
            <button className="stock-v6-info-btn" onClick={() => setShowInfo(true)} type="button">i</button>
          </div>
        </div>

        <div className="stock-v6-summary-grid">
          <div>
            <span>總檔數</span>
            <b>{fmt0(data.summary?.etf_count || 0)} 檔</b>
          </div>
          <div>
            <span>總持股市值</span>
            <b>{totalValue == null ? '-' : `${fmt(totalValue)} 億`}</b>
          </div>
          <div>
            <span>估個股總市值</span>
            <b>{totalValue && latestClose ? `${fmt((totalValue * 100000000) / (latestClose * 1000000000) * 100, 2)}%` : '-'}</b>
          </div>
        </div>

        <div className="stock-v6-table-head">
          <div><SortHead id="etf">ETF</SortHead></div>
          <div><SortHead id="value">持股市值 / 張數</SortHead></div>
          <div><SortHead id="weight">估個股比重</SortHead></div>
        </div>

        <div className="stock-v6-etf-list">
          {etfs.map((r: any) => (
            <Link key={r.etf_code} href={buildEtfHrefFromStock(r.etf_code)} className="stock-v6-etf-row">
              <div>
                <b>{r.etf_code}</b>
                <span>{r.etf_name}</span>
              </div>
              <div>
                <b>{r.market_value_billion == null ? '-' : `${fmt(r.market_value_billion)} 億`}</b>
                <span>{fmt0(lots(r.shares))} 張</span>
              </div>
              <div className="weight">{fmt(r.weight)}%</div>
            </Link>
          ))}
        </div>
      </section>

      <section className="stock-v6-section">
        <div className="stock-v6-section-head">
          <h3>近期法人進出</h3>
          <span className="muted">單位：股</span>
        </div>

        {institutionalRows.length > 0 ? (
          <div className="stock-v6-inst-table-wrap">
            <table className="stock-v6-inst-table">
              <thead>
                <tr>
                  <th>日期 <span className="sort-arrows static"><span>▲</span><span>▼</span></span></th>
                  <th>外資 <span className="sort-arrows static"><span>▲</span><span>▼</span></span></th>
                  <th>投信 <span className="sort-arrows static"><span>▲</span><span>▼</span></span></th>
                  <th>自營商 <span className="sort-arrows static"><span>▲</span><span>▼</span></span></th>
                  <th>合計 <span className="sort-arrows static"><span>▲</span><span>▼</span></span></th>
                </tr>
              </thead>
              <tbody>
                {institutionalRows.map((r: any) => (
                  <tr key={r.trade_date}>
                    <td>{r.trade_date}</td>
                    <td className={signedClass(r.foreign_net)}>{fmt0(r.foreign_net)}</td>
                    <td className={signedClass(r.investment_trust_net)}>{fmt0(r.investment_trust_net)}</td>
                    <td className={signedClass(r.dealer_net)}>{fmt0(r.dealer_net)}</td>
                    <td className={signedClass(r.total_net)}>{fmt0(r.total_net)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="stock-v6-empty">尚無法人進出資料。</div>
        )}
      </section>

      {showInfo && (
        <div className="stock-v6-modal-mask" onClick={() => setShowInfo(false)}>
          <div className="stock-v6-modal" onClick={(e) => e.stopPropagation()}>
            <div className="stock-v6-modal-title">持股張數資料說明</div>
            <div className="stock-v6-modal-text">
              以 1 張 = 1000 股顯示。<br />
              本頁持股張數由各主動式 ETF 最新 holdings 的 shares 欄位換算。<br />
              持股市值為估算值：持股股數 × 最新股價 ÷ 1 億。
            </div>
            <button className="stock-v6-modal-btn" onClick={() => setShowInfo(false)}>
              我知道了
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
