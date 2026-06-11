import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

const statusMap: any = {
  added: '新增',
  removed: '刪除',
  increased: '加碼',
  decreased: '減碼',
};

export default async function SignalTypePage({ params }: { params: { type: string } }) {
  const data = await apiGet('/signals');
  return <SignalsClient data={data} initialFilter={statusMap[params.type] || null} />;
}
