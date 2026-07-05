'use client';

import {
  useEffect,
  useId,
  useMemo,
  useState,
} from 'react';

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

type HolderSummary = {
  security_code: string;
  data_date: string;
  retail_ratio: number;
  major_ratio: number;
  thousand_holder_count: number;
  thousand_holder_ratio: number;
  total_holder_count: number;
  total_shares: number;
  source: string;
  updated_at: string | null;
};

type HolderChange = {
  retail_ratio: number;
  major_ratio: number;
  thousand_holder_count: number;
  thousand_holder_ratio: number;
};

type HolderPayload = {
  code: string;
  found: boolean;
  latest: HolderSummary | null;
  comparison: HolderSummary | null;
  four_week_change: HolderChange | null;
  trend_ready: boolean;
  history: HolderSummary[];
  source?: string;
};

type LoadState =
  | { status: 'loading' }
  | { status: 'ready'; data: HolderPayload }
  | { status: 'empty' }
  | { status: 'error'; message: string };

function formatPercent(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return '-';

  return `${value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}%`;
}

function formatSigned(
  value: number,
  suffix = '',
  digits = 1
): string {
  if (!Number.isFinite(value)) return '-';

  const sign = value > 0 ? '+' : '';

  return `${sign}${value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}${suffix}`;
}

function formatDate(value: string): string {
  const match = String(value || '').match(
    /^(\d{4})-(\d{2})-(\d{2})/
  );

  return match ? `${match[1]}/${match[2]}/${match[3]}` : value;
}

function formatWeekDate(value: string): string {
  const match = String(value || '').match(
    /^(\d{4})-(\d{2})-(\d{2})/
  );

  return match ? `${match[2]}/${match[3]}` : value;
}

function chartTick(value: unknown): string {
  const result = Number(value);

  if (!Number.isFinite(result)) return '0';

  const sign = result > 0 ? '+' : '';

  return `${sign}${result.toFixed(1)}`;
}

