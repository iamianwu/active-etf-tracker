import StockDetailPageLoader from '@/components/StockDetailPageLoader';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default function StockPage({ params }: { params: { code: string } }) {
  return <StockDetailPageLoader code={params.code} />;
}
