'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { fmt, fmt0, signedClass } from '@/lib/api';

type SortKey = 'stock' | 'price' | 'change_pct' | 'market_value' | 'shares' | 'etf_count' | 'weight';
type SortDir = 'asc' | 'desc';

function sortValue(row: any, key: SortKey) {
  if (key === 'stock') return `${row.stock_code || ''}${row.stock_name || ''}`;
  if (key === 'price') return Number(row.price || 0);
  if (key === 'change_pct') return Number(row.change_pct || 0);
  if (key === 'market_value') return Number(row.market_value_billion || 0);
  if (key === 'shares') return Number(row.total_shares || 0);
  if (key === 'etf_count') return Number(row.etf_count || 0);
  if (key === 'weight') return Number(row.total_weight || 0);
  return '';
}

function lots(shares: any) {
  return Number(shares || 0) / 1000;
}

export default function HoldingsClient({ rows }: { rows: any[] }) {
  const [sortKey, setSortKey] = useState<SortKey>('market_value');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const sortedRows = useMemo(() => {
    return [...(rows || [])].sort((a: any, b: any) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);

      let cmp = 0;
      if (typeof av === 'number' && typeof bv === 'number') {
        cmp = av - bv;
      } else {
        cmp = String(av).localeCompare(String(bv), 'zh-Hant');
      }

      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [rows, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else {
      setSortKey(key);
      setSortDir(key === 'stock' ? 'asc' : 'desc');
    }
  }

  function SortHead({ id, children }: { id: SortKey; children: any }) {
    const active = sortKey === id;
    return (
      <button type="button" className={`holdings-sort-head ${active ? 'active' : ''}`} onClick={() => toggleSort(id)}>
        <span>{children}</span>
        <span className="sort-arrows">
          <span className={active && sortDir === 'asc' ? 'on' : ''}>▲</span>
          <span className={active && sortDir === 'desc' ? 'on' : ''}>▼</span>
        </span>
      </button>
    );
  }

  return (
    <main className="page holdings-v8-page">
      <h2>資金持股</h2>
      <div className="holdings-v8-count">共 {fmt0(sortedRows.length)} 檔，可點股票進個股詳情。</div>

      <div className="holdings-v8-table-wrap">
        <table className="table holdings-v8-table">
          <thead>
            <tr>
              <th><SortHead id="stock">股票</SortHead></th>
              <th>
                <div className="holdings-price-head">
                  <SortHead id="price">股價</SortHead>
                  <SortHead id="change_pct">漲跌幅</SortHead>
                </div>
              </th>
              <th>
                <div className="holdings-value-head">
                  <SortHead id="market_value">持股市值</SortHead>
                  <SortHead id="shares">持股張數</SortHead>
                </div>
              </th>
              <th>
                <div className="holdings-etf-head">
                  <SortHead id="etf_count">主動式檔數</SortHead>
                  <SortHead id="weight">估個股比重</SortHead>
                </div>
              </th>
            </tr>
          </thead>

          <tbody>
            {sortedRows.map((r: any) => {
              const cp = Number(r.change_pct || 0);
              const limitUp = cp >= 9.5;
              const limitDown = cp <= -9.5;

              return (
                <tr key={r.stock_code}>
                  <td>
                    <Link href={`/stock/${r.stock_code}`}>
                      <b>{r.stock_name}</b>
                      <div className="code">{r.stock_code}</div>
                    </Link>
                  </td>

                  <td className="holdings-price-cell">
                    <div className={`holdings-price-box ${limitUp ? 'limit-up' : ''} ${limitDown ? 'limit-down' : ''} ${signedClass(r.change_pct)}`}>
                      {r.price == null ? '-' : fmt(r.price, Number(r.price) >= 1000 ? 0 : 1)}
                    </div>
                    <div className={signedClass(r.change_pct)}>
                      {r.change_pct == null ? '-' : `${cp > 0 ? '+' : ''}${fmt(cp, 2)}%`}
                    </div>
                  </td>

                  <td>
                    <b>{r.market_value_billion == null ? '-' : `${fmt(r.market_value_billion, 2)} 億`}</b>
                    <div className="muted">{fmt0(lots(r.total_shares))} 張</div>
                  </td>

                  <td>
                    <b>{fmt0(r.etf_count)}</b>
                    <div className="muted">{fmt(r.total_weight, 2)}%</div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </main>
  );
}
