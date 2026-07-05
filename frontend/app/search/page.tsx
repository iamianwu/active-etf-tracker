'use client';

import Link from 'next/link';
import {
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  fmt,
  fmt0,
} from '@/lib/api';

const SEARCH_INDEX_KEY =
  'activeEtfSearchIndexV3';

const HOT_ITEMS = [
  {
    code: '00403A',
    name: '主動統一升級50',
    type: 'etf',
  },
  {
    code: '00981A',
    name: '主動統一台股增長',
    type: 'etf',
  },
  {
    code: '00980A',
    name: '主動野村臺灣優選',
    type: 'etf',
  },
  {
    code: '00982A',
    name: '主動群益台灣強棒',
    type: 'etf',
  },
  {
    code: '2330',
    name: '台積電',
    type: 'stock',
  },
  {
    code: '2317',
    name: '鴻海',
    type: 'stock',
  },
  {
    code: '2454',
    name: '聯發科',
    type: 'stock',
  },
];

type SearchResults = {
  etfs: any[];
  stocks: any[];
};

type SearchIndexPayload = SearchResults & {
  generated_at?: string;
};

const EMPTY_RESULTS: SearchResults = {
  etfs: [],
  stocks: [],
};

function normalize(value: unknown): string {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '');
}

function scoreItem(
  codeValue: unknown,
  nameValue: unknown,
  query: string
): number {
  const code = normalize(codeValue);
  const name = normalize(nameValue);

  if (!query) {
    return -1;
  }

  if (code === query) {
    return 1000;
  }

  if (name === query) {
    return 950;
  }

  if (code.startsWith(query)) {
    return 900;
  }

  if (name.startsWith(query)) {
    return 800;
  }

  const codeIndex = code.indexOf(query);

  if (codeIndex >= 0) {
    return 700 - codeIndex;
  }

  const nameIndex = name.indexOf(query);

  if (nameIndex >= 0) {
    return 600 - nameIndex;
  }

  return -1;
}

function localSearch(
  index: SearchIndexPayload,
  query: string
): SearchResults {
  const normalizedQuery = normalize(query);

  if (!normalizedQuery) {
    return EMPTY_RESULTS;
  }

  const etfs = index.etfs
    .map((item: any) => ({
      item,
      score: scoreItem(
        item?.etf_code,
        item?.etf_name,
        normalizedQuery
      ),
    }))
    .filter((entry) => entry.score >= 0)
    .sort((a, b) => {
      if (b.score !== a.score) {
        return b.score - a.score;
      }

      return (
        Number(
          b.item?.holding_count || 0
        ) -
        Number(
          a.item?.holding_count || 0
        )
      );
    })
    .slice(0, 20)
    .map((entry) => entry.item);

  const stocks = index.stocks
    .map((item: any) => ({
      item,
      score: scoreItem(
        item?.stock_code,
        item?.stock_name,
        normalizedQuery
      ),
    }))
    .filter((entry) => entry.score >= 0)
    .sort((a, b) => {
      if (b.score !== a.score) {
        return b.score - a.score;
      }

      const etfCountDifference =
        Number(
          b.item?.etf_count || 0
        ) -
        Number(
          a.item?.etf_count || 0
        );

      if (etfCountDifference !== 0) {
        return etfCountDifference;
      }

      return (
        Number(
          b.item?.total_weight || 0
        ) -
        Number(
          a.item?.total_weight || 0
        )
      );
    })
    .slice(0, 40)
    .map((entry) => entry.item);

  return {
    etfs,
    stocks,
  };
}

function saveHistory(item: any) {
  try {
    const old = JSON.parse(
      localStorage.getItem(
        'searchHistory'
      ) || '[]'
    );

    const next = [
      item,
      ...old.filter(
        (value: any) =>
          !(
            value.code === item.code &&
            value.type === item.type
          )
      ),
    ].slice(0, 8);

    localStorage.setItem(
      'searchHistory',
      JSON.stringify(next)
    );
  } catch {}
}

