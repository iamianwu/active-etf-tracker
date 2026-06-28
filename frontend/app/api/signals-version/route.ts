import { NextRequest } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const supabase = createClient(supabaseUrl, supabaseKey, { auth: { persistSession: false } });

function one(v: string | null): string {
  return v || '';
}

function normalizeUniverse(input: string): 'active' | 'reference' | 'all' {
  const raw = String(input || 'active').toLowerCase();
  if (raw === 'reference' || raw === 'passive' || raw === 'general') return 'reference';
  if (raw === 'all') return 'all';
  return 'active';
}

function cacheSignalType(type: string, universe: 'active' | 'reference' | 'all') {
  return `${universe}::${String(type || '')}`;
}

export async function GET(req: NextRequest) {
  const days = Number(one(req.nextUrl.searchParams.get('days')) || '1') || 1;
  const type = one(req.nextUrl.searchParams.get('type'));
  const universe = normalizeUniverse(one(req.nextUrl.searchParams.get('universe')) || 'active');
  const signalType = cacheSignalType(type, universe);

  const { data, error } = await supabase
    .from('signals_cache')
    .select('cache_key,data_date,updated_at,days,signal_type')
    .eq('days', days)
    .eq('signal_type', signalType)
    .order('updated_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  const payload = {
    ok: !error,
    days,
    type,
    universe,
    signal_type: signalType,
    data_date: data?.data_date || null,
    updated_at: data?.updated_at || null,
    cache_key: data?.cache_key || null,
    version: data?.cache_key && data?.updated_at ? `${data.cache_key}:${data.updated_at}` : data?.cache_key || data?.updated_at || 'none',
    error: error?.message || null,
  };

  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      'CDN-Cache-Control': 'no-store',
      'Vercel-CDN-Cache-Control': 'no-store',
    },
  });
}
