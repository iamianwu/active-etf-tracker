'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || '';
  const isDetailPage = pathname.startsWith('/etf/') || pathname.startsWith('/stock/');

  return (
    <div className={`shell ${isDetailPage ? 'detail-shell' : ''}`}>
      {!isDetailPage && (
        <header className="top">
          <div className="brand">
            <Link href="/signals" className="logo" style={{ textDecoration: 'none' }}>🎯 主動式 ETF</Link>
            <div className="top-icons">
              <span>👤</span>
              <Link href="/search" aria-label="搜尋" style={{ textDecoration: 'none' }}>🔍</Link>
            </div>
          </div>
          <nav className="nav">
            <Link className={pathname.startsWith('/signals') || pathname === '/' ? 'active' : ''} href="/signals">今日訊號</Link>
            <Link className={pathname.startsWith('/holdings') ? 'active' : ''} href="/holdings">資金持股</Link>
            <Link className={pathname.startsWith('/etfs') ? 'active' : ''} href="/etfs">ETF 列表</Link>
          </nav>
        </header>
      )}
      {children}
    </div>
  );
}
