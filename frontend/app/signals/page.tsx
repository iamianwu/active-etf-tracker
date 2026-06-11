import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

export default async function SignalsPage() {
  const data = await apiGet('/signals');
  return <SignalsClient data={data} />;
}
