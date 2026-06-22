import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

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

function siteBase() {
  if (process.env.NEXT_PUBLIC_SITE_URL) return process.env.NEXT_PUBLIC_SITE_URL;
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  return 'http://localhost:3000';
}

async function getSignalsData(days: number) {
  const url = `${siteBase()}/api/signals?days=${days}`;

  try {
    const res = await fetch(url, {
      headers: { accept: 'application/json' },
      next: {
        revalidate: 300,
        tags: ['signals-page-data'],
      },
    });

    if (res.ok) return res.json();
  } catch (e) {
    console.warn('[signals page] fetch cached API failed, fallback to apiGet:', e);
  }

  return apiGet(`/signals?days=${days}`);
}

export default async function Page({ searchParams }: { searchParams?: SearchParams }) {
  const days = normalizeSignalDays(searchParams);
  const data = await getSignalsData(days);
  return <SignalsClient data={data} activeDays={days} />;
}
