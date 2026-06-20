#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import re
import sys

ROOT = Path.cwd()
FRONTEND = ROOT / 'frontend'
SIG_CLIENT = FRONTEND / 'components' / 'SignalsClient.tsx'
CSS = FRONTEND / 'app' / 'globals.css'
TOOLS = ROOT / 'tools'
README = ROOT / 'README_V119_MISSING_ETF_REAL_LIST.md'

if not FRONTEND.exists():
    print('❌ 請在 repo 根目錄執行，例如：cd ~/Downloads/active-etf-tracker-fix')
    sys.exit(1)
for p in [SIG_CLIENT, CSS]:
    if not p.exists():
        print(f'❌ 找不到必要檔案：{p}')
        sys.exit(1)

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
for p in [SIG_CLIENT, CSS]:
    bak = p.with_suffix(p.suffix + f'.bak_v119_{stamp}')
    bak.write_text(p.read_text(encoding='utf-8'), encoding='utf-8')

s = SIG_CLIENT.read_text(encoding='utf-8')

# useEffect is required for the modal to fetch the missing ETF list on open.
s = s.replace("import { useMemo, useState } from 'react';", "import { useEffect, useMemo, useState } from 'react';")
s = s.replace('import { useMemo, useState } from "react";', 'import { useEffect, useMemo, useState } from "react";')

helper_block = r'''
const ACTIVE_ETF_CODES_V119 = [
  '00400A', '00401A', '00402A', '00403A', '00404A', '00405A', '00406A',
  '00980A', '00981A', '00982A', '00983A', '00984A', '00985A', '00986A', '00987A', '00988A', '00989A',
  '00990A', '00991A', '00992A', '00993A', '00994A', '00995A', '00996A', '00997A', '00998A', '00999A',
];

const ETF_NAME_FALLBACK_V119: Record<string, string> = {
  '00400A': '主動國泰動能高息',
  '00401A': '主動摩根台灣鑫收',
  '00403A': '主動統一升級50',
  '00404A': '主動聯博動能50',
  '00405A': '主動富邦台灣龍耀',
  '00406A': '主動中信台灣收益',
  '00980A': '主動野村臺灣優選',
  '00981A': '主動統一台股增長',
  '00982A': '主動群益台灣強棒',
  '00984A': '主動安聯台灣高息',
  '00985A': '主動野村台灣50',
  '00990A': '主動元大AI新經濟',
  '00991A': '主動復華未來50',
  '00992A': '主動群益科技創新',
  '00993A': '主動安聯台灣',
  '00994A': '主動第一金台股優',
  '00995A': '主動野村台灣價值',
  '00996A': '主動兆豐台灣豐收',
  '00997A': '主動群益美國增長',
  '00999A': '主動野村臺灣高息',
};

function fullDateOfV119(dateLike: any): string {
  const s0 = String(dateLike ?? '').trim();
  const full = s0.match(/\d{4}-\d{2}-\d{2}/)?.[0];
  if (full) return full;
  const md = s0.match(/(\d{2})-(\d{2})/);
  if (md) return `${new Date().getFullYear()}-${md[1]}-${md[2]}`;
  return '';
}

function getMissingEtfs(data: any): AnyRow[] {
  const keys = ['non_today_etfs', 'nonTodayEtfs', 'missing_etfs', 'missingEtfs', 'stale_etfs', 'staleEtfs', 'outdated_etfs', 'outdatedEtfs'];
  for (const k of keys) {
    const v = data?.[k];
    if (Array.isArray(v)) {
      return v.map((x) => typeof x === 'string' ? { etf_code: x } : x).filter(Boolean);
    }
  }
  return [];
}

async function fetchMissingEtfsFromSupabaseV119(targetDateRaw: any): Promise<AnyRow[]> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    throw new Error('本機缺少 NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY，無法即時查詢未更新清單。');
  }

  const { createClient } = await import('@supabase/supabase-js');
  const supabase = createClient(url, key);

  const { data: quoteRows } = await supabase
    .from('etf_quotes')
    .select('etf_code, etf_name')
    .in('etf_code', ACTIVE_ETF_CODES_V119);

  const nameMap: Record<string, string> = {};
  if (Array.isArray(quoteRows)) {
    for (const r of quoteRows) {
      const code = String((r as any)?.etf_code ?? '').trim();
      const name = String((r as any)?.etf_name ?? '').trim();
      if (code && name) nameMap[code] = name;
    }
  }

  const latestRows = await Promise.all(
    ACTIVE_ETF_CODES_V119.map(async (code) => {
      const { data, error } = await supabase
        .from('holdings')
        .select('etf_code, data_date')
        .eq('etf_code', code)
        .order('data_date', { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) return { etf_code: code, latest_date: '' };
      return { etf_code: code, latest_date: String((data as any)?.data_date ?? '') };
    })
  );

  let target = fullDateOfV119(targetDateRaw);
  if (!target) {
    target = latestRows.map((x) => x.latest_date).filter(Boolean).sort().at(-1) ?? '';
  }

  return latestRows
    .filter((x) => !x.latest_date || (target && x.latest_date < target))
    .map((x) => ({
      etf_code: x.etf_code,
      etf_name: nameMap[x.etf_code] || ETF_NAME_FALLBACK_V119[x.etf_code] || '',
      latest_date: x.latest_date || '',
    }));
}
'''

