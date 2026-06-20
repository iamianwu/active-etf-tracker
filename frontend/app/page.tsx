import SignalsClient from '@/components/SignalsClient';
import { getSignalsV112 } from '@/lib/signalsV112';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default async function Page() {
  const data = await getSignalsV112();
  return <SignalsClient data={data} />;
}
