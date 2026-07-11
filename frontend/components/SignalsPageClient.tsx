'use client';

import { useEffect, useState } from 'react';
import SignalsClient from '@/components/SignalsClient';
import styles from './SignalsPagePolish.module.css';

type Props = {
  activeDays: number;
};

type SignalPayload = Record<string, any>;

function statusDate(value: unknown): string {
  const raw = String(value || '');

  const match = raw.match(
    /^\d{4}-(\d{2})-(\d{2})/
  );

  return match
    ? `${match[1]}/${match[2]}`
    : '-';
}

function statusUpdate(value: unknown): string {
  const date = new Date(
    String(value || '')
  );

  if (!Number.isFinite(date.getTime())) {
    return '-';
  }

  return new Intl.DateTimeFormat(
    'zh-TW',
    {
      timeZone: 'Asia/Taipei',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }
  )
    .format(date)
    .replace(',', '');
}

async function loadUniverse(
  universe: 'active' | 'reference',
  activeDays: number,
  signal: AbortSignal
): Promise<SignalPayload> {
  const versionRes = await fetch(
    `/api/signals-version?days=${activeDays}&universe=${universe}`,
    {
      signal,
      cache: 'no-store',
    }
  );

  const versionJson =
    versionRes.ok
      ? await versionRes.json()
      : {};

  const version = String(
    versionJson?.version ||
      Date.now()
  );

  const response = await fetch(
    `/api/signals?days=${activeDays}&universe=${universe}&cv=${encodeURIComponent(
      version
    )}`,
    {
      signal,
      cache: 'no-store',
    }
  );

  if (!response.ok) {
    throw new Error(
      `${universe} signals api failed: ${response.status}`
    );
  }

  const payload = await response.json();

  return {
    ...payload,
    data_date:
      payload?.data_date ||
      versionJson?.data_date,
    updated_at:
      versionJson?.updated_at ||
      payload?.updated_at,
  };
}

export default function SignalsPageClient({
  activeDays,
}: Props) {
  const [data, setData] =
    useState<SignalPayload | null>(null);

  const [
    referenceData,
    setReferenceData,
  ] =
    useState<SignalPayload | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [err, setErr] =
    useState('');

  useEffect(() => {
    const ctrl =
      new AbortController();

    async function load() {
      setLoading(true);
      setErr('');

      try {
        const activePayload =
          await loadUniverse(
            'active',
            activeDays,
            ctrl.signal
          );

        if (ctrl.signal.aborted) {
          return;
        }

        setData(activePayload);

        try {
          const referencePayload =
            await loadUniverse(
              'reference',
              activeDays,
              ctrl.signal
            );

          if (!ctrl.signal.aborted) {
            setReferenceData(
              referencePayload
            );
          }
        } catch (referenceError: any) {
          if (
            referenceError?.name !==
            'AbortError'
          ) {
            console.error(
              referenceError
            );
          }
        }
      } catch (error: any) {
        if (
          error?.name !== 'AbortError'
        ) {
          console.error(error);

          setErr(
            String(
              error?.message ||
                error
            )
          );
        }
      } finally {
        if (!ctrl.signal.aborted) {
          setLoading(false);
        }
      }
    }

    load();

    return () => ctrl.abort();
  }, [activeDays]);

  if (loading && !data) {
    return (
      <div className={styles.shell}>
        <main className="page">
          <div className="skeleton-card" />
          <div className="skeleton-card" />
          <div className="skeleton-card" />

          <p className="muted">
            今日訊號資料載入中...
          </p>
        </main>
      </div>
    );
  }

  if (err && !data) {
    return (
      <div className={styles.shell}>
        <main className="page">
          <p className="muted">
            今日訊號載入失敗：{err}
          </p>
        </main>
      </div>
    );
  }

  const activeFetched = Number(
    data?.fetched_etf_count ??
      data?.today_etf_count ??
      0
  );

  const activeTotal = Number(
    data?.total_etf_count ?? 0
  );

  const referenceFetched = Number(
    referenceData?.fetched_etf_count ??
      referenceData?.today_etf_count ??
      0
  );

  const referenceTotal = Number(
    referenceData?.total_etf_count ??
      0
  );

  const activeMissing = Math.max(
    0,
    activeTotal - activeFetched
  );

  const allFetched =
    activeFetched + referenceFetched;

  const allTotal =
    activeTotal + referenceTotal;

  return (
    <div className={styles.shell}>
      <div className={styles.statusWrap}>
        <section
          className={styles.statusRow}
        >
          <div>
            <span>資料日</span>

            <strong>
              {statusDate(
                data?.data_date
              )}
            </strong>
          </div>

          <div>
            <span>更新</span>

            <strong>
              {statusUpdate(
                data?.updated_at
              )}
            </strong>
          </div>

          <div
            className={
              activeMissing > 0
                ? styles.partialStatus
                : styles.completeStatus
            }
          >
            <i />

            <strong>
              {activeMissing > 0
                ? `部分完成・尚缺 ${activeMissing} 檔`
                : '資料完整'}
            </strong>
          </div>
        </section>
      </div>

      <SignalsClient
        data={data}
        activeDays={activeDays}
        universeLabel="主動式 ETF"
        coverage={{
          activeFetched,
          activeTotal,
          referenceFetched,
          referenceTotal,
          allFetched,
          allTotal,
        }}
      />
    </div>
  );
}
