'use client';

import { useEffect, useState } from 'react';
import SignalsClient from '@/components/SignalsClient';

type Props = {
  activeDays: number;
};

export default function SignalsPageClient({ activeDays }: Props) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string>('');

  useEffect(() => {
    const ctrl = new AbortController();

    async function load() {
      setLoading(true);
      setErr('');

      try {
        const versionRes = await fetch(`/api/signals-version?days=${activeDays}`, {
          signal: ctrl.signal,
          cache: 'no-store',
        });

        const versionJson = versionRes.ok ? await versionRes.json() : {};
        const version = String(versionJson?.version || Date.now());

        const res = await fetch(`/api/signals?days=${activeDays}&cv=${encodeURIComponent(version)}`, {
          signal: ctrl.signal,
          cache: 'force-cache',
        });

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
  }, [activeDays]);

  if (loading && !data) {
    return (
      <main className="page">
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
        <p className="muted">今日訊號載入失敗：{err}</p>
      </main>
    );
  }

  return <SignalsClient data={data} activeDays={activeDays} />;
}
