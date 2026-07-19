export type SignalsCompactObject =
  Record<string, any>;

export const SIGNAL_ROW_ALIASES = [
  'rows',
  'items',
  'allRows',
  'changes',
  'signals',
  'rawChanges',
  'all_changes',
] as const;

function signalNumber(
  value: unknown,
): number | null {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return null;
  }

  if (typeof value === 'number') {
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

function firstNumber(
  row: SignalsCompactObject,
  keys: string[],
): number | null {
  for (const key of keys) {
    const value =
      signalNumber(row?.[key]);

    if (value !== null) {
      return value;
    }
  }

  return null;
}

function firstText(
  row: SignalsCompactObject,
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
  source: SignalsCompactObject,
): number | null {
  const lots = firstNumber(
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

  return firstNumber(
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
  if (!Array.isArray(sources)) {
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

    const row =
      source as SignalsCompactObject;

    const etfCode = firstText(
      row,
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
      sourceDelta(row);

    if (
      delta === null ||
      Math.abs(delta) < 0.001
    ) {
      continue;
    }

    if (delta > 0) {
      addEtfs.add(etfCode);
    }

    if (delta < 0) {
      reduceEtfs.add(etfCode);
    }
  }

  return {
    buy: addEtfs.size,
    sell: reduceEtfs.size,
  };
}

function compactNode(
  value: unknown,
): unknown {
  if (Array.isArray(value)) {
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
    value as SignalsCompactObject;

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
    SignalsCompactObject = {};

  for (
    const [
      key,
      child,
    ] of Object.entries(source)
  ) {
    if (
      key === 'changed_etfs' ||
      key === 'changedEtfs'
    ) {
      continue;
    }

    output[key] =
      compactNode(child);
  }

  if (counts) {
    const existingBuy =
      firstNumber(
        source,
        [
          'buy_count',
          'buyCount',
        ],
      );

    const existingSell =
      firstNumber(
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
  data: SignalsCompactObject,
): any[] {
  for (
    const key
    of SIGNAL_ROW_ALIASES
  ) {
    const rows =
      data?.[key];

    if (Array.isArray(rows)) {
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

export function compactSignalsPayload(
  data: any,
): any {
  if (
    !data ||
    typeof data !== 'object'
  ) {
    return data;
  }

  const sourceRows =
    sourceRowsOfPayload(data);

  const aliasSet =
    new Set<string>(
      SIGNAL_ROW_ALIASES,
    );

  const output:
    SignalsCompactObject = {};

  for (
    const [
      key,
      value,
    ] of Object.entries(data)
  ) {
    if (aliasSet.has(key)) {
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
