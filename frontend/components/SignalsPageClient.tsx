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

    setLoading(true);
    setErr('');

    fetch(`/api/signals?days=${activeDays}`, {
      signal: ctrl.signal,
      cache: 'force-cache',
    })
      .then((r) => {
        if (!r.ok) throw new Error(`signals api failed: ${r.status}`);
        return r.json();
      })
      .then((json) => {
        setData(json);
      })
      .catch((e) => {
        if (e?.name !== 'AbortError') {
          console.error(e);
          setErr(String(e?.message || e));
        }
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setLoading(false);
      });

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
