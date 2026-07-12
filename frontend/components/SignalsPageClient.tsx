'use client';

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';

import SignalsClient from '@/components/SignalsClient';
import styles from './SignalsPagePolish.module.css';

type Props = {
  activeDays: number;
};

type SignalPayload =
  Record<string, any>;

type Universe =
  | 'active'
  | 'reference'
  | 'all';

const UNIVERSES: Universe[] = [
  'active',
  'reference',
  'all',
];

/*
  模組層記憶體 Cache：
  使用 Next.js client navigation 切換日期時仍可保留。
*/
const payloadMemoryCache =
  new Map<string, SignalPayload>();

/*
  同一份資料正在下載時，共用同一個 Promise，
  避免背景預載與點擊同時造成重複請求。
*/
const payloadRequestCache =
  new Map<
    string,
    Promise<SignalPayload>
  >();

const knownTotals:
  Partial<Record<Universe, number>> =
  {};

let preferredUniverse:
  Universe = 'active';

function payloadKey(
  activeDays: number,
  universe: Universe,
) {
  return `${activeDays}:${universe}`;
}

function fetchedCountOf(
  payload:
    | SignalPayload
    | null
    | undefined,
) {
  return Number(
    payload?.fetched_etf_count ??
      payload?.today_etf_count ??
      0,
  );
}

function totalCountOf(
  payload:
    | SignalPayload
    | null
    | undefined,
  universe?: Universe,
) {
  const total = Number(
    payload?.total_etf_count ?? 0,
  );

  if (total > 0) {
    return total;
  }

  if (universe) {
    return Number(
      knownTotals[universe] ?? 0,
    );
  }

  return 0;
}

function rememberPayload(
  activeDays: number,
  universe: Universe,
  payload: SignalPayload,
) {
  payloadMemoryCache.set(
    payloadKey(activeDays, universe),
    payload,
  );

  const total = Number(
    payload?.total_etf_count ?? 0,
  );

  if (total > 0) {
    knownTotals[universe] = total;
  }

  const activeTotal =
    Number(knownTotals.active ?? 0);

  const referenceTotal =
    Number(
      knownTotals.reference ?? 0,
    );

  if (
    activeTotal > 0 &&
    referenceTotal > 0
  ) {
    knownTotals.all =
      activeTotal + referenceTotal;
  }

  return payload;
}

function statusDate(
  value: unknown,
): string {
  const raw = String(value || '');

  const match = raw.match(
    /^\d{4}-(\d{2})-(\d{2})/,
  );

  return match
    ? `${match[1]}/${match[2]}`
    : '-';
}

function statusUpdate(
  value: unknown,
): string {
  const date = new Date(
    String(value || ''),
  );

  if (
    !Number.isFinite(date.getTime())
  ) {
    return '-';
  }

  return new Intl.DateTimeFormat(
    'zh-TW',
    {
      timeZone: 'Asia/Taipei',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    },
  )
    .format(date)
    .replace(',', '');
}

async function fetchUniverse(
  universe: Universe,
  activeDays: number,
): Promise<SignalPayload> {
  const versionRes = await fetch(
    `/api/signals-version?days=${activeDays}&universe=${universe}`,
    {
      cache: 'no-store',
    },
  );

  const versionJson =
    versionRes.ok
      ? await versionRes.json()
      : {};

  const version = String(
    versionJson?.version ||
      Date.now(),
  );

  const response = await fetch(
    `/api/signals?days=${activeDays}&universe=${universe}&cv=${encodeURIComponent(
      version,
    )}`,
    {
      cache: 'no-store',
    },
  );

  if (!response.ok) {
    throw new Error(
      `${universe} signals api failed: ${response.status}`,
    );
  }

  const payload =
    await response.json();

  return rememberPayload(
    activeDays,
    universe,
    {
      ...payload,
      data_date:
        payload?.data_date ||
        versionJson?.data_date,
      updated_at:
        versionJson?.updated_at ||
        payload?.updated_at,
    },
  );
}

function getUniversePayload(
  universe: Universe,
  activeDays: number,
): Promise<SignalPayload> {
  const key = payloadKey(
    activeDays,
    universe,
  );

  const cached =
    payloadMemoryCache.get(key);

  if (cached) {
    return Promise.resolve(cached);
  }

  const existingRequest =
    payloadRequestCache.get(key);

  if (existingRequest) {
    return existingRequest;
  }

  const request = fetchUniverse(
    universe,
    activeDays,
  ).finally(() => {
    payloadRequestCache.delete(key);
  });

  payloadRequestCache.set(
    key,
    request,
  );

  return request;
}

function cachedPayloadsForDays(
  activeDays: number,
): Partial<
  Record<Universe, SignalPayload>
