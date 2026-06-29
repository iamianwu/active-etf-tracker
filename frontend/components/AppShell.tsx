'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import BottomTaskBar from '@/components/BottomTaskBar';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || '';
  const isDetailPage = pathname.startsWith('/etf/') || pathname.startsWith('/stock/');

  return (
    <div className={`shell ${isDetailPage ? 'detail-shell' : ''}`}>
      {!isDetailPage && (
        <header className="top">
          <div className="brand">
            <Link href="/signals" className="logo" style={{ textDecoration: 'none' }}>🎯 主動式 ETF</Link>
            <div className="top-icons header-icons-v67">
              <span className="header-icon-v67 header-icon-bell-v67" aria-label="通知" title="通知" />
              <Link href="/search" aria-label="搜尋" style={{ textDecoration: 'none' }}><span className="header-icon-v67 header-icon-search-v67" /></Link>
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
      <BottomTaskBar />
    </div>
  );
}
