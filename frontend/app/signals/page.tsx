import Link from 'next/link';
import { apiGet, fmt, fmt0 } from '@/lib/api';
import SortableSignalTable from '@/components/SortableSignalTable';

const ALLOWED = new Set(['新增', '刪除', '加碼', '減碼']);

function countFromStatuses(x: any, keyword: string) {
  if (keyword === '加碼' && x.increase_etf_count !== undefined) return Number(x.increase_etf_count || 0);
  if (keyword === '減碼' && x.decrease_etf_count !== undefined) return Number(x.decrease_etf_count || 0);
  if (keyword === '買' && x.buy_etf_count !== undefined) return Number(x.buy_etf_count || 0);
  if (keyword === '賣' && x.sell_etf_count !== undefined) return Number(x.sell_etf_count || 0);
  return (x.statuses || []).filter((s: string) => String(s).includes(keyword)).length;
}

function sortByMoneyOrSharesDesc(a: any, b: any) {
  const av = a.delta_value_billion !== null && a.delta_value_billion !== undefined
    ? Math.abs(Number(a.delta_value_billion || 0))
    : Math.abs(Number(a.delta_shares || 0));

  const bv = b.delta_value_billion !== null && b.delta_value_billion !== undefined
    ? Math.abs(Number(b.delta_value_billion || 0))
    : Math.abs(Number(b.delta_shares || 0));

  return bv - av;
}

function stockMoveValue(x: any) {
  const v = x?.delta_value_billion;

  if (v !== null && v !== undefined && !Number.isNaN(Number(v)) && Number(v) !== 0) {
    const prefix = Number(v) > 0 ? '+' : '';
    return `${prefix}${fmt(v, 1)} 億`;
  }

  const lots = Number(x?.delta_shares || 0) / 1000;
  const prefix = lots > 0 ? '+' : '';
  return `${prefix}${fmt0(lots)} 張`;
}

function FocusCard({
  title,
  item,
  tone,
}: {
  title: string;
  item: any;
  tone: 'red' | 'green';
}) {
  const buyCount = countFromStatuses(item || {}, '買');
  const sellCount = countFromStatuses(item || {}, '賣');

  return (
    <Link className={`focus-card ${tone}`} href={tone === 'red' ? '/signals/increased' : '/signals/decreased'}>
      <div className="focus-card-title">{title}</div>

      {item ? (
        <div className="focus-card-body">
          <div className="focus-stock">
            <b>{item.stock_name}</b>
            <span>{item.stock_code}</span>
          </div>

          <div className="focus-metrics">
            <div>
              <span>資金動向：</span>
              <b>{stockMoveValue(item)}</b>
            </div>
            <div>
              <span>多空共識：</span>
              <b>買賣檔數 {buyCount}:{sellCount}</b>
            </div>
          </div>
        </div>
      ) : (
        <div className="focus-empty">尚無資料</div>
      )}
    </Link>
  );
}

export default async function SignalsPage() {
  const data = await apiGet('/signals');

  const changes = (data.changes || []).filter((x: any) => ALLOWED.has(x.status));
  const summary = data.summary || {};
  const agg = (data.aggregate || []).filter((x: any) => x.stock_code);

  const inflow = [...agg]
    .filter((x: any) => Number(x.delta_shares || 0) > 0)
    .sort(sortByMoneyOrSharesDesc)[0];

  const outflow = [...agg]
    .filter((x: any) => Number(x.delta_shares || 0) < 0)
    .sort(sortByMoneyOrSharesDesc)[0];

  const mostEtfAdd = [...agg]
    .filter((x: any) => countFromStatuses(x, '加碼') > 0)
    .sort((a: any, b: any) =>
      countFromStatuses(b, '加碼') - countFromStatuses(a, '加碼') ||
      Math.abs(Number(b.delta_shares || 0)) - Math.abs(Number(a.delta_shares || 0))
    )[0];

  const mostEtfReduce = [...agg]
    .filter((x: any) => countFromStatuses(x, '減碼') > 0)
    .sort((a: any, b: any) =>
      countFromStatuses(b, '減碼') - countFromStatuses(a, '減碼') ||
      Math.abs(Number(b.delta_shares || 0)) - Math.abs(Number(a.delta_shares || 0))
    )[0];

  const mmdd = data.data_date_mmdd || '';
  const complete = Number(data.fetched_etf_count || 0) === Number(data.total_etf_count || 0);

  return (
    <main className="page signals-v3-page">
      <div className="signals-title-block">
        <h2>{mmdd ? `${mmdd} 今日訊號` : '今日訊號'}</h2>
        <div className={`signals-data-status ${complete ? 'ok' : 'warn'}`}>
          已抓取 {data.fetched_etf_count || 0} / {data.total_etf_count || 0} 檔 ETF
          {data.data_date ? `，資料日期 ${data.data_date}` : ''}
        </div>
      </div>

      <div className="focus-grid">
        <FocusCard title="資金流入最多" item={inflow} tone="red" />
        <FocusCard title="資金流出最多" item={outflow} tone="green" />
        <FocusCard title="最多 ETF 加碼" item={mostEtfAdd} tone="red" />
        <FocusCard title="最多 ETF 減碼" item={mostEtfReduce} tone="green" />
      </div>

      <div className="status-pill-row">
        <Link className="status-pill add" href="/signals/added">
          <span>新增</span><b>{summary['新增'] || 0}</b>
        </Link>
        <Link className="status-pill remove" href="/signals/removed">
          <span>刪除</span><b>{summary['刪除'] || 0}</b>
        </Link>
        <Link className="status-pill inc" href="/signals/increased">
          <span>加碼</span><b>{summary['加碼'] || 0}</b>
        </Link>
        <Link className="status-pill dec" href="/signals/decreased">
          <span>減碼</span><b>{summary['減碼'] || 0}</b>
        </Link>
      </div>

      <h3>資金交易明細：共 {changes.length} 檔</h3>

      <SortableSignalTable rows={changes} />
    </main>
  );
}
