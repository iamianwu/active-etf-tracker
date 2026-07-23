'use client';

import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  rowsOf,
  etfCode,
  etfName,
  fmtFree,
  fmtPct,
  priceOf,
  changePctOf,
  amountBillionOf,
  volumeOf,
  etfRegion,
  sortRows,
  num,
  type SortDir,
} from './mobileV89Utils';
import styles from './EtfListClient.module.css';

type EtfTypeFilter = 'all' | 'active' | 'reference';
type SortKey =
  | 'pct'
  | 'price'
  | 'amount'
  | 'volume'
  | 'aum'
  | 'weekReturn'
  | 'return'
  | 'yield'
  | 'fee'
  | 'code';

function aumOf(row: any) {
  return num(
    row?.aum_billion ??
      row?.fund_size_billion ??
      row?.asset_billion ??
      row?.scale_billion,
  );
}

function weekReturnOf(row: any) {
  return num(
    row?.week_return ??
      row?.one_week_return ??
      row?.return_1w ??
      row?.weekly_return,
  );
}

function totalReturnOf(row: any) {
  return num(
    row?.total_return ??
      row?.since_inception_return ??
      row?.return_since_inception,
  );
}

function dividendYieldOf(row: any) {
  return num(
    row?.dividend_yield ??
      row?.yield ??
      row?.distribution_yield,
  );
}

function feeOf(row: any) {
  return num(
    row?.expense_ratio ??
      row?.total_fee ??
      row?.fee ??
      row?.management_fee,
  );
}

function dividendFrequencyOf(row: any) {
  return String(
    row?.dividend_frequency ??
      row?.distribution_frequency ??
      row?.dividend_cycle ??
      '—',
  );
}

function inceptionDateOf(row: any) {
  return String(
    row?.inception_date ??
      row?.listing_date ??
      row?.launch_date ??
      '',
  ).slice(0, 10);
}

function changeOf(row: any) {
  return num(
    row?.change ??
      row?.price_change ??
      row?.change_value ??
      row?.delta_price,
  );
}

function isReferenceEtfRow(row: any) {
  return String(row?.etf_group ?? row?.etf_type ?? '').toLowerCase() === 'reference';
}

function referenceRoleOf(row: any) {
  return String(row?.reference_role ?? row?.role ?? '參考對照');
}

function referenceMarketOf(row: any) {
  return String(row?.market ?? row?.region ?? etfRegion(row) ?? '台灣');
}

