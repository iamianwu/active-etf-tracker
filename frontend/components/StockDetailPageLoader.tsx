'use client';

import { useEffect, useState } from 'react';
import StockDetailClient from '@/components/StockDetailClient';

export default function StockDetailPageLoader({ code }: { code: string }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 20000);

    async function load() {
      try {
        setError('');

        const res = await fetch(
          `/api/stock-detail?code=${encodeURIComponent(code)}`,
          {
            cache: 'no-store',
            signal: controller.signal,
          }
        );

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const json = await res.json();
        setData(json);
      } catch (e: any) {
        if (e?.name === 'AbortError') {
          setError('載入時間過久，請重新整理頁面。');
        } else {
          setError(String(e?.message || e));
        }
      } finally {
        window.clearTimeout(timer);
      }
    }

    load();

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [code]);

  if (error) {
    return (
      <main className="v130-stock-loading">
        <section className="v130-stock-error">
          <b>個股資料載入失敗</b>
          <span>{error}</span>
          <button type="button" onClick={() => window.location.reload()}>
            重新載入
          </button>
        </section>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="v130-stock-loading" aria-busy="true">
        <div className="v130-stock-loading-head">
          <div>
            <span className="v130-skeleton v130-skeleton-code" />
            <span className="v130-skeleton v130-skeleton-name" />
          </div>
          <span className="v130-skeleton v130-skeleton-price" />
        </div>

        <section className="v130-stock-loading-card">
          <div className="v130-loading-metrics">
            <span className="v130-skeleton" />
            <span className="v130-skeleton" />
            <span className="v130-skeleton" />
            <span className="v130-skeleton" />
          </div>
        </section>

        <section className="v130-stock-loading-card">
          <span className="v130-skeleton v130-skeleton-title" />
          <div className="v130-loading-chart">
            <span className="v130-skeleton" />
          </div>
        </section>

        <section className="v130-stock-loading-card">
          <span className="v130-skeleton v130-skeleton-title" />
          <div className="v130-loading-rows">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index}>
                <span className="v130-skeleton" />
                <span className="v130-skeleton" />
                <span className="v130-skeleton" />
              </div>
            ))}
          </div>
        </section>
      </main>
    );
  }

  return <StockDetailClient data={data} />;
}
