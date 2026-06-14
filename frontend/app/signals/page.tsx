import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

const ALLOWED_SIGNAL_RANGES_V73 = new Set(['1', '3', '5', '10', '20']);

function cleanSignalRangeV73(raw: any) {
  const r = String(raw || '1');
  return ALLOWED_SIGNAL_RANGES_V73.has(r) ? r : '1';
}

export default async function SignalsPage({
  searchParams,
}: {
  searchParams?: { range?: string; window?: string; days?: string };
}) {
  const range = cleanSignalRangeV73(searchParams?.range || searchParams?.window || searchParams?.days);
  const data = await apiGet(range === '1' ? '/signals' : `/signals?range=${range}`);
  return <SignalsClient data={data} signalRange={range} />;
}
