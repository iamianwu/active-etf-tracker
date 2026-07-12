'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

type AnyRow = Record<string, any>;
type Status = '新增' | '刪除' | '加碼' | '減碼';
type SortKey = 'code' | 'inflow' | 'outflow' | 'absAmount' | 'lots' | 'price' | 'pct' | 'etfCount'
  | 'deltaWeight'
  | 'consensus';
type SortDir = 'asc' | 'desc';
type FilterKey = '全部' | Status;

const TOTAL_ACTIVE_ETFS = 27;
const STATUSES: Status[] = ['新增', '刪除', '加碼', '減碼'];

function num(v: any, fallback = 0): number {
  if (v === null || v === undefined || v === '') return fallback;
  const x = Number(String(v).replace(/,/g, '').replace(/[^\d.-]/g, ''));
  return Number.isFinite(x) ? x : fallback;
}

function txt(row: AnyRow, keys: string[], fallback = ''): string {
  for (const k of keys) {
    const v = row?.[k];
    if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
  }
  return fallback;
}

function firstNum(row: AnyRow, keys: string[], fallback = NaN): number {
  for (const k of keys) {
    const v = row?.[k];
    if (v !== undefined && v !== null && String(v).trim() !== '') {
      const n = num(v, NaN);
      if (Number.isFinite(n)) return n;
    }
  }
  return fallback;
}

function arr(data: any, keys: string[]): AnyRow[] {
  const out: AnyRow[] = [];
  for (const k of keys) {
    const v = data?.[k];
    if (Array.isArray(v)) out.push(...v);
  }
  return out;
}

function rowsOf(data: any): AnyRow[] {
  const v = data?.rows ?? data?.changes ?? data?.aggregate ?? data?.items ?? data?.signals ?? [];
  return Array.isArray(v) ? v : [];
}

function codeOf(r: AnyRow): string {
  return txt(r, ['stock_code', 'stockCode', 'code', 'symbol']);
}

function nameOf(r: AnyRow): string {
  return txt(r, ['stock_name', 'stockName', 'name', 'stock'], codeOf(r));
}

function etfCodeOf(r: AnyRow): string {
  return txt(r, ['etf_code', 'etfCode', 'fund_code', 'fundCode', 'etf']);
}

function etfNameOf(r: AnyRow): string {
  return txt(r, ['etf_name', 'etfName', 'fund_name', 'fundName'], etfCodeOf(r));
}

function dateOf(r: AnyRow): string {
  return txt(r, ['data_date', 'date', 'trade_date', 'tradeDate', 'dt']);
}

function priceOf(r: AnyRow): number | null {
  const v = firstNum(r, ['price', 'close_price', 'close', 'last_price', 'stock_price'], NaN);
  return Number.isFinite(v) ? v : null;
}

function pctOf(r: AnyRow): number | null {
  const v = firstNum(r, ['change_pct', 'pct', 'percent', 'changePercent', 'price_change_pct'], NaN);
  return Number.isFinite(v) ? v : null;
}

function lotsOf(r: AnyRow): number {
  const lotVal = firstNum(r, [
    'net_lots',
    'display_delta_lots',
    'change_lots',
    'delta_lots',
    'lot_change',
    'shares_lots_change',
    'delta_shares_lots',
    'shares_change_lots',
    'shares_diff_lots',
    'diff_lots',
  ], NaN);
  if (Number.isFinite(lotVal)) return lotVal;

  let shareVal = firstNum(r, [
    'delta_shares',
    'shares_change',
    'shares_diff',
    'diff_shares',
    'shareDiff',
  ], 0);

  if (Math.abs(shareVal) >= 10000) shareVal = shareVal / 1000;
  return shareVal;
}

function amountOf(r: AnyRow): number {
  const direct = firstNum(r, [
    'net_amount_billion',
    'delta_amount_billion',
    'flow_billion',
    'money_billion',
    'amount_billion',
    'delta_value_billion',
    'trade_amount_billion',
    'net_value_billion',
  ], NaN);
  if (Number.isFinite(direct)) return direct;

  const p = priceOf(r);
  const lots = lotsOf(r);
  if (p !== null && Number.isFinite(lots)) return p * lots * 1000 / 100000000;
  return 0;
}

function statusOf(r: AnyRow): Status | null {
  const s = String(r.status ?? r.type ?? r.action ?? '').trim();
  if (STATUSES.includes(s as Status)) return s as Status;

  const lots = lotsOf(r);
  if (lots > 0) return '加碼';
  if (lots < 0) return '減碼';
  return null;
}

