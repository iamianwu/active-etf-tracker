export const num=(v:any,d=0)=>{const x=Number(v);return Number.isFinite(x)?x:d};
export const str=(v:any,d='')=>v===null||v===undefined?d:String(v);
export const fmt=(v:any,d=0)=>{const x=Number(v);return Number.isFinite(x)?x.toLocaleString('zh-TW',{maximumFractionDigits:d,minimumFractionDigits:d}):'-'};
export const fm=(v:any,d=0)=>{const x=Number(v);return Number.isFinite(x)?x.toLocaleString('zh-TW',{maximumFractionDigits:d}):'-'};
export const pct=(v:any,d=2)=>{const x=Number(v);return Number.isFinite(x)?`${x>0?'+':''}${x.toFixed(d)}%`:'-'};
export const tone=(v:any)=>{const x=Number(v);return !Number.isFinite(x)||x===0?'flat':x>0?'red':'green'};
export const toneCls=(v:any)=>`v86-${tone(v)}`;
export const code=(r:any)=>str(r?.stock_code||r?.code||r?.symbol||r?.etf_code);
export const name=(r:any)=>str(r?.stock_name||r?.name||r?.title||r?.etf_name);
export const ecode=(r:any)=>str(r?.etf_code||r?.code||r?.stock_code);
export const ename=(r:any)=>str(r?.etf_name||r?.name||r?.stock_name);
export const price=(r:any)=>r?.price??r?.close_price??r?.close??r?.last_price??r?.stock_price??r?.etf_price;
export const cpct=(r:any)=>r?.change_pct??r?.changePct??r?.pct??r?.pct_chg??r?.return_pct??r?.day_return;
export const mvb=(r:any)=>{const x=Number(r?.market_value_billion??r?.value_billion??r?.holding_value_billion??r?.amount_billion??r?.aum_billion);if(Number.isFinite(x))return x;const y=Number(r?.market_value??r?.holding_value??r?.amount);return Number.isFinite(y)?y/100000000:NaN};
export const lots=(r:any)=>{const x=Number(r?.shares_lots??r?.lots??r?.holding_lots);if(Number.isFinite(x))return x;const y=Number(r?.shares??r?.holding_shares);return Number.isFinite(y)?y/1000:NaN};
export const region=(r:any)=>{const c=ecode(r); if(c==='00986A'||c==='00998A')return '全球'; return r?.region||r?.investment_region||r?.investmentRegion||r?.area||r?.market_region||'-'};
export const ddate=(d:any)=>d?.data_date||d?.latest_date||d?.latestDate||d?.date||d?.updated_date||'';
export const chartRows=(d:any,fb:any[]=[])=>{const a=d?.price_history||d?.priceHistory||d?.chart||d?.history||d?.priceRows||d?.price_rows||fb;return Array.isArray(a)?a.map((r:any,i:number)=>({date:str(r.trade_date||r.date||r.data_date||r.updated_at||i),value:num(r.close_price??r.price??r.close??r.total_shares??r.shares_lots??r.weight??r.value,NaN)})).filter((x:any)=>Number.isFinite(x.value)).slice(-120):[]};
export function fav(code:string,name:string,type:'etf'|'stock'){if(typeof window==='undefined')return;const k='active_etf_favorites_v86';const a=JSON.parse(localStorage.getItem(k)||'[]');const ex=a.some((x:any)=>x.code===code&&x.type===type);localStorage.setItem(k,JSON.stringify((ex?a.filter((x:any)=>!(x.code===code&&x.type===type)):[{code,name,type,ts:Date.now()},...a]).slice(0,100)));}
