import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { apiGet } from '@/lib/api';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const supabase = createClient(supabaseUrl, supabaseKey, { auth: { persistSession: false } });

let etfCache: { at: number; rows: any[] } | null = null;
const searchCache: Record<string, { at: number; data: any }> = {};

async function searchEtfs(keyword: string) {
  const now = Date.now();

  if (!etfCache || now - etfCache.at > 10 * 60 * 1000) {
    let rows: any[] = [];
    try {
      const data = await apiGet('/etfs');
      rows = Array.isArray(data) ? data : [];
    } catch {
      rows = [];
    }
    etfCache = { at: now, rows };
  }

  const k = keyword.toLowerCase();

  return etfCache.rows
    .filter((x: any) =>
      String(x.etf_code || '').toLowerCase().includes(k) ||
      String(x.etf_name || '').toLowerCase().includes(k)
    )
    .slice(0, 20);
}

function mergeStocks(rows: any[]) {
  const map: Record<string, any> = {};

  for (const r of rows || []) {
    const code = String(r.stock_code || '').trim();
    if (!code) continue;

    if (!map[code]) {
      map[code] = {
        stock_code: code,
        stock_name: r.stock_name || code,
        etf_count: Number(r.etf_count || 0),
        total_weight: Number(r.total_weight || 0),
        data_date: r.data_date || null,
      };
    }
  }

  return Object.values(map)
    .sort((a: any, b: any) => {
      if (b.etf_count !== a.etf_count) return b.etf_count - a.etf_count;
      return b.total_weight - a.total_weight;
    })
    .slice(0, 40);
}

async function searchStocks(keyword: string) {
  const isCode = /^\d{1,5}$/.test(keyword);

  if (isCode) {
    const { data, error } = await supabase
      .from('stock_search_index')
      .select('stock_code,stock_name,data_date,etf_count,total_weight')
      .like('stock_code', `${keyword}%`)
      .order('etf_count', { ascending: false })
      .order('total_weight', { ascending: false })
      .limit(40);

    if (error) {
      console.warn('[search] stock_search_index code search failed:', error.message);
      return [];
    }

    return data || [];
  }

  const [codeResult, nameResult] = await Promise.all([
    supabase
      .from('stock_search_index')
      .select('stock_code,stock_name,data_date,etf_count,total_weight')
      .ilike('stock_code', `%${keyword}%`)
      .order('etf_count', { ascending: false })
      .order('total_weight', { ascending: false })
      .limit(40),

    supabase
      .from('stock_search_index')
      .select('stock_code,stock_name,data_date,etf_count,total_weight')
      .ilike('stock_name', `%${keyword}%`)
      .order('etf_count', { ascending: false })
      .order('total_weight', { ascending: false })
      .limit(40),
  ]);

  if (codeResult.error) console.warn('[search] stock code search failed:', codeResult.error.message);
  if (nameResult.error) console.warn('[search] stock name search failed:', nameResult.error.message);

  return mergeStocks([...(codeResult.data || []), ...(nameResult.data || [])]);
}

export async function GET(req: NextRequest) {
  const q = String(req.nextUrl.searchParams.get('q') || '').trim();
  const key = q.toLowerCase();

  if (!q) {
    return NextResponse.json({ etfs: [], stocks: [] });
  }

  const cached = searchCache[key];
  if (cached && Date.now() - cached.at < 5 * 60 * 1000) {
    return NextResponse.json({ ...cached.data, cached: true });
  }

  const [etfs, stocks] = await Promise.all([
    searchEtfs(q),
    searchStocks(q),
  ]);

  const data = { etfs, stocks };
  searchCache[key] = { at: Date.now(), data };

  return NextResponse.json(data);
}
