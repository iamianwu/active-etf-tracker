'use client';

import Link from 'next/link';
import {
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  useWatchlist,
  type WatchlistItem,
} from '@/lib/watchlist';

import styles from './WatchlistPage.module.css';

type Tab =
  | 'all'
  | 'stocks'
  | 'etfs'
  | 'alerts';

type AnyRow =
  Record<string, any>;

const TABS: {
  key: Tab;
  label: string;
}[] = [
  { key: 'all', label: '全部' },
  { key: 'stocks', label: '個股' },
  { key: 'etfs', label: 'ETF' },
  { key: 'alerts', label: '提醒' },
];

function numberOf(
  value: unknown,
  fallback = 0,
) {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return fallback;
  }

  const parsed = Number(
    String(value)
      .replace(/,/g, '')
      .replace(/[^\d.-]/g, ''),
  );

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function firstNumber(
  row: AnyRow | undefined,
  keys: string[],
  fallback = 0,
) {
  for (const key of keys) {
    const value = row?.[key];

    if (
      value === null ||
      value === undefined ||
      value === ''
    ) {
      continue;
    }

    const result = numberOf(
      value,
      Number.NaN,
    );

    if (Number.isFinite(result)) {
      return result;
    }
  }

  return fallback;
}

function textOf(
  row: AnyRow | undefined,
  keys: string[],
  fallback = '',
) {
  for (const key of keys) {
    const value = String(
      row?.[key] ?? '',
    ).trim();

    if (value) {
      return value;
    }
  }

  return fallback;
}

function stockCodeOf(row: AnyRow) {
  return textOf(
    row,
    [
      'stock_code',
      'stockCode',
      'code',
      'symbol',
    ],
  ).toUpperCase();
}

function etfCodeOf(row: AnyRow) {
  return textOf(
    row,
    [
      'etf_code',
      'etfCode',
      'code',
      'symbol',
    ],
  ).toUpperCase();
}

function priceOf(row?: AnyRow) {
  return firstNumber(
    row,
    [
      'price',
      'close_price',
      'close',
      'last_price',
      'stock_price',
      'etf_price',
    ],
    Number.NaN,
  );
}

function pctOf(row?: AnyRow) {
  return firstNumber(
    row,
    [
      'change_pct',
      'pct',
      'percent',
      'changePercent',
      'price_change_pct',
    ],
    Number.NaN,
  );
}

function lotsOf(row?: AnyRow) {
  const lots = firstNumber(
    row,
    [
      'net_lots',
      'display_delta_lots',
      'change_lots',
      'delta_lots',
      'lot_change',
      'delta_shares_lots',
      'shares_change_lots',
    ],
    Number.NaN,
  );

  if (Number.isFinite(lots)) {
    return lots;
  }

  const shares = firstNumber(
    row,
    [
      'delta_shares',
      'shares_change',
      'shares_diff',
    ],
    0,
  );

  return Math.abs(shares) >= 10000
    ? shares / 1000
    : shares;
}

function amountOf(row?: AnyRow) {
  const direct = firstNumber(
    row,
    [
      'net_amount_billion',
      'delta_amount_billion',
      'flow_billion',
      'money_billion',
      'amount_billion',
      'delta_value_billion',
    ],
    Number.NaN,
  );

  if (Number.isFinite(direct)) {
    return direct;
  }

  const price = priceOf(row);
  const lots = lotsOf(row);

  return Number.isFinite(price)
    ? price * lots * 1000 / 100000000
    : 0;
}

function statusOf(row?: AnyRow) {
  const value = textOf(
    row,
    ['status', 'type', 'action'],
  );

  if (value) {
    return value;
  }

  const lots = lotsOf(row);

  if (lots > 0) return '加碼';
  if (lots < 0) return '減碼';
  return '無異動';
}

function buyCountOf(row?: AnyRow) {
  return firstNumber(
    row,
    [
      'buy_count',
      'buyCount',
      'increase_count',
      'add_etf_count',
    ],
    0,
  );
}

