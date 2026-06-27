'use client';

import { useEffect, useMemo, useState } from 'react';

type EtfStatusRow = {
  code: string;
  name: string;
  market: string;
  quote_date: string | null;
  holding_date: string | null;
  holding_count: number;
  price_history_count: number;
  included_in_today_signal: boolean;
  status: string;
};

type EtfStatusData = {
  generated_at: string;
  total: number;
  signal_holding_date: string | null;
  summary: Record<string, number>;
  rows: EtfStatusRow[];
};

function fmtDate(v: string | null | undefined) {
  if (!v) return '-';
  const m = String(v).match(/^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/);
  if (!m) return String(v);
  if (m[4] && m[5]) return `${m[2]}-${m[3]} ${m[4]}:${m[5]}`;
  return `${m[2]}-${m[3]}`;
}

function fmtGeneratedAt(v: string | null | undefined) {
  if (!v) return '-';
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return String(v);
  return d.toLocaleString('zh-TW', {
    timeZone: 'Asia/Taipei',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function statusClass(status: string) {
  if (status === '正常') return 'ok';
  if (status === '持股未更新') return 'warn';
  return 'bad';
}

export default function AdminEtfStatusPage() {
  const [data, setData] = useState<EtfStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('全部');

  async function load() {
    setLoading(true);
    setError('');

    try {
      const res = await fetch(`/api/debug-etf-status?t=${Date.now()}`, {
        cache: 'no-store',
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const json = await res.json();
      setData(json);
    } catch (err: any) {
      setError(String(err?.message || err || '讀取失敗'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const statusOptions = useMemo(() => {
    const set = new Set<string>(['全部']);
    for (const r of data?.rows || []) set.add(r.status || '未知');
    return Array.from(set);
  }, [data]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();

    return (data?.rows || []).filter((r) => {
      const hitQuery =
        !q ||
        r.code.toLowerCase().includes(q) ||
        r.name.toLowerCase().includes(q) ||
        r.market.toLowerCase().includes(q);

      const hitStatus = statusFilter === '全部' || r.status === statusFilter;

      return hitQuery && hitStatus;
    });
  }, [data, query, statusFilter]);

  return (
    <main className="admin-etf-status-page">
      <div className="admin-etf-status-head">
        <div>
          <a className="admin-etf-back" href="/admin">← 管理</a>
          <h1>ETF 資料健康檢查</h1>
          <p>
            檢查 27 檔主動式 ETF 的報價更新、持股日、持股數與今日訊號納入狀態。
          </p>
        </div>

        <button className="admin-etf-refresh" onClick={load} disabled={loading}>
          {loading ? '讀取中...' : '重新整理'}
        </button>
      </div>

      {error && <div className="admin-etf-error">讀取失敗：{error}</div>}

      <section className="admin-etf-summary">
        <div>
          <span>總 ETF</span>
          <b>{data?.total ?? '-'}</b>
        </div>
        <div>
          <span>訊號持股日</span>
          <b>{fmtDate(data?.signal_holding_date)}</b>
        </div>
        <div>
          <span>正常</span>
          <b>{data?.summary?.['正常'] ?? '-'}</b>
        </div>
        <div>
          <span>持股未更新</span>
          <b>{data?.summary?.['持股未更新'] ?? '-'}</b>
        </div>
      </section>

      <div className="admin-etf-meta">
        產生時間：{fmtGeneratedAt(data?.generated_at)} ｜ 顯示 {rows.length} / {data?.total ?? 0} 檔
      </div>

      <div className="admin-etf-toolbar">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜尋代號、名稱、市場"
        />

        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {statusOptions.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="admin-etf-table-wrap">
        <table className="admin-etf-table">
          <thead>
            <tr>
              <th>代號</th>
              <th>名稱</th>
              <th>市場</th>
              <th>報價更新</th>
              <th>持股日</th>
              <th>持股數</th>
              <th>歷史數</th>
              <th>今日訊號</th>
              <th>狀態</th>
            </tr>
          </thead>

          <tbody>
            {loading && !data && (
              <tr>
                <td colSpan={9} className="admin-etf-empty">讀取中...</td>
              </tr>
            )}

            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={9} className="admin-etf-empty">沒有符合條件的 ETF</td>
              </tr>
            )}

            {rows.map((r) => (
              <tr key={r.code} className={r.status === '正常' ? '' : 'admin-etf-row-warn'}>
                <td>
                  <a href={`/etf/${r.code}`}>{r.code}</a>
                </td>
                <td>{r.name}</td>
                <td>{r.market}</td>
                <td>{fmtDate(r.quote_date)}</td>
                <td>{fmtDate(r.holding_date)}</td>
                <td>{r.holding_count}</td>
                <td>{r.price_history_count}</td>
                <td>
                  <span className={r.included_in_today_signal ? 'admin-etf-pill ok' : 'admin-etf-pill warn'}>
                    {r.included_in_today_signal ? '納入' : '不納入'}
                  </span>
                </td>
                <td>
                  <span className={`admin-etf-pill ${statusClass(r.status)}`}>
                    {r.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
