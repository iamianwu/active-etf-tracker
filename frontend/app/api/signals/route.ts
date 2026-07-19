import { NextRequest } from 'next/server';
import { apiGet } from '@/lib/api';
import { createClient } from '@supabase/supabase-js';
import { compactSignalsPayload } from '@/lib/signalsCompact';

type Universe =
  | 'active'
  | 'reference'
  | 'all';

function one(
  value: string | null,
): string {
  return value || '';
}

function normalizeUniverse(
  input: string,
): Universe {
  const raw = String(
    input || 'active',
  ).toLowerCase();

  if (
    raw === 'reference' ||
    raw === 'passive' ||
    raw === 'general'
  ) {
    return 'reference';
  }

  if (raw === 'all') {
    return 'all';
  }

  return 'active';
}

function normalizeDays(
  input: string,
): number {
  const value = Number(
    input || 1,
  );

  if (!Number.isFinite(value)) {
    return 1;
  }

  return Math.max(
    1,
    Math.trunc(value),
  );
}

function makeSignalType(
  type: string,
  universe: Universe,
  compact = false,
) {
  const base =
    `${universe}::${String(
      type || '',
    )}`;

  return compact
    ? `compact::${base}`
    : base;
}

function getSupabaseForCache() {
  const url =
    process.env
      .NEXT_PUBLIC_SUPABASE_URL ||
    process.env.SUPABASE_URL ||
    '';

  const key =
    process.env
      .NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    process.env
      .SUPABASE_ANON_KEY ||
    '';

  if (!url || !key) {
    return null;
  }

  return createClient(
    url,
    key,
    {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
      },
    },
  );
}

async function readLatestCache(
  type: string,
  days: number,
  universe: Universe,
  compact = false,
) {
  const db =
    getSupabaseForCache();

  if (!db) {
    return null;
  }

  const signalType =
    makeSignalType(
      type,
      universe,
      compact,
    );

  const {
    data,
    error,
  } = await db
    .from('signals_cache')
    .select(
      [
        'payload',
        'cache_key',
        'updated_at',
        'data_date',
        'days',
        'signal_type',
      ].join(','),
    )
    .eq('days', days)
    .eq(
      'signal_type',
      signalType,
    )
    .order(
      'updated_at',
      {
        ascending: false,
      },
    )
    .limit(1)
    .maybeSingle();

  if (error) {
    console.warn(
      '[api/signals] readLatestCache failed:',
      error.message,
    );

    return null;
  }

  if (!data?.payload) {
    return null;
  }

  return {
    ...data.payload,
    cache_hit: true,
    cache_mode:
      compact
        ? 'api_route_latest_compact'
        : 'api_route_latest_full',
    cache_key:
      data.cache_key,
    cache_updated_at:
      data.updated_at,
    cache_data_date:
      data.data_date,
  };
}

function cacheHeaders(
  data: any,
  fresh: string,
  universe: string,
  compact: boolean,
) {
  const headers =
    new Headers();

  headers.set(
    'Content-Type',
    'application/json; charset=utf-8',
  );

  headers.set(
    'X-API-Route-Version',
    compact
      ? 'signals-cdn-v5-compact'
      : 'signals-cdn-v5-full',
  );

  headers.set(
    'X-Signals-Universe',
    String(
      data?.universe ||
        data?.etf_universe ||
        universe ||
        '',
    ),
  );

  headers.set(
    'X-Signals-Cache-Hit',
    String(
      Boolean(
        data?.cache_hit,
      ),
    ),
  );

  headers.set(
    'X-Signals-Cache-Mode',
    String(
      data?.cache_mode ||
        '',
    ),
  );

  headers.set(
    'X-Signals-Cache-Key',
    String(
      data?.cache_key ||
        '',
    ),
  );

  headers.set(
    'X-Signals-Data-Date',
    String(
      data?.data_date ||
        '',
    ),
  );

  headers.set(
    'X-Signals-Payload',
    compact
      ? 'compact-v1'
      : 'full',
  );

  if (fresh) {
    headers.set(
      'Cache-Control',
      'no-store',
    );

    headers.set(
      'CDN-Cache-Control',
      'no-store',
    );

    headers.set(
      'Vercel-CDN-Cache-Control',
      'no-store',
    );
  } else {
    headers.set(
      'Cache-Control',
      'public, max-age=60, s-maxage=1800, stale-while-revalidate=86400',
    );

    headers.set(
      'CDN-Cache-Control',
      'public, s-maxage=1800, stale-while-revalidate=86400',
    );

    headers.set(
      'Vercel-CDN-Cache-Control',
      'public, s-maxage=1800, stale-while-revalidate=86400',
    );
  }

  return headers;
}

export async function GET(
  req: NextRequest,
) {
  const daysText =
    one(
      req.nextUrl
        .searchParams
        .get('days'),
    ) ||
    one(
      req.nextUrl
        .searchParams
        .get('rangeDays'),
    ) ||
    one(
      req.nextUrl
        .searchParams
        .get(
          'signalRangeDays',
        ),
    ) ||
    '1';

  const days =
    normalizeDays(
      daysText,
    );

  const type =
    one(
      req.nextUrl
        .searchParams
        .get('type'),
    );

  const universeText =
    one(
      req.nextUrl
        .searchParams
        .get('universe'),
    ) ||
    one(
      req.nextUrl
        .searchParams
        .get(
          'etfUniverse',
        ),
    ) ||
    'active';

  const universe =
    normalizeUniverse(
      universeText,
    );

  const fresh =
    one(
      req.nextUrl
        .searchParams
        .get('fresh'),
    );

  const cv =
    one(
      req.nextUrl
        .searchParams
        .get('cv'),
    );

  const full =
    one(
      req.nextUrl
        .searchParams
        .get('full'),
    ) === '1';

  if (!fresh) {
    if (!full) {
      const compactCached =
        await readLatestCache(
          type,
          days,
          universe,
          true,
        );

      if (compactCached) {
        return new Response(
          JSON.stringify(
            compactCached,
          ),
          {
            status: 200,
            headers:
              cacheHeaders(
                compactCached,
                fresh,
                universe,
                true,
              ),
          },
        );
      }
    }

    const fullCached =
      await readLatestCache(
        type,
        days,
        universe,
        false,
      );

    if (fullCached) {
      const responseData =
        full
          ? fullCached
          : compactSignalsPayload(
              fullCached,
            );

      return new Response(
        JSON.stringify(
          responseData,
        ),
        {
          status: 200,
          headers:
            cacheHeaders(
              responseData,
              fresh,
              universe,
              !full,
            ),
        },
      );
    }
  }

  const qs =
    new URLSearchParams();

  qs.set(
    'days',
    String(days),
  );

  if (type) {
    qs.set(
      'type',
      type,
    );
  }

  qs.set(
    'universe',
    universe,
  );

  if (fresh) {
    qs.set(
      'fresh',
      fresh,
    );
  }

  if (cv) {
    qs.set(
      'cv',
      cv,
    );
  }

  const data =
    await apiGet(
      `/signals?${qs.toString()}`,
    );

  const responseData =
    full
      ? data
      : compactSignalsPayload(
          data,
        );

  return new Response(
    JSON.stringify(
      responseData,
    ),
    {
      status: 200,
      headers:
        cacheHeaders(
          responseData,
          fresh,
          universe,
          !full,
        ),
    },
  );
}
