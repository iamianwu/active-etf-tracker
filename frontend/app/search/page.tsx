'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { fmt0, fmt } from '@/lib/api';

const HOT_ITEMS = [
  { code: '00403A', name: '主動統一升級50', type: 'etf' },
  { code: '00981A', name: '主動統一台股增長', type: 'etf' },
  { code: '00980A', name: '主動野村臺灣優選', type: 'etf' },
  { code: '00982A', name: '主動群益台灣強棒', type: 'etf' },
  { code: '2330', name: '台積電', type: 'stock' },
  { code: '2317', name: '鴻海', type: 'stock' },
  { code: '2454', name: '聯發科', type: 'stock' },
];

type SearchResults = {
  etfs: any[];
  stocks: any[];
};

const EMPTY_RESULTS: SearchResults = { etfs: [], stocks: [] };

function saveHistory(item: any) {
  try {
    const old = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    const next = [item, ...old.filter((x: any) => !(x.code === item.code && x.type === item.type))].slice(0, 8);
    localStorage.setItem('searchHistory', JSON.stringify(next));
  } catch {}
}

export default function SearchPage() {
  const [q, setQ] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [loadedQ, setLoadedQ] = useState('');
  const [results, setResults] = useState<SearchResults>(EMPTY_RESULTS);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const cacheRef = useRef<Record<string, SearchResults>>({});

  useEffect(() => {
    try {
      setHistory(JSON.parse(localStorage.getItem('searchHistory') || '[]'));
    } catch {}
  }, []);

  useEffect(() => {
    const t = window.setTimeout(() => {
      setDebouncedQ(q.trim());
    }, 220);

    return () => window.clearTimeout(t);
  }, [q]);

  useEffect(() => {
    const keyword = debouncedQ.trim();
    const key = keyword.toLowerCase();

    if (!keyword) {
      setResults(EMPTY_RESULTS);
      setLoadedQ('');
      setLoading(false);
      return;
    }

    if (cacheRef.current[key]) {
      setResults(cacheRef.current[key]);
      setLoadedQ(key);
      setLoading(false);
      return;
    }

    const ctrl = new AbortController();
    setLoading(true);

    fetch(`/api/search?q=${encodeURIComponent(keyword)}`, {
      signal: ctrl.signal,
      cache: 'no-store',
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Search failed: ${r.status}`);
        return r.json();
      })
      .then((data) => {
        const next = {
          etfs: Array.isArray(data?.etfs) ? data.etfs : [],
          stocks: Array.isArray(data?.stocks) ? data.stocks : [],
        };
        cacheRef.current[key] = next;
        setResults(next);
        setLoadedQ(key);
      })
      .catch((e) => {
        if (e?.name !== 'AbortError') {
          console.error(e);
          setResults(EMPTY_RESULTS);
          setLoadedQ(key);
        }
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setLoading(false);
      });

    return () => ctrl.abort();
  }, [debouncedQ]);

  function clearHistory() {
    localStorage.removeItem('searchHistory');
    setHistory([]);
  }

  const queryKey = q.trim().toLowerCase();
  const hasQuery = !!queryKey;
  const stillSearching = hasQuery && loadedQ !== queryKey;
  const displayResults = hasQuery && !stillSearching ? results : EMPTY_RESULTS;

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

      {hasQuery && (loading || stillSearching) && <p className="muted">資料載入中...</p>}

      {!hasQuery && (
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

      {hasQuery && !stillSearching && (
        <>
          <section className="search-section">
            <h3>ETF 搜尋結果</h3>
            {displayResults.etfs.length === 0 ? (
              <p className="muted">沒有符合的 ETF</p>
            ) : (
              <div className="result-list">
                {displayResults.etfs.map((x: any) => (
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
            {displayResults.stocks.length === 0 ? (
              <p className="muted">沒有符合的個股</p>
            ) : (
              <div className="result-list">
                {displayResults.stocks.map((x: any) => (
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
