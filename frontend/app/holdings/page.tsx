import Link from 'next/link';
import { apiGet, fmt, fmt0, signedClass } from '@/lib/api';
export default async function HoldingsPage(){
  const rows = await apiGet('/holdings');
  return <main className="page">
    <h2>資金持股</h2><p className="muted">共 {rows.length} 檔，可點股票進個股詳情。</p>
    <table className="table"><thead><tr><th>股票</th><th>今日漲幅</th><th>持股市值<br/>持股張數</th><th>主動式檔數<br/>合計權重</th></tr></thead><tbody>
      {rows.map((r:any)=><tr key={r.stock_code}>
        <td><Link href={`/stock/${r.stock_code}`}><b>{r.stock_name}</b><div className="code">{r.stock_code}</div></Link></td>
        <td className={signedClass(r.change_pct)}>{r.change_pct==null?'-':`${fmt(r.change_pct)}%`}</td>
        <td><b>{r.market_value_billion==null?'-':`${fmt(r.market_value_billion)} 億`}</b><div className="code">{fmt0((r.total_shares||0)/1000)} 張</div></td>
        <td><b>{r.etf_count}</b><div className="code">{fmt(r.total_weight)}%</div></td>
      </tr>)}
    </tbody></table>
  </main>
}
