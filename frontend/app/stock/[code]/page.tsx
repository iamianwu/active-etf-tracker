import { apiGet } from '@/lib/api';
import StockDetailClient from '@/components/StockDetailClient';

export default async function StockPage({ params }: { params: { code: string } }) {
  const data = await apiGet(`/stocks/${params.code}`);
  return <StockDetailClient data={data} />;
}
