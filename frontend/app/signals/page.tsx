import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

const VALID_SIGNAL_DAYS = [1, 5, 10, 20];

function normalizeSignalDays(searchParams?: { days?: string; rangeDays?: string; signalRangeDays?: string }) {
  const raw =
    searchParams?.days ||
    searchParams?.rangeDays ||
    searchParams?.signalRangeDays ||
    '1';

  const n = Number(raw);
  return VALID_SIGNAL_DAYS.includes(n) ? n : 1;
}

export default async function SignalsPage({
  searchParams,
}: {
  searchParams?: { days?: string; rangeDays?: string; signalRangeDays?: string };
}) {
  const days = normalizeSignalDays(searchParams);
  const data = await apiGet(`/signals?days=${days}`);

  return (
    <SignalsClient
      data={{
        ...data,
        rangeDays: days,
        signalRangeDays: days,
      }}
    />
  );
}
