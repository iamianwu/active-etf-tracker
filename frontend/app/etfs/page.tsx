import Link from 'next/link';
import { apiGet, fmt, fmt0, signedClass } from '@/lib/api';
export default async function EtfsPage(){
  const rows = await apiGet('/etfs');
  return <main className="page">
    <h2>ETF 列表</h2><p className="muted">每檔 ETF 可點進詳情頁。</p>
    <table className="table"><thead><tr><th>股票</th><th>股價</th><th>漲跌幅</th><th>成分股數</th><th>股票權重</th></tr></thead><tbody>
      {rows.map((r:any)=><tr key={r.etf_code}>
        <td><Link href={`/etf/${r.etf_code}`}><b>{r.etf_code}</b><div className="code">{r.etf_name}</div></Link></td>
        <td>{r.price==null?'-':fmt(r.price)}</td>
        <td className={signedClass(r.change_pct)}>{r.change_pct==null?'-':`${fmt(r.change_pct)}%`}</td>
        <td>{fmt0(r.holding_count)}</td>
        <td>{fmt(r.stock_weight)}%</td>
      </tr>)}
    </tbody></table>
  </main>
}
