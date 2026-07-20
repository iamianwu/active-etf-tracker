'use client';

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';

export type WatchlistItemType =
  | 'stock'
  | 'etf';

export type WatchlistItem = {
  code: string;
  name: string;
  type: WatchlistItemType;
  addedAt: number;
};

export const WATCHLIST_STORAGE_KEY =
  'active_etf_favorites_v89';

export const WATCHLIST_CHANGE_EVENT =
  'active-etf-watchlist-change';

const LEGACY_STORAGE_KEY =
  'active_etf_favorites_v86';

function normalizeItem(
  value: any,
): WatchlistItem | null {
  const code = String(
    value?.code || '',
  )
    .trim()
    .toUpperCase();

  const type =
    value?.type === 'stock' ||
    value?.type === 'etf'
      ? value.type
      : null;

  if (!code || !type) {
    return null;
  }

  const addedAt = Number(
    value?.addedAt ??
      value?.ts ??
      0,
  );

  return {
    code,
    name:
      String(
        value?.name || code,
      ).trim() || code,
    type,
    addedAt:
      Number.isFinite(addedAt) &&
      addedAt > 0
        ? addedAt
        : 0,
  };
}

function normalizeItems(
  values: unknown,
): WatchlistItem[] {
  if (!Array.isArray(values)) {
    return [];
  }

  const seen = new Set<string>();
  const output: WatchlistItem[] = [];

  for (const value of values) {
    const item = normalizeItem(value);

    if (!item) {
      continue;
    }

    const key =
      `${item.type}:${item.code}`;

    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    output.push(item);
  }

  return output.slice(0, 100);
}

function readStorageKey(
  key: string,
): WatchlistItem[] {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    return normalizeItems(
      JSON.parse(
        window.localStorage.getItem(
          key,
        ) || '[]',
      ),
    );
  } catch {
    return [];
  }
}

function emitWatchlistChange(
  items: WatchlistItem[],
) {
  if (typeof window === 'undefined') {
    return;
  }

  window.dispatchEvent(
    new CustomEvent(
      WATCHLIST_CHANGE_EVENT,
      {
        detail: items,
      },
    ),
  );
}

export function writeWatchlist(
  values: WatchlistItem[],
): WatchlistItem[] {
  if (typeof window === 'undefined') {
    return [];
  }

  const items =
    normalizeItems(values);

  try {
    window.localStorage.setItem(
      WATCHLIST_STORAGE_KEY,
      JSON.stringify(items),
    );

    window.localStorage.removeItem(
      LEGACY_STORAGE_KEY,
    );
  } catch {
    return readStorageKey(
      WATCHLIST_STORAGE_KEY,
    );
  }

  emitWatchlistChange(items);
  return items;
}

export function readWatchlist(): WatchlistItem[] {
  if (typeof window === 'undefined') {
    return [];
  }

  const current = readStorageKey(
    WATCHLIST_STORAGE_KEY,
  );

  const legacy = readStorageKey(
    LEGACY_STORAGE_KEY,
  );

  if (!legacy.length) {
    return current;
  }

  return writeWatchlist([
    ...current,
    ...legacy,
  ]);
}

export function watchlistHas(
  code: string,
  type: WatchlistItemType,
): boolean {
  const normalizedCode = String(
    code || '',
  )
    .trim()
    .toUpperCase();

  return readWatchlist().some(
    (item) =>
      item.code === normalizedCode &&
      item.type === type,
  );
}

export function toggleWatchlistItem(
  value: {
    code: string;
    name: string;
    type: WatchlistItemType;
  },
): boolean {
  const item = normalizeItem({
    ...value,
    addedAt: Date.now(),
  });

  if (!item) {
    return false;
  }

  const current = readWatchlist();
  const exists = current.some(
    (row) =>
      row.code === item.code &&
      row.type === item.type,
  );

  const next = exists
    ? current.filter(
        (row) =>
          !(
            row.code === item.code &&
            row.type === item.type
          ),
      )
    : [item, ...current];

  writeWatchlist(next);
  return !exists;
}

export function removeWatchlistItem(
  code: string,
  type: WatchlistItemType,
) {
  const normalizedCode = String(
    code || '',
  )
    .trim()
    .toUpperCase();

  return writeWatchlist(
    readWatchlist().filter(
      (item) =>
        !(
          item.code === normalizedCode &&
          item.type === type
        ),
    ),
  );
}

export function subscribeWatchlist(
  listener: (
    items: WatchlistItem[],
  ) => void,
) {
  if (typeof window === 'undefined') {
    return () => undefined;
  }

  const sync = () => {
    listener(readWatchlist());
  };

  const handleStorage = (
    event: StorageEvent,
  ) => {
    if (
      !event.key ||
      event.key ===
        WATCHLIST_STORAGE_KEY ||
      event.key ===
        LEGACY_STORAGE_KEY
    ) {
      sync();
    }
  };

  window.addEventListener(
    WATCHLIST_CHANGE_EVENT,
    sync,
  );

  window.addEventListener(
    'storage',
    handleStorage,
  );

  return () => {
    window.removeEventListener(
      WATCHLIST_CHANGE_EVENT,
      sync,
    );

    window.removeEventListener(
      'storage',
      handleStorage,
    );
  };
}

export function useWatchlist() {
  const [items, setItems] =
    useState<WatchlistItem[]>([]);

  const [ready, setReady] =
    useState(false);

  useEffect(() => {
    setItems(readWatchlist());
    setReady(true);
    return subscribeWatchlist(setItems);
  }, []);

  const toggle = useCallback(
    (value: {
      code: string;
      name: string;
      type: WatchlistItemType;
    }) =>
      toggleWatchlistItem(value),
    [],
  );

  const remove = useCallback(
    (
      code: string,
      type: WatchlistItemType,
    ) =>
      removeWatchlistItem(code, type),
    [],
  );

  const isWatched = useCallback(
    (
      code: string,
      type: WatchlistItemType,
    ) => {
      const normalizedCode = String(
        code || '',
      )
        .trim()
        .toUpperCase();

      return items.some(
        (item) =>
          item.code === normalizedCode &&
          item.type === type,
      );
    },
    [items],
  );

  const counts = useMemo(
    () => ({
      all: items.length,
      stocks: items.filter(
        (item) =>
          item.type === 'stock',
      ).length,
      etfs: items.filter(
        (item) =>
          item.type === 'etf',
      ).length,
    }),
    [items],
  );

  return {
    items,
    counts,
    ready,
    toggle,
    remove,
    isWatched,
  };
}
