'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { fmt, fmt0, signedClass } from '@/lib/api';

const STATUS_LIST = ['新增', '刪除', '加碼', '減碼'] as const;
type FilterStatus = typeof STATUS_LIST[number];
type SortKey = 'stock' | 'price' | 'change_pct' | 'status' | 'amount' | 'etf_count' | 'delta_shares' | 'magnitude';
type SortDir = 'asc' | 'desc';

function countFromStatuses(x: any, keyword: string) {
  if (keyword === '加碼' && x.increase_etf_count !== undefined) return Number(x.increase_etf_count || 0);
  if (keyword === '減碼' && x.decrease_etf_count !== undefined) return Number(x.decrease_etf_count || 0);
  if (keyword === '買' && x.buy_etf_count !== undefined) return Number(x.buy_etf_count || 0);
  if (keyword === '賣' && x.sell_etf_count !== undefined) return Number(x.sell_etf_count || 0);
  return (x.statuses || []).filter((s: string) => String(s).includes(keyword)).length;
}

function sortByMoneyOrSharesDesc(a: any, b: any) {
  const av = a.delta_value_billion !== null && a.delta_value_billion !== undefined
    ? Math.abs(Number(a.delta_value_billion || 0))
    : Math.abs(Number(a.delta_shares || 0));

  const bv = b.delta_value_billion !== null && b.delta_value_billion !== undefined
    ? Math.abs(Number(b.delta_value_billion || 0))
    : Math.abs(Number(b.delta_shares || 0));

  return bv - av;
}

function stockMoveValue(x: any) {
  const v = x?.delta_value_billion;

  if (v !== null && v !== undefined && !Number.isNaN(Number(v)) && Number(v) !== 0) {
    const prefix = Number(v) > 0 ? '+' : '';
    return `${prefix}${fmt(v, 1)} 億`;
  }

  const lots = Number(x?.delta_shares || 0) / 1000;
  const prefix = lots > 0 ? '+' : '';
  return `${prefix}${fmt0(lots)} 張`;
}

function signedAmount(v: any) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '-';
  const n = Number(v);
  const prefix = n > 0 ? '+' : n < 0 ? '-' : '';
  return `${prefix}${fmt(Math.abs(n), 2)} 億`;
}

function signedLots(v: any) {
  const lots = Number(v || 0) / 1000;
  const prefix = lots > 0 ? '+' : lots < 0 ? '-' : '';
  return `${prefix}${fmt0(Math.abs(lots))} 張`;
}

function statusClass(status: string) {
  if (status === '加碼') return 'red';
  if (status === '減碼') return 'green';
  if (status === '新增') return 'gold';
  return '';
}

function displayMagnitude(row: any) {
  const status = row.status;
  const prev = Number(row.previous_shares || 0);
  const curr = Number(row.current_shares || 0);
  const pct = row.magnitude_pct;

  if (status === '新增' || (prev <= 0 && curr > 0)) return '新增';
  if (status === '刪除' || curr <= 0) return '刪除';
  if (pct === null || pct === undefined || Number.isNaN(Number(pct))) return '-';

  const n = Number(pct);
  if (n >= 200) return '>2倍';
  if (n <= -100) return '-100%';

  const prefix = n > 0 ? '+' : '';
  return `${prefix}${fmt(n, 1)}%`;
}

function buildRows(data: any, selectedStatuses: Set<FilterStatus>) {
  const source = (data.changes || []).filter((x: any) => selectedStatuses.has(x.status));

  const map = new Map<string, any>();

  for (const c of source) {
    const code = String(c.stock_code || '');
    if (!code) continue;

    const deltaShares = Number(c.delta_shares || 0);
    const currentShares = Number(c.shares || 0);
    const previousShares = currentShares - deltaShares;
    const price = c.price ?? null;
    const changePct = c.change_pct ?? null;
    const priceNum = Number(price || 0);
    const deltaValue = priceNum ? deltaShares * priceNum / 100000000 : null;

    if (!map.has(code)) {
      map.set(code, {
        stock_code: code,
        stock_name: c.stock_name,
        price,
        change_pct: changePct,
        current_shares: 0,
        previous_shares: 0,
        delta_shares: 0,
        delta_weight: 0,
        delta_value_billion: 0,
        has_price: false,
        etf_codes: [],
        etf_count: 0,
        buy_etf_count: 0,
        sell_etf_count: 0,
        increase_etf_count: 0,
        decrease_etf_count: 0,
        add_etf_count: 0,
        remove_etf_count: 0,
        statuses: [],
        status_set: new Set<string>(),
      });
    }

    const r = map.get(code);
    r.current_shares += currentShares;
    r.previous_shares += previousShares;
    r.delta_shares += deltaShares;
    r.delta_weight += Number(c.delta_weight || 0);
    r.etf_codes.push(c.etf_code);
    r.statuses.push(`${c.etf_code} ${c.status}`);
    r.status_set.add(c.status);

    if (deltaValue !== null) {
      r.delta_value_billion += deltaValue;
      r.has_price = true;
    }

    if (c.status === '加碼') {
      r.increase_etf_count += 1;
      r.buy_etf_count += 1;
    }
    if (c.status === '新增') {
      r.add_etf_count += 1;
      r.buy_etf_count += 1;
    }
    if (c.status === '減碼') {
      r.decrease_etf_count += 1;
      r.sell_etf_count += 1;
    }
    if (c.status === '刪除') {
      r.remove_etf_count += 1;
      r.sell_etf_count += 1;
    }
  }

  return [...map.values()].map((r: any) => {
    const etfCodes = Array.from(new Set(r.etf_codes || []));
    const magnitude = r.previous_shares ? (r.delta_shares / r.previous_shares) * 100 : null;

    let status = '混合';
    if (r.status_set.size === 1) status = Array.from(r.status_set)[0] as string;
    else if (r.delta_shares > 0) status = r.add_etf_count > 0 && r.increase_etf_count === 0 ? '新增' : '加碼';
    else if (r.delta_shares < 0) status = r.remove_etf_count > 0 && r.decrease_etf_count === 0 ? '刪除' : '減碼';

    return {
      ...r,
      status,
      etf_codes: etfCodes,
      etf_count: etfCodes.length,
      delta_value_billion: r.has_price ? r.delta_value_billion : null,
      magnitude_pct: magnitude,
    };
  });
}

