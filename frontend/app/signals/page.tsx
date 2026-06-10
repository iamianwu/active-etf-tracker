import Link from 'next/link';
import { apiGet, fmt0, signedClass } from '@/lib/api';

export default async function SignalsPage(){
  const data = await apiGet('/signals');
  const changes = data.changes || [];
  const summary = data.summary || {};
  const agg = data.aggregate || [];
  const inflow = agg.filter((x:any)=>Number(x.delta_shares)>0)[0];
  const outflow = agg.filter((x:any)=>Number(x.delta_shares)<0)[0];
  return <main className="page">
    <h2>今日訊號</h2>
    <div className="grid2">
      <Link className="card" href="/signals/increased" style={{textDecoration:'none',color:'inherit'}}>
        <h3 className="red">資金流入 / 加碼最多</h3>
        <div>{inflow ? <><b>{inflow.stock_name}</b><div className="code">{inflow.stock_code}</div><div>變動張數：<span className="red">+{fmt0(inflow.delta_shares/1000)} 張</span></div></> : '尚無資料'}</div>
      </Link>
      <Link className="card" href="/signals/decreased" style={{textDecoration:'none',color:'inherit'}}>
        <h3 className="green">資金流出 / 減碼最多</h3>
        <div>{outflow ? <><b>{outflow.stock_name}</b><div className="code">{outflow.stock_code}</div><div>變動張數：<span className="green">{fmt0(outflow.delta_shares/1000)} 張</span></div></> : '尚無資料'}</div>
      </Link>
    </div>
    <div className="pillrow">
      <Link className="pill gold" href="/signals/added">新增 {summary['新增']||0}</Link>
      <Link className="pill" href="/signals/removed">刪除 {summary['刪除']||0}</Link>
      <Link className="pill red" href="/signals/increased">加碼 {summary['加碼']||0}</Link>
      <Link className="pill green" href="/signals/decreased">減碼 {summary['減碼']||0}</Link>
    </div>
    <h3>資金交易明細：共 {changes.length} 檔</h3>
    <table className="table"><thead><tr><th>標的</th><th>ETF</th><th>狀態</th><th>變動張數</th><th>權重變動</th></tr></thead><tbody>
      {changes.map((r:any, i:number)=><tr key={i} className="rowlink">
        <td><Link href={`/stock/${r.stock_code}`}><b>{r.stock_name}</b><div className="code">{r.stock_code}</div></Link></td>
        <td><Link href={`/etf/${r.etf_code}`}>{r.etf_code}</Link></td>
        <td><span className={`badge ${r.status==='加碼'?'red':r.status==='減碼'?'green':r.status==='新增'?'gold':''}`}>{r.status}</span></td>
        <td className={signedClass(r.delta_shares)}>{fmt0((r.delta_shares||0)/1000)} 張</td>
        <td className={signedClass(r.delta_weight)}>{Number(r.delta_weight||0).toFixed(2)}%</td>
      </tr>)}
    </tbody></table>
  </main>
}
