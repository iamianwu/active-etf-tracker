import { NextRequest } from 'next/server';
import { apiGet } from '@/lib/api';

function one(v: string | null): string {
  return v || '';
}

function cacheHeaders(data: any, fresh: string, universe: string) {
  const headers = new Headers();

  headers.set('Content-Type', 'application/json; charset=utf-8');
  headers.set('X-API-Route-Version', 'signals-cdn-v3-universe');
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
  const days =
    one(req.nextUrl.searchParams.get('days')) ||
    one(req.nextUrl.searchParams.get('rangeDays')) ||
    one(req.nextUrl.searchParams.get('signalRangeDays')) ||
    '1';

  const type = one(req.nextUrl.searchParams.get('type'));
  const universe =
    one(req.nextUrl.searchParams.get('universe')) ||
    one(req.nextUrl.searchParams.get('etfUniverse'));

  const fresh = one(req.nextUrl.searchParams.get('fresh'));
  const cv = one(req.nextUrl.searchParams.get('cv'));

  const qs = new URLSearchParams();
  qs.set('days', days);
  if (type) qs.set('type', type);
  if (universe) qs.set('universe', universe);
  if (fresh) qs.set('fresh', fresh);
  if (cv) qs.set('cv', cv);

  const data = await apiGet(`/signals?${qs.toString()}`);

  return new Response(JSON.stringify(data), {
    status: 200,
    headers: cacheHeaders(data, fresh, universe),
  });
}
