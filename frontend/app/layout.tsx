import './globals.css';
import AppShell from '@/components/AppShell';

export const metadata = { title: '主動式 ETF Tracker' };
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-Hant">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