function sortValue(row: any, key: SortKey) {
  if (key === 'stock') return `${row.stock_code || ''}${row.stock_name || ''}`;
  if (key === 'price') return Number(row.price || 0);
  if (key === 'change_pct') return Number(row.change_pct || 0);
  if (key === 'status') return row.status || '';
  if (key === 'amount') return Number(row.delta_value_billion || 0);
  if (key === 'etf_count') return Number(row.etf_count || 0);
  if (key === 'delta_shares') return Number(row.delta_shares || 0);
  if (key === 'magnitude') return Number(row.magnitude_pct || 0);
  return '';
}

function FocusCard({
  title,
  item,
  tone,
}: {
  title: string;
  item: any;
  tone: 'red' | 'green';
}) {
  const buyCount = countFromStatuses(item || {}, '買');
  const sellCount = countFromStatuses(item || {}, '賣');

  return (
    <Link className={`focus-card ${tone}`} href={tone === 'red' ? '/signals/increased' : '/signals/decreased'}>
      <div className="focus-card-title">{title}</div>

      {item ? (
        <div className="focus-card-body">
          <div className="focus-stock">
            <b>{item.stock_name}</b>
            <span>{item.stock_code}</span>
          </div>

          <div className="focus-metrics">
            <div>
              <span>資金動向：</span>
              <b>{stockMoveValue(item)}</b>
            </div>
            <div className="nowrap">
              <span>多空共識：</span>
              <b>買賣檔數 {buyCount}:{sellCount}</b>
            </div>
          </div>
        </div>
      ) : (
        <div className="focus-empty">尚無資料</div>
      )}
    </Link>
  );
}

