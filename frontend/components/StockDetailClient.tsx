'use client';

import Link from 'next/link';
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
  return s.slice(5).replace('-', '/');
}

function lots(shares: any) {
  return Number(shares || 0) / 1000;
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

function calcPriceReturn(priceHistory: any[]) {
  if (!priceHistory || priceHistory.length < 2) return null;
  const first = Number(priceHistory[0]?.close || 0);
  const last = Number(priceHistory[priceHistory.length - 1]?.close || 0);
  if (!first || !last) return null;
  return (last - first) / first * 100;
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
  const [showInfo, setShowInfo] = useState(false);
  const [chartMode, setChartMode] = useState<'price' | 'holding'>('price');
  const [etfSortKey, setEtfSortKey] = useState<EtfSortKey>('value');
  const [etfSortDir, setEtfSortDir] = useState<SortDir>('desc');

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

  const holdingChart = useMemo(() => buildHoldingHistory(data.history || []), [data.history]);
  const priceChart = useMemo(() => (data.price_history || []).slice(-90), [data.price_history]);
  const institutionalRows = useMemo(() => sumInstitutionalByDate(data.institutional || []), [data.institutional]);

  const totalLots = lots(data.summary?.total_shares);
  const totalValue = data.summary?.market_value_billion;
  const totalWeight = data.summary?.total_weight;
  const quote = data.quote || {};
  const priceReturn = calcPriceReturn(priceChart);

  const hasPriceChart = priceChart.length >= 2;
  const hasHoldingChart = holdingChart.length >= 2;

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
    <main className="stock-v2-page">
      <header className="stock-v2-header">
        <Link className="stock-v2-back" href="/search">‹</Link>
        <div className="stock-v2-title">
          <div className="stock-v2-code">{data.stock_code}</div>
          <div className="stock-v2-name">{data.stock_name}</div>
        </div>
        <div style={{ width: 44 }} />
      </header>

      <section className="stock-v2-quote-row">
        <div className="stock-v2-quote-item">
          <div className="label">今日股價</div>
          <div className="big">{quote.price == null ? '-' : fmt0(quote.price)}</div>
          <div className={signedClass(quote.change_pct)}>
            {quote.change_pct == null ? '-' : `${fmt(quote.change_pct)}%`}
          </div>
        </div>

        <div className="stock-v2-divider" />

        <div className="stock-v2-quote-item">
          <div className="label">主動式 ETF 持有</div>
          <div className="big">{fmt0(data.summary?.etf_count || 0)}</div>
          <div className="muted">合計權重 {fmt(totalWeight)}%</div>
        </div>
      </section>

      <section className="stock-v2-section">
        <div className="stock-v2-section-head">
          <h3>近三月走勢</h3>
          <div className="stock-v2-segment">
            <button className={chartMode === 'price' ? 'active' : ''} onClick={() => setChartMode('price')}>
              股價
            </button>
            <button className={chartMode === 'holding' ? 'active' : ''} onClick={() => setChartMode('holding')}>
              持股
            </button>
          </div>
        </div>

        <div className="stock-v2-chart-card">
          {chartMode === 'price' && hasPriceChart ? (
            <>
              <div className="stock-v2-chart-summary">
                <div>
                  <span>區間報酬</span>
                  <b className={signedClass(priceReturn)}>{priceReturn == null ? '-' : `${fmt(priceReturn)}%`}</b>
                </div>
                <div>
                  <span>最新收盤</span>
                  <b>{fmt0(priceChart[priceChart.length - 1]?.close)}</b>
                </div>
              </div>

              <div className="stock-v2-chart-box">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={priceChart}>
                    <CartesianGrid strokeDasharray="4 4" />
                    <XAxis dataKey="trade_date" tickFormatter={shortDate} tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} domain={['auto', 'auto']} />
                    <Tooltip
                      formatter={(value: any) => [fmt(value), '收盤價']}
                      labelFormatter={(label) => `日期：${label}`}
                    />
                    <Area type="monotone" dataKey="close" stroke="#db5555" fill="#f5c6c6" fillOpacity={0.7} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </>
          ) : chartMode === 'holding' && hasHoldingChart ? (
            <>
              <div className="stock-v2-chart-summary">
                <div>
                  <span>期末張數</span>
                  <b>{fmt0(holdingChart[holdingChart.length - 1]?.shares_lots)} 張</b>
                </div>
                <div>
                  <span>期初張數</span>
                  <b>{fmt0(holdingChart[0]?.shares_lots)} 張</b>
                </div>
              </div>

              <div className="stock-v2-chart-box">
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
            <div className="stock-v2-empty">
              {chartMode === 'price' ? '尚無股價歷史資料，請先跑 GitHub Actions 更新 market data。' : '尚未有足夠 holdings 歷史資料。'}
            </div>
          )}
        </div>
      </section>

      <section className="stock-v2-section">
        <div className="stock-v2-section-head">
          <div className="stock-v2-info-title">
            <h3>持股主動式 ETF</h3>
            <button className="stock-v2-info-btn" onClick={() => setShowInfo(true)} type="button">i</button>
          </div>
        </div>

        <div className="stock-v2-summary-grid">
          <div>
            <span>總檔數</span>
            <b>{fmt0(data.summary?.etf_count || 0)} 檔</b>
          </div>
          <div>
            <span>總持股市值</span>
            <b>{totalValue == null ? '-' : `${fmt(totalValue)} 億`}</b>
          </div>
          <div>
            <span>總持股張數</span>
            <b>{fmt0(totalLots)} 張</b>
          </div>
        </div>

        <div className="stock-v2-table-head">
          <div><SortHead id="etf">ETF</SortHead></div>
          <div><SortHead id="value">持股市值 / 張數</SortHead></div>
          <div><SortHead id="weight">ETF權重</SortHead></div>
        </div>

        <div className="stock-v2-etf-list">
          {etfs.map((r: any) => (
            <Link key={r.etf_code} href={`/etf/${r.etf_code}`} className="stock-v2-etf-row">
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

      <section className="stock-v2-section">
        <div className="stock-v2-section-head">
          <h3>近期法人進出</h3>
          <span className="muted">單位：股</span>
        </div>

        {institutionalRows.length > 0 ? (
          <div className="stock-v2-inst-table-wrap">
            <table className="stock-v2-inst-table">
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
          <div className="stock-v2-empty">尚無法人進出資料。</div>
        )}
      </section>

      {showInfo && (
        <div className="stock-v2-modal-mask" onClick={() => setShowInfo(false)}>
          <div className="stock-v2-modal" onClick={(e) => e.stopPropagation()}>
            <div className="stock-v2-modal-title">持股張數資料說明</div>
            <div className="stock-v2-modal-text">
              以 1 張 = 1000 股顯示。<br />
              本頁持股張數由各主動式 ETF 最新 holdings 的 shares 欄位換算。<br />
              持股市值為估算值：持股股數 × 最新股價 ÷ 1 億。
            </div>
            <button className="stock-v2-modal-btn" onClick={() => setShowInfo(false)}>
              我知道了
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
