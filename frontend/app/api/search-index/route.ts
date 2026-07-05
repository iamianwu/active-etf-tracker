import {
  NextResponse,
} from 'next/server';

import {
  createClient,
} from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

const CACHE_KEY =
  'search:index:v1';

const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || '';

const supabaseKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

const supabase = createClient(
  supabaseUrl,
  supabaseKey,
  {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
    },
  }
);

export async function GET() {
  if (!supabaseUrl || !supabaseKey) {
    return NextResponse.json(
      {
        error:
          'missing_supabase_config',
      },
      {
        status: 500,
      }
    );
  }

  const { data, error } =
    await supabase
      .from('app_cache')
      .select(`
        payload,
        data_date,
        updated_at
      `)
      .eq('cache_key', CACHE_KEY)
      .maybeSingle();

  if (error) {
    console.error(
      '[search-index] cache read failed:',
      error.message
    );

    return NextResponse.json(
      {
        error:
          'search_index_cache_failed',
        message: error.message,
      },
      {
        status: 500,
      }
    );
  }

  if (!data?.payload) {
    return NextResponse.json(
      {
        error:
          'search_index_not_ready',
        message:
          '搜尋索引尚未建立',
      },
      {
        status: 503,
      }
    );
  }

  return NextResponse.json(
    {
      ...data.payload,
      cache_key: CACHE_KEY,
      data_date: data.data_date,
      updated_at: data.updated_at,
    },
    {
      headers: {
        'Cache-Control':
          'public, s-maxage=3600, stale-while-revalidate=86400',
      },
    }
  );
}
