import './globals.css';
import Link from 'next/link';
export const metadata = { title: '主動式 ETF Tracker' };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="zh-Hant"><body><div className="shell"><header className="top"><div className="brand"><div className="logo">🎯 主動式 ETF</div><div>👤 🔍</div></div><nav className="nav"><Link href="/signals">今日訊號</Link><Link href="/holdings">資金持股</Link><Link href="/etfs">ETF 列表</Link></nav></header>{children}</div></body></html>;
}
