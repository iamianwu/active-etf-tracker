import { NextRequest, NextResponse } from 'next/server';
import { apiGet } from '@/lib/api';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(req: NextRequest) {
  const code = String(req.nextUrl.searchParams.get('code') || '').trim();

  if (!/^[0-9]{4}$/.test(code)) {
    return NextResponse.json({ ok: false, error: 'invalid code' }, { status: 400 });
  }

  try {
    const data = await apiGet(`/stocks/${code}`);
    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=300',
      },
    });
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, code, error: String(e?.message || e) },
      { status: 500 }
    );
  }
}
