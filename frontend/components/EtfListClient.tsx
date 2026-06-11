'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { fmt, fmt0, signedClass, num } from '@/lib/etfData';

type Mode = 'quote' | 'return' | 'basic';
type SortKey =
  | 'code'
  | 'price'
  | 'change_pct'
  | 'volume'
  | 'amount'
  | 'week_return'
  | 'total_return'
  | 'dividend_yield'
  | 'aum'
  | 'expense'
  | 'region';
type SortDir = 'asc' | 'desc';

function hasPrice(row: any) {
  const price = num(row.price);
  return price !== null && price > 0;
}

function amountBillion(row: any) {
  const amount = num(row.amount);
  if (amount && amount > 0) return amount / 100000000;
  return null;
}

function displayVolume(row: any) {
  if (!hasPrice(row)) return '-';
  const volume = num(row.volume);
  if (!volume || volume <= 0) return '-';
  return fmt0(volume);
}

function displayAmount(row: any) {
  const amount = amountBillion(row);
  if (amount === null) return '-';
  return `${fmt(amount, 2)} 億`;
}

function displayPrice(row: any) {
  const price = num(row.price);
  if (!price || price <= 0) return '-';
  return fmt(price, price >= 1000 ? 0 : 2);
}

function displayChange(row: any) {
  if (!hasPrice(row)) return '-';

  const change = num(row.change);
  const pct = num(row.change_pct);

  if (change === null && pct === null) return '-';

  const changeText = change === null
    ? ''
    : `${change > 0 ? '▲' : change < 0 ? '▼' : ''}${fmt(Math.abs(change), Math.abs(change) >= 10 ? 1 : 2)}`;

  const pctText = pct === null ? '' : `${fmt(Math.abs(pct), 2)}%`;

  if (changeText && pctText) return `${changeText}\n${pctText}`;
  return changeText || pctText;
}

function displayPct(v: any, digits = 1) {
  const x = num(v);
  if (x === null) return '-';
  return `${fmt(x, digits)}%`;
}

function displaySignedPct(v: any, digits = 1) {
  const x = num(v);
  if (x === null) return '-';
  return `${x > 0 ? '+' : ''}${fmt(x, digits)}%`;
}

function displayAum(row: any) {
  const aum = num(row.aum_billion);
  if (aum && aum > 0) return `${fmt0(aum)} 億`;
  return '-';
}

function inferRegion(row: any) {
  const name = String(row.etf_name || '');
  if (row.region) return row.region;
  if (name.includes('全球') || name.includes('Global') || name.includes('ARK') || name.includes('AI')) return '全球';
  if (name.includes('美國') || name.includes('US')) return '美國';
  return '台灣';
}

function sortValue(row: any, key: SortKey) {
  if (key === 'code') return `${row.etf_code || ''}${row.etf_name || ''}`;
  if (key === 'price') return num(row.price) ?? -Infinity;
  if (key === 'change_pct') return num(row.change_pct) ?? -Infinity;
  if (key === 'volume') return num(row.volume) ?? -Infinity;
  if (key === 'amount') return amountBillion(row) ?? -Infinity;
  if (key === 'week_return') return num(row.week_return) ?? -Infinity;
  if (key === 'total_return') return num(row.total_return) ?? -Infinity;
  if (key === 'dividend_yield') return num(row.dividend_yield) ?? -Infinity;
  if (key === 'aum') return num(row.aum_billion) ?? -Infinity;
  if (key === 'expense') return num(row.expense_ratio) ?? Infinity;
  if (key === 'region') return inferRegion(row);
  return '';
}

function Candle({ pct, price }: { pct: any; price: any }) {
  const p = num(price);
  const x = num(pct);
  const cls = !p || p <= 0 ? 'flat' : x === null ? 'flat' : x >= 0 ? 'up' : 'down';

  return (
    <span className={`etf-v11-candle ${cls}`}>
      <i />
      <b />
    </span>
  );
}

