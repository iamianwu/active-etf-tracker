import Link from 'next/link';
import { apiGet, fmt, fmt0, signedClass } from '@/lib/api';
export default async function StockPage({params}:{params:{code:string}}){
  const data = await apiGet(`/stocks/${params.code}`);
  return <main className="page">
    <Link className="back" href="/holdings">‹</Link>
    <h2>{data.stock_name} <span className="muted">{data.stock_code}</span></h2>
    <div className="grid2"><div className="stat"><div className="label">股價</div><div className="value">{data.quote?.price ?? '-'}</div><div className={signedClass(data.quote?.change_pct)}>{data.quote?.change_pct==null?'-':`${fmt(data.quote.change_pct)}%`}</div></div><div className="stat"><div className="label">主動式 ETF 持有</div><div className="value">{data.summary.etf_count}</div><div className="muted">合計權重 {fmt(data.summary.total_weight)}%</div></div></div>
    <div className="card"><h3>合計</h3><div className="listrow"><span>合計持股張數</span><b>{fmt0((data.summary.total_shares||0)/1000)} 張</b></div><div className="listrow"><span>合計持股市值</span><b>{fmt(data.summary.market_value_billion)} 億</b></div></div>
    <h3>哪些 ETF 持有</h3><table className="table"><thead><tr><th>ETF</th><th>權重</th><th>持股張數</th><th>持股市值</th></tr></thead><tbody>{data.etfs.map((r:any)=><tr key={r.etf_code}><td><Link href={`/etf/${r.etf_code}`}><b>{r.etf_code}</b><div className="code">{r.etf_name}</div></Link></td><td>{fmt(r.weight)}%</td><td>{fmt0((r.shares||0)/1000)} 張</td><td>{r.market_value_billion==null?'-':`${fmt(r.market_value_billion)} 億`}</td></tr>)}</tbody></table>
    <h3>歷史紀錄</h3><table className="table"><thead><tr><th>日期</th><th>ETF</th><th>權重</th><th>持股張數</th></tr></thead><tbody>{data.history.map((r:any,i:number)=><tr key={i}><td>{r.data_date}</td><td><Link href={`/etf/${r.etf_code}`}>{r.etf_code}</Link></td><td>{fmt(r.weight)}%</td><td>{fmt0((r.shares||0)/1000)} 張</td></tr>)}</tbody></table>
  </main>
}
