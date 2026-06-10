'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { fmt, fmt0, signedClass } from '@/lib/api';

function buildHistory(rows: any[] = []) {
  const map = new Map<string, { date: string; shares_lots: number; weight_sum: number }>();

  for (const r of rows) {
    const d = String(r.data_date || '');
    if (!d) continue;
    if (!map.has(d)) {
      map.set(d, { date: d, shares_lots: 0, weight_sum: 0 });
    }
    const x = map.get(d)!;
    x.shares_lots += Number(r.shares || 0) / 1000;
    x.weight_sum += Number(r.weight || 0);
  }

  return [...map.values()]
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-60);
}

function shortDate(s: string) {
  if (!s) return '';
  return s.slice(5).replace('-', '/');
}

export default function StockDetailClient({ data }: { data: any }) {
  const [showInfo, setShowInfo] = useState(false);

  const etfs = useMemo(() => {
    return [...(data.etfs || [])].sort((a, b) => {
      const av = Number(a.market_value_billion || 0);
      const bv = Number(b.market_value_billion || 0);
      if (bv !== av) return bv - av;
      return Number(b.weight || 0) - Number(a.weight || 0);
    });
  }, [data.etfs]);

  const chartData = useMemo(() => buildHistory(data.history || []), [data.history]);

  const totalLots = Number(data.summary?.total_shares || 0) / 1000;
  const totalValue = data.summary?.market_value_billion;
  const totalWeight = data.summary?.total_weight;
  const quote = data.quote || {};

  return (
    <main className="stock-mobile-page">
      <header className="stock-mobile-header">
        <Link className="stock-back-btn" href="/search">‹</Link>
        <div className="stock-mobile-title">
          <div className="stock-mobile-code">{data.stock_code}</div>
          <div className="stock-mobile-name">{data.stock_name}</div>
        </div>
        <div style={{ width: 40 }} />
      </header>

      <section className="stock-top-grid">
        <div className="stock-top-card">
          <div className="stock-top-label">今日股價</div>
          <div className="stock-top-value">
            {quote.price == null ? '-' : fmt0(quote.price)}
          </div>
          <div className={`stock-top-sub ${signedClass(quote.change_pct)}`}>
            {quote.change_pct == null ? '-' : `${fmt(quote.change_pct)}%`}
          </div>
        </div>

        <div className="stock-top-card">
          <div className="stock-top-label">主動式 ETF 持有</div>
          <div className="stock-top-value">{fmt0(data.summary?.etf_count || 0)}</div>
          <div className="stock-top-sub muted">
            合計持股 {fmt0(totalLots)} 張
          </div>
        </div>
      </section>

      <section className="stock-block">
        <div className="stock-block-head">
          <h3>近期待股張數變化</h3>
          <span className="muted">依已匯入 holdings</span>
        </div>

        {chartData.length >= 2 ? (
          <div className="stock-chart-card">
            <div className="stock-chart-box">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="4 4" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={shortDate}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip
                    formatter={(value: any) => [`${fmt0(value)} 張`, '持股張數']}
                    labelFormatter={(label) => `日期：${label}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="shares_lots"
                    stroke="#db5555"
                    fill="#f4c9c9"
                    fillOpacity={0.65}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="stock-mini-metrics">
              <div className="stock-mini-metric">
                <div className="label">近期期末</div>
                <div className="value">{fmt0(chartData[chartData.length - 1]?.shares_lots)} 張</div>
              </div>
              <div className="stock-mini-metric">
                <div className="label">近期期初</div>
                <div className="value">{fmt0(chartData[0]?.shares_lots)} 張</div>
              </div>
              <div className="stock-mini-metric">
                <div className="label">ETF 合計權重</div>
                <div className="value">{fmt(totalWeight)}%</div>
              </div>
            </div>
          </div>
        ) : (
          <div className="stock-empty-card">尚未有足夠歷史資料可畫圖</div>
        )}
      </section>

      <section className="stock-block">
        <div className="stock-block-head">
          <div className="stock-info-title">
            <h3>持股主動式 ETF</h3>
            <button
              className="stock-info-btn"
              onClick={() => setShowInfo(true)}
              type="button"
            >
              i
            </button>
          </div>
        </div>

        <div className="stock-summary-grid">
          <div className="stock-summary-item">
            <div className="label">總檔數</div>
            <div className="value">{fmt0(data.summary?.etf_count || 0)} 檔</div>
          </div>
          <div className="stock-summary-item">
            <div className="label">總持股市值</div>
            <div className="value">
              {totalValue == null ? '-' : `${fmt(totalValue)} 億`}
            </div>
          </div>
          <div className="stock-summary-item">
            <div className="label">總持股張數</div>
            <div className="value">{fmt0(totalLots)} 張</div>
          </div>
        </div>

        <div className="stock-list-head">
          <div className="left">ETF</div>
          <div className="mid">持股市值 / 持股張數</div>
          <div className="right">ETF 權重</div>
        </div>

        <div className="stock-holding-list">
          {etfs.map((r: any) => (
            <Link key={r.etf_code} href={`/etf/${r.etf_code}`} className="stock-holding-row">
              <div className="left">
                <div className="code">{r.etf_code}</div>
                <div className="name">{r.etf_name}</div>
              </div>

              <div className="mid">
                <div className="primary">
                  {r.market_value_billion == null ? '-' : `${fmt(r.market_value_billion)} 億`}
                </div>
                <div className="secondary">{fmt0((r.shares || 0) / 1000)} 張</div>
              </div>

              <div className="right">
                {fmt(r.weight)}%
              </div>
            </Link>
          ))}
        </div>
      </section>

      {showInfo && (
        <div className="stock-modal-mask" onClick={() => setShowInfo(false)}>
          <div className="stock-modal" onClick={(e) => e.stopPropagation()}>
            <div className="stock-modal-title">持股張數資料說明</div>
            <div className="stock-modal-text">
              以 1 張 = 1000 股顯示。<br />
              本頁「總持股張數」與各 ETF 持股張數，皆由 holdings 的 shares 欄位換算而來。
            </div>
            <button className="stock-modal-btn" onClick={() => setShowInfo(false)}>
              我知道了
            </button>
          </div>
        </div>
      )}
    </main>
  );
}