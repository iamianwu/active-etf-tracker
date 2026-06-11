import { createClient } from '@supabase/supabase-js';
import EtfListClient from '@/components/EtfListClient';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const ETF_CODES = [
  '00980A',
  '00982A',
  '00981A',
  '00983A',
  '00984A',
  '00985A',
  '00986A',
  '00989A',
  '00988A',
  '00991A',
  '00990A',
  '00987A',
  '00992A',
  '00994A',
  '00995A',
  '00993A',
  '00996A',
  '00400A',
  '00401A',
  '00997A',
  '00999A',
  '00403A',
];

const ETF_NAMES: Record<string, string> = {
  '00980A': '主動野村臺灣優選',
  '00981A': '主動統一台股增長',
  '00982A': '主動群益台灣強棒',
  '00983A': '主動中信ARK創新',
  '00984A': '主動安聯台灣高息',
  '00985A': '主動野村台灣50',
  '00986A': '主動元大臺灣價值',
  '00987A': '主動凱基台灣精選',
  '00988A': '主動統一全球創新',
  '00989A': '主動復華未來50',
  '00990A': '主動永豐臺灣ESG',
  '00991A': '主動富邦未來車',
  '00992A': '主動國泰台灣領袖',
  '00993A': '主動台新台灣成長',
  '00994A': '主動第一金台股優',
  '00995A': '主動兆豐台灣科技',
  '00996A': '主動群益科技高息',
  '00997A': '主動中信台灣成長',
  '00999A': '主動台新全球AI',
  '00400A': '主動野村全球優選',
  '00401A': '主動統一美國增長',
  '00403A': '主動統一升級50',
};

function nz(v: any) {
  if (v === null || v === undefined || v === '') return null;
  const n = Number(v);
  if (!Number.isFinite(n)) return null;
  return n;
}

function normalizeQuote(q: any, code: string) {
  const price = nz(q?.price);
  const volume = nz(q?.volume);
  const amount = nz(q?.amount);

  return {
    etf_code: code,
    etf_name: q?.etf_name || ETF_NAMES[code] || code,
    price: price && price > 0 ? price : null,
    change: price && price > 0 ? nz(q?.change) : null,
    change_pct: price && price > 0 ? nz(q?.change_pct) : null,
    volume: volume && volume > 0 ? volume : null,
    amount: amount && amount > 0 ? amount : null,
    aum_billion: nz(q?.aum_billion),
    expense_ratio: nz(q?.expense_ratio),
    inception_date: q?.inception_date || null,
    dividend_frequency: q?.dividend_frequency || null,
    week_return: nz(q?.week_return),
    total_return: nz(q?.total_return),
    dividend_yield: nz(q?.dividend_yield),
    region: q?.region || null,
    currency: q?.currency || null,
    updated_at: q?.updated_at || null,
  };
}

export default async function EtfsPage() {
  const { data, error } = await supabase.from('etf_quotes').select('*');

  if (error) {
    throw new Error(`etf_quotes: ${error.message}`);
  }

  const map: Record<string, any> = {};
  for (const q of data || []) {
    map[String(q.etf_code)] = q;
  }

  const rows = ETF_CODES.map((code) => normalizeQuote(map[code] || {}, code));

  return <EtfListClient rows={rows} />;
}
