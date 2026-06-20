export const revalidate = 60;

import Link from 'next/link';
import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

const VALID_SIGNAL_DAYS = [1, 5, 10, 20] as const;
type SignalDays = typeof VALID_SIGNAL_DAYS[number];

type SearchParams = {
  days?: string | string[];
  rangeDays?: string | string[];
  signalRangeDays?: string | string[];
};

function one(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}

function normalizeSignalDays(searchParams?: SearchParams): SignalDays {
  const raw = one(searchParams?.days) || one(searchParams?.rangeDays) || one(searchParams?.signalRangeDays) || '1';
  const n = Number(raw);
  return (VALID_SIGNAL_DAYS as readonly number[]).includes(n) ? (n as SignalDays) : 1;
}

export default async function SignalsPage({ searchParams }: { searchParams?: SearchParams }) {
  const days = normalizeSignalDays(searchParams);
  const data = await apiGet(`/signals?days=${days}`);

  return (
    <main className="signals-page-v114">
      <section className="signals-range-card-v114" aria-label="訊號區間">
        <div className="signals-range-label-v114">訊號區間</div>
        <div className="signals-segment-v114">
          {VALID_SIGNAL_DAYS.map((d) => (
            <Link
              key={d}
              href={d === 1 ? '/signals' : `/signals?days=${d}`}
              className={days === d ? 'active' : ''}
              prefetch
            >
              {d === 1 ? '今日' : `${d}日`}
            </Link>
          ))}
        </div>
      </section>

      <SignalsClient data={data} activeDays={days} />
    </main>
  );
}