function sourceRowsOf(data: any): AnyRow[] {
  const direct = arr(data, [
    'source_rows',
    'sourceRows',
    'detail_rows',
    'detailRows',
    'details',
    'records',
    'operation_records',
    'operationRecords',
    'operations',
    'raw_rows',
    'rawRows',
    'change_rows',
    'changeRows',
  ]);

  const nested = rowsOf(data).flatMap((r) => arr(r, [
    'source_rows',
    'sourceRows',
    'details',
    'records',
    'operation_records',
    'operationRecords',
    'etf_changes',
    'etfChanges',
  ]));

  const fromRows = rowsOf(data).filter((r) => etfCodeOf(r) && codeOf(r));
  const all = [...direct, ...nested, ...fromRows].filter((r) => etfCodeOf(r) && codeOf(r));

  const seen = new Set<string>();
  return all.filter((r) => {
    const key = [dateOf(r), etfCodeOf(r), codeOf(r), lotsOf(r), amountOf(r), statusOf(r) ?? ''].join('|');
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function groupFromSources(src: AnyRow[]): AnyRow[] {
  const m = new Map<string, AnyRow>();

  for (const r of src) {
    const code = codeOf(r);
    if (!code) continue;

    const cur = m.get(code) ?? {
      stock_code: code,
      stock_name: nameOf(r),
      price: priceOf(r),
      change_pct: pctOf(r),
      net_lots: 0,
      net_amount_billion: 0,
      source_rows: [],
    };

    cur.stock_name = cur.stock_name || nameOf(r);
    if (cur.price === null || cur.price === undefined) cur.price = priceOf(r);
    if (cur.change_pct === null || cur.change_pct === undefined) cur.change_pct = pctOf(r);
    cur.net_lots += lotsOf(r);
    cur.net_amount_billion += amountOf(r);
    cur.source_rows.push(r);

    m.set(code, cur);
  }

  return Array.from(m.values());
}

function displayRowsOf(data: any, src: AnyRow[]): AnyRow[] {
  const aggregate = rowsOf(data).filter((r) => codeOf(r) && !etfCodeOf(r));
  if (aggregate.length) return aggregate;
  if (src.length) return groupFromSources(src);
  return rowsOf(data).filter((r) => codeOf(r));
}

function sourcesFor(row: AnyRow, allSrc: AnyRow[]): AnyRow[] {
  const code = codeOf(row);
  const nested = arr(row, [
    'source_rows',
    'sourceRows',
    'details',
    'records',
    'operation_records',
    'operationRecords',
    'etf_changes',
    'etfChanges',
    'changed_etfs',
    'changedEtfs',
  ]);

  const global = allSrc.filter((r) => codeOf(r) === code);
  const seen = new Set<string>();

  return [...nested, ...global]
    .filter((r) => etfCodeOf(r))
    .filter((r) => {
      const key = [dateOf(r), etfCodeOf(r), lotsOf(r), amountOf(r), statusOf(r) ?? ''].join('|');
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function buySell(row: AnyRow, src: AnyRow[]): { buy: number; sell: number } {
  const rowStatus = statusOf(row);

  if (src.length && (rowStatus === '加碼' || rowStatus === '減碼')) {
    const addEtfs = new Set<string>();
    const reduceEtfs = new Set<string>();

    for (const s of src) {
      const etf = etfCodeOf(s);
      if (!etf) continue;

      const deltaLots = firstNum(s, [
        'delta_shares',
        'delta_shares_lots',
        'shares_change',
        'change_lots',
        'delta_lots',
        'display_delta_lots',
      ], NaN);

      const deltaRaw = firstNum(s, [
        'delta_raw_shares',
        'deltaRawShares',
        'raw_delta_shares',
      ], NaN);

      const delta = Number.isFinite(deltaLots)
        ? deltaLots
        : Number.isFinite(deltaRaw)
          ? deltaRaw
          : NaN;

      if (!Number.isFinite(delta) || Math.abs(delta) < 0.001) continue;

      if (delta > 0) addEtfs.add(etf);
      if (delta < 0) reduceEtfs.add(etf);
    }

    return { buy: addEtfs.size, sell: reduceEtfs.size };
  }

  if (rowStatus === '新增' || rowStatus === '刪除') {
    const add = firstNum(row, ['add_count'], NaN);
    const del = firstNum(row, ['delete_count', 'remove_count'], NaN);

    if (Number.isFinite(add) || Number.isFinite(del)) {
      return {
        buy: Math.max(0, Math.round(Number.isFinite(add) ? add : 0)),
        sell: Math.max(0, Math.round(Number.isFinite(del) ? del : 0)),
      };
    }
  }

  if (src.length) {
    const buyEtfs = new Set<string>();
    const sellEtfs = new Set<string>();

    for (const s of src) {
      const etfCode = etfCodeOf(s);
      if (!etfCode) continue;

      const status = statusOf(s);
      const lots = lotsOf(s);

      if (lots > 0 || status === '新增' || status === '加碼') buyEtfs.add(etfCode);
      if (lots < 0 || status === '刪除' || status === '減碼') sellEtfs.add(etfCode);
    }

    return { buy: buyEtfs.size, sell: sellEtfs.size };
  }

  const directBuy = firstNum(row, ['buy_count', 'buy_etf_count', 'add_etf_count', 'increase_count'], NaN);
  const directSell = firstNum(row, ['sell_count', 'sell_etf_count', 'reduce_etf_count', 'decrease_count'], NaN);

  if (Number.isFinite(directBuy) || Number.isFinite(directSell)) {
    return {
      buy: Math.max(0, Math.round(Number.isFinite(directBuy) ? directBuy : 0)),
      sell: Math.max(0, Math.round(Number.isFinite(directSell) ? directSell : 0)),
    };
  }

  const s = statusOf(row);
  if (s === '新增' || s === '加碼') return { buy: 1, sell: 0 };
  if (s === '刪除' || s === '減碼') return { buy: 0, sell: 1 };
  return { buy: 0, sell: 0 };
}

function mmdd(v: any): string {
  const s = String(v ?? '').trim();
  const m = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[2]}-${m[3]}`;
  return s || '-';
}

function fmtUpdatedAt(value: any): string {
  const date = new Date(String(value ?? ''));

  if (!Number.isFinite(date.getTime())) {
    return '-';
  }

  return new Intl.DateTimeFormat('zh-TW', {
    timeZone: 'Asia/Taipei',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
    .format(date)
    .replace(',', '');
}

function fmtPrice(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return '-';
  return v.toLocaleString('zh-TW', { maximumFractionDigits: v >= 100 ? 1 : 2 });
}

function fmtPct(v: number | null): string {
  if (v === null || !Number.isFinite(v)) return '-';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(2)}%`;
}

function fmtLots(v: number): string {
  if (!Number.isFinite(v)) return '-';
  if (Math.abs(v) < 0.01) return '0張';
  const sign = v > 0 ? '+' : '';
  return `${sign}${Math.round(v).toLocaleString('zh-TW')}張`;
}

function fmtBillion(v: number): string {
  if (!Number.isFinite(v)) return '-';
  if (Math.abs(v) < 0.005) return '0億';
  const sign = v > 0 ? '+' : '';
  const abs = Math.abs(v);
  const digits = abs >= 10 ? 1 : 2;
  return `${sign}${v.toLocaleString('zh-TW', { maximumFractionDigits: digits })}億`;
}

function tone(v: number): string {
  if (v > 0) return 'red';
  if (v < 0) return 'green';
  return 'muted';
}

function isLimitUp(row: AnyRow): boolean {
  const p = pctOf(row);
  return p !== null && p >= 9.7;
}

function isLimitDown(row: AnyRow): boolean {
  const p = pctOf(row);
  return p !== null && p <= -9.7;
}

function getTotalEtfs(data: any): number {
  const v = firstNum(data, ['total_etf_count', 'totalEtfCount', 'total_etfs', 'totalEtfs'], NaN);
  return Number.isFinite(v) && v > 0 ? Math.round(v) : TOTAL_ACTIVE_ETFS;
}

function getTodayEtfs(data: any, total: number): number {
  const v = firstNum(data, ['today_etf_count', 'todayEtfCount', 'today_etfs', 'todayEtfs', 'fetched_etf_count', 'includedEtfCount'], NaN);
  if (Number.isFinite(v) && v >= 0) return Math.min(total, Math.round(v));

  const missing = firstNum(data, ['non_today_etf_count', 'nonTodayEtfCount', 'missing_etf_count'], NaN);
  if (Number.isFinite(missing) && missing >= 0) return Math.max(0, total - Math.round(missing));

  return total;
}

function missingRowsOf(data: any): AnyRow[] {
  const dedupeRows = (rows: AnyRow[]): AnyRow[] => {
    const seen = new Set<string>();
    const out: AnyRow[] = [];

    for (const r of rows) {
      const code = etfCodeOf(r) || codeOf(r);
      if (!code || seen.has(code)) continue;
      seen.add(code);
      out.push(r);
    }

    return out;
  };

  const containers = [data, data?.summary, data?.meta, data?.payload, data?.data].filter(Boolean);

  for (const box of containers) {
    const rows = arr(box, ['non_today_etfs', 'nonTodayEtfs', 'missing_etfs', 'missingEtfs', 'stale_etfs', 'staleEtfs']);
    if (rows.length) {
      return dedupeRows(rows.map((x: any) => typeof x === 'string'
        ? {
            etf_code: String(x),
            etfCode: String(x),
            code: String(x),
            etf_name: '',
            etfName: '',
            latest_date: '',
            latestDate: '',
            status: '非今日資料',
          }
        : x
      ));
    }
  }

  for (const box of containers) {
    const codeArrays = [
      box?.missing_today_etf_codes,
      box?.missingTodayEtfCodes,
      box?.non_today_etf_codes,
      box?.nonTodayEtfCodes,
    ];

    for (const codeList of codeArrays) {
      if (Array.isArray(codeList) && codeList.length) {
        return dedupeRows(codeList.map((code: any) => ({
          etf_code: String(code),
          etfCode: String(code),
          code: String(code),
          etf_name: '',
          etfName: '',
          latest_date: '',
          latestDate: '',
          status: '非今日資料',
        })));
      }
    }
  }

  for (const box of containers) {
    const text = [
      box?.missing_today_etf_codes_text,
      box?.non_today_etf_codes_text,
      box?.missingEtfCodesText,
      box?.nonTodayEtfCodesText,
    ].find((v: any) => typeof v === 'string' && v.trim());

    if (text) {
      return dedupeRows(String(text)
        .split(/[，,\s]+/)
        .map((x) => x.trim())
        .filter(Boolean)
        .map((code) => ({
          etf_code: code,
          etfCode: code,
          code,
          etf_name: '',
          etfName: '',
          latest_date: '',
          latestDate: '',
          status: '非今日資料',
        })));
    }
  }

  for (const box of containers) {
    const allCodes = box?.all_etf_codes || box?.allEtfCodes || box?.total_etf_codes || box?.totalEtfCodes;
    const todayCodes = box?.today_etf_codes || box?.todayEtfCodes;

    if (Array.isArray(allCodes) && allCodes.length && Array.isArray(todayCodes)) {
      const todaySet = new Set(todayCodes.map((x: any) => String(x).trim()));
      const missingCodes = allCodes
        .map((x: any) => String(x).trim())
        .filter((code: string) => code && !todaySet.has(code));

      if (missingCodes.length) {
        return missingCodes.map((code: string) => ({
          etf_code: code,
          etfCode: code,
          code,
          etf_name: '',
          etfName: '',
          latest_date: '',
          latestDate: '',
          status: '非今日資料',
        }));
      }
    }
  }

  return [];
}

function signalNumber(
  value: unknown
): number | null {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return null;
  }

  const result = Number(
    String(value)
      .replace(/,/g, '')
      .replace(/[^\d.-]/g, '')
  );

  return Number.isFinite(result)
    ? result
    : null;
}

function deltaWeightOf(
  row: AnyRow
): number | null {
  const directKeys = [
    'delta_weight',
    'deltaWeight',
    'weight_change',
    'weightChange',
    'net_delta_weight',
    'total_delta_weight',
  ];

  for (const key of directKeys) {
    const value = signalNumber(
      row?.[key]
    );

    if (value !== null) {
      return value;
    }
  }

  const sources = Array.isArray(
    row?.__sources
  )
    ? row.__sources
    : [];

  let total = 0;
  let found = false;

  for (const source of sources) {
    const value = signalNumber(
      source?.delta_weight ??
        source?.deltaWeight ??
        source?.weight_change ??
        source?.weightChange
    );

    if (value !== null) {
      total += value;
      found = true;
    }
  }

  return found ? total : null;
}

function fmtWeightDelta(
  value: number | null
): string {
  if (value === null) {
    return '-';
  }

  const sign = value > 0 ? '+' : '';

  return `${sign}${value.toFixed(2)}%`;
}

function consensusScoreOf(
  row: AnyRow
): number {
  const buy = Number(
    row?.__buySell?.buy ?? 0
  );

  const sell = Number(
    row?.__buySell?.sell ?? 0
  );

  return buy - sell;
}

function consensusTotalOf(
  row: AnyRow
): number {
  const buy = Number(
    row?.__buySell?.buy ?? 0
  );

  const sell = Number(
    row?.__buySell?.sell ?? 0
  );

  return buy + sell;
}

function sortRows(rows: AnyRow[], key: SortKey, dir: SortDir): AnyRow[] {
  const copy = [...rows];

  copy.sort((a, b) => {
    if (key === 'code') return codeOf(a).localeCompare(codeOf(b), 'zh-Hant');
    if (key === 'inflow') return amountOf(b) - amountOf(a);
    if (key === 'outflow') return amountOf(a) - amountOf(b);
    if (key === 'absAmount') return Math.abs(amountOf(b)) - Math.abs(amountOf(a));
    if (key === 'lots') return Math.abs(lotsOf(b)) - Math.abs(lotsOf(a));
    if (key === 'price') return (priceOf(b) ?? -Infinity) - (priceOf(a) ?? -Infinity);
    if (key === 'pct') return (pctOf(b) ?? -Infinity) - (pctOf(a) ?? -Infinity);
    if (key === 'deltaWeight') {
      return (
        (deltaWeightOf(b) ?? -Infinity) -
        (deltaWeightOf(a) ?? -Infinity)
      );
    }

    if (key === 'consensus') {
      const scoreDiff =
        consensusScoreOf(b) -
        consensusScoreOf(a);

      if (scoreDiff !== 0) {
        return scoreDiff;
      }

      return (
        consensusTotalOf(b) -
        consensusTotalOf(a)
      );
    }

    if (key === 'etfCount') {
      const ab = (a.__buySell?.buy ?? 0) + (a.__buySell?.sell ?? 0);
      const bb = (b.__buySell?.buy ?? 0) + (b.__buySell?.sell ?? 0);
      return bb - ab;
    }
    return 0;
  });

  if (dir === 'asc') copy.reverse();

  return copy;
}

function getFocusRows(rows: AnyRow[]) {
  const inflow = rows.filter((r) => amountOf(r) > 0).sort((a, b) => amountOf(b) - amountOf(a))[0] ?? null;
  const outflow = rows.filter((r) => amountOf(r) < 0).sort((a, b) => amountOf(a) - amountOf(b))[0] ?? null;
  const mostAdd = rows.filter((r) => lotsOf(r) > 0).sort((a, b) => (b.__buySell.buy - a.__buySell.buy) || (lotsOf(b) - lotsOf(a)))[0] ?? null;
  const mostReduce = rows.filter((r) => lotsOf(r) < 0).sort((a, b) => (b.__buySell.sell - a.__buySell.sell) || (Math.abs(lotsOf(b)) - Math.abs(lotsOf(a))))[0] ?? null;
  return { inflow, outflow, mostAdd, mostReduce };
}

function FocusCard({ title, row, kind }: { title: string; row: AnyRow | null; kind: 'red' | 'green' }) {
  if (!row) {
    return (
      <div className={`v120-focus ${kind}`}>
        <b>{title}</b>
        <span>尚無有效訊號</span>
      </div>
    );
  }

  const amount = amountOf(row);
  const lots = lotsOf(row);
  const p = priceOf(row);
  const pct = pctOf(row);
  const bs = row.__buySell ?? { buy: 0, sell: 0 };

  return (
    <Link className={`v120-focus ${kind}`} href={`/stock/${codeOf(row)}`}>
      <b>{title}</b>
      <div className="v120-focus-name">
        <strong>{nameOf(row)}</strong>
        <em>{codeOf(row)}</em>
      </div>
      <div className="v120-focus-price">
        <strong>{fmtPrice(p)}</strong>
        <span className={tone(pct ?? 0)}>{fmtPct(pct)}</span>
      </div>
      <div className="v120-focus-meta">
        <span>淨額 <i className={tone(amount)}>{fmtBillion(amount).replace('億', '')}</i></span>
        <span>張數 <i className={tone(lots)}>{fmtLots(lots).replace('張', '')}</i></span>
        <span>異動ETF {bs.buy}:{bs.sell}</span>
      </div>
    </Link>
  );
}

const ETF_NAME_FALLBACK_V121: Record<string, string> = {
  "00400A": "主動國泰動能高息",
  "00401A": "主動摩根台灣鑫收",
  "00402A": "主動安聯美國科技",
  "00403A": "主動統一升級50",
  "00404A": "主動聯博動能50",
  "00405A": "主動富邦台灣龍耀",
  "00406A": "主動中信台灣收益",
  "00980A": "主動野村臺灣優選",
  "00981A": "主動統一台股增長",
  "00982A": "主動群益台灣強棒",
  "00983A": "主動中信ARK創新",
  "00984A": "主動安聯台灣高息",
  "00985A": "主動野村台灣50",
  "00986A": "主動台新龍頭成長",
  "00987A": "主動台新優勢成長",
  "00988A": "主動統一全球創新",
  "00989A": "主動摩根美國科技",
  "00990A": "主動元大AI新經濟",
  "00991A": "主動復華未來50",
  "00992A": "主動群益科技創新",
  "00993A": "主動安聯台灣",
  "00994A": "主動第一金台股優",
  "00995A": "主動中信台灣卓越",
  "00996A": "主動兆豐台灣豐收",
  "00997A": "主動群益美國增長",
  "00998A": "主動復華金融股息",
  "00999A": "主動野村臺灣高息",
};

const ETF_MISSING_META_FALLBACK_V121: Record<string, { market: string; reason: string }> = {
  "00402A": { market: "美國", reason: "揭露延後" },
  "00983A": { market: "美國", reason: "揭露延後" },
  "00986A": { market: "全球", reason: "揭露延後" },
  "00988A": { market: "全球", reason: "揭露延後" },
  "00989A": { market: "美國", reason: "揭露延後" },
  "00990A": { market: "全球", reason: "揭露延後" },
  "00997A": { market: "美國", reason: "揭露延後" },
  "00998A": { market: "全球", reason: "資料待補" },
};

function etfDisplayNameFallback(code: any, row?: any) {
  const c = String(code || '').trim().toUpperCase();
  return String(
    row?.etf_name ||
    row?.etfName ||
    row?.name ||
    ETF_NAME_FALLBACK_V121[c] ||
    ''
  );
}

function etfMissingMetaFallback(code: any, row?: any) {
  const c = String(code || '').trim().toUpperCase();
  const fallback = ETF_MISSING_META_FALLBACK_V121[c] || { market: "未判定", reason: "資料待補" };
  const market = String(row?.market || row?.investment_market || row?.investmentMarket || '').trim();
  const reason = String(row?.missing_reason || row?.missingReason || row?.reason || '').trim();
  return {
    market: market || fallback.market,
    reason: reason || fallback.reason,
  };
}


function missingDateOf(r: any) {
  const v =
    r?.latest_date ??
    r?.latestDate ??
    r?.data_date ??
    r?.dataDate ??
    r?.date ??
    r?.trade_date ??
    r?.tradeDate ??
    r?.dt ??
    '';
  return String(v || '');
}


function MissingModal({ data, onClose }: { data: any; onClose: () => void }) {
  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const targetDate = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';
  const rows0 = missingRowsOf(data);

  const fallbackCodes =
    (Array.isArray(data?.missing_today_etf_codes) && data.missing_today_etf_codes.length ? data.missing_today_etf_codes : null) ||
    (Array.isArray(data?.missingTodayEtfCodes) && data.missingTodayEtfCodes.length ? data.missingTodayEtfCodes : null) ||
    (Array.isArray(data?.summary?.missing_today_etf_codes) && data.summary.missing_today_etf_codes.length ? data.summary.missing_today_etf_codes : null) ||
    (Array.isArray(data?.summary?.missingTodayEtfCodes) && data.summary.missingTodayEtfCodes.length ? data.summary.missingTodayEtfCodes : null) ||
    [];

  const rowMap = new Map<string, any>();

  for (const r of rows0) {
    const code = etfCodeOf(r);
    if (code) rowMap.set(code, r);
  }

  for (const code0 of fallbackCodes) {
    const code = String(code0 || '').trim().toUpperCase();
    if (!code || rowMap.has(code)) continue;
    rowMap.set(code, {
      etf_code: code,
      etfCode: code,
      code,
      etf_name: '',
      etfName: '',
      latest_date: '',
      latestDate: '',
      status: '非今日資料',
    });
  }

  const rows = Array.from(rowMap.values());

  return (
    <div className="v120-modal-mask" onClick={onClose}>
      <div className="v120-modal" onClick={(e) => e.stopPropagation()}>
        <button className="v120-modal-x" type="button" onClick={onClose}>×</button>
        <h3>未更新 ETF</h3>
        <p>今日訊號只使用{targetDate ? ` ${mmdd(targetDate)} 當日` : '當日'}資料，不混入前一日資料。</p>
        <p>下方列出未納入今日訊號的 ETF、持股日與主要市場。</p>
        <div className="v120-modal-count">已取得 {today} / {total} 檔，未更新 {missing} 檔</div>

        {rows.length ? (
          <div className="v120-missing-table-wrap">
            <table className="v120-missing-table">
              <thead>
                <tr>
                  <th>代號</th>
                  <th>ETF 名稱</th>
                  <th>持股日</th>
                  <th>市場</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const code = etfCodeOf(r);
                  const name = etfDisplayNameFallback(code, r);
                  const meta = etfMissingMetaFallback(code, r);
                  const latestDate = missingDateOf(r);
                  return (
                    <tr key={`${code || i}`}>
                      <td><b>{code}</b></td>
                      <td>{name && name !== code ? name : '-'}</td>
                      <td>{latestDate ? mmdd(latestDate) : '-'}</td>
                      <td><strong className="v120-missing-meta">{meta.market}</strong></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="v120-modal-note">
            目前前端仍未取得 ETF 代號清單，請稍後重新整理。
          </div>
        )}

        <button className="v120-modal-ok" type="button" onClick={onClose}>我知道了</button>
      </div>
    </div>
  );
}

function RangeTabs({ activeDays }: { activeDays: number }) {
  const items = [1, 5, 10, 20];
  return (
    <section className="v120-range">
      <div className="v120-range-label">訊號區間</div>
      <div className="v120-range-tabs">
        {items.map((d) => (
          <Link key={d} href={d === 1 ? '/signals' : `/signals?days=${d}`} className={activeDays === d ? 'active' : ''}>
            {d === 1 ? '今日' : `${d}日`}
          </Link>
        ))}
      </div>
    </section>
  );
}

function SortButton({ label, active, onClick, arrow }: { label: string; active: boolean; onClick: () => void; arrow: string }) {
  return (
    <button type="button" className={active ? 'active' : ''} onClick={onClick}>
      {label} <span>{arrow}</span>
    </button>
  );
}

function DetailRow({ row }: { row: AnyRow }) {
  const p = priceOf(row);
  const pct = pctOf(row);
  const amount = amountOf(row);
  const lots = lotsOf(row);
  const deltaWeight =
    deltaWeightOf(row);
  const st = statusOf(row);

  const bs =
    row.__buySell ?? {
      buy: 0,
      sell: 0,
    };

  const statusClass =
    st === '新增'
      ? 'new'
      : st === '刪除'
        ? 'remove'
        : st === '加碼'
          ? 'add'
          : st === '減碼'
            ? 'reduce'
            : 'flat';

  const limitTitle = isLimitUp(row)
    ? '漲停'
    : isLimitDown(row)
      ? '跌停'
      : undefined;

  return (
    <Link
      className="v120-row"
      href={`/stock/${codeOf(row)}`}
    >
      <div className="v120-target">
        <b>{nameOf(row)}</b>
        <span>{codeOf(row)}</span>
      </div>

      <div className="v120-price">
        <b
          title={limitTitle}
          className={
            isLimitUp(row)
              ? 'v123-limit-up-price'
              : isLimitDown(row)
                ? 'v123-limit-down-price'
                : tone(pct ?? 0)
          }
        >
          {fmtPrice(p)}
        </b>

        <span className={tone(pct ?? 0)}>
          {fmtPct(pct)}
        </span>
      </div>

      <div className="v125-status-text">
        <b className={statusClass}>
          {st || '-'}
        </b>

        <span>
          {bs.buy}:{bs.sell}
        </span>
      </div>

      <div className="v126-flow">
        <b className={tone(lots)}>
          {fmtLots(lots)}
        </b>

        <span className={tone(amount)}>
          {fmtBillion(amount)}
        </span>
      </div>

      <div className="v125-weight">
        <b
          className={tone(
            deltaWeight ?? 0
          )}
        >
          {fmtWeightDelta(
            deltaWeight
          )}
        </b>
      </div>
    </Link>
  );
}

export default function SignalsClient(props: {
  data: any;
  activeDays?: number;
  universeLabel?: string;
  coverage?: {
    activeFetched: number;
    activeTotal: number;
    referenceFetched: number;
    referenceTotal: number;
    allFetched: number;
    allTotal: number;
  };
}) {
  const data = props.data ?? {};

  const activeDays =
    Number(
      props.activeDays ??
        data?.signalRangeDays ??
        data?.rangeDays ??
        1,
    ) || 1;

  const universeLabel =
    props.universeLabel || 'ETF';

  const coverage =
    props.coverage;

  const [filter, setFilter] = useState<FilterKey>('全部');
  const [sortKey, setSortKey] = useState<SortKey>('lots');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [showMissing, setShowMissing] = useState(false);

  const sourceRows = useMemo(() => sourceRowsOf(data), [data]);

  const rows = useMemo(() => {
    const base = displayRowsOf(data, sourceRows)
      .filter((r) => codeOf(r))
      .map((r) => {
        const src = sourcesFor(r, sourceRows);
        return { ...r, __sources: src, __buySell: buySell(r, src) };
      });

    return base;
  }, [data, sourceRows]);

  const counts = useMemo(() => {
    const out: Record<Status, number> = { 新增: 0, 刪除: 0, 加碼: 0, 減碼: 0 };
    for (const r of rows) {
      const s = statusOf(r);
      if (s) out[s] += 1;
    }
    return out;
  }, [rows]);

  const filteredRows = useMemo(() => {
    const f = filter === '全部' ? rows : rows.filter((r) => statusOf(r) === filter);
    return sortRows(f, sortKey, sortDir);
  }, [rows, filter, sortKey, sortDir]);

  const focus = useMemo(() => getFocusRows(rows), [rows]);

  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';

  function setSort(nextKey: SortKey, defaultDir: SortDir = 'desc') {
    if (sortKey === nextKey) {
      setSortDir((prev) => prev === 'desc' ? 'asc' : 'desc');
      return;
    }

    setSortKey(nextKey);
    setSortDir(defaultDir);
  }

  function sortArrow(key: SortKey) {
    if (sortKey !== key) return '↕';
    return sortDir === 'asc' ? '▲' : '▼';
  }

  function sortClass(key: SortKey) {
    return sortKey === key ? `active ${sortDir}` : '';
  }

  return (
    <main className="signals-v120">
      <section className="v120-title">
        <div className="v120-overview-kicker">
          SIGNAL OVERVIEW
        </div>

        <h1>
          {activeDays === 1
            ? `${universeLabel} 今日出現 ${rows.length} 筆持股異動`
            : `${universeLabel} 近 ${activeDays} 日出現 ${rows.length} 筆訊號`}
        </h1>

        <p className="v120-overview-copy">
          最大加碼為{' '}
          <b className="red">
            {focus.inflow
              ? `${nameOf(focus.inflow)} ${fmtBillion(amountOf(focus.inflow))}`
              : '-'}
          </b>
          {'；'}最大減碼為{' '}
          <b className="green">
            {focus.outflow
              ? `${nameOf(focus.outflow)} ${fmtBillion(amountOf(focus.outflow))}`
              : '-'}
          </b>
        </p>

        {coverage && (
          <div className="v120-overview-coverage">
            <span>
              主動式{' '}
              <b>
                {coverage.activeFetched}/
                {coverage.activeTotal}
              </b>
            </span>

            <span>
              一般 ETF{' '}
              <b>
                {coverage.referenceFetched}/
                {coverage.referenceTotal}
              </b>
            </span>

            <span>
              全部追蹤{' '}
              <b>
                {coverage.allFetched}/
                {coverage.allTotal}
              </b>
            </span>
          </div>
        )}
      </section>

      <section className="v120-focus-grid">
        <FocusCard title="淨資金流入最多" row={focus.inflow} kind="red" />
        <FocusCard title="淨資金流出最多" row={focus.outflow} kind="green" />
        <FocusCard title="最多 ETF 加碼" row={focus.mostAdd} kind="red" />
        <FocusCard title="最多 ETF 減碼" row={focus.mostReduce} kind="green" />
      </section>

      <section className="v120-detail">
        <h2>資金交易明細：共 {filteredRows.length} 檔</h2>

        <div className="v120-status-tabs">
          <button type="button" className={filter === '全部' ? 'active all' : ''} onClick={() => setFilter('全部')}>全部 {rows.length}</button>
          <button type="button" className={filter === '新增' ? 'active new' : 'new'} onClick={() => setFilter('新增')}>新增 {counts.新增}</button>
          <button type="button" className={filter === '刪除' ? 'active remove' : 'remove'} onClick={() => setFilter('刪除')}>刪除 {counts.刪除}</button>
          <button type="button" className={filter === '加碼' ? 'active add' : 'add'} onClick={() => setFilter('加碼')}>加碼 {counts.加碼}</button>
          <button type="button" className={filter === '減碼' ? 'active reduce' : 'reduce'} onClick={() => setFilter('減碼')}>減碼 {counts.減碼}</button>
        </div>

        <div className="v120-table">
          <div className="v120-head">
            <button
              type="button"
              className={sortClass('code')}
              onClick={() =>
                setSort('code', 'asc')
              }
            >
              <span>標的</span>

              <i aria-hidden="true">
                <em>▲</em>
                <em>▼</em>
              </i>
            </button>

            <div className="v124-dual-sort">
              <button
                type="button"
                className={sortClass('price')}
                onClick={() =>
                  setSort('price', 'desc')
                }
              >
                <span>股價</span>

                <i aria-hidden="true">
                  <em>▲</em>
                  <em>▼</em>
                </i>
              </button>

              <button
                type="button"
                className={sortClass('pct')}
                onClick={() =>
                  setSort('pct', 'desc')
                }
              >
                <span>漲跌幅</span>

                <i aria-hidden="true">
                  <em>▲</em>
                  <em>▼</em>
                </i>
              </button>
            </div>

            <button
              type="button"
              className={`v125-consensus-head ${sortClass(
                'consensus'
              )}`}
              onClick={() =>
                setSort(
                  'consensus',
                  'desc'
                )
              }
            >
              <span>多空共識</span>

              <i aria-hidden="true">
                <em>▲</em>
                <em>▼</em>
              </i>
            </button>

            <div className="v126-flow-head">
              <button
                type="button"
                className={sortClass('lots')}
                onClick={() =>
                  setSort('lots', 'desc')
                }
              >
                <span>變動張數</span>

                <i aria-hidden="true">
                  <em>▲</em>
                  <em>▼</em>
                </i>
              </button>

              <button
                type="button"
                className={
                  sortKey === 'inflow' ||
                  sortKey === 'outflow' ||
                  sortKey === 'absAmount'
                    ? `active ${sortDir}`
                    : ''
                }
                onClick={() =>
                  setSort('inflow', 'desc')
                }
              >
                <span>淨額</span>

                <i aria-hidden="true">
                  <em>▲</em>
                  <em>▼</em>
                </i>
              </button>
            </div>

            <button
              type="button"
              className={sortClass(
                'deltaWeight'
              )}
              onClick={() =>
                setSort(
                  'deltaWeight',
                  'desc'
                )
              }
            >
              <span>變動幅度</span>

              <i aria-hidden="true">
                <em>▲</em>
                <em>▼</em>
              </i>
            </button>
          </div>

          {filteredRows.length ? (
            filteredRows.map((r) => <DetailRow key={`${codeOf(r)}-${amountOf(r)}-${lotsOf(r)}-${sortKey}`} row={r} />)
          ) : (
            <div className="v120-empty">目前沒有符合條件的訊號。</div>
          )}
        </div>
      </section>

      {showMissing && <MissingModal data={data} onClose={() => setShowMissing(false)} />}
    </main>
  );
}