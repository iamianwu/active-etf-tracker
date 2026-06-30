import { NextRequest, NextResponse } from 'next/server';
import { apiGet } from '@/lib/api';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(req: NextRequest) {
  const code = String(req.nextUrl.searchParams.get('code') || '').trim();
  const started = Date.now();

  if (!/^[0-9]{4}$/.test(code)) {
    return NextResponse.json({ ok: false, error: 'invalid code' }, { status: 400 });
  }

  try {
    const data: any = await apiGet(`/stocks/${code}`);
    const duration_ms = Date.now() - started;

    return NextResponse.json({
      ok: true,
      code,
      duration_ms,
      cache_hit: data?.cache_hit ?? null,
      cache_key: data?.cache_key ?? null,
      cache_updated_at: data?.cache_updated_at ?? null,
      stock_name: data?.stock_name ?? null,
      etf_count: data?.summary?.etf_count ?? null,
      etfs_len: Array.isArray(data?.etfs) ? data.etfs.length : null,
      history_len: Array.isArray(data?.history) ? data.history.length : null,
      price_history_len: Array.isArray(data?.price_history) ? data.price_history.length : null,
      institutional_len: Array.isArray(data?.institutional) ? data.institutional.length : null,
      payload_size: JSON.stringify(data || {}).length,
    });
  } catch (e: any) {
    return NextResponse.json({
      ok: false,
      code,
      duration_ms: Date.now() - started,
      error: String(e?.message || e),
    }, { status: 500 });
  }
}