export default function HolderChipCard({
  code,
}: {
  code: string;
}) {
  const titleId = useId();
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<LoadState>({
    status: 'loading',
  });

  useEffect(() => {
    const normalizedCode = String(code || '')
      .trim()
      .toUpperCase();

    if (!normalizedCode) {
      setState({ status: 'empty' });
      return;
    }

    const controller = new AbortController();
    let active = true;

    const timeout = window.setTimeout(() => {
      controller.abort();
    }, 20000);

    async function load() {
      setState({ status: 'loading' });

      try {
        const response = await fetch(
          `/api/holder-chips?code=${encodeURIComponent(
            normalizedCode
          )}`,
          {
            cache: 'no-store',
            signal: controller.signal,
          }
        );

        const payload = await response.json().catch(() => null);

        if (!active) return;

        if (
          response.status === 404 ||
          payload?.found === false ||
          !payload?.latest
        ) {
          setState({ status: 'empty' });
          return;
        }

        if (!response.ok) {
          throw new Error(
            payload?.message ||
              `大戶籌碼 API 回傳 HTTP ${response.status}`
          );
        }

        setState({
          status: 'ready',
          data: payload as HolderPayload,
        });
      } catch (error: any) {
        if (!active) return;

        setState({
          status: 'error',
          message:
            error?.name === 'AbortError'
              ? '大戶籌碼載入逾時'
              : String(error?.message || '大戶籌碼載入失敗'),
        });
      } finally {
        window.clearTimeout(timeout);
      }
    }

    load();

    return () => {
      active = false;
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [code, reloadKey]);

  const trendRows = useMemo(() => {
    if (state.status !== 'ready') {
      return [];
    }

    const history = Array.isArray(state.data.history)
      ? state.data.history.slice(-5)
      : [];

    if (!history.length) {
      return [];
    }

    const baseline = history[0];

    const baselineLargeRatio =
      baseline.major_ratio +
      baseline.thousand_holder_ratio;

    return history.map((row) => {
      const largeRatio =
        row.major_ratio +
        row.thousand_holder_ratio;

      return {
        date: row.data_date,
        large_ratio: largeRatio,
        retail_ratio: row.retail_ratio,
        large_change:
          largeRatio - baselineLargeRatio,
        retail_change:
          row.retail_ratio -
          baseline.retail_ratio,
        thousand_holder_count:
          row.thousand_holder_count,
      };
    });
  }, [state]);

  if (state.status === 'loading') {
    return (
      <section
        className="v140-holder-card is-loading"
        aria-busy="true"
        aria-labelledby={titleId}
      >
        <div className="v140-holder-title-row">
          <h2 id={titleId}>大戶籌碼</h2>
          <span className="v140-holder-skeleton short" />
        </div>

        <div className="v140-holder-grid">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index}>
              <span className="v140-holder-skeleton label" />
              <span className="v140-holder-skeleton value" />
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (state.status === 'error') {
    return (
      <section
        className="v140-holder-card is-error"
        aria-labelledby={titleId}
      >
        <h2 id={titleId}>大戶籌碼</h2>

        <div role="alert" className="v140-holder-message">
          <b>大戶籌碼載入失敗</b>
          <span>{state.message}</span>

          <button
            type="button"
            onClick={() => setReloadKey((value) => value + 1)}
          >
            重新載入
          </button>
        </div>
      </section>
    );
  }

  if (state.status === 'empty') {
    return (
      <section
        className="v140-holder-card"
        aria-labelledby={titleId}
      >
        <h2 id={titleId}>大戶籌碼</h2>

        <div className="v140-holder-message">
          目前沒有 TDCC 集保持股分布資料
        </div>
      </section>
    );
  }

  const { latest, trend_ready } = state.data;

  if (!latest) return null;

  const firstTrend = trendRows[0];
  const lastTrend =
    trendRows[trendRows.length - 1];

  const largeChange =
    lastTrend?.large_change || 0;

  const retailChange =
    lastTrend?.retail_change || 0;

  const holderCountChange =
    firstTrend && lastTrend
      ? lastTrend.thousand_holder_count -
        firstTrend.thousand_holder_count
      : 0;

  const concentrationStatus =
    largeChange >= 0.2 &&
    retailChange <= -0.1
      ? {
          label: '籌碼集中',
          className: 'is-concentrating',
        }
      : largeChange <= -0.2 &&
          retailChange >= 0.1
        ? {
            label: '籌碼分散',
            className: 'is-dispersing',
          }
        : Math.abs(largeChange) < 0.2 &&
            Math.abs(retailChange) < 0.2
          ? {
              label: '籌碼大致持平',
              className: 'is-mixed',
            }
          : {
              label: '籌碼變化分歧',
              className: 'is-mixed',
            };

  return (
    <section
      className="v140-holder-card"
      aria-labelledby={titleId}
    >
      <div className="v140-holder-title-row">
        <div>
          <h2 id={titleId}>大戶籌碼</h2>
          <span>
            TDCC 集保戶股權分散表・每週更新
          </span>
        </div>

        <time dateTime={latest.data_date}>
          {formatDate(latest.data_date)}
        </time>
      </div>

      <div className="v140-holder-grid">
        <div>
          <span>散戶持股</span>
          <b>{formatPercent(latest.retail_ratio)}</b>
          <small>5 張以下</small>
        </div>

        <div>
          <span>主力持股</span>
          <b>{formatPercent(latest.major_ratio)}</b>
          <small>400～1000 張</small>
        </div>

        <div>
          <span>千張大戶</span>
          <b>
            {latest.thousand_holder_count.toLocaleString()}
          </b>
          <small>人</small>
        </div>

        <div>
          <span>千張以上持股</span>
          <b>
            {formatPercent(
              latest.thousand_holder_ratio
            )}
          </b>
          <small>占集保庫存</small>
        </div>
      </div>

      {trend_ready && trendRows.length >= 5 ? (
        <div className="v140-concentration">
          <div className="v140-concentration-heading">
            <div>
              <h3>近 5 週籌碼集中趨勢</h3>
              <span>
                以最早一週為基準，單位為百分點
              </span>
            </div>

            <b
              className={
                concentrationStatus.className
              }
            >
              {concentrationStatus.label}
            </b>
          </div>

          <div className="v140-concentration-chart">
            <ResponsiveContainer
              width="100%"
              height={190}
            >
              <LineChart
                data={trendRows}
                margin={{
                  top: 12,
                  right: 20,
                  bottom: 0,
                  left: -12,
                }}
              >
                <CartesianGrid
                  vertical={false}
                  strokeDasharray="3 3"
                />

                <XAxis
                  dataKey="date"
                  tickFormatter={formatWeekDate}
                  interval={0}
                  tick={{
                    fontSize: 10,
                  }}
                />

                <YAxis
                  tickFormatter={chartTick}
                  tick={{
                    fontSize: 10,
                  }}
                />

                <ReferenceLine
                  y={0}
                  stroke="rgba(15, 23, 42, 0.35)"
                />

                <Tooltip
                  labelFormatter={(label) =>
                    formatDate(String(label || ''))
                  }
                  formatter={(
                    value: any,
                    name: any
                  ) => [
                    formatSigned(
                      Number(value),
                      ' 個百分點',
                      2
                    ),
                    name === 'large_change'
                      ? '大額持股'
                      : '散戶持股',
                  ]}
                />

                <Line
                  type="monotone"
                  dataKey="large_change"
                  stroke="#d9485f"
                  strokeWidth={2.5}
                  dot={{
                    r: 3,
                  }}
                  activeDot={{
                    r: 5,
                  }}
                  isAnimationActive={false}
                />

                <Line
                  type="monotone"
                  dataKey="retail_change"
                  stroke="#18865f"
                  strokeWidth={2.5}
                  dot={{
                    r: 3,
                  }}
                  activeDot={{
                    r: 5,
                  }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="v140-concentration-legend">
            <span className="large">
              大額持股
            </span>

            <span className="retail">
              散戶持股
            </span>
          </div>

          <div className="v140-holder-trend">
            <div>
              <span>近 4 週大額持股</span>
              <b
                className={
                  largeChange >= 0
                    ? 'up'
                    : 'down'
                }
              >
                {formatSigned(
                  largeChange,
                  ' 個百分點',
                  2
                )}
              </b>
            </div>

            <div>
              <span>近 4 週散戶持股</span>
              <b
                className={
                  retailChange <= 0
                    ? 'up'
                    : 'down'
                }
              >
                {formatSigned(
                  retailChange,
                  ' 個百分點',
                  2
                )}
              </b>
            </div>

            <div>
              <span>近 4 週千張大戶</span>
              <b
                className={
                  holderCountChange >= 0
                    ? 'up'
                    : 'down'
                }
              >
                {formatSigned(
                  holderCountChange,
                  ' 人',
                  0
                )}
              </b>
            </div>
          </div>

          <div className="v140-holder-count-heading">
            <div>
              <h3>千張大戶人數</h3>
              <span>最近 5 週</span>
            </div>

            <b>
              {latest.thousand_holder_count.toLocaleString()}
              <small> 人</small>
            </b>
          </div>

          <div className="v140-holder-count-chart">
            <ResponsiveContainer
              width="100%"
              height={105}
            >
              <LineChart
                data={trendRows}
                margin={{
                  top: 8,
                  right: 20,
                  bottom: 0,
                  left: -12,
                }}
              >
                <CartesianGrid
                  vertical={false}
                  strokeDasharray="3 3"
                />

                <XAxis
                  dataKey="date"
                  tickFormatter={formatWeekDate}
                  interval={0}
                  tick={{
                    fontSize: 10,
                  }}
                />

                <YAxis
                  domain={['dataMin - 2', 'dataMax + 2']}
                  tick={{
                    fontSize: 10,
                  }}
                />

                <Tooltip
                  labelFormatter={(label) =>
                    formatDate(String(label || ''))
                  }
                  formatter={(value: any) => [
                    `${Math.round(
                      Number(value)
                    ).toLocaleString()} 人`,
                    '千張大戶',
                  ]}
                />

                <Line
                  type="monotone"
                  dataKey="thousand_holder_count"
                  stroke="#2563eb"
                  strokeWidth={2.5}
                  dot={{
                    r: 3,
                  }}
                  activeDot={{
                    r: 5,
                  }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="v140-holder-pending">
          近 5 週趨勢資料累積中
        </div>
      )}

      <details className="v140-holder-details">
        <summary>指標說明</summary>

        <ul>
          <li>散戶持股：TDCC 持股分級 1～2，合計 5 張以下。</li>
          <li>主力持股：TDCC 持股分級 12～14，合計 400～1000 張。</li>
          <li>千張大戶：TDCC 持股分級 15，持有超過 1000 張的人數。</li>
          <li>資料為集保歸戶統計，不代表特定法人或實際買賣意圖。</li>
        </ul>
      </details>
    </section>
  );
}
