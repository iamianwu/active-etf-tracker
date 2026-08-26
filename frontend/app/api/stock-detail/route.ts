import { NextRequest, NextResponse } from 'next/server';
import { apiGet } from '@/lib/api';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET(req: NextRequest) {
  const code = String(req.nextUrl.searchParams.get('code') || '').trim();

  if (!/^[0-9]{4}$/.test(code)) {
    return NextResponse.json({ ok: false, error: 'invalid code' }, { status: 400 });
  }

  try {
    const fresh = ["1", "true", "yes"].includes(
      String(req.nextUrl.searchParams.get("fresh") || "").toLowerCase()
    );
    const operationsOnly = ["1", "true", "yes"].includes(
      String(req.nextUrl.searchParams.get("operationsOnly") || "").toLowerCase()
    );
    const operationDate = String(
      req.nextUrl.searchParams.get("date") || ""
    ).slice(0, 10);

    const data = await apiGet(
      `/stocks/${code}?fresh=${fresh ? "1" : "0"}`
    );

    if (operationsOnly) {
      const payload = (
        data && typeof data === "object" && data.data && typeof data.data === "object"
          ? data.data
          : data
      ) as Record<string, any>;
      const records = Array.isArray(payload?.operation_records)
        ? payload.operation_records
        : Array.isArray(payload?.operationRecords)
          ? payload.operationRecords
          : Array.isArray(payload?.recent_operations)
            ? payload.recent_operations
            : [];
      const operationRecords = operationDate
        ? records.filter((row: any) => {
            const rowDate = String(
              row?.data_date || row?.date || row?.trade_date || ""
            ).slice(0, 10);
            return rowDate === operationDate;
          })
        : records;

      return NextResponse.json(
        {
          stock_code: String(payload?.stock_code || code),
          data_date: operationDate || String(
            operationRecords[0]?.data_date || ""
          ).slice(0, 10),
          operation_records: operationRecords,
        },
        {
          headers: {
            'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=300',
          },
        }
      );
    }

    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=300',
      },
    });
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, code, error: String(e?.message || e) },
      { status: 500 }
    );
  }
}
