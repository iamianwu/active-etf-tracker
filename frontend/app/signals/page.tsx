import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

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

export default async function Page({ searchParams }: { searchParams?: SearchParams }) {
  const days = normalizeSignalDays(searchParams);
  const data = await apiGet(`/signals?days=${days}`);
  return <SignalsClient data={data} activeDays={days} />;
}
