import { NextRequest, NextResponse } from 'next/server';
import { apiGet } from '@/lib/api';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

function one(v: string | null): string {
  return v || '';
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

  const res = NextResponse.json(data);

  if (fresh) {
    res.headers.set('Cache-Control', 'no-store');
  } else {
    res.headers.set('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=3600');
  }

  res.headers.set('X-Signals-Cache-Hit', String(Boolean(data?.cache_hit)));
  res.headers.set('X-Signals-Cache-Mode', String(data?.cache_mode || ''));
  res.headers.set('X-Signals-Data-Date', String(data?.data_date || ''));

  return res;
}
