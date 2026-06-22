import { NextRequest } from 'next/server';
import { apiGet } from '@/lib/api';

function one(v: string | null): string {
  return v || '';
}

function cacheHeaders(data: any, fresh: string) {
  const headers = new Headers();

  headers.set('Content-Type', 'application/json; charset=utf-8');
  headers.set('X-API-Route-Version', 'signals-cdn-v2');
  headers.set('X-Signals-Cache-Hit', String(Boolean(data?.cache_hit)));
  headers.set('X-Signals-Cache-Mode', String(data?.cache_mode || ''));
  headers.set('X-Signals-Data-Date', String(data?.data_date || ''));

  if (fresh) {
    headers.set('Cache-Control', 'no-store');
    headers.set('CDN-Cache-Control', 'no-store');
    headers.set('Vercel-CDN-Cache-Control', 'no-store');
  } else {
    headers.set('Cache-Control', 'public, max-age=0, s-maxage=300, stale-while-revalidate=3600');
    headers.set('CDN-Cache-Control', 'public, s-maxage=300, stale-while-revalidate=3600');
    headers.set('Vercel-CDN-Cache-Control', 'public, s-maxage=300, stale-while-revalidate=3600');
  }

  return headers;
}

export async function GET(req: NextRequest) {
  const days = one(req.nextUrl.searchParams.get('days')) || '1';
  const type = one(req.nextUrl.searchParams.get('type'));
  const fresh = one(req.nextUrl.searchParams.get('fresh'));

  const qs = new URLSearchParams();
  qs.set('days', days);
  if (type) qs.set('type', type);
  if (fresh) qs.set('fresh', fresh);

  const data = await apiGet(`/signals?${qs.toString()}`);

  return new Response(JSON.stringify(data), {
    status: 200,
    headers: cacheHeaders(data, fresh),
  });
}