# Replace existing getMissingEtfs if present; otherwise insert helper block before MissingModal/DataQuality.
if 'async function fetchMissingEtfsFromSupabaseV119' not in s:
    m = re.search(r"function getMissingEtfs\(data: any\): AnyRow\[\] \{[\s\S]*?\n\}\n\nfunction statusCounts", s)
    if m:
        s = s[:m.start()] + helper_block + "\nfunction statusCounts" + s[m.end():]
    else:
        marker = 'function MissingModal'
        if marker in s:
            s = s.replace(marker, helper_block + '\n' + marker, 1)
        else:
            marker = 'function DataQuality'
            if marker in s:
                s = s.replace(marker, helper_block + '\n' + marker, 1)
            else:
                print('❌ 找不到 MissingModal 或 DataQuality，請貼 SignalsClient.tsx 的 modal 區塊。')
                sys.exit(1)

missing_modal_block = r'''function MissingModal({ data, onClose }: { data: any; onClose: () => void }) {
  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const apiList = getMissingEtfs(data);
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';
  const [list, setList] = useState<AnyRow[]>(apiList);
  const [loading, setLoading] = useState(apiList.length === 0 && missing > 0);
  const [errorText, setErrorText] = useState('');

  useEffect(() => {
    let alive = true;
    async function run() {
      if (apiList.length > 0 || missing <= 0) return;
      setLoading(true);
      setErrorText('');
      try {
        const rows = await fetchMissingEtfsFromSupabaseV119(date);
        if (!alive) return;
        setList(rows);
      } catch (err: any) {
        if (!alive) return;
        setErrorText(String(err?.message || err || '無法查詢未更新清單'));
      } finally {
        if (alive) setLoading(false);
      }
    }
    run();
    return () => { alive = false; };
  }, [apiList.length, missing, date]);

  return (
    <div className="signals-modal-mask-v117 signals-modal-mask-v119" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="signals-modal-v117 signals-modal-v119" onClick={(e) => e.stopPropagation()}>
        <button className="signals-modal-close-v117 signals-modal-close-v119" onClick={onClose} aria-label="關閉">×</button>
        <h3>未更新 ETF 清單</h3>
        <p>今日訊號只使用 {mmdd(date)} 當日資料，不混入前一日資料。</p>
        <div className="signals-modal-count-v117 signals-modal-count-v119">已取得 {today} / {total} 檔，未更新 {missing} 檔</div>

        {loading ? (
          <div className="signals-modal-note-v117 signals-modal-note-v119">正在查詢未更新 ETF 代號…</div>
        ) : list.length > 0 ? (
          <div className="signals-missing-list-v117 signals-missing-list-v119">
            {list.map((x, idx) => {
              const code = String(x.etf_code ?? x.code ?? x.etfCode ?? '').trim() || `ETF ${idx + 1}`;
              const name = String(x.etf_name ?? x.name ?? x.etfName ?? '').trim();
              const d = x.latest_date ?? x.data_date ?? x.date ?? '';
              return (
                <div key={`${code}-${idx}`} className="signals-missing-item-v117 signals-missing-item-v119">
                  <div className="missing-left-v119">
                    <b>{code}</b>
                    {name && <span>{name}</span>}
                  </div>
                  <em>{d ? `最新 ${mmdd(d)}` : '尚無資料'}</em>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="signals-modal-note-v117 signals-modal-note-v119">
            {errorText || '目前沒有查到未更新 ETF 清單。若你是在本機預覽，請確認 frontend/.env.local 有 Supabase URL 與 anon key。'}
          </div>
        )}

        <button className="signals-modal-ok-v117 signals-modal-ok-v119" onClick={onClose}>我知道了</button>
      </div>
    </div>
  );
}
'''

