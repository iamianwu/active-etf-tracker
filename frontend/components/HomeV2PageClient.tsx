'use client';

import Link from 'next/link';
import {
  useEffect,
  useMemo,
  useState,
} from 'react';
import styles from './HomeV2PageClient.module.css';

type Universe = 'active' | 'reference';

type ChangedEtf = {
  etf_code?: string;
  status?: string;
  delta_shares?: number;
  delta_raw_shares?: number;
};

type SignalRow = {
  code?: string;
  name?: string;
  stock_code?: string;
  stock_name?: string;
  status?: string;
  price?: number;
  amount?: number;
  amount_billion?: number;
  net_amount_billion?: number;
  delta_amount_billion?: number;
  delta_shares?: number;
  delta_shares_lots?: number;
  etf_count?: number;
  etf_change_count?: number;
  buy_count?: number;
  sell_count?: number;
  increase_count?: number;
  decrease_count?: number;
  consensus?: string;
  buySellText?: string;
  changed_etfs?: ChangedEtf[];
};

type SignalPayload = {
  data_date?: string;
  target_data_date?: string;
  updated_at?: string;
  fetched_etf_count?: number;
  total_etf_count?: number;
  signal_count?: number;
  rows?: SignalRow[];
};

type EtfIndexRow = {
  etf_code?: string;
  etf_name?: string;
};

type SearchIndexPayload = {
  etfs?: EtfIndexRow[];
  generated_at?: string;
  updated_at?: string;
};

type Favorite = {
  code?: string;
  name?: string;
  type?: 'stock' | 'etf';
};

type EtfOperation = {
  code: string;
  name: string;
  addAmount: number;
  reduceAmount: number;
  addStocks: number;
  reduceStocks: number;
};

function numberOf(value: unknown): number {
  const result = Number(value);
  return Number.isFinite(result) ? result : 0;
}

function rowsOf(
  payload: SignalPayload | null,
): SignalRow[] {
  return Array.isArray(payload?.rows)
    ? payload.rows
    : [];
}

function codeOf(row: SignalRow): string {
  return String(
    row.code ||
      row.stock_code ||
      '',
  ).trim();
}

function nameOf(row: SignalRow): string {
  return String(
    row.name ||
      row.stock_name ||
      codeOf(row),
  ).trim();
}

function amountOf(row: SignalRow): number {
  const candidates = [
    row.amount_billion,
    row.net_amount_billion,
    row.delta_amount_billion,
    row.amount,
  ];

  for (const candidate of candidates) {
    const value = Number(candidate);

    if (Number.isFinite(value)) {
      return value;
    }
  }

  return 0;
}

function etfCountOf(row: SignalRow): number {
  return numberOf(
    row.etf_count ||
      row.etf_change_count,
  );
}

function buyCountOf(row: SignalRow): number {
  return numberOf(
    row.buy_count ||
      row.increase_count,
  );
}

function sellCountOf(row: SignalRow): number {
  return numberOf(
    row.sell_count ||
      row.decrease_count,
  );
}

function statusOf(row: SignalRow): string {
  if (row.status) {
    return String(row.status);
  }

  return amountOf(row) >= 0
    ? '加碼'
    : '減碼';
}

function isPositive(row: SignalRow): boolean {
  return amountOf(row) > 0;
}

function dateText(value: unknown): string {
  const raw = String(value || '');

  const match = raw.match(
    /^\d{4}-(\d{2})-(\d{2})/,
  );

  return match
    ? `${match[1]}/${match[2]}`
    : raw || '-';
}

