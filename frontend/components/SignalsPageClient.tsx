'use client';

import { useEffect, useState } from 'react';
import SignalsClient from '@/components/SignalsClient';

type SignalUniverse = 'active' | 'reference' | 'all';

type Props = {
  activeDays: number;
};

const UNIVERSE_OPTIONS: { key: SignalUniverse; label: string; hint: string }[] = [
  { key: 'active', label: '主動式 ETF', hint: '只看主動式 ETF 訊號' },
  { key: 'reference', label: '一般 ETF', hint: '只看 0050、0056、00878 等參考 ETF' },
  { key: 'all', label: '全部 ETF', hint: '主動式 ETF + 一般 ETF' },
];

export default function SignalsPageClient({ activeDays }: Props) {
  const [universe, setUniverse] = useState<SignalUniverse>('active');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string>('');

  useEffect(() => {
    const ctrl = new AbortController();

    async function load() {
      setLoading(true);
      setErr('');

      try {
        const versionRes = await fetch(`/api/signals-version?days=${activeDays}&universe=${universe}`, {
          signal: ctrl.signal,
          cache: 'no-store',
        });

        const versionJson = versionRes.ok ? await versionRes.json() : {};
        const version = String(versionJson?.version || Date.now());

        const res = await fetch(
          `/api/signals?days=${activeDays}&universe=${universe}&fresh=1&cv=${encodeURIComponent(version)}`,
          {
            signal: ctrl.signal,
            cache: 'no-store',
          }
        );

        if (!res.ok) throw new Error(`signals api failed: ${res.status}`);

        const json = await res.json();
        setData(json);
      } catch (e: any) {
        if (e?.name !== 'AbortError') {
          console.error(e);
          setErr(String(e?.message || e));
        }
      } finally {
        if (!ctrl.signal.aborted) setLoading(false);
      }
    }

    load();

    return () => ctrl.abort();
  }, [activeDays, universe]);

  const currentOption = UNIVERSE_OPTIONS.find((x) => x.key === universe) || UNIVERSE_OPTIONS[0];

  if (loading && !data) {
    return (
      <main className="page">
        <div className="v89-etf-type-filter" style={{ marginBottom: 12 }}>
          {UNIVERSE_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              type="button"
              className={opt.key === universe ? 'chip active' : 'chip'}
              onClick={() => setUniverse(opt.key)}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <p className="muted">{currentOption.hint}</p>
        <div className="skeleton-card" />
        <div className="skeleton-card" />
        <div className="skeleton-card" />
        <p className="muted">今日訊號資料載入中...</p>
      </main>
    );
  }

  if (err && !data) {
    return (
      <main className="page">
        <div className="v89-etf-type-filter" style={{ marginBottom: 12 }}>
          {UNIVERSE_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              type="button"
              className={opt.key === universe ? 'chip active' : 'chip'}
              onClick={() => setUniverse(opt.key)}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <p className="muted">今日訊號載入失敗：{err}</p>
      </main>
    );
  }

  return (
    <>
      <main className="page" style={{ paddingBottom: 0 }}>
        <div className="v89-etf-type-filter" style={{ marginBottom: 12 }}>
          {UNIVERSE_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              type="button"
              className={opt.key === universe ? 'chip active' : 'chip'}
              onClick={() => setUniverse(opt.key)}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <p className="muted" style={{ marginTop: 0 }}>
          {currentOption.hint}
          {data?.total_etf_count ? `｜ETF ${data.fetched_etf_count ?? data.today_etf_count ?? 0}/${data.total_etf_count} 檔｜訊號 ${data.signal_count ?? data.rows?.length ?? 0} 筆` : ''}
        </p>
      </main>

      <SignalsClient data={data} activeDays={activeDays} />
    </>
  );
}
