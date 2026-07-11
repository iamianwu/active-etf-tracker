'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const items = [
  { href: '/', label: '總覽', icon: '⌂', active: (p: string) => p === '/' || p.startsWith('/home-v2') },
  { href: '/signals', label: '訊號', icon: '⌁', active: (p: string) => p.startsWith('/signals') },
  { href: '/search', label: '個股', icon: '⌕', active: (p: string) => p.startsWith('/search') || p.startsWith('/stock') },
  { href: '/etfs', label: 'ETF', icon: '▱', active: (p: string) => p.startsWith('/etfs') || p.startsWith('/etf/') },
  { href: '/watchlist', label: '追蹤', icon: '☆', active: (p: string) => p.startsWith('/watchlist') },
];

export default function BottomTaskBar() {
  const pathname = usePathname() || '/';

  return (
    <nav className="bottom-taskbar-v120" aria-label="主要導覽">
      {items.map((item) => {
        const isActive = item.active(pathname);

        return (
          <Link
            key={item.href}
            href={item.href}
            className={isActive ? 'active' : ''}
            aria-current={isActive ? 'page' : undefined}
          >
            <span className="bottom-taskbar-icon-v120">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
