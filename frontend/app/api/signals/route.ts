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
  return NextResponse.json(data);
}