function formatSignedNumber(value: number | null, digits = 2) {
  if (value === null || !Number.isFinite(value)) return '—';
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${fmtFree(value, digits)}`;
}

function formatBillionOrDash(value: number | null, digits = 0) {
  return value !== null && Number.isFinite(value) ? `${fmtFree(value, digits)} 億` : '—';
}

function formatPercentOrDash(value: number | null, digits = 2) {
  return value !== null && Number.isFinite(value) ? `${fmtFree(value, digits)}%` : '—';
}

function directionClass(value: number | null) {
  if (value === null) return styles.flat;
  if (value > 0) return styles.up;
  if (value < 0) return styles.down;
  return styles.flat;
}

function SortButton({
  label,
  sublabel,
  k,
  sortKey,
  sortDir,
  onClick,
}: {
  label: string;
  sublabel?: string;
  k: SortKey;
  sortKey: SortKey;
  sortDir: SortDir;
  onClick: () => void;
}) {
  const active = sortKey === k;

  return (
    <button
      type="button"
      className={`${styles.sortButton} ${active ? styles.sortActive : ''}`}
      aria-label={`${label}排序`}
      onClick={onClick}
    >
      <span className={styles.sortLabel}>
        {label}
        {sublabel && <small>{sublabel}</small>}
      </span>
      <i aria-hidden="true">
        <em className={active && sortDir === 'asc' ? styles.arrowActive : ''}>▲</em>
        <em className={active && sortDir === 'desc' ? styles.arrowActive : ''}>▼</em>
      </i>
    </button>
  );
}

function MetricCell({
  primary,
  secondary,
  tone,
  accent = false,
}: {
  primary: string;
  secondary?: string;
  tone?: string;
  accent?: boolean;
}) {
  return (
    <div className={`${styles.metricCell} ${tone ?? ''}`}>
      <strong className={accent ? styles.accent : ''}>{primary}</strong>
      {secondary && <span>{secondary}</span>}
    </div>
  );
}

export default function EtfListClient(props: any) {
  const rows = rowsOf(props);
  const headerViewportRef = useRef<HTMLDivElement>(null);
  const bodyViewportRef = useRef<HTMLElement>(null);
  const [typeFilter, setTypeFilter] = useState<EtfTypeFilter>('all');
  const [sortKey, setSortKey] = useState<SortKey>('pct');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [q, setQ] = useState('');

  useEffect(() => {
    const roots = [document.documentElement, document.body];
    const rootStyle = document.documentElement.style;
    const previousStickyTop = rootStyle.getPropertyValue('--etf-list-sticky-top');
    const previousStickyTopPriority = rootStyle.getPropertyPriority('--etf-list-sticky-top');
    const previous = roots.map((root) => ({
      overflowX: root.style.getPropertyValue('overflow-x'),
      overflowXPriority: root.style.getPropertyPriority('overflow-x'),
      overflowY: root.style.getPropertyValue('overflow-y'),
      overflowYPriority: root.style.getPropertyPriority('overflow-y'),
    }));

    roots.forEach((root) => {
      root.style.setProperty('overflow-x', 'clip', 'important');
      root.style.setProperty('overflow-y', 'visible', 'important');
    });

    const appHeader = document.querySelector<HTMLElement>('.top');
    rootStyle.setProperty(
      '--etf-list-sticky-top',
      `${Math.round(appHeader?.getBoundingClientRect().height ?? 0)}px`,
    );

    return () => {
      roots.forEach((root, index) => {
        const old = previous[index];
        if (old.overflowX) root.style.setProperty('overflow-x', old.overflowX, old.overflowXPriority);
        else root.style.removeProperty('overflow-x');
        if (old.overflowY) root.style.setProperty('overflow-y', old.overflowY, old.overflowYPriority);
        else root.style.removeProperty('overflow-y');
      });
      if (previousStickyTop) {
        rootStyle.setProperty('--etf-list-sticky-top', previousStickyTop, previousStickyTopPriority);
      } else {
        rootStyle.removeProperty('--etf-list-sticky-top');
      }
    };
  }, []);

  useEffect(() => {
    const bodyViewport = bodyViewportRef.current;
    const headerViewport = headerViewportRef.current;

    if (!bodyViewport || !headerViewport) return;

    const syncHeaderToBody = () => {
      headerViewport.scrollLeft = bodyViewport.scrollLeft;
    };

    const frame = window.requestAnimationFrame(syncHeaderToBody);
    bodyViewport.addEventListener('scroll', syncHeaderToBody, { passive: true });
    window.addEventListener('resize', syncHeaderToBody);

    return () => {
      window.cancelAnimationFrame(frame);
      bodyViewport.removeEventListener('scroll', syncHeaderToBody);
      window.removeEventListener('resize', syncHeaderToBody);
    };
  }, []);

  const activeCount = rows.filter((row: any) => !isReferenceEtfRow(row)).length;
  const referenceCount = rows.filter((row: any) => isReferenceEtfRow(row)).length;

  const typeFiltered = rows.filter((row: any) => {
    if (typeFilter === 'active') return !isReferenceEtfRow(row);
    if (typeFilter === 'reference') return isReferenceEtfRow(row);
    return true;
  });

  const filtered = typeFiltered.filter((row: any) => {
    const keyword = `${etfCode(row)} ${etfName(row)} ${referenceRoleOf(row)} ${referenceMarketOf(row)}`.toLowerCase();
    return keyword.includes(q.trim().toLowerCase());
  });

  const sorted = useMemo(
    () =>
      sortRows(
        filtered,
        (row: any) => {
          const isRef = isReferenceEtfRow(row);
          if (sortKey === 'price') return isRef ? -Infinity : priceOf(row);
          if (sortKey === 'amount') return isRef ? -Infinity : amountBillionOf(row);
          if (sortKey === 'volume') return isRef ? -Infinity : volumeOf(row);
          if (sortKey === 'aum') return isRef ? -Infinity : aumOf(row);
          if (sortKey === 'weekReturn') return isRef ? -Infinity : weekReturnOf(row);
          if (sortKey === 'return') return isRef ? -Infinity : totalReturnOf(row);
          if (sortKey === 'yield') return isRef ? -Infinity : dividendYieldOf(row);
          if (sortKey === 'fee') return feeOf(row);
          if (sortKey === 'code') return etfCode(row);
          return isRef ? -Infinity : changePctOf(row);
        },
        sortDir,
      ),
    [filtered, sortKey, sortDir],
  );

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((current) => (current === 'desc' ? 'asc' : 'desc'));
      return;
    }

    setSortKey(key);
    setSortDir('desc');
  }

  function switchTypeFilter(next: EtfTypeFilter) {
    setTypeFilter(next);
    if (next === 'reference') {
      setSortKey('code');
      setSortDir('asc');
    }
  }

  return (
    <main className={`page v89-page ${styles.page}`}>
      <header className={styles.titleRow}>
        <div>
          <p className={styles.eyebrow}>ETF MARKET</p>
          <h1>ETF 列表</h1>
          <p className={styles.summary}>共 {sorted.length} 檔｜所有欄位可左右滑動查看</p>
        </div>
      </header>

      <section className={styles.controls} aria-label="ETF 列表控制">
        <div className={styles.typeSwitch} aria-label="ETF 類型">
          <button type="button" className={typeFilter === 'all' ? styles.selected : ''} onClick={() => switchTypeFilter('all')}>全部 {activeCount + referenceCount}</button>
          <button type="button" className={typeFilter === 'active' ? styles.selected : ''} onClick={() => switchTypeFilter('active')}>主動式 {activeCount}</button>
          <button type="button" className={typeFilter === 'reference' ? styles.selected : ''} onClick={() => switchTypeFilter('reference')}>被動式 {referenceCount}</button>
        </div>

        <label className={styles.searchBox}>
          <span aria-hidden="true">⌕</span>
          <input
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="搜尋 ETF、代號或參考用途"
          />
        </label>
      </section>

      <section className={styles.tableArea} aria-label="ETF 行情表">
        <div className={styles.stickyHeader}>
          <div
            ref={headerViewportRef}
            className={styles.stickyHeaderViewport}
          >
            <div className={`${styles.table} ${styles.allGrid}`}>
              <div className={`${styles.tableHeader} ${styles.gridRow}`}>
                <div className={`${styles.headerCell} ${styles.identityHeader}`}>
                  <SortButton label="ETF" k="code" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('code')} />
                </div>

                <div className={styles.headerCell}><SortButton label="股價" k="price" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('price')} /></div>
                <div className={styles.headerCell}><SortButton label="漲跌幅" k="pct" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('pct')} /></div>
                <div className={styles.headerCell}><SortButton label="成交量" sublabel="成交金額" k="volume" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('volume')} /></div>
                <div className={styles.headerCell}><SortButton label="1 週報酬" k="weekReturn" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('weekReturn')} /></div>
                <div className={styles.headerCell}><SortButton label="成立報酬" sublabel="成立以來" k="return" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('return')} /></div>
                <div className={styles.headerCell}><SortButton label="殖利率" sublabel="配息頻率" k="yield" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('yield')} /></div>
                <div className={styles.headerCell}><SortButton label="資產規模" k="aum" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('aum')} /></div>
                <div className={styles.headerCell}><SortButton label="內扣費用" k="fee" sortKey={sortKey} sortDir={sortDir} onClick={() => toggleSort('fee')} /></div>
                <div className={`${styles.headerCell} ${styles.plainHeader}`}>投資區域</div>
              </div>
            </div>
          </div>
        </div>

        <section
          ref={bodyViewportRef}
          className={styles.tableViewport}
          aria-label="ETF 行情資料"
        >
          <div className={`${styles.table} ${styles.allGrid}`}>
            <div className={styles.tableBody}>
              {sorted.map((row: any, index: number) => {
              const code = etfCode(row);
              const isRef = isReferenceEtfRow(row);
              const changePct = changePctOf(row);
              const href = isRef ? '/reference-etfs' : `/etf/${code}?from=etfs`;
              const tone = directionClass(changePct);

              return (
                <Link key={`${code}-${index}`} href={href} className={`${styles.gridRow} ${styles.dataRow}`}>
                  <div className={styles.identityCell}>
                    <span className={`${styles.candle} ${isRef ? styles.reference : tone}`} aria-hidden="true"><i /></span>
                    <span className={styles.identityText}>
                      <strong>{code}</strong>
                      <span>{etfName(row)}</span>
                      {isRef && <small>被動式 ETF・{referenceMarketOf(row)}</small>}
                    </span>
                  </div>

                  <MetricCell primary={isRef ? '—' : fmtFree(priceOf(row), 2)} />
                  <MetricCell
                    primary={isRef ? '—' : formatSignedNumber(changeOf(row), 2)}
                    secondary={isRef ? '參考對照' : fmtPct(changePct, 2)}
                    tone={isRef ? styles.muted : tone}
                  />
                  <MetricCell
                    primary={isRef ? '—' : fmtFree(volumeOf(row), 0)}
                    secondary={isRef ? '無即時行情' : `(${fmtFree(amountBillionOf(row), 2)} 億)`}
                    accent={!isRef}
                  />
                  <MetricCell primary={isRef ? '—' : fmtPct(weekReturnOf(row), 1)} tone={isRef ? styles.muted : directionClass(weekReturnOf(row))} />
                  <MetricCell
                    primary={isRef ? '—' : fmtPct(totalReturnOf(row), 1)}
                    secondary={isRef ? '參考對照' : inceptionDateOf(row) || '成立以來'}
                    tone={isRef ? styles.muted : directionClass(totalReturnOf(row))}
                  />
                  <MetricCell
                    primary={isRef ? '—' : fmtPct(dividendYieldOf(row), 2)}
                    secondary={isRef ? '—' : dividendFrequencyOf(row)}
                  />
                  <MetricCell primary={isRef ? '—' : formatBillionOrDash(aumOf(row), 0)} />
                  <MetricCell primary={formatPercentOrDash(feeOf(row), 2)} />
                  <MetricCell primary={isRef ? referenceMarketOf(row) : etfRegion(row)} />
                </Link>
              );
              })}
            </div>
          </div>
        </section>
      </section>

      {sorted.length === 0 && <p className={styles.empty}>找不到符合條件的 ETF。</p>}
    </main>
  );
}
