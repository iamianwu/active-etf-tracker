'use client';
import { useState } from 'react';
import { apiPost } from '@/lib/api';
export default function AdminPage(){
  const [msg,setMsg]=useState('');
  async function run(path:string){ setMsg('執行中...'); try{ const r=await apiPost(path); setMsg(JSON.stringify(r,null,2)); }catch(e:any){ setMsg(e.message); } }
  return <main className="page"><h2>管理</h2><a className="btn" href="/admin/etf-status">ETF 資料健康檢查</a> <button className="btn" onClick={()=>run('/admin/seed-demo')}>建立 Demo 資料</button> <button className="btn btn-primary" onClick={()=>run('/admin/update-all?dt_range=1')}>更新全部 ETF 最新資料</button><pre className="card" style={{whiteSpace:'pre-wrap'}}>{msg}</pre></main>
}
