export const revalidate = 60;

import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';


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

export default async function SignalTypePage({
  params,
  searchParams,
}: {
  params: { type: string };
  searchParams?: { days?: string; rangeDays?: string; signalRangeDays?: string };
}) {
  const days = normalizeSignalDays(searchParams);
  const type = params.type;
  const data = await apiGet(`/signals?type=${type}&days=${days}&fresh=1`);

  return (
    <SignalsClient
      data={{
        ...data,
        activeType: type,
        selectedType: type,
        rangeDays: days,
        signalRangeDays: days,
      }}
    />
  );
}
