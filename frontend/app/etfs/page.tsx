import { getEtfListRows } from '@/lib/etfData';
import EtfListClient from '@/components/EtfListClient';

export default async function EtfsPage() {
  const rows = await getEtfListRows();
  return <EtfListClient rows={rows || []} />;
}