export default function EtfListClient({ rows }: { rows: any[] }) {
  const [mode, setMode] = useState<Mode>('quote');
  const [sortKey, setSortKey] = useState<SortKey>('change_pct');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const sortedRows = useMemo(() => {
    return [...(rows || [])].sort((a, b) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);

      let cmp = 0;
      if (typeof av === 'number' && typeof bv === 'number') cmp = av - bv;
      else cmp = String(av).localeCompare(String(bv), 'zh-Hant');

      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [rows, sortKey, sortDir]);

  function setModeAndDefaultSort(next: Mode) {
    setMode(next);

    if (next === 'quote') {
      setSortKey('change_pct');
      setSortDir('desc');
    } else if (next === 'return') {
      setSortKey('week_return');
      setSortDir('desc');
    } else {
      setSortKey('aum');
      setSortDir('desc');
    }
  }

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else {
      setSortKey(key);
      setSortDir(key === 'code' || key === 'region' || key === 'expense' ? 'asc' : 'desc');
    }
  }

  function SortHead({ id, children }: { id: SortKey; children: any }) {
    const active = sortKey === id;

    return (
      <button type="button" className={`etf-v11-sort-head ${active ? 'active' : ''}`} onClick={() => toggleSort(id)}>
        <span>{children}</span>
        <span className="sort-arrows">
          <span className={active && sortDir === 'asc' ? 'on' : ''}>▲</span>
          <span className={active && sortDir === 'desc' ? 'on' : ''}>▼</span>
        </span>
      </button>
    );
  }

  return (
    <main className="page etf-v11-page">
      <h2>ETF 列表</h2>

      <div className="etf-v11-topbar">
        <div className="etf-v11-count">共 {fmt0(sortedRows.length)} 檔，每檔 ETF 可點進詳情。</div>

        <div className="etf-v11-segment">
          <button className={mode === 'quote' ? 'active' : ''} onClick={() => setModeAndDefaultSort('quote')}>即時</button>
          <button className={mode === 'return' ? 'active' : ''} onClick={() => setModeAndDefaultSort('return')}>報酬</button>
          <button className={mode === 'basic' ? 'active' : ''} onClick={() => setModeAndDefaultSort('basic')}>基本</button>
        </div>
      </div>

      <div className="etf-v11-table-wrap">
        <table className={`table etf-v11-table mode-${mode}`}>
          <thead>
            {mode === 'quote' && (
              <tr>
                <th><SortHead id="code">股票</SortHead></th>
                <th><SortHead id="price">股價</SortHead></th>
                <th><SortHead id="change_pct">漲跌幅</SortHead></th>
                <th>
                  <div className="etf-v11-double-head">
                    <SortHead id="volume">今成交量</SortHead>
                    <SortHead id="amount">成交金額</SortHead>
                  </div>
                </th>
              </tr>
            )}

            {mode === 'return' && (
              <tr>
                <th><SortHead id="code">股票</SortHead></th>
                <th><SortHead id="week_return">1週報酬</SortHead></th>
                <th><SortHead id="total_return">總報酬<br />成立以來</SortHead></th>
                <th><SortHead id="dividend_yield">殖利率</SortHead></th>
              </tr>
            )}

            {mode === 'basic' && (
              <tr>
                <th><SortHead id="code">股票</SortHead></th>
                <th><SortHead id="aum">資產規模</SortHead></th>
                <th><SortHead id="expense">內扣費用</SortHead></th>
                <th><SortHead id="region">投資區域</SortHead></th>
              </tr>
            )}
          </thead>

          <tbody>
            {sortedRows.map((r: any) => {
              const cp = num(r.change_pct);
              const price = num(r.price);
              const validPrice = price !== null && price > 0;
              const limitUp = validPrice && cp !== null && cp >= 9.5;
              const limitDown = validPrice && cp !== null && cp <= -9.5;

              return (
                <tr key={r.etf_code}>
                  <td className="etf-v11-name-cell">
                    <Link href={`/etf/${r.etf_code}`}>
                      <Candle pct={r.change_pct} price={r.price} />
                      <span className="etf-v11-name-text">
                        <b>{r.etf_code}</b>
                        <small>{r.etf_name}</small>
                      </span>
                    </Link>
                  </td>

                  {mode === 'quote' && (
                    <>
                      <td className="etf-v11-price-cell">
                        <span className={`etf-v11-price ${limitUp ? 'limit-up' : ''} ${limitDown ? 'limit-down' : ''} ${validPrice ? signedClass(r.change_pct) : 'muted'}`}>
                          {displayPrice(r)}
                        </span>
                      </td>

                      <td className={`etf-v11-change-cell ${validPrice ? signedClass(r.change_pct) : 'muted'}`}>
                        {displayChange(r).split('\n').map((x, i) => <div key={i}>{x}</div>)}
                      </td>

                      <td className="etf-v11-volume-cell">
                        <b>{displayVolume(r)}</b>
                        <small>({displayAmount(r)})</small>
                      </td>
                    </>
                  )}

                  {mode === 'return' && (
                    <>
                      <td className={signedClass(r.week_return)}>{displaySignedPct(r.week_return, 1)}</td>
                      <td className={signedClass(r.total_return)}>
                        <b>{displaySignedPct(r.total_return, 1)}</b>
                        <small>{r.inception_date ? `(${r.inception_date})` : ''}</small>
                      </td>
                      <td>
                        <b>{displayPct(r.dividend_yield, 2)}</b>
                        <small>{r.dividend_frequency ? `(${r.dividend_frequency})` : ''}</small>
                      </td>
                    </>
                  )}

                  {mode === 'basic' && (
                    <>
                      <td><b>{displayAum(r)}</b></td>
                      <td><b>{r.expense_ratio == null ? '-' : `${fmt(r.expense_ratio, 2)}%`}</b></td>
                      <td><b>{inferRegion(r)}</b></td>
                    </>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </main>
  );
}
