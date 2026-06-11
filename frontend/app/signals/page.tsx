import Link from 'next/link';
import { apiGet, fmt, fmt0, signedClass } from '@/lib/api';

const ALLOWED = new Set(['新增', '刪除', '加碼', '減碼']);

function countFromStatuses(x: any, keyword: string) {
  if (keyword === '加碼' && x.increase_etf_count !== undefined) return Number(x.increase_etf_count || 0);
  if (keyword === '減碼' && x.decrease_etf_count !== undefined) return Number(x.decrease_etf_count || 0);
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

function moneyOrSharesLine(x: any, colorClass: string) {
  const v = x?.delta_value_billion;

  if (v !== null && v !== undefined && !Number.isNaN(Number(v)) && Number(v) !== 0) {
    const prefix = Number(v) > 0 ? '+' : '';
    return <div>估算金額：<span className={colorClass}>{prefix}{fmt(v)} 億</span></div>;
  }

  const lots = Number(x?.delta_shares || 0) / 1000;
  const prefix = lots > 0 ? '+' : '';
  return <div>變動張數：<span className={colorClass}>{prefix}{fmt0(lots)} 張</span></div>;
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

  return (
    <main className="page">
      <h2>今日訊號</h2>

      <div className="grid2">
        <Link className="card" href="/signals/increased" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3 className="red">資金流入最多</h3>
          <div>
            {inflow ? (
              <>
                <b>{inflow.stock_name}</b>
                <div className="code">{inflow.stock_code}</div>
                {moneyOrSharesLine(inflow, 'red')}
              </>
            ) : '尚無資料'}
          </div>
        </Link>

        <Link className="card" href="/signals/decreased" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3 className="green">資金流出最多</h3>
          <div>
            {outflow ? (
              <>
                <b>{outflow.stock_name}</b>
                <div className="code">{outflow.stock_code}</div>
                {moneyOrSharesLine(outflow, 'green')}
              </>
            ) : '尚無資料'}
          </div>
        </Link>

        <Link className="card" href="/signals/increased" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3 className="red">最多 ETF 加碼</h3>
          <div>
            {mostEtfAdd ? (
              <>
                <b>{mostEtfAdd.stock_name}</b>
                <div className="code">{mostEtfAdd.stock_code}</div>
                <div>ETF 檔數：<span className="red">{countFromStatuses(mostEtfAdd, '加碼')} 檔</span></div>
                <div>變動張數：<span className="red">+{fmt0(Number(mostEtfAdd.delta_shares || 0) / 1000)} 張</span></div>
              </>
            ) : '尚無資料'}
          </div>
        </Link>

        <Link className="card" href="/signals/decreased" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h3 className="green">最多 ETF 減碼</h3>
          <div>
            {mostEtfReduce ? (
              <>
                <b>{mostEtfReduce.stock_name}</b>
                <div className="code">{mostEtfReduce.stock_code}</div>
                <div>ETF 檔數：<span className="green">{countFromStatuses(mostEtfReduce, '減碼')} 檔</span></div>
                <div>變動張數：<span className="green">{fmt0(Number(mostEtfReduce.delta_shares || 0) / 1000)} 張</span></div>
              </>
            ) : '尚無資料'}
          </div>
        </Link>
      </div>

      <div className="pillrow">
        <Link className="pill gold" href="/signals/added">新增 {summary['新增'] || 0}</Link>
        <Link className="pill" href="/signals/removed">刪除 {summary['刪除'] || 0}</Link>
        <Link className="pill red" href="/signals/increased">加碼 {summary['加碼'] || 0}</Link>
        <Link className="pill green" href="/signals/decreased">減碼 {summary['減碼'] || 0}</Link>
      </div>

      <h3>資金交易明細：共 {changes.length} 檔</h3>

      <table className="table">
        <thead>
          <tr>
            <th>標的</th>
            <th>ETF</th>
            <th>狀態</th>
            <th>變動張數</th>
            <th>目前權重</th>
          </tr>
        </thead>
        <tbody>
          {changes.map((r: any, i: number) => (
            <tr key={i} className="rowlink">
              <td>
                <Link href={`/stock/${r.stock_code}`}>
                  <b>{r.stock_name}</b>
                  <div className="code">{r.stock_code}</div>
                </Link>
              </td>
              <td><Link href={`/etf/${r.etf_code}`}>{r.etf_code}</Link></td>
              <td>
                <span className={`badge ${r.status === '加碼' ? 'red' : r.status === '減碼' ? 'green' : r.status === '新增' ? 'gold' : ''}`}>
                  {r.status}
                </span>
              </td>
              <td className={signedClass(r.delta_shares)}>{fmt0(Number(r.delta_shares || 0) / 1000)} 張</td>
              <td>{Number(r.weight || 0).toFixed(2)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