function sellCountOf(row?: AnyRow) {
  return firstNumber(
    row,
    [
      'sell_count',
      'sellCount',
      'decrease_count',
      'reduce_etf_count',
    ],
    0,
  );
}

function toneClass(value: number) {
  if (value > 0) return styles.positive;
  if (value < 0) return styles.negative;
  return styles.neutral;
}

function formatPrice(value: number) {
  if (!Number.isFinite(value)) {
    return '-';
  }

  return value.toLocaleString(
    'zh-TW',
    {
      minimumFractionDigits:
        value < 100 ? 2 : 0,
      maximumFractionDigits: 2,
    },
  );
}

function formatPct(value: number) {
  if (!Number.isFinite(value)) {
    return '-';
  }

  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatLots(value: number) {
  if (!Number.isFinite(value)) {
    return '-';
  }

  return `${value > 0 ? '+' : ''}${Math.round(value).toLocaleString('zh-TW')} 張`;
}

function formatAmount(value: number) {
  if (!Number.isFinite(value) || value === 0) {
    return '-';
  }

  return `${value > 0 ? '+' : ''}${value.toFixed(
    Math.abs(value) >= 10 ? 1 : 2,
  )} 億`;
}

function shortDate(value: unknown) {
  const raw = String(value || '');
  const match = raw.match(
    /^\d{4}-(\d{2})-(\d{2})/,
  );

  return match
    ? `${match[1]}/${match[2]}`
    : '-';
}

function EmptyState({
  kind,
}: {
  kind: 'all' | 'stocks' | 'etfs' | 'alerts';
}) {
  const content = {
    all: {
      title: '建立你的投資監控清單',
      copy: '在個股或 ETF 詳情頁點選星號，這裡會集中顯示今日異動與提醒。',
    },
    stocks: {
      title: '尚未追蹤個股',
      copy: '從訊號或搜尋找到標的後，在個股詳情頁點選星號。',
    },
    etfs: {
      title: '尚未追蹤 ETF',
      copy: '前往 ETF 列表，進入 ETF 詳情後點選星號加入追蹤。',
    },
    alerts: {
      title: '今天沒有追蹤提醒',
      copy: '已追蹤個股出現 ETF 加減碼時，提醒會自動集中在這裡。',
    },
  }[kind];

  return (
    <div className={styles.emptyState}>
      <span aria-hidden="true">☆</span>

      <div>
        <strong>{content.title}</strong>
        <p>{content.copy}</p>
      </div>

      <div className={styles.emptyActions}>
        <Link href="/search">
          搜尋個股
        </Link>

        <Link href="/etfs">
          瀏覽 ETF
        </Link>
      </div>
    </div>
  );
}

export default function WatchlistClient() {
  const {
    items,
    counts,
    ready,
    remove,
  } = useWatchlist();

  const [tab, setTab] =
    useState<Tab>('all');

  const [signalRows, setSignalRows] =
    useState<AnyRow[]>([]);

  const [etfRows, setEtfRows] =
    useState<AnyRow[]>([]);

  const [signalDate, setSignalDate] =
    useState('');

  const [loadingStocks, setLoadingStocks] =
    useState(false);

  const [loadingEtfs, setLoadingEtfs] =
    useState(false);

  const [loadError, setLoadError] =
    useState('');

  const stockItems = useMemo(
    () =>
      items.filter(
        (item) =>
          item.type === 'stock',
      ),
    [items],
  );

  const etfItems = useMemo(
    () =>
      items.filter(
        (item) =>
          item.type === 'etf',
      ),
    [items],
  );

  const stockKey = stockItems
    .map((item) => item.code)
    .sort()
    .join(',');

  const etfKey = etfItems
    .map((item) => item.code)
    .sort()
    .join(',');

  useEffect(() => {
    if (!stockKey) {
      setSignalRows([]);
      setSignalDate('');
      setLoadingStocks(false);
      return;
    }

    const controller =
      new AbortController();

    async function loadSignals() {
      setLoadingStocks(true);
      setLoadError('');

      try {
        const response = await fetch(
          '/api/signals?days=1&universe=all',
          {
            signal: controller.signal,
          },
        );

        if (!response.ok) {
          throw new Error(
            `signals ${response.status}`,
          );
        }

        const payload =
          await response.json();

        if (!controller.signal.aborted) {
          setSignalRows(
            Array.isArray(payload?.rows)
              ? payload.rows
              : [],
          );

          setSignalDate(
            String(
              payload?.data_date ||
                payload?.target_data_date ||
                '',
            ),
          );
        }
      } catch (error: any) {
        if (
          error?.name !== 'AbortError'
        ) {
          setLoadError(
            '部分即時資料暫時無法載入，追蹤清單仍可使用。',
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadingStocks(false);
        }
      }
    }

    void loadSignals();
    return () => controller.abort();
  }, [stockKey]);

  useEffect(() => {
    if (!etfKey) {
      setEtfRows([]);
      setLoadingEtfs(false);
      return;
    }

    const controller =
      new AbortController();

    async function loadEtfs() {
      setLoadingEtfs(true);

      try {
        const response = await fetch(
          '/api/watchlist-etfs',
          {
            signal: controller.signal,
          },
        );

        if (!response.ok) {
          throw new Error(
            `watchlist etfs ${response.status}`,
          );
        }

        const payload =
          await response.json();

        if (!controller.signal.aborted) {
          setEtfRows(
            Array.isArray(payload?.rows)
              ? payload.rows
              : [],
          );
        }
      } catch (error: any) {
        if (
          error?.name !== 'AbortError'
        ) {
          setLoadError(
            '部分即時資料暫時無法載入，追蹤清單仍可使用。',
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoadingEtfs(false);
        }
      }
    }

    void loadEtfs();
    return () => controller.abort();
  }, [etfKey]);

  const signalMap = useMemo(
    () =>
      new Map(
        signalRows.map((row) => [
          stockCodeOf(row),
          row,
        ]),
      ),
    [signalRows],
  );

  const etfMap = useMemo(
    () =>
      new Map(
        etfRows.map((row) => [
          etfCodeOf(row),
          row,
        ]),
      ),
    [etfRows],
  );

  const reminders = useMemo(
    () =>
      stockItems
        .map((item) => ({
          item,
          row: signalMap.get(
            item.code,
          ),
        }))
        .filter(
          (entry) =>
            Boolean(entry.row),
        )
        .sort(
          (a, b) =>
            Math.abs(amountOf(b.row)) -
            Math.abs(amountOf(a.row)),
        ),
    [signalMap, stockItems],
  );

  function tabCount(tabKey: Tab) {
    if (tabKey === 'stocks') {
      return counts.stocks;
    }

    if (tabKey === 'etfs') {
      return counts.etfs;
    }

    if (tabKey === 'alerts') {
      return reminders.length;
    }

    return counts.all;
  }

  function renderStocks() {
    if (!stockItems.length) {
      return <EmptyState kind="stocks" />;
    }

    return (
      <section className={styles.listSection}>
        <header className={styles.sectionHeader}>
          <div>
            <span>STOCKS</span>
            <h2>追蹤個股</h2>
          </div>

          <small>
            {loadingStocks
              ? '更新中…'
              : signalDate
                ? `資料日 ${shortDate(signalDate)}`
                : '今日無異動也會保留清單'}
          </small>
        </header>

        <div className={styles.stockList}>
          {stockItems.map((item) => {
            const row = signalMap.get(
              item.code,
            );

            const price = priceOf(row);
            const pct = pctOf(row);
            const lots = lotsOf(row);
            const amount = amountOf(row);
            const buy = buyCountOf(row);
            const sell = sellCountOf(row);
            const status = row
              ? statusOf(row)
              : '今日無異動';

            return (
              <article
                className={styles.stockRow}
                key={`stock:${item.code}`}
              >
                <Link
                  href={`/stock/${item.code}`}
                  className={styles.stockLink}
                >
                  <div className={styles.nameCell}>
                    <strong>{item.name}</strong>
                    <span>{item.code}</span>
                  </div>

                  <div className={styles.numberCell}>
                    <strong>{formatPrice(price)}</strong>
                    <span className={toneClass(pct)}>
                      {formatPct(pct)}
                    </span>
                  </div>

                  <div className={styles.consensusCell}>
                    <strong
                      className={
                        status.includes('減') ||
                        status.includes('刪')
                          ? styles.negative
                          : status === '今日無異動'
                            ? styles.neutral
                            : styles.positive
                      }
                    >
                      {status}
                    </strong>
                    <span>{buy}:{sell}</span>
                  </div>

                  <div className={styles.flowCell}>
                    <strong className={toneClass(lots)}>
                      {row
                        ? formatLots(lots)
                        : '-'}
                    </strong>
                    <span className={toneClass(amount)}>
                      {formatAmount(amount)}
                    </span>
                  </div>
                </Link>

                <button
                  type="button"
                  className={styles.removeButton}
                  aria-label={`取消追蹤 ${item.name}`}
                  title="取消追蹤"
                  onClick={() =>
                    remove(
                      item.code,
                      'stock',
                    )
                  }
                >
                  ★
                </button>
              </article>
            );
          })}
        </div>
      </section>
    );
  }

  function renderEtfs() {
    if (!etfItems.length) {
      return <EmptyState kind="etfs" />;
    }

    return (
      <section className={styles.listSection}>
        <header className={styles.sectionHeader}>
          <div>
            <span>ETFS</span>
            <h2>追蹤 ETF</h2>
          </div>

          <small>
            {loadingEtfs
              ? '更新中…'
              : `${etfItems.length} 檔`}
          </small>
        </header>

        <div className={styles.etfList}>
          {etfItems.map((item) => {
            const row = etfMap.get(
              item.code,
            );

            const etfGroup = String(
              row?.etf_group ||
                row?.etf_type ||
                '',
            ).toLowerCase();

            /*
              ETF 快照尚未載入時，先用現有代號規則判斷。
              主動式 ETF 為五碼加 A；一般 ETF 不應短暫
              被導向主動式 ETF 詳情頁。
            */
            const isReference = etfGroup
              ? etfGroup === 'reference'
              : !/^[0-9]{5}A$/.test(
                  item.code,
                );

            const price = priceOf(row);
            const pct = pctOf(row);
            const latestDate =
              textOf(
                row,
                [
                  'latest_holding_date',
                  'latestHoldingDate',
                  'data_date',
                ],
              );

            const role = textOf(
              row,
              [
                'reference_role',
                'role',
                'region',
              ],
              isReference
                ? '參考對照'
                : '主動式 ETF',
            );

            const href = isReference
              ? '/reference-etfs'
              : `/etf/${item.code}?from=watchlist`;

            return (
              <article
                className={styles.etfRow}
                key={`etf:${item.code}`}
              >
                <Link
                  href={href}
                  className={styles.etfLink}
                >
                  <div className={styles.nameCell}>
                    <strong>{item.name}</strong>
                    <span>{item.code}</span>
                  </div>

                  <div className={styles.etfTypeCell}>
                    <strong>
                      {isReference
                        ? '一般 ETF'
                        : '主動式 ETF'}
                    </strong>
                    <span>{role}</span>
                  </div>

                  <div className={styles.numberCell}>
                    <strong>
                      {isReference
                        ? '參考'
                        : formatPrice(price)}
                    </strong>
                    <span
                      className={
                        isReference
                          ? styles.neutral
                          : toneClass(pct)
                      }
                    >
                      {isReference
                        ? '不納入訊號'
                        : formatPct(pct)}
                    </span>
                  </div>

                  <div className={styles.dataCell}>
                    <strong>
                      {isReference
                        ? '對照資料'
                        : latestDate
                          ? '持股已更新'
                          : '持股待更新'}
                    </strong>
                    <span>
                      {latestDate
                        ? shortDate(latestDate)
                        : '-'}
                    </span>
                  </div>
                </Link>

                <button
                  type="button"
                  className={styles.removeButton}
                  aria-label={`取消追蹤 ${item.name}`}
                  title="取消追蹤"
                  onClick={() =>
                    remove(
                      item.code,
                      'etf',
                    )
                  }
                >
                  ★
                </button>
              </article>
            );
          })}
        </div>
      </section>
    );
  }

  function renderAlerts() {
    if (!reminders.length) {
      return <EmptyState kind="alerts" />;
    }

    return (
      <section className={styles.listSection}>
        <header className={styles.sectionHeader}>
          <div>
            <span>ALERTS</span>
            <h2>今日追蹤提醒</h2>
          </div>

          <small>{reminders.length} 則</small>
        </header>

        <div className={styles.alertList}>
          {reminders.map(({ item, row }) => {
            const status = statusOf(row);
            const buy = buyCountOf(row);
            const sell = sellCountOf(row);
            const amount = amountOf(row);
            const isNegative =
              status.includes('減') ||
              status.includes('刪');

            return (
              <Link
                href={`/stock/${item.code}`}
                className={styles.alertRow}
                key={`alert:${item.code}`}
              >
                <span
                  className={
                    isNegative
                      ? styles.alertDotNegative
                      : styles.alertDotPositive
                  }
                />

                <div>
                  <strong>
                    {item.name}
                    <small>{item.code}</small>
                  </strong>

                  <p>
                    ETF 共識 {buy}:{sell}・{status}
                  </p>
                </div>

                <b className={toneClass(amount)}>
                  {formatAmount(amount)}
                </b>
              </Link>
            );
          })}
        </div>
      </section>
    );
  }

  if (!ready) {
    return (
      <main className={styles.page}>
        <div className={styles.loadingCard}>
          追蹤資料載入中…
        </div>
      </main>
    );
  }

  const isEmpty = counts.all === 0;

  return (
    <main className={styles.page}>
      <header className={styles.titleRow}>
        <div>
          <span>MY WATCHLIST</span>
          <h1>我的追蹤</h1>
          <p>
            集中查看關注個股、ETF 與今日持股異動。
          </p>
        </div>

        <Link href="/search">
          ＋新增
        </Link>
      </header>

      <section
        className={styles.summary}
        aria-label="追蹤摘要"
      >
        <div>
          <span>追蹤個股</span>
          <strong>{counts.stocks}</strong>
        </div>

        <div>
          <span>追蹤 ETF</span>
          <strong>{counts.etfs}</strong>
        </div>

        <div>
          <span>今日提醒</span>
          <strong>{reminders.length}</strong>
        </div>
      </section>

      <nav
        className={styles.tabs}
        role="tablist"
        aria-label="追蹤內容分類"
      >
        {TABS.map((item) => (
          <button
            type="button"
            role="tab"
            key={item.key}
            aria-selected={
              tab === item.key
            }
            className={
              tab === item.key
                ? styles.activeTab
                : ''
            }
            onClick={() =>
              setTab(item.key)
            }
          >
            {item.label}
            <span>{tabCount(item.key)}</span>
          </button>
        ))}
      </nav>

      {loadError && (
        <div className={styles.dataNotice}>
          {loadError}
        </div>
      )}

      {isEmpty ? (
        <EmptyState kind="all" />
      ) : (
        <>
          {tab === 'all' && (
            <>
              {reminders.length > 0 &&
                renderAlerts()}
              {renderStocks()}
              {renderEtfs()}
            </>
          )}

          {tab === 'stocks' &&
            renderStocks()}

          {tab === 'etfs' &&
            renderEtfs()}

          {tab === 'alerts' &&
            renderAlerts()}
        </>
      )}

      <footer className={styles.localNote}>
        <span aria-hidden="true">⌁</span>
        第一版追蹤清單儲存在這台裝置；清除瀏覽器資料後需重新加入。
      </footer>
    </main>
  );
}
