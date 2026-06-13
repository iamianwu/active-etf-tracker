'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { apiGet, fmt0, fmt } from '@/lib/api';

const HOT_ITEMS = [
  { code: '00403A', name: '主動統一升級50', type: 'etf' },
  { code: '00981A', name: '主動統一台股增長', type: 'etf' },
  { code: '00980A', name: '主動野村臺灣優選', type: 'etf' },
  { code: '00982A', name: '主動群益台灣強棒', type: 'etf' },
  { code: '2330', name: '台積電', type: 'stock' },
  { code: '2317', name: '鴻海', type: 'stock' },
  { code: '2454', name: '聯發科', type: 'stock' },
];

function saveHistory(item: any) {
  try {
    const old = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    const next = [item, ...old.filter((x: any) => !(x.code === item.code && x.type === item.type))].slice(0, 8);
    localStorage.setItem('searchHistory', JSON.stringify(next));
  } catch {}
}

export default function SearchPage() {
  const [q, setQ] = useState('');
  const [etfs, setEtfs] = useState<any[]>([]);
  const [stocks, setStocks] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [etfData, stockData] = await Promise.all([
          apiGet('/etfs'),
          apiGet('/holdings'),
        ]);
        setEtfs(etfData || []);
        setStocks(stockData || []);
      } finally {
        setLoading(false);
      }
    }

    load();

    try {
      setHistory(JSON.parse(localStorage.getItem('searchHistory') || '[]'));
    } catch {}
  }, []);

  const results = useMemo(() => {
    const keyword = q.trim().toLowerCase();
    if (!keyword) return { etfs: [], stocks: [] };

    const matchedEtfs = etfs
      .filter((x: any) =>
        String(x.etf_code || '').toLowerCase().includes(keyword) ||
        String(x.etf_name || '').toLowerCase().includes(keyword)
      )
      .slice(0, 20);

    const matchedStocks = stocks
      .filter((x: any) =>
        String(x.stock_code || '').toLowerCase().includes(keyword) ||
        String(x.stock_name || '').toLowerCase().includes(keyword)
      )
      .slice(0, 40);

    return { etfs: matchedEtfs, stocks: matchedStocks };
  }, [q, etfs, stocks]);

  function clearHistory() {
    localStorage.removeItem('searchHistory');
    setHistory([]);
  }

  return (
    <main className="page search-page">
      <div className="search-header">
        <Link href="/" className="back">‹</Link>
        <h2>搜尋</h2>
        <div className="back-placeholder" />
      </div>

      <div className="search-box">
        <span className="search-mark"><a href="/search" className="header-icon-link-v67" aria-label="搜尋" title="搜尋"><span className="header-icon-v67 header-icon-search-v67" /></a></span>
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="輸入 ETF 或個股代號 / 名稱"
        />
      </div>

      {loading && <p className="muted">資料載入中...</p>}

      {!q.trim() && (
        <>
          <section className="search-section">
            <h3>熱門搜尋</h3>
            <div className="search-chip-row">
              {HOT_ITEMS.map((item) => {
                const href = item.type === 'etf' ? `/etf/${item.code}` : `/stock/${item.code}`;
                return (
                  <Link
                    key={`${item.type}-${item.code}`}
                    className="search-chip"
                    href={href}
                    onClick={() => saveHistory(item)}
                  >
                    <b>{item.code}</b> {item.name}
                  </Link>
                );
              })}
            </div>
          </section>

          <section className="search-section">
            <div className="search-section-title">
              <h3>歷史搜尋</h3>
              {history.length > 0 && <button className="clear-btn" onClick={clearHistory}>清空</button>}
            </div>

            {history.length === 0 ? (
              <p className="muted">尚無歷史搜尋</p>
            ) : (
              <div className="history-list">
                {history.map((item: any) => {
                  const href = item.type === 'etf' ? `/etf/${item.code}` : `/stock/${item.code}`;
                  return (
                    <Link
                      key={`${item.type}-${item.code}`}
                      href={href}
                      className="history-item"
                      onClick={() => saveHistory(item)}
                    >
                      <b>{item.code}</b>
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
              </div>
            )}
          </section>
        </>
      )}

      {q.trim() && (
        <>
          <section className="search-section">
            <h3>ETF 搜尋結果</h3>
            {results.etfs.length === 0 ? (
              <p className="muted">沒有符合的 ETF</p>
            ) : (
              <div className="result-list">
                {results.etfs.map((x: any) => (
                  <Link
                    key={x.etf_code}
                    href={`/etf/${x.etf_code}`}
                    className="result-row"
                    onClick={() => saveHistory({ code: x.etf_code, name: x.etf_name, type: 'etf' })}
                  >
                    <div>
                      <b>{x.etf_code}</b>
                      <div>{x.etf_name}</div>
                    </div>
                    <div className="result-meta">
                      <div>成分股 {fmt0(x.holding_count)} 檔</div>
                      <div>股票權重 {fmt(x.stock_weight)}%</div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>

          <section className="search-section">
            <h3>個股搜尋結果</h3>
            {results.stocks.length === 0 ? (
              <p className="muted">沒有符合的個股</p>
            ) : (
              <div className="result-list">
                {results.stocks.map((x: any) => (
                  <Link
                    key={x.stock_code}
                    href={`/stock/${x.stock_code}`}
                    className="result-row"
                    onClick={() => saveHistory({ code: x.stock_code, name: x.stock_name, type: 'stock' })}
                  >
                    <div>
                      <b>{x.stock_name}</b>
                      <div className="code">{x.stock_code}</div>
                    </div>
                    <div className="result-meta">
                      <div>ETF {fmt0(x.etf_count)} 檔</div>
                      <div>合計權重 {fmt(x.total_weight)}%</div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
