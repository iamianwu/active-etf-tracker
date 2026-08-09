import { ETF_CODES, ETF_NAMES, getEtfDetailData, getEtfListRows } from '@/lib/etfData';

export const dynamic = 'force-dynamic';

const MARKET_MAP: Record<string, string> = {
  '00400A': '台灣',
  '00401A': '台灣',
  '00402A': '美國',
  '00403A': '台灣',
  '00404A': '台灣',
  '00405A': '台灣',
  '00406A': '台灣',
  '00407A': '台灣',
  '00410A': '台灣',
  '00980A': '台灣',
  '00981A': '台灣',
  '00982A': '台灣',
  '00983A': '美國',
  '00984A': '台灣',
  '00985A': '台灣',
  '00986A': '全球',
  '00987A': '台灣',
  '00988A': '全球',
  '00989A': '美國',
  '00990A': '全球',
  '00991A': '台灣',
  '00992A': '台灣',
  '00993A': '台灣',
  '00994A': '台灣',
  '00995A': '台灣',
  '00996A': '台灣',
  '00997A': '美國',
  '00998A': '全球',
  '00999A': '台灣',
};

function str(v: any): string {
  return String(v ?? '').trim();
}

function arr(v: any): any[] {
  return Array.isArray(v) ? v : [];
}

function codeOf(r: any): string {
  return str(r?.etf_code ?? r?.code ?? r?.symbol ?? r?.fund_code);
}

function latestDateFromObject(r: any): string {
  return str(
    r?.data_date ??
    r?.trade_date ??
    r?.latest_date ??
    r?.latestDate ??
    r?.date ??
    r?.updated_date ??
    r?.updated_at ??
    r?.dt
  );
}

function latestDateFromRows(rows: any[]): string {
  let best = '';
  for (const r of rows || []) {
    const d = latestDateFromObject(r);
    if (d && (!best || d > best)) best = d;
  }
  return best;
}

function pickHoldings(detail: any): any[] {
  return (
    arr(detail?.holdings).length ? arr(detail?.holdings) :
    arr(detail?.constituents).length ? arr(detail?.constituents) :
    arr(detail?.data?.holdings).length ? arr(detail?.data?.holdings) :
    []
  );
}

function pickPriceHistory(detail: any): any[] {
  return (
    arr(detail?.price_history).length ? arr(detail?.price_history) :
    arr(detail?.priceHistory).length ? arr(detail?.priceHistory) :
    arr(detail?.chart).length ? arr(detail?.chart) :
    arr(detail?.history).length ? arr(detail?.history) :
    []
  );
}

function pickQuote(detail: any, listRow: any): any {
  return detail?.quote || detail?.etf || detail?.summary || listRow || {};
}

function marketOf(code: string, name: string): string {
  return MARKET_MAP[code] || '台灣';
}

export async function GET() {
  const listRows = arr(await getEtfListRows());
  const listByCode: Record<string, any> = {};

  for (const r of listRows) {
    const code = codeOf(r);
    if (code) listByCode[code] = r;
  }

  const detailResults = await Promise.all(
    ETF_CODES.map(async (code) => {
      try {
        const detail = await getEtfDetailData(code);
        const listRow = listByCode[code] || {};
        const quote = pickQuote(detail, listRow);
        const holdings = pickHoldings(detail);
        const priceHistory = pickPriceHistory(detail);

        const name = str(
          detail?.etf_name ??
          detail?.name ??
          quote?.etf_name ??
          quote?.name ??
          listRow?.etf_name ??
          listRow?.name ??
          ETF_NAMES[code] ??
          code
        );

        const quoteDate = latestDateFromObject(quote) || latestDateFromObject(listRow);
        const holdingDate = latestDateFromRows(holdings);
        const priceHistoryDate = latestDateFromRows(priceHistory);

        return {
          code,
          name,
          market: marketOf(code, name),
          quote_date: quoteDate || null,
          holding_date: holdingDate || null,
          holding_count: holdings.length,
          price_history_date: priceHistoryDate || null,
          price_history_count: priceHistory.length,
          has_quote: Boolean(quoteDate),
          has_holdings: holdings.length > 0,
          error: null,
        };
      } catch (err: any) {
        return {
          code,
          name: ETF_NAMES[code] || code,
          market: marketOf(code, ETF_NAMES[code] || code),
          quote_date: null,
          holding_date: null,
          holding_count: 0,
          price_history_date: null,
          price_history_count: 0,
          has_quote: false,
          has_holdings: false,
          error: String(err?.message || err || 'unknown error'),
        };
      }
    })
  );

  const signalHoldingDate = latestDateFromRows(detailResults.map((r) => ({ data_date: r.holding_date })));

  const rows = detailResults.map((r) => {
    let status = '正常';

    if (r.error) status = '錯誤';
    else if (!r.has_quote) status = '缺報價';
    else if (!r.has_holdings) status = '缺成分股';
    else if (signalHoldingDate && r.holding_date !== signalHoldingDate) status = '持股未更新';

    return {
      ...r,
      signal_holding_date: signalHoldingDate || null,
      included_in_today_signal: status === '正常',
      status,
    };
  });

  const summary = rows.reduce((acc: Record<string, number>, r: any) => {
    acc[r.status] = (acc[r.status] || 0) + 1;
    return acc;
  }, {});

  return Response.json(
    {
      generated_at: new Date().toISOString(),
      total: ETF_CODES.length,
      signal_holding_date: signalHoldingDate || null,
      summary,
      rows,
    },
    {
      headers: {
        'Cache-Control': 'no-store',
        'CDN-Cache-Control': 'no-store',
        'Vercel-CDN-Cache-Control': 'no-store',
      },
    }
  );
}
