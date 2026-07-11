'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import styles from './HomePageClient.module.css';

type Universe = 'active' | 'reference';

type SignalRow = {
  code?: string;
  name?: string;
  stock_code?: string;
  stock_name?: string;
  status?: string;
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
};

type SignalPayload = {
  data_date?: string;
  target_data_date?: string;
  fetched_etf_count?: number;
  total_etf_count?: number;
  signal_count?: number;
  rows?: SignalRow[];
};

function numberOf(value: unknown): number {
  const result = Number(value);
  return Number.isFinite(result) ? result : 0;
}

function rowsOf(payload: SignalPayload | null): SignalRow[] {
  return Array.isArray(payload?.rows) ? payload.rows : [];
}

function codeOf(row: SignalRow): string {
  return String(row.code || row.stock_code || '').trim();
}

function nameOf(row: SignalRow): string {
  return String(row.name || row.stock_name || codeOf(row)).trim();
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
    if (Number.isFinite(value)) return value;
  }

  return 0;
}

function lotsOf(row: SignalRow): number {
  const direct = Number(row.delta_shares_lots);
  if (Number.isFinite(direct)) return direct;

  return numberOf(row.delta_shares);
}

function etfCountOf(row: SignalRow): number {
  return numberOf(row.etf_count || row.etf_change_count);
}

function buyCountOf(row: SignalRow): number {
  return numberOf(row.buy_count || row.increase_count);
}

function sellCountOf(row: SignalRow): number {
  return numberOf(row.sell_count || row.decrease_count);
}

function statusOf(row: SignalRow): string {
  if (row.status) return String(row.status);
  return amountOf(row) >= 0 ? '加碼' : '減碼';
}

function dateText(value: unknown): string {
  const raw = String(value || '');
  const match = raw.match(/^\d{4}-(\d{2})-(\d{2})/);
  return match ? `${match[1]}/${match[2]}` : raw || '-';
}

function formatAmount(value: number): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(Math.abs(value) >= 100 ? 1 : 2)} 億`;
}

function formatLots(value: number): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${Math.round(value).toLocaleString('zh-TW')} 張`;
}

function completeness(payload: SignalPayload | null) {
  const fetched = numberOf(payload?.fetched_etf_count);
  const total = numberOf(payload?.total_etf_count);

  return {
    fetched,
    total,
    missing: Math.max(0, total - fetched),
  };
}

async function loadUniverse(
  universe: Universe,
  signal: AbortSignal,
): Promise<SignalPayload> {
  const versionResponse = await fetch(
    `/api/signals-version?days=1&universe=${universe}`,
    {
      cache: 'no-store',
      signal,
    },
  );

  const versionPayload = versionResponse.ok
    ? await versionResponse.json()
    : {};

  const version = String(versionPayload?.version || Date.now());

  const response = await fetch(
    `/api/signals?days=1&universe=${universe}&cv=${encodeURIComponent(version)}`,
    {
      cache: 'no-store',
      signal,
    },
  );

  if (!response.ok) {
    throw new Error(`${universe} signals api failed: ${response.status}`);
  }

  return response.json();
}

