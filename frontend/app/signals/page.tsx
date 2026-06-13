import Link from 'next/link';
import { apiGet, fmt, fmt0 } from '@/lib/api';
import SortableSignalTable from '@/components/SortableSignalTable';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

const ALLOWED = new Set(['新增', '刪除', '加碼', '減碼']);
const SIGNAL_RANGES = ['1', '3', '5', '10', '20'];

function cleanRange(raw: any) {
  const r = String(raw || '1');
  return SIGNAL_RANGES.includes(r) ? r : '1';
}

function rangeHref(range: string) {
  return range === '1' ? '/' : `/?range=${range}`;
}

function signalsRangeHref(range: string) {
  return range === '1' ? '/signals' : `/signals?range=${range}`;
}

function typeHref(type: string, range: string) {
  return range === '1' ? `/signals/${type}` : `/signals/${type}?range=${range}`;
}

function rangeTitle(range: string) {
  return range === '1' ? '今日訊號' : `近${range}日訊號`;
}

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

function SignalRangeTabs({ range, base = 'home' }: { range: string; base?: 'home' | 'signals' }) {
  const items = [
    { value: '1', label: '即時' },
    { value: '3', label: '3日' },
    { value: '5', label: '5日' },
    { value: '10', label: '10日' },
    { value: '20', label: '20日' },
  ];

  return (
    <div className="signals-window-tabs-v70" aria-label="訊號區間">
      {items.map((item) => (
        <Link
          key={item.value}
          href={signalsRangeHref(item.value)}
          className={range === item.value ? 'active' : ''}
        >
          {item.label}
        </Link>
      ))}
    </div>
  );
}

function FocusCard({
  title,
  item,
  tone,
  href,
}: {
  title: string;
  item: any;
  tone: 'red' | 'green';
  href: string;
}) {
  const buyCount = countFromStatuses(item || {}, '買');
  const sellCount = countFromStatuses(item || {}, '賣');

  return (
    <Link className={`focus-card ${tone}`} href={href}>
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

export default async function SignalsHomePage({
  searchParams,
}: {
  searchParams?: { range?: string; window?: string; days?: string };
}) {
  const range = cleanRange(searchParams?.range || searchParams?.window || searchParams?.days);
  const data = await apiGet(range === '1' ? '/signals' : `/signals?range=${range}`);

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
  const title = rangeTitle(range);

  return (
    <main className="page signals-v3-page signals-window-page-v70">
      <SignalRangeTabs range={range} base="signals" />

      <div className="signals-title-block">
        <h2>{mmdd ? `${mmdd} ${title}` : title}</h2>
        <div className={`signals-data-status ${complete ? 'ok' : 'warn'}`}>
          已抓取 {data.fetched_etf_count || 0} / {data.total_etf_count || 0} 檔 ETF
          {data.data_date ? `，資料日期 ${data.data_date}` : ''}
        </div>
        <div className="signals-window-note-v70">
          {range === '1'
            ? '即時＝最新持股日與前一個持股日比較。'
            : `近${range}日＝每檔 ETF 最新持股與 ${range} 個持股資料日前比較，顯示區間淨變動。`}
        </div>
      </div>

      <div className="focus-grid">
        <FocusCard title="資金流入最多" item={inflow} tone="red" href={typeHref('increased', range)} />
        <FocusCard title="資金流出最多" item={outflow} tone="green" href={typeHref('decreased', range)} />
        <FocusCard title="最多 ETF 加碼" item={mostEtfAdd} tone="red" href={typeHref('increased', range)} />
        <FocusCard title="最多 ETF 減碼" item={mostEtfReduce} tone="green" href={typeHref('decreased', range)} />
      </div>

      <h3>資金交易明細：共 {changes.length} 檔</h3>

      <div className="status-pill-row">
        <Link className="status-pill add" href={typeHref('added', range)}>
          <span>新增</span><b>{summary['新增'] || 0}</b>
        </Link>
        <Link className="status-pill remove" href={typeHref('removed', range)}>
          <span>刪除</span><b>{summary['刪除'] || 0}</b>
        </Link>
        <Link className="status-pill inc" href={typeHref('increased', range)}>
          <span>加碼</span><b>{summary['加碼'] || 0}</b>
        </Link>
        <Link className="status-pill dec" href={typeHref('decreased', range)}>
          <span>減碼</span><b>{summary['減碼'] || 0}</b>
        </Link>
      </div>

      <SortableSignalTable rows={changes} />
    </main>
  );
}