function updateText(value: unknown): string {
  const raw = String(value || '').trim();

  if (!raw) return '-';

  const date = new Date(raw);

  if (Number.isNaN(date.getTime())) {
    return '-';
  }

  return new Intl.DateTimeFormat('zh-TW', {
    timeZone: 'Asia/Taipei',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
    .format(date)
    .replace(',', '');
}

function latestUpdatedAt(
  ...values: unknown[]
): string {
  return values
    .map((value) => String(value || '').trim())
    .filter(
      (value) =>
        value &&
        Number.isFinite(
          new Date(value).getTime(),
        ),
    )
    .sort(
      (a, b) =>
        new Date(b).getTime() -
        new Date(a).getTime(),
    )[0] || '';
}

function formatAmount(value: number): string {
  const sign = value > 0 ? '+' : '';
  const digits =
    Math.abs(value) >= 100 ? 1 : 2;

  return `${sign}${value.toFixed(digits)} 億`;
}

function formatCompactAmount(
  value: number,
): string {
  const sign = value > 0 ? '+' : '';
  const digits =
    Math.abs(value) >= 10 ? 1 : 2;

  return `${sign}${value.toFixed(digits)}億`;
}

function coverageOf(
  payload: SignalPayload | null,
) {
  const fetched = numberOf(
    payload?.fetched_etf_count,
  );

  const total = numberOf(
    payload?.total_etf_count,
  );

  return {
    fetched,
    total,
    missing: Math.max(
      0,
      total - fetched,
    ),
  };
}

async function loadUniverse(
  universe: Universe,
  signal: AbortSignal,
): Promise<SignalPayload> {
  const versionResponse = await fetch(
    `/api/signals-version?days=1&universe=${universe}`,
    {
      signal,
      cache: 'no-store',
    },
  );

  const versionPayload: any =
    versionResponse.ok
      ? await versionResponse.json()
      : {};

  const version = String(
    versionPayload?.version ||
      Date.now(),
  );

  const response = await fetch(
    `/api/signals?days=1&universe=${universe}&cv=${encodeURIComponent(
      version,
    )}`,
    {
      signal,
      cache: 'no-store',
    },
  );

  if (!response.ok) {
    throw new Error(
      `${universe} signals api failed: ${response.status}`,
    );
  }

  const payload: SignalPayload =
    await response.json();

  return {
    ...payload,
    data_date:
      payload.data_date ||
      versionPayload.data_date,
    updated_at:
      versionPayload.updated_at ||
      payload.updated_at,
  };
}

async function loadSearchIndex(
  signal: AbortSignal,
): Promise<SearchIndexPayload> {
  const response = await fetch(
    '/api/search-index',
    {
      signal,
      cache: 'force-cache',
    },
  );

  if (!response.ok) {
    throw new Error(
      `search index failed: ${response.status}`,
    );
  }

  return response.json();
}

function readFavorites(): Favorite[] {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const raw = JSON.parse(
      window.localStorage.getItem(
        'active_etf_favorites_v89',
      ) || '[]',
    );

    return Array.isArray(raw)
      ? raw
      : [];
  } catch {
    return [];
  }
}

export default function HomeV2PageClient() {
  const [
    activeData,
    setActiveData,
  ] = useState<SignalPayload | null>(
    null,
  );

  const [
    referenceData,
    setReferenceData,
  ] = useState<SignalPayload | null>(
    null,
  );

  const [
    searchIndex,
    setSearchIndex,
  ] = useState<SearchIndexPayload | null>(
    null,
  );

  const [
    favorites,
    setFavorites,
  ] = useState<Favorite[]>([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    error,
    setError,
  ] = useState('');

  const [
    reloadKey,
    setReloadKey,
  ] = useState(0);

  useEffect(() => {
    setFavorites(readFavorites());
  }, []);

  useEffect(() => {
    const controller =
      new AbortController();

    async function load() {
      setLoading(true);
      setError('');

      const results =
        await Promise.allSettled([
          loadUniverse(
            'active',
            controller.signal,
          ),

          loadUniverse(
            'reference',
            controller.signal,
          ),

          loadSearchIndex(
            controller.signal,
          ),
        ]);

      if (controller.signal.aborted) {
        return;
      }

      const [
        activeResult,
        referenceResult,
        indexResult,
      ] = results;

      if (
        activeResult.status ===
        'fulfilled'
      ) {
        setActiveData(
          activeResult.value,
        );
      }

      if (
        referenceResult.status ===
        'fulfilled'
      ) {
        setReferenceData(
          referenceResult.value,
        );
      }

      if (
        indexResult.status ===
        'fulfilled'
      ) {
        setSearchIndex(
          indexResult.value,
        );
      }

      const failedCount =
        results.filter(
          (result) =>
            result.status ===
            'rejected',
        ).length;

      if (failedCount === 3) {
        setError(
          '總覽資料暫時無法載入',
        );
      } else if (failedCount > 0) {
        setError(
          '部分資料暫時無法載入',
        );
      }

      setLoading(false);
    }

    load().catch((reason) => {
      if (!controller.signal.aborted) {
        setError(
          String(
            reason?.message ||
              reason,
          ),
        );

        setLoading(false);
      }
    });

    return () =>
      controller.abort();
  }, [reloadKey]);

  const activeRows = useMemo(
    () => rowsOf(activeData),
    [activeData],
  );

  const referenceRows = useMemo(
    () => rowsOf(referenceData),
    [referenceData],
  );

  const activeCoverage = coverageOf(
    activeData,
  );

  const referenceCoverage =
    coverageOf(referenceData);

  const totalFetched =
    activeCoverage.fetched +
    referenceCoverage.fetched;

  const totalEtfs =
    activeCoverage.total +
    referenceCoverage.total;

  const totalMissing = Math.max(
    0,
    totalEtfs - totalFetched,
  );

  const dataDate =
    activeData?.data_date ||
    activeData?.target_data_date ||
    referenceData?.data_date ||
    referenceData?.target_data_date;

  const updateTime =
    latestUpdatedAt(
      activeData?.updated_at,
      referenceData?.updated_at,
    );

  const positiveRows = useMemo(
    () =>
      activeRows.filter(
        (row) => amountOf(row) > 0,
      ),
    [activeRows],
  );

  const negativeRows = useMemo(
    () =>
      activeRows.filter(
        (row) => amountOf(row) < 0,
      ),
    [activeRows],
  );

  const topSignals = useMemo(
    () =>
      [...activeRows]
        .filter((row) => codeOf(row))
        .sort(
          (a, b) =>
            Math.abs(amountOf(b)) -
            Math.abs(amountOf(a)),
        )
        .slice(0, 5),
    [activeRows],
  );

  const biggestIncrease =
    useMemo(
      () =>
        [...positiveRows].sort(
          (a, b) =>
            amountOf(b) -
            amountOf(a),
        )[0] || null,
      [positiveRows],
    );

  const biggestDecrease =
    useMemo(
      () =>
        [...negativeRows].sort(
          (a, b) =>
            amountOf(a) -
            amountOf(b),
        )[0] || null,
      [negativeRows],
    );

  const etfNames = useMemo(() => {
    const result =
      new Map<string, string>();

    for (
      const row of
      searchIndex?.etfs || []
    ) {
      const code = String(
        row.etf_code || '',
      ).trim();

      const name = String(
        row.etf_name || code,
      ).trim();

      if (code) {
        result.set(code, name);
      }
    }

    return result;
  }, [searchIndex]);

  const operationFocus =
    useMemo(() => {
      const map =
        new Map<
          string,
          EtfOperation
        >();

      for (const row of activeRows) {
        const price = numberOf(
          row.price,
        );

        if (price <= 0) continue;

        for (
          const change of
          row.changed_etfs || []
        ) {
          const etfCode = String(
            change.etf_code || '',
          ).trim();

          if (!etfCode) continue;

          let rawShares = numberOf(
            change.delta_raw_shares,
          );

          if (!rawShares) {
            rawShares =
              numberOf(
                change.delta_shares,
              ) * 1000;
          }

          if (!rawShares) continue;

          const amount =
            Math.abs(
              price * rawShares,
            ) / 100_000_000;

          const current =
            map.get(etfCode) || {
              code: etfCode,
              name:
                etfNames.get(
                  etfCode,
                ) || etfCode,
              addAmount: 0,
              reduceAmount: 0,
              addStocks: 0,
              reduceStocks: 0,
            };

          const status = String(
            change.status || '',
          );

          const positive =
            rawShares > 0 ||
            status.includes('加碼') ||
            status.includes('新增');

          if (positive) {
            current.addAmount +=
              amount;

            current.addStocks += 1;
          } else {
            current.reduceAmount +=
              amount;

            current.reduceStocks += 1;
          }

          map.set(
            etfCode,
            current,
          );
        }
      }

      const rows = Array.from(
        map.values(),
      );

      return {
        add: [...rows]
          .filter(
            (row) =>
              row.addAmount > 0,
          )
          .sort(
            (a, b) =>
              b.addAmount -
              a.addAmount,
          )
          .slice(0, 3),

        reduce: [...rows]
          .filter(
            (row) =>
              row.reduceAmount > 0,
          )
          .sort(
            (a, b) =>
              b.reduceAmount -
              a.reduceAmount,
          )
          .slice(0, 3),
      };
    }, [activeRows, etfNames]);

  const watchlistRows =
    useMemo(() => {
      const activeMap =
        new Map(
          activeRows.map((row) => [
            codeOf(row),
            row,
          ]),
        );

      const referenceMap =
        new Map(
          referenceRows.map((row) => [
            codeOf(row),
            row,
          ]),
        );

      return favorites
        .filter(
          (item) =>
            item.type === 'stock' &&
            item.code,
        )
        .slice(0, 5)
        .map((item) => {
          const code = String(
            item.code || '',
          );

          return {
            code,
            name:
              item.name || code,
            active:
              activeMap.get(code) ||
              null,
            reference:
              referenceMap.get(
                code,
              ) || null,
          };
        });
    }, [
      activeRows,
      referenceRows,
      favorites,
    ]);

  return (
    <main className={styles.page}>
      <section
        className={styles.updateBar}
      >
        <div>
          <span>資料日</span>
          <strong>
            {dateText(dataDate)}
          </strong>
          <small>
            更新 {updateText(updateTime)}
          </small>
        </div>

        <div
          className={styles.coverage}
        >
          <span
            className={
              totalMissing > 0
                ? styles.partialDot
                : styles.completeDot
            }
          />

          <strong>
            {loading
              ? '資料更新中'
              : totalMissing > 0
                ? `部分完成・尚缺 ${totalMissing} 檔`
                : '資料完整'}
          </strong>
        </div>
      </section>

      {error ? (
        <section
          className={styles.notice}
        >
          <span>{error}</span>

          <button
            type="button"
            onClick={() =>
              setReloadKey(
                (value) =>
                  value + 1,
              )
            }
          >
            重新載入
          </button>
        </section>
      ) : null}

      <section
        className={styles.hero}
      >
        <span className={styles.kicker}>
          TODAY OVERVIEW
        </span>

        <h1>
          主動式 ETF 今日出現{' '}
          {numberOf(
            activeData?.signal_count,
          )}{' '}
          筆持股異動
        </h1>

        <p>
          {biggestIncrease
            ? `最大加碼為 ${nameOf(
                biggestIncrease,
              )} ${formatAmount(
                amountOf(
                  biggestIncrease,
                ),
              )}`
            : '正在整理今日重點'}

          {biggestDecrease
            ? `；最大減碼為 ${nameOf(
                biggestDecrease,
              )} ${formatAmount(
                amountOf(
                  biggestDecrease,
                ),
              )}`
            : ''}
        </p>

        <div
          className={styles.summaryGrid}
        >
          <article>
            <span>今日訊號</span>
            <strong>
              {numberOf(
                activeData?.signal_count,
              )}
            </strong>
            <small>筆持股異動</small>
          </article>

          <article>
            <span>加碼股票</span>
            <strong
              className={styles.positive}
            >
              {positiveRows.length}
            </strong>
            <small>淨金額為正</small>
          </article>

          <article>
            <span>減碼股票</span>
            <strong
              className={styles.negative}
            >
              {negativeRows.length}
            </strong>
            <small>淨金額為負</small>
          </article>
        </div>

        <div
          className={styles.universeLine}
        >
          <span>
            主動式{' '}
            <b>
              {activeCoverage.fetched}/
              {activeCoverage.total}
            </b>
          </span>

          <span>
            一般 ETF{' '}
            <b>
              {referenceCoverage.fetched}/
              {referenceCoverage.total}
            </b>
          </span>

          <span>
            全部追蹤{' '}
            <b>
              {totalFetched}/
              {totalEtfs}
            </b>
          </span>
        </div>
      </section>

      <section
        className={styles.card}
      >
        <header
          className={
            styles.sectionHeading
          }
        >
          <div>
            <span>
              ACTIVE ETF SIGNALS
            </span>
            <h2>今日訊號 TOP 5</h2>
          </div>

          <Link href="/signals">
            查看全部
          </Link>
        </header>

        <div
          className={styles.signalHeader}
        >
          <span>股票</span>
          <span>訊號</span>
          <span>ETF</span>
          <span>金額／共識</span>
        </div>

        <div
          className={styles.signalList}
        >
          {topSignals.map(
            (row, index) => {
              const code =
                codeOf(row);

              const amount =
                amountOf(row);

              const positive =
                isPositive(row);

              return (
                <Link
                  href={`/stock/${encodeURIComponent(
                    code,
                  )}`}
                  className={
                    styles.signalRow
                  }
                  key={`${code}-${index}`}
                >
                  <div
                    className={
                      styles.identity
                    }
                  >
                    <span>
                      {index + 1}
                    </span>

                    <div>
                      <strong>
                        {nameOf(row)}
                      </strong>
                      <small>
                        {code}
                      </small>
                    </div>
                  </div>

                  <span
                    className={
                      positive
                        ? styles.positiveBadge
                        : styles.negativeBadge
                    }
                  >
                    {statusOf(row)}
                  </span>

                  <strong
                    className={
                      styles.etfCount
                    }
                  >
                    {etfCountOf(row)}
                  </strong>

                  <div
                    className={
                      styles.signalValue
                    }
                  >
                    <strong
                      className={
                        positive
                          ? styles.positive
                          : styles.negative
                      }
                    >
                      {formatCompactAmount(
                        amount,
                      )}
                    </strong>

                    <small>
                      {buyCountOf(row)}:
                      {sellCountOf(row)}
                    </small>
                  </div>
                </Link>
              );
            },
          )}
        </div>
      </section>

      <section
        className={styles.card}
      >
        <header
          className={
            styles.sectionHeading
          }
        >
          <div>
            <span>
              ETF OPERATIONS
            </span>
            <h2>
              主動式 ETF 操作焦點
            </h2>
          </div>

          <Link href="/etfs">
            ETF 列表
          </Link>
        </header>

        <div
          className={
            styles.operationGrid
          }
        >
          <article
            className={
              styles.operationCard
            }
          >
            <header>
              <span
                className={
                  styles.addDot
                }
              />
              <strong>
                加碼金額 TOP 3
              </strong>
            </header>

            {operationFocus.add.map(
              (row, index) => (
                <Link
                  href={`/etf/${row.code}`}
                  key={row.code}
                >
                  <span>
                    {index + 1}
                  </span>

                  <div>
                    <strong>
                      {row.name}
                    </strong>
                    <small>
                      {row.code}・加碼{' '}
                      {row.addStocks} 檔
                    </small>
                  </div>

                  <b
                    className={
                      styles.positive
                    }
                  >
                    {formatCompactAmount(
                      row.addAmount,
                    )}
                  </b>
                </Link>
              ),
            )}
          </article>

          <article
            className={
              styles.operationCard
            }
          >
            <header>
              <span
                className={
                  styles.reduceDot
                }
              />
              <strong>
                減碼金額 TOP 3
              </strong>
            </header>

            {operationFocus.reduce.map(
              (row, index) => (
                <Link
                  href={`/etf/${row.code}`}
                  key={row.code}
                >
                  <span>
                    {index + 1}
                  </span>

                  <div>
                    <strong>
                      {row.name}
                    </strong>
                    <small>
                      {row.code}・減碼{' '}
                      {row.reduceStocks} 檔
                    </small>
                  </div>

                  <b
                    className={
                      styles.negative
                    }
                  >
                    -
                    {row.reduceAmount.toFixed(
                      row.reduceAmount >= 10
                        ? 1
                        : 2,
                    )}
                    億
                  </b>
                </Link>
              ),
            )}
          </article>
        </div>

        <p className={styles.dataNote}>
          操作金額以持股增減股數乘上當日股票價格估算。
        </p>
      </section>

      <section
        className={styles.card}
      >
        <header
          className={
            styles.sectionHeading
          }
        >
          <div>
            <span>WATCHLIST</span>
            <h2>自選股今日異動</h2>
          </div>

          <Link href="/watchlist">
            管理追蹤
          </Link>
        </header>

        {watchlistRows.length ? (
          <div
            className={
              styles.watchlist
            }
          >
            {watchlistRows.map(
              (item) => {
                const activeAmount =
                  item.active
                    ? amountOf(
                        item.active,
                      )
                    : 0;

                const referenceAmount =
                  item.reference
                    ? amountOf(
                        item.reference,
                      )
                    : 0;

                const totalAmount =
                  activeAmount +
                  referenceAmount;

                return (
                  <Link
                    href={`/stock/${item.code}`}
                    key={item.code}
                  >
                    <div>
                      <strong>
                        {item.name}
                      </strong>
                      <span>
                        {item.code}
                      </span>
                    </div>

                    <p>
                      {item.active
                        ? `主動式 ${statusOf(
                            item.active,
                          )} ${etfCountOf(
                            item.active,
                          )} 檔`
                        : '主動式無異動'}

                      {'・'}

                      {item.reference
                        ? `一般 ETF ${statusOf(
                            item.reference,
                          )} ${etfCountOf(
                            item.reference,
                          )} 檔`
                        : '一般 ETF 無異動'}
                    </p>

                    <b
                      className={
                        totalAmount > 0
                          ? styles.positive
                          : totalAmount < 0
                            ? styles.negative
                            : styles.neutral
                      }
                    >
                      {totalAmount
                        ? formatCompactAmount(
                            totalAmount,
                          )
                        : '無異動'}
                    </b>
                  </Link>
                );
              },
            )}
          </div>
        ) : (
          <div
            className={
              styles.emptyWatchlist
            }
          >
            <span>☆</span>

            <div>
              <strong>
                尚未追蹤股票
              </strong>

              <p>
                在個股頁點選星號，即可在首頁查看今日異動。
              </p>
            </div>

            <Link href="/search">
              搜尋個股
            </Link>
          </div>
        )}
      </section>
    </main>
  );
}
