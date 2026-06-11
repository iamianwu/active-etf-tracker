import { apiGet } from '@/lib/api';
import EtfListClient from '@/components/EtfListClient';

export default async function EtfsPage() {
  const data = await apiGet('/etfs');
  return <EtfListClient rows={data || []} />;
}
