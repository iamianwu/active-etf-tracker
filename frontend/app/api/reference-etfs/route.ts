import { NextResponse } from 'next/server';
import { REFERENCE_ETFS } from '@/lib/referenceEtfs';

export const dynamic = 'force-dynamic';

export async function GET() {
  return NextResponse.json(
    {
      generated_at: new Date().toISOString(),
      total: REFERENCE_ETFS.length,
      include_in_today_signal: false,
      note: '一般 ETF 僅作為參考對照，不納入主動式 ETF 今日訊號計算。',
      rows: REFERENCE_ETFS,
    },
    {
      headers: {
        'Cache-Control': 'no-store, max-age=0',
      },
    }
  );
}
