import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { ETF_CODES } from '@/lib/etfData';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

type AnyRow = Record<string, any>;

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

function dateOnly(value: any) {
  return String(value || '').slice(0, 10);
}

function number(value: any) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

async function selectPaged(
  supabase: any,
  table: string,
  columns: string,
  build: (query: any) => any,
) {
  const output: AnyRow[] = [];
  const pageSize = 1000;

  for (let from = 0; ; from += pageSize) {
    const query = build(
      supabase
        .from(table)
        .select(columns)
        .range(from, from + pageSize - 1),
    );
    const { data, error } = await query;

    if (error) {
      throw new Error(`${table}: ${error.message}`);
    }

    const rows = data || [];
    output.push(...rows);

    if (rows.length < pageSize) break;
  }

  return output;
}

async function loadDatePairs(
  supabase: any,
  targetDate: string,
) {
  const pairs: Record<string, string> = {};
  const missingTargetEtfs: string[] = [];
  const codes = Array.from(new Set(
    (ETF_CODES || [])
      .map((value) => String(value || '').trim().toUpperCase())
      .filter((value) => value.endsWith('A')),
  ));
  const batchSize = 6;

  for (let start = 0; start < codes.length; start += batchSize) {
    const batch = codes.slice(start, start + batchSize);
    const results = await Promise.all(
      batch.map(async (etfCode) => {
        const { data, error } = await supabase
          .from('holdings')
          .select('data_date')
          .eq('etf_code', etfCode)
          .lte('data_date', targetDate)
          .order('data_date', { ascending: false })
          .limit(1000);

        if (error) {
          throw new Error(`holdings ${etfCode}: ${error.message}`);
        }

        const dates = Array.from(new Set(
          (data || [])
            .map((row: AnyRow) => dateOnly(row.data_date))
            .filter(Boolean),
        )).sort().reverse();

        return {
          etfCode,
          current: dates[0] || '',
          previous: dates.find((date) => date < targetDate) || '',
        };
      }),
    );

    for (const result of results) {
      if (result.current !== targetDate) {
        missingTargetEtfs.push(result.etfCode);
        continue;
      }

      if (result.previous) {
        pairs[result.etfCode] = result.previous;
      }
    }
  }

  return {
    pairs,
    missingTargetEtfs,
    configuredEtfCount: codes.length,
  };
}

export async function GET(req: NextRequest) {
  const targetDate = dateOnly(req.nextUrl.searchParams.get('date'));

  if (!/^\d{4}-\d{2}-\d{2}$/.test(targetDate)) {
    return NextResponse.json(
      { ok: false, error: 'invalid date' },
      { status: 400 },
    );
  }

  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    return NextResponse.json(
      { ok: false, error: 'missing Supabase environment' },
      { status: 500 },
    );
  }

  try {
    const supabase = createClient(
      SUPABASE_URL,
      SUPABASE_ANON_KEY,
      {
        auth: {
          persistSession: false,
          autoRefreshToken: false,
        },
      },
    );
    const {
      pairs,
      missingTargetEtfs,
      configuredEtfCount,
    } = await loadDatePairs(supabase, targetDate);
    const includedEtfs = Object.keys(pairs).sort();
    const neededDates = Array.from(new Set([
      targetDate,
      ...Object.values(pairs),
    ])).sort();
    const holdings = includedEtfs.length
      ? await selectPaged(
          supabase,
          'holdings',
          'etf_code,data_date,stock_code,stock_name,shares,weight',
          (query) => query
            .in('etf_code', includedEtfs)
            .in('data_date', neededDates)
            .order('etf_code', { ascending: true })
            .order('data_date', { ascending: true })
            .order('stock_code', { ascending: true }),
        )
      : [];
    const rowsByEtfDate: Record<
      string,
      Record<string, Record<string, AnyRow>>
    > = {};

    for (const row of holdings) {
      const etfCode = String(row.etf_code || '').trim().toUpperCase();
      const dataDate = dateOnly(row.data_date);
      const stockCode = String(row.stock_code || '').trim();

      if (!etfCode || !dataDate || !/^\d{4}$/.test(stockCode)) continue;

      rowsByEtfDate[etfCode] ||= {};
      rowsByEtfDate[etfCode][dataDate] ||= {};
      rowsByEtfDate[etfCode][dataDate][stockCode] = row;
    }

    const operationRecords: AnyRow[] = [];

    for (const etfCode of includedEtfs) {
      const previousDate = pairs[etfCode];
      const currentRows = rowsByEtfDate[etfCode]?.[targetDate] || {};
      const previousRows = rowsByEtfDate[etfCode]?.[previousDate] || {};
      const stockCodes = new Set([
        ...Object.keys(currentRows),
        ...Object.keys(previousRows),
      ]);

      for (const stockCode of stockCodes) {
        const current = currentRows[stockCode];
        const previous = previousRows[stockCode];
        const currentShares = number(current?.shares);
        const previousShares = number(previous?.shares);
        const deltaRawShares = currentShares - previousShares;

        if (Math.abs(deltaRawShares) < 0.000001) continue;

        const status = !previous && current
          ? '新增'
          : previous && !current
            ? '刪除'
            : deltaRawShares > 0
              ? '加碼'
              : '減碼';

        operationRecords.push({
          data_date: targetDate,
          prev_date: previousDate,
          etf_code: etfCode,
          stock_code: stockCode,
          stock_name: current?.stock_name || previous?.stock_name || stockCode,
          prev_raw_shares: previousShares,
          curr_raw_shares: currentShares,
          delta_raw_shares: deltaRawShares,
          delta_shares: deltaRawShares / 1000,
          prev_weight: number(previous?.weight),
          curr_weight: number(current?.weight),
          status,
          operation_status: status,
        });
      }
    }

    operationRecords.sort((a, b) =>
      String(a.stock_code).localeCompare(String(b.stock_code)) ||
      String(a.etf_code).localeCompare(String(b.etf_code)),
    );

    return NextResponse.json(
      {
        ok: true,
        data_date: targetDate,
        configured_etf_count: configuredEtfCount,
        included_etf_count: includedEtfs.length,
        included_etfs: includedEtfs,
        missing_target_etfs: missingTargetEtfs.sort(),
        operation_count: operationRecords.length,
        operation_records: operationRecords,
      },
      {
        headers: {
          'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=3600',
          'X-Operation-Snapshot-Version': 'v1',
        },
      },
    );
  } catch (error: any) {
    return NextResponse.json(
      {
        ok: false,
        data_date: targetDate,
        error: String(error?.message || error),
      },
      { status: 500 },
    );
  }
}
