'use client';

import {
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

type TradingRow = {
  security_code: string;
  security_name: string | null;
  trade_date: string;
  market: string;

  foreign_net: number;
  trust_net: number;

  dealer_self_net: number;
  dealer_hedge_net: number;
  dealer_net: number;

  institutional_net: number;
};

type TradingTotals = {
  foreign_net: number;
  trust_net: number;

  dealer_self_net: number;
  dealer_hedge_net: number;
  dealer_net: number;

  institutional_net: number;
};

type PeriodSummary = {
  trading_days: number;
  start_date: string | null;
  end_date: string | null;
  totals: TradingTotals;
};

type TradingPayload = {
  code: string;
  found: boolean;
  security_name: string | null;
  market: string;

  latest: TradingRow | null;
  recent_5_days: PeriodSummary | null;
  recent_20_days: PeriodSummary | null;

  available_days: number;
  history: TradingRow[];
  unit: string;
};

type MetricKey =
  | 'institutional_net'
  | 'foreign_net'
  | 'trust_net'
  | 'dealer_net';

type LoadState =
  | {
      status: 'loading';
    }
  | {
      status: 'ready';
      data: TradingPayload;
    }
  | {
      status: 'empty';
    }
  | {
      status: 'error';
      message: string;
    };

const METRICS: Array<{
  key: MetricKey;
  label: string;
}> = [
  {
    key: 'institutional_net',
    label: '合計',
  },
  {
    key: 'foreign_net',
    label: '外資',
  },
  {
    key: 'trust_net',
    label: '投信',
  },
  {
    key: 'dealer_net',
    label: '自營商',
  },
];

function numberOf(value: unknown): number {
  const result = Number(value);
  return Number.isFinite(result) ? result : 0;
}

function toLots(value: unknown): number {
  return numberOf(value) / 1000;
}

function formatLots(value: unknown): string {
  const lots = toLots(value);

  if (!Number.isFinite(lots)) {
    return '-';
  }

  const rounded = Math.round(lots);
  const sign = rounded > 0 ? '+' : '';

  return `${sign}${rounded.toLocaleString('zh-TW')}`;
}

function formatAxis(value: unknown): string {
  const result = numberOf(value);
  const absolute = Math.abs(result);

  if (absolute >= 100000) {
    return `${(result / 10000).toFixed(0)}萬`;
  }

  if (absolute >= 10000) {
    return `${(result / 10000).toFixed(1)}萬`;
  }

  if (absolute >= 1000) {
    return `${(result / 1000).toFixed(1)}千`;
  }

  return Math.round(result).toLocaleString('zh-TW');
}

function dateLabel(value: string): string {
  const match = String(value || '').match(
    /^(\d{4})-(\d{2})-(\d{2})/
  );

  if (!match) {
    return value;
  }

  return `${match[2]}/${match[3]}`;
}

function fullDateLabel(value: string): string {
  const match = String(value || '').match(
    /^(\d{4})-(\d{2})-(\d{2})/
  );

  if (!match) {
    return value;
  }

  return `${match[1]}/${match[2]}/${match[3]}`;
}

function toneClass(value: unknown): string {
  const result = numberOf(value);

  if (result > 0) {
    return 'is-positive';
  }

  if (result < 0) {
    return 'is-negative';
  }

  return 'is-neutral';
}

function TrendTooltip({
  active,
  payload,
  label,
}: any) {
  if (!active || !payload?.length) {
    return null;
  }

  const value = numberOf(payload[0]?.value);

  return (
    <div className="v141-tooltip">
      <b>{fullDateLabel(String(label || ''))}</b>
      <span className={toneClass(value)}>
        {value > 0 ? '+' : ''}
        {Math.round(value).toLocaleString('zh-TW')} 張
      </span>
    </div>
  );
}

function TradingCell({
  value,
}: {
  value: unknown;
}) {
  return (
    <td className={toneClass(value)}>
      {formatLots(value)}
    </td>
  );
}

function PeriodRow({
  label,
  values,
}: {
  label: string;
  values: TradingTotals | TradingRow;
}) {
  return (
    <tr>
      <th scope="row">{label}</th>

      <TradingCell value={values.foreign_net} />
      <TradingCell value={values.trust_net} />
      <TradingCell value={values.dealer_net} />
      <TradingCell value={values.institutional_net} />
    </tr>
  );
}

function SummaryGridCell({
  value,
}: {
  value: unknown;
}) {
  return (
    <div
      role="cell"
      className={toneClass(value)}
    >
      {formatLots(value)}
    </div>
  );
}

function SummaryGridRow({
  label,
  values,
}: {
  label: string;
  values: TradingTotals | TradingRow;
}) {
  return (
    <div
      role="row"
      className="v141-summary-grid-row"
    >
      <div role="rowheader">{label}</div>
      <SummaryGridCell value={values.foreign_net} />
      <SummaryGridCell value={values.trust_net} />
      <SummaryGridCell value={values.dealer_net} />
      <SummaryGridCell value={values.institutional_net} />
    </div>
  );
}


function DealerBreakdownRow({
  label,
  values,
}: {
  label: string;
  values: TradingTotals | TradingRow;
}) {
  return (
    <tr>
      <th scope="row">{label}</th>

      <TradingCell value={values.dealer_self_net} />
      <TradingCell value={values.dealer_hedge_net} />
      <TradingCell value={values.dealer_net} />
    </tr>
  );
}

export default function InstitutionalTradingCard({
  code,
  isEtf = false,
}: {
  code: string;
  isEtf?: boolean;
}) {
  const [reloadKey, setReloadKey] = useState(0);
  const [metric, setMetric] =
    useState<MetricKey>('institutional_net');

  const [state, setState] = useState<LoadState>({
    status: 'loading',
  });

  useEffect(() => {
    const normalizedCode = String(code || '')
      .trim()
      .toUpperCase();

    if (!normalizedCode) {
      setState({
        status: 'empty',
      });
      return;
    }

    const controller = new AbortController();
    let active = true;

    const timeout = window.setTimeout(() => {
      controller.abort();
    }, 20000);

    async function load() {
      setState({
        status: 'loading',
      });

      try {
        const response = await fetch(
          `/api/institutional-trading?code=${encodeURIComponent(
            normalizedCode
          )}`,
          {
            cache: 'no-store',
            signal: controller.signal,
          }
        );

        const payload = await response
          .json()
          .catch(() => null);

        if (!active) {
          return;
        }

        if (
          response.status === 404 ||
          payload?.found === false ||
          !payload?.latest
        ) {
          setState({
            status: 'empty',
          });
          return;
        }

        if (!response.ok) {
          throw new Error(
            payload?.message ||
              `三大法人 API 回傳 HTTP ${response.status}`
          );
        }

        setState({
          status: 'ready',
          data: payload as TradingPayload,
        });
      } catch (error: any) {
        if (!active) {
          return;
        }

        setState({
          status: 'error',
          message:
            error?.name === 'AbortError'
              ? '三大法人資料載入逾時'
              : String(
                  error?.message ||
                    '三大法人資料載入失敗'
                ),
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

  const chartRows = useMemo(() => {
    if (state.status !== 'ready') {
      return [];
    }

    return state.data.history
      .slice(-20)
      .map((row) => ({
        date: row.trade_date,
        value: toLots(row[metric]),
      }));
  }, [state, metric]);

  if (state.status === 'loading') {
    return (
      <section
        className="v141-card is-loading"
        aria-busy="true"
      >
        <div className="v141-heading">
          <div>
            <h2>三大法人</h2>
            <span>資料載入中</span>
          </div>
        </div>

        <div className="v141-loading-block" />
        <div className="v141-loading-chart" />
      </section>
    );
  }

  if (state.status === 'error') {
    return (
      <section className="v141-card">
        <div className="v141-heading">
          <div>
            <h2>三大法人</h2>
          </div>
        </div>

        <div
          className="v141-message"
          role="alert"
        >
          <b>三大法人資料載入失敗</b>
          <span>{state.message}</span>

          <button
            type="button"
            onClick={() => {
              setReloadKey((value) => value + 1);
            }}
          >
            重新載入
          </button>
        </div>
      </section>
    );
  }

  if (state.status === 'empty') {
    return (
      <section className="v141-card">
        <div className="v141-heading">
          <div>
            <h2>三大法人</h2>
          </div>
        </div>

        <div className="v141-message">
          目前沒有三大法人資料
        </div>
      </section>
    );
  }

  const data = state.data;
  const latest = data.latest;
  const recent5 = data.recent_5_days;
  const recent20 = data.recent_20_days;

  if (!latest || !recent5 || !recent20) {
    return null;
  }

  const selectedMetric =
    METRICS.find((item) => item.key === metric) ||
    METRICS[0];

  return (
    <section className="v141-card">
      <div className="v141-heading">
        <div>
          <h2>三大法人</h2>

          <span>
            單位：張・正數買超、負數賣超
          </span>
        </div>

        <div className="v141-heading-meta">
          <time dateTime={latest.trade_date}>
            {fullDateLabel(latest.trade_date)}
          </time>

          <small>
            {data.available_days} 個交易日
          </small>
        </div>
      </div>

      <div
        className="v141-summary-grid"
        role="table"
        aria-label="三大法人買賣超摘要"
      >
        <div
          className="v141-summary-grid-row is-header"
          role="row"
        >
          <div role="columnheader">期間</div>
          <div role="columnheader">外資</div>
          <div role="columnheader">投信</div>
          <div role="columnheader">自營商</div>
          <div role="columnheader">合計</div>
        </div>

        <SummaryGridRow
          label="當日"
          values={latest}
        />

        <SummaryGridRow
          label="近 5 日"
          values={recent5.totals}
        />

        <SummaryGridRow
          label="近 20 日"
          values={recent20.totals}
        />
      </div>

      {isEtf ? (
        <details className="v141-dealer-details">
          <summary>ETF 自營商分拆</summary>

          <p>
            ETF 的避險與造市交易可能較大，應與自行買賣分開觀察。
          </p>

          <div className="v141-table-wrap">
            <table className="v141-dealer-table">
              <thead>
                <tr>
                  <th scope="col">期間</th>
                  <th scope="col">自行買賣</th>
                  <th scope="col">避險</th>
                  <th scope="col">合計</th>
                </tr>
              </thead>

              <tbody>
                <DealerBreakdownRow
                  label="當日"
                  values={latest}
                />

                <DealerBreakdownRow
                  label="近 5 日"
                  values={recent5.totals}
                />

                <DealerBreakdownRow
                  label="近 20 日"
                  values={recent20.totals}
                />
              </tbody>
            </table>
          </div>
        </details>
      ) : null}

      <div className="v141-chart-heading">
        <div>
          <h3>最近 20 日買賣超</h3>

          <span>
            目前顯示：{selectedMetric.label}
          </span>
        </div>

        <div
          className="v141-tabs"
          role="group"
          aria-label="選擇法人趨勢"
        >
          {METRICS.map((item) => (
            <button
              key={item.key}
              type="button"
              aria-pressed={metric === item.key}
              className={
                metric === item.key
                  ? 'is-active'
                  : ''
              }
              onClick={() => {
                setMetric(item.key);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="v141-chart">
        <ResponsiveContainer
          width="100%"
          height={250}
        >
          <BarChart
            data={chartRows}
            margin={{
              top: 12,
              right: 8,
              bottom: 0,
              left: 0,
            }}
          >
            <CartesianGrid
              vertical={false}
              strokeDasharray="3 3"
            />

            <XAxis
              dataKey="date"
              tickFormatter={dateLabel}
              tick={{
                fontSize: 11,
              }}
              minTickGap={20}
            />

            <YAxis
              width={55}
              tickFormatter={formatAxis}
              tick={{
                fontSize: 11,
              }}
            />

            <Tooltip
              cursor={{
                fill: 'rgba(15, 23, 42, 0.04)',
              }}
              content={<TrendTooltip />}
            />

            <ReferenceLine
              y={0}
              stroke="rgba(15, 23, 42, 0.35)"
            />

            <Bar
              dataKey="value"
              maxBarSize={22}
              radius={[4, 4, 4, 4]}
            >
              {chartRows.map((row) => (
                <Cell
                  key={`${row.date}-${metric}`}
                  fill={
                    row.value >= 0
                      ? '#d9485f'
                      : '#18865f'
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="v141-footnote">
        三大法人資料代表每日淨買賣超，不等同於目前持股水位。
      </div>
    </section>
  );
}
