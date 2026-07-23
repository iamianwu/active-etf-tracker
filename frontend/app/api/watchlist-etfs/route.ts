import { NextResponse } from 'next/server';

import {
  getEtfListRows,
  getEtfQuoteMetadataMap,
} from '@/lib/etfData';

import {
  REFERENCE_ETFS,
} from '@/lib/referenceEtfs';

export const revalidate = 60;

export async function GET() {
  try {
    const [activeRows, referenceQuoteMap] =
      await Promise.all([
        getEtfListRows(),
        getEtfQuoteMetadataMap(
          REFERENCE_ETFS.map((row) => row.code),
        ),
      ]);

    const active = (
      activeRows || []
    ).map((row: any) => ({
      ...row,
      etf_group: 'active',
    }));

    const reference =
      REFERENCE_ETFS.map((row) => ({
        ...(referenceQuoteMap[row.code] || {}),
        ...row,
        etf_code: row.code,
        etf_name: row.name,
        etf_group: 'reference',
        reference_role: row.role,
        region: row.market,
        has_holding_data: false,
      }));

    return NextResponse.json(
      {
        rows: [
          ...active,
          ...reference,
        ],
        active_count: active.length,
        reference_count:
          reference.length,
      },
      {
        headers: {
          'Cache-Control':
            'public, s-maxage=60, stale-while-revalidate=600',
        },
      },
    );
  } catch (error: any) {
    return NextResponse.json(
      {
        rows: [],
        error:
          String(
            error?.message || error,
          ),
      },
      {
        status: 500,
      },
    );
  }
}