> {
  const result:
    Partial<
      Record<
        Universe,
        SignalPayload
      >
    > = {};

  for (const universe of UNIVERSES) {
    const payload =
      payloadMemoryCache.get(
        payloadKey(
          activeDays,
          universe,
        ),
      );

    if (payload) {
      result[universe] = payload;
    }
  }

  return result;
}

function universeLabelOf(
  universe: Universe,
) {
  if (universe === 'reference') {
    return '一般 ETF';
  }

  if (universe === 'all') {
    return '全部 ETF';
  }

  return '主動式 ETF';
}

export default function SignalsPageClient({
  activeDays,
}: Props) {
  const mountedRef =
    useRef(true);

  const switchSequenceRef =
    useRef(0);

  const initialUniverse =
    preferredUniverse;

  const initialCached =
    payloadMemoryCache.get(
      payloadKey(
        activeDays,
        initialUniverse,
      ),
    );

  const [
    payloads,
    setPayloads,
  ] = useState<
    Partial<
      Record<
        Universe,
        SignalPayload
      >
    >
  >(() =>
    cachedPayloadsForDays(
      activeDays,
    ),
  );

  const [
    universe,
    setUniverse,
  ] = useState<Universe>(
    initialUniverse,
  );

  const [
    pendingUniverse,
    setPendingUniverse,
  ] =
    useState<Universe | null>(
      null,
    );

  const [
    loading,
    setLoading,
  ] = useState(
    !initialCached,
  );

  const [
    err,
    setErr,
  ] =
    useState('');

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
    };
  }, []);

  const ensureUniverse =
    useCallback(
      async (
        targetUniverse:
          Universe,
        targetDays = activeDays,
      ) => {
        const payload =
          await getUniversePayload(
            targetUniverse,
            targetDays,
          );

        if (
          mountedRef.current &&
          targetDays === activeDays
        ) {
          setPayloads(
            (previous) => ({
              ...previous,
              [targetUniverse]:
                payload,
            }),
          );
        }

        return payload;
      },
      [activeDays],
    );

  useEffect(() => {
    let cancelled = false;

    const selectedUniverse =
      preferredUniverse;

    setUniverse(
      selectedUniverse,
    );

    setPendingUniverse(null);
    setErr('');

    const cached =
      cachedPayloadsForDays(
        activeDays,
      );

    setPayloads(cached);

    const selectedCached =
      cached[selectedUniverse];

    setLoading(
      !selectedCached,
    );

    async function start() {
      try {
        let primary =
          selectedCached;

        if (!primary) {
          primary =
            await getUniversePayload(
              selectedUniverse,
              activeDays,
            );
        }

        if (cancelled) {
          return;
        }

        setPayloads(
          (previous) => ({
            ...previous,
            [selectedUniverse]:
              primary,
          }),
        );

        setLoading(false);

        /*
          畫面出現後，背景載入同一天另外兩個 universe。
          完成後切換可直接顯示。
        */
        for (
          const otherUniverse
          of UNIVERSES
        ) {
          if (
            otherUniverse ===
            selectedUniverse
          ) {
            continue;
          }

          void getUniversePayload(
            otherUniverse,
            activeDays,
          )
            .then((payload) => {
              if (cancelled) {
                return;
              }

              setPayloads(
                (previous) => ({
                  ...previous,
                  [otherUniverse]:
                    payload,
                }),
              );
            })
            .catch((error) => {
              console.error(
                error,
              );
            });
        }

      } catch (error: any) {
        if (cancelled) {
          return;
        }

        console.error(error);

        setErr(
          String(
            error?.message ||
              error,
          ),
        );

        setLoading(false);
      }
    }

    void start();

    return () => {
      cancelled = true;

    };
  }, [activeDays]);

  function primeUniverse(
    targetUniverse: Universe,
  ) {
    if (
      payloads[
        targetUniverse
      ]
    ) {
      return;
    }

    void ensureUniverse(
      targetUniverse,
    ).catch((error) => {
      console.error(error);
    });
  }

  async function switchUniverse(
    targetUniverse: Universe,
  ) {
    preferredUniverse =
      targetUniverse;

    const sequence =
      ++switchSequenceRef.current;

    const cached =
      payloads[
        targetUniverse
      ] ||
      payloadMemoryCache.get(
        payloadKey(
          activeDays,
          targetUniverse,
        ),
      );

    if (cached) {
      setPayloads(
        (previous) => ({
          ...previous,
          [targetUniverse]:
            cached,
        }),
      );

      setPendingUniverse(null);
      setUniverse(
        targetUniverse,
      );

      return;
    }

    /*
      尚未下載完成時保留原畫面，
      不再顯示全頁 skeleton。
    */
    setPendingUniverse(
      targetUniverse,
    );

    try {
      await ensureUniverse(
        targetUniverse,
      );

      if (
        sequence !==
          switchSequenceRef
            .current ||
        !mountedRef.current
      ) {
        return;
      }

      setUniverse(
        targetUniverse,
      );
    } catch (error) {
      console.error(error);
    } finally {
      if (
        sequence ===
        switchSequenceRef
          .current &&
        mountedRef.current
      ) {
        setPendingUniverse(
          null,
        );
      }
    }
  }

  const selectedData =
    payloads[universe];

  if (
    loading &&
    !selectedData
  ) {
    return (
      <div
        className={
          styles.shell
        }
      >
        <main className="page">
          <div className="skeleton-card" />
          <div className="skeleton-card" />
          <div className="skeleton-card" />

          <p className="muted">
            今日訊號資料載入中...
          </p>
        </main>
      </div>
    );
  }

  if (
    err &&
    !selectedData
  ) {
    return (
      <div
        className={
          styles.shell
        }
      >
        <main className="page">
          <p className="muted">
            今日訊號載入失敗：
            {err}
          </p>
        </main>
      </div>
    );
  }

  if (!selectedData) {
    return null;
  }

  const activeData =
    payloads.active;

  const referenceData =
    payloads.reference;

  const allData =
    payloads.all;

  const activeFetched =
    fetchedCountOf(
      activeData,
    );

  const activeTotal =
    totalCountOf(
      activeData,
      'active',
    );

  const referenceFetched =
    fetchedCountOf(
      referenceData,
    );

  const referenceTotal =
    totalCountOf(
      referenceData,
      'reference',
    );

  const allFetched =
    fetchedCountOf(allData) ||
    (
      activeFetched +
      referenceFetched
    );

  const allTotal =
    totalCountOf(
      allData,
      'all',
    ) ||
    (
      activeTotal +
      referenceTotal
    );

  const selectedFetched =
    fetchedCountOf(
      selectedData,
    );

  const selectedTotal =
    totalCountOf(
      selectedData,
      universe,
    );

  const selectedMissing =
    Math.max(
      0,
      selectedTotal -
        selectedFetched,
    );

  const selectedLabel =
    universeLabelOf(
      universe,
    );

  function selectorCount(
    targetUniverse:
      Universe,
  ) {
    const payload =
      payloads[
        targetUniverse
      ];

    const total =
      totalCountOf(
        payload,
        targetUniverse,
      );

    return total > 0
      ? String(total)
      : '…';
  }

  const coverageReady =
    Boolean(
      activeData &&
      referenceData,
    );

  return (
    <div
      className={
        styles.shell
      }
    >
      <div
        className={
          styles.statusWrap
        }
      >
        <section
          className={
            styles.statusRow
          }
        >
          <div>
            <span>
              資料日
            </span>

            <strong>
              {statusDate(
                selectedData
                  ?.data_date,
              )}
            </strong>
          </div>

          <div>
            <span>
              更新
            </span>

            <strong>
              {statusUpdate(
                selectedData
                  ?.updated_at,
              )}
            </strong>
          </div>

          <div
            className={
              selectedMissing > 0
                ? styles.partialStatus
                : styles.completeStatus
            }
          >
            <i />

            <strong>
              {selectedMissing > 0
                ? `部分完成・尚缺 ${selectedMissing} 檔`
                : '資料完整'}
            </strong>
          </div>
        </section>
      </div>

      <div
        className={
          styles.statusWrap
        }
      >
        <div
          className="v89-etf-type-filter"
          role="tablist"
          aria-label="ETF 訊號範圍"
        >
          {UNIVERSES.map(
            (
              item,
            ) => {
              const label =
                universeLabelOf(
                  item,
                );

              const pending =
                pendingUniverse ===
                item;

              return (
                <button
                  key={item}
                  type="button"
                  role="tab"
                  aria-selected={
                    universe ===
                    item
                  }
                  aria-busy={
                    pending
                  }
                  className={`chip ${
                    universe ===
                    item
                      ? 'active'
                      : ''
                  }`}
                  onPointerDown={() =>
                    primeUniverse(
                      item,
                    )
                  }
                  onPointerEnter={() =>
                    primeUniverse(
                      item,
                    )
                  }
                  onFocus={() =>
                    primeUniverse(
                      item,
                    )
                  }
                  onClick={() =>
                    void switchUniverse(
                      item,
                    )
                  }
                >
                  {label}{' '}
                  {pending
                    ? '…'
                    : selectorCount(
                        item,
                      )}
                </button>
              );
            },
          )}
        </div>
      </div>

      <SignalsClient
        data={
          selectedData
        }
        activeDays={
          activeDays
        }
        universeLabel={
          selectedLabel
        }
        coverage={
          coverageReady
            ? {
                activeFetched,
                activeTotal,
                referenceFetched,
                referenceTotal,
                allFetched,
                allTotal,
              }
            : undefined
        }
      />
    </div>
  );
}
