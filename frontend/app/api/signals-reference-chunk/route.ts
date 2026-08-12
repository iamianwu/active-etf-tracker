import { NextRequest } from 'next/server';
import { getSignals } from '@/lib/api';
import { REFERENCE_ETF_CODES } from '@/lib/referenceEtfs';

export const dynamic = 'force-dynamic';
export const maxDuration = 300;

const allowedCodes = new Set(
  REFERENCE_ETF_CODES.map((code) => String(code).trim().toUpperCase()),
);

export async function GET(req: NextRequest) {
  const days = Math.max(
    1,
    Math.trunc(Number(req.nextUrl.searchParams.get('days') || 1)) || 1,
  );
  const requestedCodes = String(req.nextUrl.searchParams.get('codes') || '')
    .split(',')
    .map((code) => code.trim().toUpperCase())
    .filter((code) => allowedCodes.has(code));

  if (!requestedCodes.length || requestedCodes.length > 10) {
    return Response.json(
      { error: 'Provide between 1 and 10 valid reference ETF codes.' },
      { status: 400 },
    );
  }

  const data = await getSignals(null, days, 'reference', requestedCodes);

  return Response.json(data, {
    headers: {
      'Cache-Control': 'no-store',
      'X-Signals-Reference-Chunk-Size': String(requestedCodes.length),
    },
  });
}
