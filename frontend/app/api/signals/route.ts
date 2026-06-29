import { NextRequest } from 'next/server';
import { apiGet } from '@/lib/api';
import { supabase } from '@/lib/supabaseClient';

function one(v: string | null): string {
  return v || '';
}

function normalizeUniverse(input: string): 'active' | 'reference' | 'all' {
  const raw = String(input || 'active').toLowerCase();
  if (raw === 'reference' || raw === 'passive' || raw === 'general') return 'reference';
  if (raw === 'all') return 'all';
  return 'active';
}

function normalizeDays(input: string): number {
  const n = Number(input || 1);
  if (!Number.isFinite(n)) return 1;
  return Math.max(1, Math.trunc(n));
}

function makeSignalType(type: string, universe: 'active' | 'reference' | 'all') {
  return `${universe}::${String(type || '')}`;
}

async function readLatestCache(type: string, days: number, universe: 'active' | 'reference' | 'all') {
  const signalType = makeSignalType(type, universe);

  const { data, error } = await supabase
    .from('signals_cache')
    .select('payload,cache_key,updated_at,data_date,days,signal_type')
    .eq('days', days)
    .eq('signal_type', signalType)
    .order('updated_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) {
    console.warn('[api/signals] readLatestCache failed:', error.message);
    return null;
  }

  if (!data?.payload) return null;

  return {
    ...data.payload,
    cache_hit: true,
    cache_mode: 'api_route_latest',
    cache_key: data.cache_key,
    cache_updated_at: data.updated_at,
    cache_data_date: data.data_date,
  };
}

function cacheHeaders(data: any, fresh: string, universe: string) {
  const headers = new Headers();

  headers.set('Content-Type', 'application/json; charset=utf-8');
  headers.set('X-API-Route-Version', 'signals-cdn-v4-direct-cache');
  headers.set('X-Signals-Universe', String(data?.universe || data?.etf_universe || universe || ''));
  headers.set('X-Signals-Cache-Hit', String(Boolean(data?.cache_hit)));
  headers.set('X-Signals-Cache-Mode', String(data?.cache_mode || ''));
  headers.set('X-Signals-Cache-Key', String(data?.cache_key || ''));
  headers.set('X-Signals-Data-Date', String(data?.data_date || ''));

  if (fresh) {
    headers.set('Cache-Control', 'no-store');
    headers.set('CDN-Cache-Control', 'no-store');
    headers.set('Vercel-CDN-Cache-Control', 'no-store');
  } else {
    headers.set('Cache-Control', 'public, max-age=60, s-maxage=1800, stale-while-revalidate=86400');
    headers.set('CDN-Cache-Control', 'public, s-maxage=1800, stale-while-revalidate=86400');
    headers.set('Vercel-CDN-Cache-Control', 'public, s-maxage=1800, stale-while-revalidate=86400');
  }

  return headers;
}

export async function GET(req: NextRequest) {
  const daysText =
    one(req.nextUrl.searchParams.get('days')) ||
    one(req.nextUrl.searchParams.get('rangeDays')) ||
    one(req.nextUrl.searchParams.get('signalRangeDays')) ||
    '1';

  const days = normalizeDays(daysText);
  const type = one(req.nextUrl.searchParams.get('type'));
  const universeText =
    one(req.nextUrl.searchParams.get('universe')) ||
    one(req.nextUrl.searchParams.get('etfUniverse')) ||
    'active';

  const universe = normalizeUniverse(universeText);
  const fresh = one(req.nextUrl.searchParams.get('fresh'));
  const cv = one(req.nextUrl.searchParams.get('cv'));

  if (!fresh) {
    const cached = await readLatestCache(type, days, universe);
    if (cached) {
      return new Response(JSON.stringify(cached), {
        status: 200,
        headers: cacheHeaders(cached, fresh, universe),
      });
    }
  }

  const qs = new URLSearchParams();
  qs.set('days', String(days));
  if (type) qs.set('type', type);
  qs.set('universe', universe);
  if (fresh) qs.set('fresh', fresh);
  if (cv) qs.set('cv', cv);

  const data = await apiGet(`/signals?${qs.toString()}`);

  return new Response(JSON.stringify(data), {
    status: 200,
    headers: cacheHeaders(data, fresh, universe),
  });
}