# Replace MissingModal block if it exists.
s2 = re.sub(r"function MissingModal\(\{ data, onClose \}: \{ data: any; onClose: \(\) => void \}\) \{[\s\S]*?\n\}\n\nfunction DataQuality", missing_modal_block + "\nfunction DataQuality", s, count=1)
if s2 == s:
    print('⚠️ 找不到標準 MissingModal 區塊，將保留原 modal；但已補上查詢 helper。')
else:
    s = s2

SIG_CLIENT.write_text(s, encoding='utf-8')

css = CSS.read_text(encoding='utf-8')
start = '/* === V119 real missing ETF list START === */'
end = '/* === V119 real missing ETF list END === */'
if start in css and end in css:
    css = css.split(start)[0] + css.split(end)[1]
css += r'''

/* === V119 real missing ETF list START === */
.signals-modal-mask-v119 {
  z-index: 99999 !important;
}
.signals-modal-v119 {
  max-width: 460px !important;
}
.signals-modal-count-v119 {
  color: #a97719 !important;
  font-weight: 900 !important;
}
.signals-missing-list-v119 {
  display: flex !important;
  flex-direction: column !important;
  gap: 0 !important;
  max-height: 44vh !important;
  overflow-y: auto !important;
  border: 1px solid #e5eaf2 !important;
  border-radius: 16px !important;
  background: #fff !important;
}
.signals-missing-item-v119 {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 10px !important;
  padding: 11px 12px !important;
  border-bottom: 1px solid #eef2f7 !important;
}
.signals-missing-item-v119:last-child {
  border-bottom: 0 !important;
}
.missing-left-v119 {
  min-width: 0 !important;
}
.missing-left-v119 b {
  display: block !important;
  font-size: 18px !important;
  line-height: 1.1 !important;
  color: #111827 !important;
  font-weight: 900 !important;
}
.missing-left-v119 span {
  display: block !important;
  margin-top: 3px !important;
  max-width: 250px !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
  color: #6b7280 !important;
  font-size: 14px !important;
  font-weight: 750 !important;
}
.signals-missing-item-v119 em {
  flex: 0 0 auto !important;
  font-style: normal !important;
  color: #a97719 !important;
  font-size: 14px !important;
  font-weight: 850 !important;
  white-space: nowrap !important;
}
.signals-modal-note-v119 {
  font-size: 15px !important;
  line-height: 1.55 !important;
}
@media (max-width: 520px) {
  .signals-modal-v119 {
    width: calc(100vw - 32px) !important;
    padding: 22px 18px 18px !important;
    border-radius: 24px !important;
  }
  .signals-modal-v119 h3 {
    font-size: 28px !important;
    line-height: 1.15 !important;
  }
  .signals-modal-v119 p,
  .signals-modal-count-v119 {
    font-size: 16px !important;
    line-height: 1.45 !important;
  }
  .signals-missing-list-v119 {
    max-height: 42vh !important;
  }
}
/* === V119 real missing ETF list END === */
'''
CSS.write_text(css, encoding='utf-8')

TOOLS.mkdir(exist_ok=True)
(TOOLS / 'apply_v119_missing_etf_real_list.py').write_text(Path(__file__).read_text(encoding='utf-8'), encoding='utf-8')
README.write_text('''# V119 Missing ETF Real List

修正內容：

1. 未更新 ETF modal 不再只顯示「API 尚未回傳清單」。
2. 若 `/signals` 沒有 `non_today_etfs`，前端會在打開彈窗時直接查 Supabase `holdings`，找出 27 檔 ETF 各自最新 `data_date`。
3. 彈窗會列出：ETF 代號、ETF 名稱、最新資料日。
4. 手機版彈窗字級與列表間距縮小，避免過大與看不懂。

注意：本機若要測試彈窗查詢，`frontend/.env.local` 需要有：

```env
NEXT_PUBLIC_SUPABASE_URL=你的 Supabase URL
NEXT_PUBLIC_SUPABASE_ANON_KEY=你的 anon public key
```

Vercel 已有這兩個環境變數就可以正常運作。
''', encoding='utf-8')

print('✅ V119 已完成：未更新 ETF 清單會查 Supabase 顯示實際 ETF 代號與最新資料日')
print('接著執行：cd frontend && npm run build')
