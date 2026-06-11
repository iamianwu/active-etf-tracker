import { getEtfDetailData } from '@/lib/etfData';
import EtfDetailClient from '@/components/EtfDetailClient';

export default async function EtfDetailPage({ params }: { params: { code: string } }) {
  const data = await getEtfDetailData(params.code);
  return <EtfDetailClient data={data} />;
}