export default function SearchPage() {
  const [q, setQ] = useState('');
  const [index, setIndex] =
    useState<SearchIndexPayload | null>(
      null
    );
  const [history, setHistory] =
    useState<any[]>([]);
  const [loading, setLoading] =
    useState(true);
  const [loadError, setLoadError] =
    useState('');

  useEffect(() => {
    let active = true;

    try {
      setHistory(
        JSON.parse(
          localStorage.getItem(
            'searchHistory'
          ) || '[]'
        )
      );
    } catch {}

    try {
      const cachedText =
        localStorage.getItem(
          SEARCH_INDEX_KEY
        );

      if (cachedText) {
        const cached = JSON.parse(
          cachedText
        );

        if (
          Array.isArray(
            cached?.data?.etfs
          ) &&
          Array.isArray(
            cached?.data?.stocks
          )
        ) {
          setIndex(cached.data);
          setLoading(false);
        }
      }
    } catch {}

    fetch('/api/search-index', {
      cache: 'force-cache',
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(
            `HTTP ${response.status}`
          );
        }

        return response.json();
      })
      .then((payload) => {
        if (!active) {
          return;
        }

        const next: SearchIndexPayload = {
          etfs: Array.isArray(
            payload?.etfs
          )
            ? payload.etfs
            : [],

          stocks: Array.isArray(
            payload?.stocks
          )
            ? payload.stocks
            : [],

          generated_at:
            payload?.generated_at,
        };

        setIndex(next);
        setLoadError('');

        try {
          localStorage.setItem(
            SEARCH_INDEX_KEY,
            JSON.stringify({
              saved_at: Date.now(),
              data: next,
            })
          );
        } catch {}
      })
      .catch((error) => {
        console.error(error);

        if (active && !index) {
          setLoadError(
            '搜尋資料暫時無法載入'
          );
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
    // 搜尋索引只在進入頁面時載入一次。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const queryKey = normalize(q);
  const hasQuery = Boolean(queryKey);

  const displayResults = useMemo(
    () =>
      index && hasQuery
        ? localSearch(index, queryKey)
        : EMPTY_RESULTS,
    [index, hasQuery, queryKey]
  );

  function clearHistory() {
    localStorage.removeItem(
      'searchHistory'
    );
    setHistory([]);
  }

  return (
    <main className="page search-page">
      <div className="search-header">
        <Link href="/" className="back">
          ‹
        </Link>

        <h2>搜尋</h2>

        <div className="back-placeholder" />
      </div>

      <div className="search-box">
        <span className="search-mark">
          <span
            className="
              header-icon-v67
              header-icon-search-v67
            "
          />
        </span>

        <input
          autoFocus
          autoComplete="off"
          enterKeyHint="search"
          inputMode="search"
          value={q}
          onChange={(event) =>
            setQ(event.target.value)
          }
          placeholder="輸入 ETF 或個股代號 / 名稱"
        />
      </div>

      {hasQuery &&
        !index &&
        loading && (
          <p className="muted">
            正在準備搜尋資料…
          </p>
        )}

      {hasQuery &&
        !index &&
        loadError && (
          <p className="muted">
            {loadError}
          </p>
        )}

      {!hasQuery && (
        <>
          <section className="search-section">
            <h3>熱門搜尋</h3>

            <div className="search-chip-row">
              {HOT_ITEMS.map((item) => {
                const href =
                  item.type === 'etf'
                    ? `/etf/${item.code}`
                    : `/stock/${item.code}`;

                return (
                  <Link
                    key={`${item.type}-${item.code}`}
                    className="search-chip"
                    href={href}
                    onClick={() =>
                      saveHistory(item)
                    }
                  >
                    <b>{item.code}</b>{' '}
                    {item.name}
                  </Link>
                );
              })}
            </div>
          </section>

          <section className="search-section">
            <div className="search-section-title">
              <h3>歷史搜尋</h3>

              {history.length > 0 && (
                <button
                  className="clear-btn"
                  onClick={clearHistory}
                >
                  清空
                </button>
              )}
            </div>

            {history.length === 0 ? (
              <p className="muted">
                尚無歷史搜尋
              </p>
            ) : (
              <div className="history-list">
                {history.map(
                  (item: any) => {
                    const href =
                      item.type === 'etf'
                        ? `/etf/${item.code}`
                        : `/stock/${item.code}`;

                    return (
                      <Link
                        key={`${item.type}-${item.code}`}
                        href={href}
                        className="history-item"
                        onClick={() =>
                          saveHistory(item)
                        }
                      >
                        <b>{item.code}</b>
                        <span>
                          {item.name}
                        </span>
                      </Link>
                    );
                  }
                )}
              </div>
            )}
          </section>
        </>
      )}

      {hasQuery && index && (
        <>
          <section className="search-section">
            <h3>ETF 搜尋結果</h3>

            {displayResults.etfs.length ===
            0 ? (
              <p className="muted">
                沒有符合的 ETF
              </p>
            ) : (
              <div className="result-list">
                {displayResults.etfs.map(
                  (item: any) => (
                    <Link
                      key={item.etf_code}
                      href={`/etf/${item.etf_code}`}
                      className="result-row"
                      onClick={() =>
                        saveHistory({
                          code:
                            item.etf_code,
                          name:
                            item.etf_name,
                          type: 'etf',
                        })
                      }
                    >
                      <div>
                        <b>
                          {item.etf_code}
                        </b>

                        <div>
                          {item.etf_name}
                        </div>
                      </div>

                      <div className="result-meta">
                        <div>
                          成分股{' '}
                          {fmt0(
                            item.holding_count
                          )}{' '}
                          檔
                        </div>

                        <div>
                          股票權重{' '}
                          {fmt(
                            item.stock_weight
                          )}
                          %
                        </div>
                      </div>
                    </Link>
                  )
                )}
              </div>
            )}
          </section>

          <section className="search-section">
            <h3>個股搜尋結果</h3>

            {displayResults.stocks
              .length === 0 ? (
              <p className="muted">
                沒有符合的個股
              </p>
            ) : (
              <div className="result-list">
                {displayResults.stocks.map(
                  (item: any) => (
                    <Link
                      key={item.stock_code}
                      href={`/stock/${item.stock_code}`}
                      className="result-row"
                      onClick={() =>
                        saveHistory({
                          code:
                            item.stock_code,
                          name:
                            item.stock_name,
                          type: 'stock',
                        })
                      }
                    >
                      <div>
                        <b>
                          {item.stock_name}
                        </b>

                        <div className="code">
                          {item.stock_code}
                        </div>
                      </div>

                      <div className="result-meta">
                        <div>
                          ETF{' '}
                          {fmt0(
                            item.etf_count
                          )}{' '}
                          檔
                        </div>

                        <div>
                          合計權重{' '}
                          {fmt(
                            item.total_weight
                          )}
                          %
                        </div>
                      </div>
                    </Link>
                  )
                )}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
