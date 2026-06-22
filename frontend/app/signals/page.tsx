import { unstable_cache } from 'next/cache';
import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

export const dynamic = 'force-dynamic';
export const revalidate = 300;

type SearchParams = {
  days?: string | string[];
  rangeDays?: string | string[];
  signalRangeDays?: string | string[];
};

function one(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}

function normalizeSignalDays(searchParams?: SearchParams): number {
  const raw = one(searchParams?.days) || one(searchParams?.rangeDays) || one(searchParams?.signalRangeDays) || '1';
  const n = Number(raw);
  return [1, 5, 10, 20].includes(n) ? n : 1;
}

const getCachedSignals = unstable_cache(
  async (days: number) => {
    return apiGet(`/signals?days=${days}`);
  },
  ['signals-page-data-v1'],
  {
    revalidate: 300,
    tags: ['signals-page-data'],
  }
);

export default async function Page({ searchParams }: { searchParams?: SearchParams }) {
  const days = normalizeSignalDays(searchParams);
  const data = await getCachedSignals(days);
  return <SignalsClient data={data} activeDays={days} />;
}
