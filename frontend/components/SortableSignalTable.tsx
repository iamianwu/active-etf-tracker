'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

type SortKey = 'stock' | 'etf' | 'status' | 'delta_shares' | 'weight';
type SortDir = 'asc' | 'desc';

function fmt0(n: any, empty = '-') {
  if (n === null || n === undefined || n === '' || Number.isNaN(Number(n))) return empty;
  return Number(n).toLocaleString('zh-TW', { maximumFractionDigits: 0 });
}

function signedClass(n: any) {
  const v = Number(n || 0);
  if (v > 0) return 'red';
  if (v < 0) return 'green';
  return 'muted';
}

function statusClass(status: string) {
  if (status === '加碼') return 'red';
  if (status === '減碼') return 'green';
  if (status === '新增') return 'gold';
  return '';
}

function sortValue(row: any, key: SortKey) {
  if (key === 'stock') return `${row.stock_code || ''}${row.stock_name || ''}`;
  if (key === 'etf') return row.etf_code || '';
  if (key === 'status') return row.status || '';
  if (key === 'delta_shares') return Number(row.delta_shares || 0);
  if (key === 'weight') return Number(row.weight || 0);
  return '';
}

export default function SortableSignalTable({ rows }: { rows: any[] }) {
  const [sortKey, setSortKey] = useState<SortKey>('delta_shares');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  function toggle(key: SortKey) {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir(key === 'stock' || key === 'etf' || key === 'status' ? 'asc' : 'desc');
    }
  }

  const sortedRows = useMemo(() => {
    return [...(rows || [])].sort((a, b) => {
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

  function SortHead({ id, children }: { id: SortKey; children: React.ReactNode }) {
    const active = sortKey === id;
    return (
      <button type="button" className={`sort-head ${active ? 'active' : ''}`} onClick={() => toggle(id)}>
        <span>{children}</span>
        <span className="sort-arrows">
          <span className={active && sortDir === 'asc' ? 'on' : ''}>▲</span>
          <span className={active && sortDir === 'desc' ? 'on' : ''}>▼</span>
        </span>
      </button>
    );
  }

  return (
    <table className="table signal-sort-table">
      <thead>
        <tr>
          <th><SortHead id="stock">標的</SortHead></th>
          <th><SortHead id="etf">ETF</SortHead></th>
          <th><SortHead id="status">狀態</SortHead></th>
          <th><SortHead id="delta_shares">變動張數</SortHead></th>
          <th><SortHead id="weight">目前權重</SortHead></th>
        </tr>
      </thead>
      <tbody>
        {sortedRows.map((r: any, i: number) => (
          <tr key={`${r.etf_code}-${r.stock_code}-${r.status}-${i}`} className="rowlink">
            <td>
              <Link href={`/stock/${r.stock_code}`}>
                <b>{r.stock_name}</b>
                <div className="code">{r.stock_code}</div>
              </Link>
            </td>
            <td><Link href={`/etf/${r.etf_code}`}>{r.etf_code}</Link></td>
            <td>
              <span className={`badge ${statusClass(r.status)}`}>
                {r.status}
              </span>
            </td>
            <td className={signedClass(r.delta_shares)}>{fmt0(Number(r.delta_shares || 0) / 1000)} 張</td>
            <td>{Number(r.weight || 0).toFixed(2)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
