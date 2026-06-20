from pathlib import Path
from datetime import datetime
import re

ROOT = Path.cwd()
FRONTEND = ROOT / 'frontend'
APP_PAGE = FRONTEND / 'app' / 'page.tsx'
SIG_PAGE = FRONTEND / 'app' / 'signals' / 'page.tsx'
SIG_CLIENT = FRONTEND / 'components' / 'SignalsClient.tsx'
CSS = FRONTEND / 'app' / 'globals.css'
TOOLS = ROOT / 'tools'
README = ROOT / 'README_V118_SINGLE_SIGNAL_RANGE.md'

required = [APP_PAGE, SIG_PAGE, SIG_CLIENT, CSS]
for p in required:
    if not p.exists():
        raise SystemExit(f'❌ 找不到必要檔案：{p}')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
for p in required:
    bak = p.with_suffix(p.suffix + f'.bak_v118_{stamp}')
    bak.write_text(p.read_text(encoding='utf-8'), encoding='utf-8')

# 統一首頁與 /signals：都只負責抓資料，不再各自畫「訊號區間」。
# 這樣「訊號區間」只會由 SignalsClient 的 RangeSwitch 顯示一次。
PAGE_CODE = r"""import { apiGet } from '@/lib/api';
import SignalsClient from '@/components/SignalsClient';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

type SearchParams = {
  days?: string | string[];
  rangeDays?: string | string[];
  signalRangeDays?: string | string[];
};

function one(v: string | string[] | undefined): string | undefined {
  return Array.isArray(v) ? v[0] : v;
}

function normalizeSignalDays(searchParams?: SearchParams): number {
  const raw = one(searchParams?.days) || one(searchParams?.rangeDays) || one(searchParams?.signalRangeDays) || '1';
  const n = Number(raw);
  return [1, 5, 10, 20].includes(n) ? n : 1;
}

export default async function Page({ searchParams }: { searchParams?: SearchParams }) {
  const days = normalizeSignalDays(searchParams);
  const data = await apiGet(`/signals?days=${days}`);
  return <SignalsClient data={data} activeDays={days} />;
}
"""
APP_PAGE.write_text(PAGE_CODE, encoding='utf-8')
SIG_PAGE.write_text(PAGE_CODE, encoding='utf-8')

# 讓 SignalsClient 的 RangeSwitch 依目前路徑產生連結：
# 在首頁就是 /?days=5，在 /signals 就是 /signals?days=5，避免跳頁後版面來源不一致。
s = SIG_CLIENT.read_text(encoding='utf-8')
if "from 'next/navigation'" not in s:
    s = s.replace("import Link from 'next/link';\n", "import Link from 'next/link';\nimport { usePathname } from 'next/navigation';\n")

range_func = r"""function RangeSwitch({ activeDays }: { activeDays: number }) {
  const pathname = usePathname() || '/';
  const base = pathname === '/signals' ? '/signals' : '/';
  const hrefFor = (days: number) => days === 1 ? base : `${base}?days=${days}`;

  return (
    <section className="signals-range-v117" aria-label="訊號區間">
      <div className="signals-section-label-v117">訊號區間</div>
      <div className="signals-range-tabs-v117">
        {RANGE_OPTIONS.map((opt) => (
          <Link key={opt.days} className={activeDays === opt.days ? 'is-active' : ''} href={hrefFor(opt.days)}>
            {opt.label}
          </Link>
        ))}
      </div>
    </section>
  );
}
"""

# 替換既有 RangeSwitch。
s2 = re.sub(
    r"function RangeSwitch\(\{ activeDays \}: \{ activeDays: number \}\) \{[\s\S]*?\n\}\n\nfunction MissingModal",
    range_func + "\nfunction MissingModal",
    s,
    count=1,
)
if s2 == s:
    print('⚠️ 沒有找到標準 RangeSwitch 區塊，保留 SignalsClient 原內容；主要仍已修正 page.tsx 重複區間。')
else:
    s = s2
SIG_CLIENT.write_text(s, encoding='utf-8')

# 補一段保險 CSS：若舊版 range card 不小心還殘留，只顯示 V117 這一組。
css = CSS.read_text(encoding='utf-8')
marker_start = '/* === V118 single signal range START === */'
marker_end = '/* === V118 single signal range END === */'
if marker_start in css and marker_end in css:
    css = css.split(marker_start)[0] + css.split(marker_end)[1]
css += r"""

/* === V118 single signal range START === */
/* 保險：首頁與 /signals 已統一只由 SignalsClient 顯示一組訊號區間。若舊版區間殘留，避免手機畫面出現兩組。 */
.signals-page-v117 .signals-range-card-v114,
.signals-page-v117 .signals-range-card-v115,
.signals-page-v117 .signals-range-card-v116 {
  display: none !important;
}
.signals-range-v117 + .signals-range-v117 {
  display: none !important;
}
@media (max-width: 520px) {
  .signals-range-v117 {
    margin-top: 4px !important;
    margin-bottom: 24px !important;
  }
}
/* === V118 single signal range END === */
"""
CSS.write_text(css, encoding='utf-8')

TOOLS.mkdir(exist_ok=True)
tool_copy = TOOLS / 'apply_v118_single_signal_range.py'
tool_copy.write_text(Path(__file__).read_text(encoding='utf-8'), encoding='utf-8')

README.write_text("""# V118 Single Signal Range

修正：

1. 首頁 `/` 與 `/signals` 統一由 `SignalsClient` 顯示「訊號區間」。
2. 移除 page.tsx 端重複的訊號區間，避免點 5 日後出現兩組。
3. RangeSwitch 會依目前路徑產生連結，避免 `/` 與 `/signals` 版面來源不一致。
4. 加保險 CSS，避免舊版 range 元件殘留時重複顯示。

套用後請 commit：

```bash
git add frontend/app/page.tsx frontend/app/signals/page.tsx frontend/components/SignalsClient.tsx frontend/app/globals.css tools/apply_v118_single_signal_range.py README_V118_SINGLE_SIGNAL_RANGE.md
git commit -m "Fix duplicated signal range tabs v118"
git push origin main
```
""", encoding='utf-8')

print('✅ V118 已完成：修正點 5 日後出現兩組「訊號區間」的問題')
print('接著可直接 git add / commit / push')
