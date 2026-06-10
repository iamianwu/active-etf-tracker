import Link from 'next/link';
import { apiGet, fmt, fmt0, signedClass } from '@/lib/api';

function Donut({items}:{items:any[]}){
  const total = items.reduce((s,x)=>s+Number(x.weight||0),0) || 1;
  let acc = 0;
  const colors = ['#ffad3b','#18aee2','#4d88d9','#c77df3','#d6d6d6'];
  const stops = items.map((x,i)=>{ const start=acc; const end=acc+Number(x.weight||0)/total*100; acc=end; return `${colors[i%colors.length]} ${start}% ${end}%`; }).join(',');
  return <div style={{display:'flex',gap:18,alignItems:'center'}}><div style={{width:180,height:180,borderRadius:'50%',background:`conic-gradient(${stops})`,position:'relative',flex:'0 0 auto'}}><div style={{position:'absolute',inset:48,borderRadius:'50%',background:'#fff'}} /></div><div style={{flex:1}}>{items.map((x,i)=><div key={x.stock_code||x.stock_name} className="listrow"><span><span style={{display:'inline-block',width:10,height:10,background:colors[i%colors.length],marginRight:8}} />{x.stock_name}</span><b>{fmt(x.weight)}%</b></div>)}</div></div>
}

export default async function EtfDetailPage({params, searchParams}:{params:{code:string}, searchParams:{tab?:string}}){
  const data = await apiGet(`/etfs/${params.code}`);
  const tab = searchParams.tab || 'overview';
  const h = data.holdings || [];
  const changes = data.changes || [];
  const summary = data.change_summary || {};
  const topItems = h.slice(0,4);
  const otherWeight = Math.max(0, 100 - topItems.reduce((s:number,x:any)=>s+Number(x.weight||0),0));
  const pieItems = [...topItems, {stock_code:'OTHER', stock_name:'其他', weight: otherWeight}];
  return <main className="page">
    <div className="hero"><Link className="back" href="/etfs">‹</Link><div className="hero-title"><div className="hero-code">{data.etf_code}</div><div className="hero-name">{data.etf_name}</div></div><span className="back muted">›</span></div>
    <div className="tabs"><Link className={tab==='overview'?'active':''} href={`/etf/${params.code}?tab=overview`}>總覽</Link><Link className={tab==='quote'?'active':''} href={`/etf/${params.code}?tab=quote`}>即時</Link><Link className={tab==='operations'?'active':''} href={`/etf/${params.code}?tab=operations`}>操作日報</Link><Link className={tab==='holdings'?'active':''} href={`/etf/${params.code}?tab=holdings`}>成分股</Link><Link className={tab==='premium'?'active':''} href={`/etf/${params.code}?tab=premium`}>折溢價</Link></div>

    {tab==='overview' && <><div className="grid2"><div className="stat"><div className="label">股價</div><div className="value red">{data.quote?.price ?? '-'}</div><div className={signedClass(data.quote?.change_pct)}>{data.quote?.change_pct==null?'-':`${fmt(data.quote.change_pct)}%`}</div></div><div className="stat"><div className="label">股票權重</div><div className="value">{fmt(h.filter((x:any)=>x.stock_code!=='C_NTD').reduce((s:number,x:any)=>s+Number(x.weight||0),0))}%</div><div className="muted">更新 {data.data_date}</div></div></div><div className="card"><h3>{data.data_date} 持股異動：<span className="gold">新增 {summary['新增']||0} 檔</span>｜刪除 {summary['刪除']||0} 檔</h3><Link href={`/etf/${params.code}?tab=operations`}>更多 ›</Link></div><div className="card"><h3>基本資料</h3><div className="listrow"><span>基金名稱</span><b>{data.etf_name}</b></div><div className="listrow"><span>成立日期</span><b>{data.quote?.inception_date || '-'}</b></div><div className="listrow"><span>內扣費用</span><b>{data.quote?.expense_ratio == null ? '-' : `${fmt(data.quote.expense_ratio)}%`}</b></div><div className="listrow"><span>持股人數</span><b>{fmt0(data.quote?.holder_count)}</b></div><div className="listrow"><span>配息週期</span><b>{data.quote?.dividend_frequency || '-'}</b></div></div></>}

    {tab==='quote' && <div className="card"><h3>即時資訊</h3><div className="grid2"><div className="stat"><div className="label">股價</div><div className="value">{data.quote?.price ?? '-'}</div></div><div className="stat"><div className="label">漲跌幅</div><div className={`value ${signedClass(data.quote?.change_pct)}`}>{data.quote?.change_pct==null?'-':`${fmt(data.quote.change_pct)}%`}</div></div><div className="stat"><div className="label">成交量</div><div className="value">{fmt0(data.quote?.volume)}</div></div><div className="stat"><div className="label">成交金額</div><div className="value">{fmt(data.quote?.amount)} 億</div></div></div></div>}

    {tab==='operations' && <><h3>{data.data_date} 操作日報</h3><div className="pillrow"><span className="pill gold">新增 {summary['新增']||0}</span><span className="pill">刪除 {summary['刪除']||0}</span><span className="pill red">加碼 {summary['加碼']||0}</span><span className="pill green">減碼 {summary['減碼']||0}</span></div><table className="table"><thead><tr><th>標的</th><th>狀態</th><th>持股變動</th><th>目前權重</th></tr></thead><tbody>{changes.map((r:any,i:number)=><tr key={i}><td><Link href={`/stock/${r.stock_code}`}><b>{r.stock_name}</b><div className="code">{r.stock_code}</div></Link></td><td><span className="badge">{r.status}</span></td><td className={signedClass(r.delta_shares)}>{fmt0((r.delta_shares||0)/1000)} 張</td><td>{fmt(r.weight)}%</td></tr>)}</tbody></table></>}

    {tab==='holdings' && <><div className="card"><Donut items={pieItems}/></div><table className="table"><thead><tr><th>標的</th><th>持股市值<br/>持股張數</th><th>權重</th><th>股價<br/>漲跌幅</th></tr></thead><tbody>{h.map((r:any)=><tr key={r.stock_code}><td><Link href={`/stock/${r.stock_code}`}><b>{r.stock_name}</b><div className="code">{r.stock_code}</div></Link></td><td><b>{r.market_value_billion==null?'-':`${fmt(r.market_value_billion)} 億`}</b><div className="code">{fmt0((r.shares||0)/1000)} 張</div></td><td>{fmt(r.weight)}%</td><td>{r.price ?? '-'}<div className={signedClass(r.change_pct)}>{r.change_pct==null?'-':`${fmt(r.change_pct)}%`}</div></td></tr>)}</tbody></table></>}

    {tab==='premium' && <div className="card"><h3>折溢價</h3><div className="grid2"><div className="stat"><div className="label">折溢價</div><div className={`value ${signedClass(data.quote?.premium_pct)}`}>{data.quote?.premium_pct==null?'-':`${fmt(data.quote.premium_pct)}%`}</div></div><div className="stat"><div className="label">淨值</div><div className="value">{data.quote?.nav ?? '-'}</div></div></div><p className="muted">下一版可接 Pocket ETF 日資訊 API，自動補上折溢價歷史。</p></div>}
  </main>
}
