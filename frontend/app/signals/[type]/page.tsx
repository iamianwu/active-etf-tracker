import Link from 'next/link';
import { apiGet } from '@/lib/api';
import SortableSignalTable from '@/components/SortableSignalTable';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

const titleMap: any = {
  added: '新增清單',
  removed: '刪除清單',
  increased: '加碼清單',
  decreased: '減碼清單',
};

const ALLOWED = new Set(['新增', '刪除', '加碼', '減碼']);
const SIGNAL_RANGES = ['1', '3', '5', '10', '20'];

function cleanRange(raw: any) {
  const r = String(raw || '1');
  return SIGNAL_RANGES.includes(r) ? r : '1';
}

function backHref(range: string) {
  return range === '1' ? '/' : `/?range=${range}`;
}

export default async function SignalTypePage({
  params,
  searchParams,
}: {
  params: { type: string };
  searchParams?: { range?: string; window?: string; days?: string };
}) {
  const range = cleanRange(searchParams?.range || searchParams?.window || searchParams?.days);
  const data = await apiGet(range === '1'
    ? `/signals?type=${params.type}`
    : `/signals?type=${params.type}&range=${range}`
  );
  const rows = (data.changes || []).filter((x: any) => ALLOWED.has(x.status));
  const mmdd = data.data_date_mmdd || '';
  const rangeText = range === '1' ? '' : `近${range}日`;
  const listTitle = `${rangeText}${titleMap[params.type] || '訊號清單'}`;

  return (
    <main className="page signals-v3-page">
      <Link className="back" href={backHref(range)}>‹</Link>
      <div className="signals-title-block">
        <h2>{mmdd ? `${mmdd} ${listTitle}` : listTitle}：共 {rows.length} 檔</h2>
        <div className="signals-data-status">
          已抓取 {data.fetched_etf_count || 0} / {data.total_etf_count || 0} 檔 ETF
          {data.data_date ? `，資料日期 ${data.data_date}` : ''}
        </div>
      </div>

      <SortableSignalTable rows={rows} />
    </main>
  );
}
