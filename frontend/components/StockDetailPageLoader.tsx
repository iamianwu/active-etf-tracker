'use client';

import { useEffect, useState } from 'react';
import StockDetailClient from '@/components/StockDetailClient';

export default function StockDetailPageLoader({ code }: { code: string }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    let alive = true;

    async function load() {
      try {
        setError('');
        const res = await fetch(`/api/stock-detail?code=${encodeURIComponent(code)}`, {
          cache: 'no-store',
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const json = await res.json();
        if (alive) setData(json);
      } catch (e: any) {
        if (alive) setError(String(e?.message || e));
      }
    }

    load();

    return () => {
      alive = false;
    };
  }, [code]);

  if (error) {
    return (
      <main className="page">
        <section className="card">
          <h1>個股資料載入失敗</h1>
          <p>{error}</p>
        </section>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="page">
        <section className="card">
          <h1>{code}</h1>
          <p className="muted">正在載入個股資料...</p>
        </section>
      </main>
    );
  }

  return <StockDetailClient data={data} />;
}
