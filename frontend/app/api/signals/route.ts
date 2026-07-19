import { NextRequest } from 'next/server';
import { apiGet } from '@/lib/api';
import { createClient } from '@supabase/supabase-js';

type Universe =
  | 'active'
  | 'reference'
  | 'all';

type AnyObject =
  Record<string, any>;

const ROW_ALIASES = [
  'rows',
  'items',
  'allRows',
  'changes',
  'signals',
  'rawChanges',
  'all_changes',
] as const;

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
) {
  return `${universe}::${String(
    type || '',
  )}`;
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
      'api_route_latest',
    cache_key:
      data.cache_key,
    cache_updated_at:
      data.updated_at,
    cache_data_date:
      data.data_date,
  };
}

function parseSignalNumber(
  value: unknown,
): number | null {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return null;
  }

  if (
    typeof value ===
    'number'
  ) {
    return Number.isFinite(value)
      ? value
      : null;
  }

  const parsed = Number(
    String(value)
      .replace(/,/g, '')
      .replace(/[^\d.-]/g, ''),
  );

  return Number.isFinite(parsed)
    ? parsed
    : null;
}

function firstSignalNumber(
  row: AnyObject,
  keys: string[],
): number | null {
  for (const key of keys) {
    const value =
      parseSignalNumber(
        row?.[key],
      );

    if (value !== null) {
      return value;
    }
  }

  return null;
}

function firstSignalText(
  row: AnyObject,
  keys: string[],
): string {
  for (const key of keys) {
    const value = String(
      row?.[key] ?? '',
    ).trim();

    if (value) {
      return value;
    }
  }

  return '';
}

function sourceDelta(
  source: AnyObject,
): number | null {
  const lots =
    firstSignalNumber(
      source,
      [
        'delta_shares',
        'delta_shares_lots',
        'shares_change',
        'change_lots',
        'delta_lots',
        'display_delta_lots',
      ],
    );

  if (lots !== null) {
    return lots;
  }

  return firstSignalNumber(
    source,
    [
      'delta_raw_shares',
      'deltaRawShares',
      'raw_delta_shares',
    ],
  );
}

function changedEtfCounts(
  sources: unknown,
) {
  if (
    !Array.isArray(sources)
  ) {
    return null;
  }

  const addEtfs =
    new Set<string>();

  const reduceEtfs =
    new Set<string>();

  for (const source of sources) {
    if (
      !source ||
      typeof source !== 'object'
    ) {
      continue;
    }

    const etfCode =
      firstSignalText(
        source,
        [
          'etf_code',
          'etfCode',
          'fund_code',
          'fundCode',
          'etf',
        ],
      );

    if (!etfCode) {
      continue;
    }

    const delta =
      sourceDelta(source);

    if (
      delta === null ||
      Math.abs(delta) <
        0.001
    ) {
      continue;
    }

    if (delta > 0) {
      addEtfs.add(etfCode);
    }

    if (delta < 0) {
      reduceEtfs.add(
        etfCode,
      );
    }
  }

  return {
    buy: addEtfs.size,
    sell:
      reduceEtfs.size,
  };
}

function compactNode(
  value: unknown,
): unknown {
  if (
    Array.isArray(value)
  ) {
    return value.map(
      compactNode,
    );
  }

  if (
    !value ||
    typeof value !== 'object'
  ) {
    return value;
  }

  const source =
    value as AnyObject;

  const changedEtfs =
    Array.isArray(
      source.changed_etfs,
    )
      ? source.changed_etfs
      : Array.isArray(
            source.changedEtfs,
          )
        ? source.changedEtfs
        : null;

  const counts =
    changedEtfCounts(
      changedEtfs,
    );

  const output:
    AnyObject = {};

  for (
    const [
      key,
      child,
    ] of Object.entries(
      source,
    )
  ) {
    if (
      key ===
        'changed_etfs' ||
      key ===
        'changedEtfs'
    ) {
      continue;
    }

    output[key] =
      compactNode(child);
  }

  if (counts) {
    const existingBuy =
      firstSignalNumber(
        source,
        [
          'buy_count',
          'buyCount',
        ],
      );

    const existingSell =
      firstSignalNumber(
        source,
        [
          'sell_count',
          'sellCount',
        ],
      );

    output.buy_count =
      existingBuy ??
      counts.buy;

    output.sell_count =
      existingSell ??
      counts.sell;
  }

  return output;
}

function sourceRowsOfPayload(
  data: AnyObject,
): any[] {
  for (
    const key
    of ROW_ALIASES
  ) {
    const rows =
      data?.[key];

    if (
      Array.isArray(rows)
    ) {
      return rows;
    }
  }

  if (
    Array.isArray(
      data?.aggregate,
    )
  ) {
    return data.aggregate;
  }

  return [];
}

function compactSignalsPayload(
  data: any,
) {
  if (
    !data ||
    typeof data !== 'object'
  ) {
    return data;
  }

  const rowAliasSet =
    new Set<string>(
      ROW_ALIASES,
    );

  const sourceRows =
    sourceRowsOfPayload(
      data,
    );

  const output:
    AnyObject = {};

  for (
    const [
      key,
      value,
    ] of Object.entries(
      data,
    )
  ) {
    /*
      所有列表別名都先略過，
      最後只輸出一份 rows。
    */
    if (
      rowAliasSet.has(key)
    ) {
      continue;
    }

    output[key] =
      compactNode(value);
  }

  output.rows =
    sourceRows.map(
      compactNode,
    );

  output.compact_payload =
    true;

  output.compact_version =
    1;

  return output;
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
    const cached =
      await readLatestCache(
        type,
        days,
        universe,
      );

    if (cached) {
      const responseData =
        full
          ? cached
          : compactSignalsPayload(
              cached,
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
