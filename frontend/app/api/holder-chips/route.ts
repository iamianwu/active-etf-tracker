import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

const supabase = createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
  {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
    },
  }
);

function numberOf(value: unknown): number {
  const result = Number(value);
  return Number.isFinite(result) ? result : 0;
}

function dateMs(value: unknown): number {
  const text = String(value || '').slice(0, 10);

  if (!text) return Number.NaN;

  return Date.parse(`${text}T00:00:00Z`);
}

function normalizeRow(row: any) {
  if (!row) return null;

  return {
    security_code: String(row.security_code || ''),
    data_date: String(row.data_date || '').slice(0, 10),
    retail_ratio: numberOf(row.retail_ratio),
    major_ratio: numberOf(row.major_ratio),
    thousand_holder_count: numberOf(
      row.thousand_holder_count
    ),
    thousand_holder_ratio: numberOf(
      row.thousand_holder_ratio
    ),
    total_holder_count: numberOf(
      row.total_holder_count
    ),
    total_shares: numberOf(row.total_shares),
    source: String(row.source || 'TDCC_OD_1-5'),
    updated_at: row.updated_at || null,
  };
}

export async function GET(request: NextRequest) {
  const rawCode = request.nextUrl.searchParams.get('code');
  const code = String(rawCode || '')
    .trim()
    .toUpperCase();

  if (!/^[0-9A-Z]{4,6}$/.test(code)) {
    return NextResponse.json(
      {
        error: 'invalid_security_code',
        message: '請提供有效的股票或 ETF 代號。',
      },
      {
        status: 400,
      }
    );
  }

  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    return NextResponse.json(
      {
        error: 'missing_supabase_config',
      },
      {
        status: 500,
      }
    );
  }

  const { data, error } = await supabase
    .from('tdcc_holder_summary')
    .select(`
      security_code,
      data_date,
      retail_ratio,
      major_ratio,
      thousand_holder_count,
      thousand_holder_ratio,
      total_holder_count,
      total_shares,
      source,
      updated_at
    `)
    .eq('security_code', code)
    .order('data_date', {
      ascending: false,
    })
    .limit(20);

  if (error) {
    console.error(
      '[holder-chips] query failed:',
      error.message
    );

    return NextResponse.json(
      {
        error: 'holder_chips_query_failed',
        message: error.message,
      },
      {
        status: 500,
      }
    );
  }

  const rows = Array.isArray(data) ? data : [];

  const normalizedRows = rows
    .map((row: any) => normalizeRow(row))
    .filter(Boolean) as Array<
      NonNullable<ReturnType<typeof normalizeRow>>
    >;

  const latest = normalizedRows[0] || null;

  if (!latest) {
    return NextResponse.json(
      {
        code,
        found: false,
        latest: null,
        comparison: null,
        four_week_change: null,
        trend_ready: false,
        history: [],
      },
      {
        status: 404,
        headers: {
          'Cache-Control':
            'public, s-maxage=3600, stale-while-revalidate=86400',
        },
      }
    );
  }

  const latestTimestamp = dateMs(latest.data_date);
  const fourWeekTarget =
    latestTimestamp - 28 * 24 * 60 * 60 * 1000;

  const comparison =
    normalizedRows.find((row) => {
      const timestamp = dateMs(row.data_date);

      return (
        Number.isFinite(timestamp) &&
        timestamp <= fourWeekTarget
      );
    }) || null;

  const fourWeekChange = comparison
    ? {
        retail_ratio:
          latest.retail_ratio -
          comparison.retail_ratio,
        major_ratio:
          latest.major_ratio -
          comparison.major_ratio,
        thousand_holder_count:
          latest.thousand_holder_count -
          comparison.thousand_holder_count,
        thousand_holder_ratio:
          latest.thousand_holder_ratio -
          comparison.thousand_holder_ratio,
      }
    : null;

  return NextResponse.json(
    {
      code,
      found: true,
      latest,
      comparison,
      four_week_change: fourWeekChange,
      trend_ready:
        Boolean(comparison) &&
        normalizedRows.length >= 5,
      history: [...normalizedRows].reverse(),
      source: 'TDCC_OD_1-5',
    },
    {
      headers: {
        'Cache-Control':
          'public, s-maxage=3600, stale-while-revalidate=86400',
      },
    }
  );
}