export default function HomePageClient() {
  const [activeData, setActiveData] = useState<SignalPayload | null>(null);
  const [referenceData, setReferenceData] =
    useState<SignalPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setLoading(true);
      setError('');

      const [activeResult, referenceResult] = await Promise.allSettled([
        loadUniverse('active', controller.signal),
        loadUniverse('reference', controller.signal),
      ]);

      if (controller.signal.aborted) return;

      if (activeResult.status === 'fulfilled') {
        setActiveData(activeResult.value);
      }

      if (referenceResult.status === 'fulfilled') {
        setReferenceData(referenceResult.value);
      }

      const failures = [activeResult, referenceResult].filter(
        (result) => result.status === 'rejected',
      );

      if (failures.length === 2) {
        setError('總覽資料暫時無法載入');
      } else if (failures.length === 1) {
        setError('部分資料暫時無法載入');
      }

      setLoading(false);
    }

    load().catch((reason) => {
      if (!controller.signal.aborted) {
        setError(String(reason?.message || reason));
        setLoading(false);
      }
    });

    return () => controller.abort();
  }, [reloadKey]);

  const activeRows = useMemo(() => rowsOf(activeData), [activeData]);

  const topSignals = useMemo(
    () =>
      [...activeRows]
        .filter((row) => codeOf(row))
        .sort((a, b) => Math.abs(amountOf(b)) - Math.abs(amountOf(a)))
        .slice(0, 5),
    [activeRows],
  );

  const inflows = useMemo(
    () =>
      [...activeRows]
        .filter((row) => amountOf(row) > 0)
        .sort((a, b) => amountOf(b) - amountOf(a))
        .slice(0, 3),
    [activeRows],
  );

  const outflows = useMemo(
    () =>
      [...activeRows]
        .filter((row) => amountOf(row) < 0)
        .sort((a, b) => amountOf(a) - amountOf(b))
        .slice(0, 3),
    [activeRows],
  );

  const activeCoverage = completeness(activeData);
  const referenceCoverage = completeness(referenceData);

  const totalFetched =
    activeCoverage.fetched + referenceCoverage.fetched;
  const totalEtfs = activeCoverage.total + referenceCoverage.total;
  const totalMissing = Math.max(0, totalEtfs - totalFetched);

  const dataDate =
    activeData?.data_date ||
    activeData?.target_data_date ||
    referenceData?.data_date ||
    referenceData?.target_data_date;

  return (
    <main className={styles.page}>
      <section className={styles.statusCard}>
        <div>
          <span className={styles.eyebrow}>市場資料</span>
          <h1>今日總覽</h1>
          <p>
            資料日 {dateText(dataDate)}
            {activeData
              ? `・主動式 ETF ${numberOf(activeData.signal_count)} 筆訊號`
              : ''}
          </p>
        </div>

        <div className={styles.statusRight}>
          <span
            className={`${styles.statusDot} ${
              !loading && totalMissing > 0 ? styles.statusPartial : ''
            }`}
          />
          <strong>
            {loading
              ? '更新中'
              : totalMissing > 0
                ? '部分完成'
                : '已完成'}
          </strong>
          <small>
            {loading
              ? '正在讀取資料'
              : totalMissing > 0
                ? `尚缺 ${totalMissing} 檔`
                : 'ETF 資料完整'}
          </small>
        </div>
      </section>

      {error ? (
        <div className={styles.notice}>
          <span>{error}</span>
          <button type="button" onClick={() => setReloadKey((key) => key + 1)}>
            重新載入
          </button>
        </div>
      ) : null}

      <section className={styles.summarySection}>
        <div className={styles.sectionHeading}>
          <div>
            <span>MARKET COVERAGE</span>
            <h2>今日市場摘要</h2>
          </div>
        </div>

        <div className={styles.summaryGrid}>
          <article className={styles.summaryCard}>
            <span>主動式 ETF</span>
            <strong>
              {activeCoverage.fetched}
              <small> / {activeCoverage.total || '-'}</small>
            </strong>
            <p>
              {activeCoverage.missing
                ? `${activeCoverage.missing} 檔尚無當日持股`
                : '資料完整'}
            </p>
          </article>

          <article className={styles.summaryCard}>
            <span>一般 ETF</span>
            <strong>
              {referenceCoverage.fetched}
              <small> / {referenceCoverage.total || '-'}</small>
            </strong>
            <p>
              {referenceCoverage.missing
                ? `${referenceCoverage.missing} 檔尚無當日持股`
                : '資料完整'}
            </p>
          </article>

          <article className={styles.summaryCard}>
            <span>全部追蹤</span>
            <strong>
              {totalFetched}
              <small> / {totalEtfs || '-'}</small>
            </strong>
            <p>
              {totalEtfs
                ? `${Math.round((totalFetched / totalEtfs) * 100)}% 已取得`
                : '載入中'}
            </p>
          </article>
        </div>
      </section>

      <section className={styles.sectionCard}>
        <div className={styles.sectionHeading}>
          <div>
            <span>ACTIVE ETF SIGNALS</span>
            <h2>今日訊號 TOP 5</h2>
          </div>

          <Link href="/signals">查看全部</Link>
        </div>

        {loading && topSignals.length === 0 ? (
          <div className={styles.skeletonList}>
            <div />
            <div />
            <div />
          </div>
        ) : (
          <div className={styles.signalList}>
            {topSignals.map((row, index) => {
              const code = codeOf(row);
              const amount = amountOf(row);
              const positive = amount >= 0;
              const buyCount = buyCountOf(row);
              const sellCount = sellCountOf(row);

              return (
                <Link
                  href={`/stock/${encodeURIComponent(code)}`}
                  className={styles.signalRow}
                  key={`${code}-${index}`}
                >
                  <span className={styles.rank}>{index + 1}</span>

                  <div className={styles.identity}>
                    <strong>{nameOf(row)}</strong>
                    <span>{code}</span>
                  </div>

                  <div className={styles.signalMeta}>
                    <span
                      className={
                        positive
                          ? styles.positiveBadge
                          : styles.negativeBadge
                      }
                    >
                      {statusOf(row)}
                    </span>
                    <small>{etfCountOf(row)} 檔 ETF</small>
                  </div>

                  <div className={styles.signalValue}>
                    <strong
                      className={
                        positive ? styles.positive : styles.negative
                      }
                    >
                      {formatAmount(amount)}
                    </strong>
                    <span>
                      {buyCount || sellCount
                        ? `${buyCount}:${sellCount}`
                        : row.consensus || row.buySellText || '-'}
                    </span>
                  </div>
                </Link>
              );
            })}

            {!loading && topSignals.length === 0 ? (
              <p className={styles.empty}>目前沒有可顯示的訊號。</p>
            ) : null}
          </div>
        )}
      </section>

      <section className={styles.flowSection}>
        <div className={styles.sectionHeading}>
          <div>
            <span>ACTIVE ETF FUND FLOW</span>
            <h2>主動式 ETF 資金流向</h2>
          </div>

          <Link href="/signals">深入分析</Link>
        </div>

        <div className={styles.flowGrid}>
          <article className={styles.flowCard}>
            <header>
              <div>
                <span className={styles.inflowDot} />
                <strong>淨流入 TOP 3</strong>
              </div>
              <small>億元</small>
            </header>

            <div className={styles.flowList}>
              {inflows.map((row) => {
                const code = codeOf(row);

                return (
                  <Link href={`/stock/${code}`} key={`in-${code}`}>
                    <div>
                      <strong>{nameOf(row)}</strong>
                      <span>
                        {code}・{formatLots(lotsOf(row))}
                      </span>
                    </div>
                    <b className={styles.positive}>
                      {formatAmount(amountOf(row))}
                    </b>
                  </Link>
                );
              })}
            </div>
          </article>

          <article className={styles.flowCard}>
            <header>
              <div>
                <span className={styles.outflowDot} />
                <strong>淨流出 TOP 3</strong>
              </div>
              <small>億元</small>
            </header>

            <div className={styles.flowList}>
              {outflows.map((row) => {
                const code = codeOf(row);

                return (
                  <Link href={`/stock/${code}`} key={`out-${code}`}>
                    <div>
                      <strong>{nameOf(row)}</strong>
                      <span>
                        {code}・{formatLots(lotsOf(row))}
                      </span>
                    </div>
                    <b className={styles.negative}>
                      {formatAmount(amountOf(row))}
                    </b>
                  </Link>
                );
              })}
            </div>
          </article>
        </div>
      </section>

      <section className={styles.nextSection}>
        <div>
          <span>WATCHLIST</span>
          <strong>掌握自選股重要異動</strong>
          <p>追蹤關注股票，集中查看 ETF 加減碼與籌碼變化。</p>
        </div>
        <Link href="/watchlist">前往追蹤</Link>
      </section>
    </main>
  );
}
