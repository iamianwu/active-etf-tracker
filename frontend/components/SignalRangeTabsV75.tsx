'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';

const OPTIONS = [
  { label: '今日', days: '1' },
  { label: '5日', days: '5' },
  { label: '10日', days: '10' },
  { label: '20日', days: '20' },
];

export default function SignalRangeTabsV75() {
  const pathname = usePathname() || '/signals';
  const searchParams = useSearchParams();

  const activeDays =
    searchParams.get('days') ||
    searchParams.get('rangeDays') ||
    searchParams.get('signalRangeDays') ||
    '1';

  const makeHref = (days: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('days', days);
    params.delete('rangeDays');
    params.delete('signalRangeDays');
    return `${pathname}?${params.toString()}`;
  };

  return (
    <div className="signal-range-wrap-v75">
      <div className="signal-range-title-v75">訊號區間</div>
      <div className="signal-range-tabs-v75" aria-label="今日訊號區間切換">
        {OPTIONS.map((opt) => {
          const active = String(activeDays) === opt.days;
          return (
            <Link
              key={opt.days}
              href={makeHref(opt.days)}
              className={`signal-range-tab-v75 ${active ? 'active' : ''}`}
            >
              {opt.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
