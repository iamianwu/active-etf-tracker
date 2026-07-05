'use client';

import { useEffect, useId, useState } from 'react';

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

  const { latest, four_week_change, trend_ready } =
    state.data;

  if (!latest) return null;

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

      {trend_ready && four_week_change ? (
        <div className="v140-holder-trend">
          <div>
            <span>近 4 週千張大戶</span>
            <b
              className={
                four_week_change.thousand_holder_count >= 0
                  ? 'up'
                  : 'down'
              }
            >
              {formatSigned(
                four_week_change.thousand_holder_count,
                ' 人',
                0
              )}
            </b>
          </div>

          <div>
            <span>主力持股變化</span>
            <b
              className={
                four_week_change.major_ratio >= 0
                  ? 'up'
                  : 'down'
              }
            >
              {formatSigned(
                four_week_change.major_ratio,
                ' 個百分點'
              )}
            </b>
          </div>

          <div>
            <span>散戶持股變化</span>
            <b
              className={
                four_week_change.retail_ratio <= 0
                  ? 'up'
                  : 'down'
              }
            >
              {formatSigned(
                four_week_change.retail_ratio,
                ' 個百分點'
              )}
            </b>
          </div>
        </div>
      ) : (
        <div className="v140-holder-pending">
          近 4 週趨勢資料累積中
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
