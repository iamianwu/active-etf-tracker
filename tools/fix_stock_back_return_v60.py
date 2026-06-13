from pathlib import Path
from urllib.parse import quote
import re

ROOT = Path.cwd()
FRONTEND = ROOT / 'frontend'
STOCK_DETAIL = FRONTEND / 'components' / 'StockDetailClient.tsx'
changed = []

def write(path: Path, text: str, old: str):
    if text != old:
        path.write_text(text, encoding='utf-8')
        changed.append(str(path.relative_to(ROOT)))


def patch_holdings_stock_links():
    """資金持股頁點個股時，強制帶 from=holdings&returnTo=/holdings。"""
    holdings_dir = FRONTEND / 'app' / 'holdings'
    if not holdings_dir.exists():
        return
    for path in holdings_dir.rglob('*.tsx'):
        text = path.read_text(encoding='utf-8')
        old = text
        encoded = quote('/holdings', safe='')

        def repl_template(m: re.Match) -> str:
            expr = m.group(1)
            whole = m.group(0)
            if 'returnTo=' in whole or '?from=' in whole:
                return whole
            return f"href={{`/stock/${{{expr}}}?from=holdings&returnTo={encoded}`}}"

        text = re.sub(r"href=\{`/stock/\$\{([^}]+)\}`\}", repl_template, text)

        # href={'/stock/' + xxx} / href={`/stock/${xxx}?foo`} 之外的常見寫法不強改，避免破壞。
        write(path, text, old)


def patch_stock_detail_back():
    if not STOCK_DETAIL.exists():
        raise FileNotFoundError('找不到 frontend/components/StockDetailClient.tsx')

    text = STOCK_DETAIL.read_text(encoding='utf-8')
    old = text

    # import useSearchParams
    if "useSearchParams" not in text:
        if "from 'next/navigation'" in text:
            text = re.sub(
                r"import \{([^}]+)\} from 'next/navigation';",
                lambda m: "import {" + (m.group(1).strip() + ', useSearchParams' if 'useSearchParams' not in m.group(1) else m.group(1).strip()) + "} from 'next/navigation';",
                text,
                count=1,
            )
        else:
            # 放在 Link import 後面
            text = text.replace(
                "import Link from 'next/link';\n",
                "import Link from 'next/link';\nimport { useSearchParams } from 'next/navigation';\n",
                1,
            )

    # 在 component 內加入 stockBackHref helper
    if 'const stockBackHref = resolveStockBackHref();' not in text:
        marker = "export default function StockDetailClient({ data }: { data: any }) {\n"
        insert = r'''export default function StockDetailClient({ data }: { data: any }) {
  const searchParams = useSearchParams();

  function resolveStockBackHref() {
    const returnToParam = searchParams.get('returnTo') || '';
    const fromParam = searchParams.get('from') || '';

    if (returnToParam) return returnToParam;
    if (fromParam === 'holdings') return '/holdings';
    if (fromParam === 'signals') return '/signals';
    if (fromParam === 'etfs') return '/etfs';
    if (fromParam === 'search') return '/search';

    if (typeof window !== 'undefined') {
      const storedReturnTo =
        window.sessionStorage.getItem('stockReturnTo') ||
        window.sessionStorage.getItem('activeEtfReturnTo') ||
        window.sessionStorage.getItem('activeEtfOriginReturnTo') ||
        '';
      const storedFrom =
        window.sessionStorage.getItem('stockFrom') ||
        window.sessionStorage.getItem('activeEtfFrom') ||
        '';

      if (storedReturnTo) return storedReturnTo;
      if (storedFrom === 'holdings') return '/holdings';
      if (storedFrom === 'signals') return '/signals';
      if (storedFrom === 'etfs') return '/etfs';
      if (storedFrom === 'search') return '/search';
    }

    // 個股頁最常見入口是資金持股；不要再 fallback 到搜尋頁。
    return '/holdings';
  }

  const stockBackHref = resolveStockBackHref();
'''
        if marker in text:
            text = text.replace(marker, insert, 1)
        else:
            raise RuntimeError('找不到 StockDetailClient function marker，請把 StockDetailClient.tsx 貼給我看。')

    # 將返回按鈕從 /search 改成 stockBackHref
    replacements = [
        (r'<Link([^>]*className="[^"]*stock-v2-back[^"]*"[^>]*)href="/search"([^>]*)>', r'<Link\1href={stockBackHref}\2>'),
        (r'<Link([^>]*href="/search"[^>]*className="[^"]*stock-v2-back[^"]*"[^>]*)>', None),
        (r'<Link([^>]*className="[^"]*stock-back[^"]*"[^>]*)href="/search"([^>]*)>', r'<Link\1href={stockBackHref}\2>'),
        (r'<Link([^>]*className="[^"]*back[^"]*"[^>]*)href="/search"([^>]*)>', r'<Link\1href={stockBackHref}\2>'),
    ]
    for pat, repl in replacements:
        if repl is None:
            # 處理 href 在 className 前面的狀況：直接將 href="/search" 換掉
            text = re.sub(pat, lambda m: m.group(0).replace('href="/search"', 'href={stockBackHref}'), text)
        else:
            text = re.sub(pat, repl, text)

    # 特別處理原始精確字串
    text = text.replace('<Link className="stock-v2-back" href="/search">', '<Link className="stock-v2-back" href={stockBackHref}>')
    text = text.replace('<Link href="/search" className="stock-v2-back">', '<Link href={stockBackHref} className="stock-v2-back">')

    # 個股頁底下 ETF link 繼續帶原來源。若 v58 已處理則不重複。
    if 'buildEtfHrefFromStock' not in text:
        # 插入 helper 到 stockBackHref 後面
        needle = '  const stockBackHref = resolveStockBackHref();\n'
        helper = r'''

  function buildEtfHrefFromStock(etfCode: string) {
    const returnTo = stockBackHref || '/holdings';
    const from = returnTo.startsWith('/holdings') ? 'holdings'
      : returnTo.startsWith('/signals') ? 'signals'
      : returnTo.startsWith('/etfs') ? 'etfs'
      : returnTo.startsWith('/search') ? 'search'
      : 'holdings';

    if (typeof window !== 'undefined') {
      window.sessionStorage.setItem('activeEtfReturnTo', returnTo);
      window.sessionStorage.setItem('activeEtfOriginReturnTo', returnTo);
      window.sessionStorage.setItem('activeEtfFrom', from);
    }

    const params = new URLSearchParams();
    params.set('from', from);
    params.set('returnTo', returnTo);
    return `/etf/${etfCode}?${params.toString()}`;
  }
'''
        text = text.replace(needle, needle + helper, 1)

    text = re.sub(
        r"href=\{`/etf/\$\{([^}]+)\}`\}",
        r"href={buildEtfHrefFromStock(\1)}",
        text,
    )

    write(STOCK_DETAIL, text, old)


def main():
    patch_holdings_stock_links()
    patch_stock_detail_back()
    if changed:
        print('v60 patched files:')
        for f in changed:
            print(' -', f)
    else:
        print('No changes. v60 logic may already exist.')

if __name__ == '__main__':
    main()
