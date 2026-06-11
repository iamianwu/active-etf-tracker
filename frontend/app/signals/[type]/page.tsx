import Link from 'next/link';
import { apiGet } from '@/lib/api';
import SortableSignalTable from '@/components/SortableSignalTable';

const titleMap: any = {
  added: '新增清單',
  removed: '刪除清單',
  increased: '加碼清單',
  decreased: '減碼清單',
};

const ALLOWED = new Set(['新增', '刪除', '加碼', '減碼']);

export default async function SignalTypePage({ params }: { params: { type: string } }) {
  const data = await apiGet(`/signals?type=${params.type}`);
  const rows = (data.changes || []).filter((x: any) => ALLOWED.has(x.status));
  const mmdd = data.data_date_mmdd || '';

  return (
    <main className="page signals-v3-page">
      <Link className="back" href="/signals">‹</Link>
      <div className="signals-title-block">
        <h2>{mmdd ? `${mmdd} ${titleMap[params.type] || '訊號清單'}` : titleMap[params.type] || '訊號清單'}：共 {rows.length} 檔</h2>
        <div className="signals-data-status">
          已抓取 {data.fetched_etf_count || 0} / {data.total_etf_count || 0} 檔 ETF
          {data.data_date ? `，資料日期 ${data.data_date}` : ''}
        </div>
      </div>

      <SortableSignalTable rows={rows} />
    </main>
  );
}
