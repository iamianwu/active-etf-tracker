import { NextResponse } from 'next/server';
import { apiGet } from '@/lib/api';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  try {
    const rows: any[] = await apiGet('/holdings');

    const codes = Array.from(new Set(
      (rows || [])
        .map((r: any) => String(r.stock_code || '').trim())
        .filter((x: string) => /^[0-9]{4}$/.test(x))
    ));

    codes.sort();

    return NextResponse.json({
      ok: true,
      count: codes.length,
      codes,
    });
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, error: String(e?.message || e) },
      { status: 500 }
    );
  }
}
