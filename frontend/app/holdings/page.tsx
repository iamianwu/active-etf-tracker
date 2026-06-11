import { apiGet } from '@/lib/api';
import HoldingsClient from '@/components/HoldingsClient';

export default async function HoldingsPage() {
  const data = await apiGet('/holdings');
  return <HoldingsClient rows={data || []} />;
}