export default function SignalsClient({ data, initialFilter = null }: { data: any; initialFilter?: FilterStatus | null }) {
  const defaultStatuses: FilterStatus[] = initialFilter ? [initialFilter] : ['新增', '刪除', '加碼', '減碼'];
  const [selectedStatuses, setSelectedStatuses] = useState<FilterStatus[]>(defaultStatuses);
  const [sortKey, setSortKey] = useState<SortKey>('amount');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const agg = (data.aggregate || []).filter((x: any) => x.stock_code);

  const inflow = [...agg]
    .filter((x: any) => Number(x.delta_shares || 0) > 0)
    .sort(sortByMoneyOrSharesDesc)[0];

  const outflow = [...agg]
    .filter((x: any) => Number(x.delta_shares || 0) < 0)
    .sort(sortByMoneyOrSharesDesc)[0];

  const mostEtfAdd = [...agg]
    .filter((x: any) => countFromStatuses(x, '加碼') > 0)
    .sort((a: any, b: any) =>
      countFromStatuses(b, '加碼') - countFromStatuses(a, '加碼') ||
      Math.abs(Number(b.delta_shares || 0)) - Math.abs(Number(a.delta_shares || 0))
    )[0];

  const mostEtfReduce = [...agg]
    .filter((x: any) => countFromStatuses(x, '減碼') > 0)
    .sort((a: any, b: any) =>
      countFromStatuses(b, '減碼') - countFromStatuses(a, '減碼') ||
      Math.abs(Number(b.delta_shares || 0)) - Math.abs(Number(a.delta_shares || 0))
    )[0];

  const selectedSet = useMemo(() => new Set(selectedStatuses), [selectedStatuses]);

  const rows = useMemo(() => {
    const built = buildRows(data, selectedSet);
    return built.sort((a: any, b: any) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);

      let cmp = 0;
      if (typeof av === 'number' && typeof bv === 'number') cmp = av - bv;
      else cmp = String(av).localeCompare(String(bv), 'zh-Hant');

      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [data, selectedSet, sortKey, sortDir]);

  const mmdd = data.data_date_mmdd || '';
  const complete = Number(data.fetched_etf_count || 0) === Number(data.total_etf_count || 0);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else {
      setSortKey(key);
      setSortDir(key === 'stock' || key === 'status' ? 'asc' : 'desc');
    }
  }

  function SortHead({ id, children }: { id: SortKey; children: any }) {
    const active = sortKey === id;
    return (
      <button type="button" className={`sort-head ${active ? 'active' : ''}`} onClick={() => toggleSort(id)}>
        <span>{children}</span>
        <span className="sort-arrows">
          <span className={active && sortDir === 'asc' ? 'on' : ''}>▲</span>
          <span className={active && sortDir === 'desc' ? 'on' : ''}>▼</span>
        </span>
      </button>
    );
  }

  function toggleFilter(status: FilterStatus) {
    setSelectedStatuses((prev) => {
      if (prev.includes(status)) return prev.filter((x) => x !== status);
      return [...prev, status];
    });
  }

  return (
    <main className="page signals-v5-page">
      <div className="signals-title-block">
        <h2>{mmdd ? `${mmdd} 今日訊號` : '今日訊號'}</h2>
        <div className={`signals-data-status ${complete ? 'ok' : 'warn'}`}>
          已抓取 {data.fetched_etf_count || 0} / {data.total_etf_count || 0} 檔 ETF
          {data.data_date ? `，資料日期 ${data.data_date}` : ''}
        </div>
      </div>

      <div className="focus-grid">
        <FocusCard title="資金流入最多" item={inflow} tone="red" />
        <FocusCard title="資金流出最多" item={outflow} tone="green" />
        <FocusCard title="最多 ETF 加碼" item={mostEtfAdd} tone="red" />
        <FocusCard title="最多 ETF 減碼" item={mostEtfReduce} tone="green" />
      </div>

      <h3>資金交易明細：共 {rows.length} 檔</h3>

      <div className="status-pill-row">
        <button className={`status-pill add ${selectedSet.has('新增') ? 'active' : 'inactive'}`} onClick={() => toggleFilter('新增')}>
          <span>新增</span><b>{data.summary?.['新增'] || 0}</b>
        </button>
        <button className={`status-pill remove ${selectedSet.has('刪除') ? 'active' : 'inactive'}`} onClick={() => toggleFilter('刪除')}>
          <span>刪除</span><b>{data.summary?.['刪除'] || 0}</b>
        </button>
        <button className={`status-pill inc ${selectedSet.has('加碼') ? 'active' : 'inactive'}`} onClick={() => toggleFilter('加碼')}>
          <span>加碼</span><b>{data.summary?.['加碼'] || 0}</b>
        </button>
        <button className={`status-pill dec ${selectedSet.has('減碼') ? 'active' : 'inactive'}`} onClick={() => toggleFilter('減碼')}>
          <span>減碼</span><b>{data.summary?.['減碼'] || 0}</b>
        </button>
      </div>

      <div className="signal-v5-table-wrap">
        <table className="table signal-v5-table">
          <thead>
            <tr>
              <th><SortHead id="stock">標的</SortHead></th>
              <th>
                <div className="price-sort-head">
                  <SortHead id="price">股價</SortHead>
                  <SortHead id="change_pct">漲跌幅</SortHead>
                </div>
              </th>
              <th><SortHead id="status">狀態</SortHead></th>
              <th><SortHead id="amount">金額</SortHead></th>
              <th><SortHead id="etf_count">ETF檔數</SortHead></th>
              <th><SortHead id="delta_shares">變動張數</SortHead></th>
              <th><SortHead id="magnitude">變動幅度</SortHead></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r: any) => {
              const cp = Number(r.change_pct || 0);
              const limitUp = cp >= 9.5;
              const limitDown = cp <= -9.5;
              const amount = r.delta_value_billion;
              const buy = Number(r.buy_etf_count || 0);
              const sell = Number(r.sell_etf_count || 0);

              return (
                <tr key={`${r.stock_code}-${r.status}`}>
                  <td>
                    <Link href={`/stock/${r.stock_code}`}>
                      <b>{r.stock_name}</b>
                      <div className="code">{r.stock_code}</div>
                    </Link>
                  </td>
                  <td className="price-cell">
                    <div className={`price-box ${limitUp ? 'limit-up' : ''} ${limitDown ? 'limit-down' : ''}`}>
                      {r.price == null ? '-' : fmt(r.price, 1)}
                    </div>
                    <div className={signedClass(r.change_pct)}>
                      {r.change_pct == null ? '-' : `${cp > 0 ? '+' : ''}${fmt(cp, 2)}%`}
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${statusClass(r.status)}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className={signedClass(amount)}>
                    {amount === null || amount === undefined ? '-' : signedAmount(amount)}
                  </td>
                  <td>
                    <b>{fmt0(r.etf_count)} 檔</b>
                    <div className="small-muted">買賣 {buy}:{sell}</div>
                  </td>
                  <td className={signedClass(r.delta_shares)}>
                    {signedLots(r.delta_shares)}
                  </td>
                  <td className={signedClass(r.magnitude_pct)}>
                    {displayMagnitude(r)}
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
