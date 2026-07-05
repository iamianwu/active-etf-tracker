import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || '';

const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

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

type InstitutionalRow = {
  security_code: string;
  security_name: string | null;
  trade_date: string;
  market: string;

  foreign_net: number;
  trust_net: number;

  dealer_self_net: number;
  dealer_hedge_net: number;
  dealer_net: number;

  institutional_net: number;
};

type InstitutionalSum = {
  foreign_net: number;
  trust_net: number;
  dealer_self_net: number;
  dealer_hedge_net: number;
  dealer_net: number;
  institutional_net: number;
};

function numberOf(value: unknown): number {
  const result = Number(value);
  return Number.isFinite(result) ? result : 0;
}

function normalizeRow(row: any): InstitutionalRow {
  return {
    security_code: String(row.security_code || ''),
    security_name: row.security_name
      ? String(row.security_name)
      : null,
    trade_date: String(row.trade_date || '').slice(0, 10),
    market: String(row.market || ''),

    foreign_net: numberOf(row.foreign_net),
    trust_net: numberOf(row.trust_net),

    dealer_self_net: numberOf(row.dealer_self_net),
    dealer_hedge_net: numberOf(row.dealer_hedge_net),
    dealer_net: numberOf(row.dealer_net),

    institutional_net: numberOf(
      row.institutional_net
    ),
  };
}

function sumRows(
  rows: InstitutionalRow[]
): InstitutionalSum {
  return rows.reduce<InstitutionalSum>(
    (sum, row) => ({
      foreign_net:
        sum.foreign_net + row.foreign_net,
      trust_net:
        sum.trust_net + row.trust_net,
      dealer_self_net:
        sum.dealer_self_net +
        row.dealer_self_net,
      dealer_hedge_net:
        sum.dealer_hedge_net +
        row.dealer_hedge_net,
      dealer_net:
        sum.dealer_net + row.dealer_net,
      institutional_net:
        sum.institutional_net +
        row.institutional_net,
    }),
    {
      foreign_net: 0,
      trust_net: 0,
      dealer_self_net: 0,
      dealer_hedge_net: 0,
      dealer_net: 0,
      institutional_net: 0,
    }
  );
}

export async function GET(request: NextRequest) {
  const code = String(
    request.nextUrl.searchParams.get('code') || ''
  )
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
    .from('institutional_trading_daily')
    .select(`
      security_code,
      security_name,
      trade_date,
      market,
      foreign_net,
      trust_net,
      dealer_self_net,
      dealer_hedge_net,
      dealer_net,
      institutional_net
    `)
    .eq('security_code', code)
    .order('trade_date', {
      ascending: false,
    })
    .limit(80);

  if (error) {
    console.error(
      '[institutional-trading] query failed:',
      error.message
    );

    return NextResponse.json(
      {
        error: 'institutional_query_failed',
        message: error.message,
      },
      {
        status: 500,
      }
    );
  }

  const rows = Array.isArray(data)
    ? data.map(normalizeRow)
    : [];

  if (!rows.length) {
    return NextResponse.json(
      {
        code,
        found: false,
        latest: null,
        recent_5_days: null,
        recent_20_days: null,
        history: [],
      },
      {
        status: 404,
        headers: {
          'Cache-Control':
            'public, s-maxage=900, stale-while-revalidate=3600',
        },
      }
    );
  }

  const latest = rows[0];
  const recent5 = rows.slice(0, 5);
  const recent20 = rows.slice(0, 20);

  return NextResponse.json(
    {
      code,
      found: true,
      security_name: latest.security_name,
      market: latest.market,
      latest,
      recent_5_days: {
        trading_days: recent5.length,
        start_date:
          recent5[recent5.length - 1]?.trade_date ||
          null,
        end_date: recent5[0]?.trade_date || null,
        totals: sumRows(recent5),
      },
      recent_20_days: {
        trading_days: recent20.length,
        start_date:
          recent20[recent20.length - 1]
            ?.trade_date || null,
        end_date: recent20[0]?.trade_date || null,
        totals: sumRows(recent20),
      },
      available_days: rows.length,
      history: [...rows].reverse(),
      unit: 'shares',
    },
    {
      headers: {
        'Cache-Control':
          'public, s-maxage=900, stale-while-revalidate=3600',
      },
    }
  );
}
