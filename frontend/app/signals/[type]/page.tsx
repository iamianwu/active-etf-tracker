import Link from 'next/link';
import { apiGet, fmt0, signedClass } from '@/lib/api';
const titleMap:any = {added:'新增清單', removed:'刪除清單', increased:'加碼清單', decreased:'減碼清單'};
export default async function SignalTypePage({params}:{params:{type:string}}){
  const data = await apiGet(`/signals?type=${params.type}`);
  const rows = data.changes || [];
  return <main className="page">
    <Link className="back" href="/signals">‹</Link>
    <h2>{titleMap[params.type] || '訊號清單'}：共 {rows.length} 檔</h2>
    <table className="table"><thead><tr><th>標的</th><th>ETF</th><th>狀態</th><th>變動張數</th><th>目前權重</th></tr></thead><tbody>
      {rows.map((r:any,i:number)=><tr key={i}>
        <td><Link href={`/stock/${r.stock_code}`}><b>{r.stock_name}</b><div className="code">{r.stock_code}</div></Link></td>
        <td><Link href={`/etf/${r.etf_code}`}>{r.etf_code}</Link></td>
        <td><span className="badge">{r.status}</span></td>
        <td className={signedClass(r.delta_shares)}>{fmt0((r.delta_shares||0)/1000)} 張</td>
        <td>{Number(r.weight||0).toFixed(2)}%</td>
      </tr>)}
    </tbody></table>
  </main>
}
