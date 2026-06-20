#!/usr/bin/env python3
from pathlib import Path
import re
from datetime import datetime

ROOT = Path.cwd()
SIG = ROOT / 'frontend' / 'components' / 'SignalsClient.tsx'
CSS = ROOT / 'frontend' / 'app' / 'globals.css'
README = ROOT / 'README_V117_MISSING_ETF_LIST_MODAL.md'

if not SIG.exists():
    raise SystemExit('❌ 找不到 frontend/components/SignalsClient.tsx，請確認目前在 repo 根目錄。')
if not CSS.exists():
    raise SystemExit('❌ 找不到 frontend/app/globals.css，請確認目前在 repo 根目錄。')

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
(SIG.with_suffix(SIG.suffix + f'.bak_v117_{ts}')).write_text(SIG.read_text(encoding='utf-8'), encoding='utf-8')
(CSS.with_suffix(CSS.suffix + f'.bak_v117_{ts}')).write_text(CSS.read_text(encoding='utf-8'), encoding='utf-8')

text = SIG.read_text(encoding='utf-8')

# 1) useEffect is needed for loading real missing ETF list from Supabase only when modal opens.
text = text.replace("import { useMemo, useState } from 'react';", "import { useEffect, useMemo, useState } from 'react';")

# 2) Remove duplicated range picker inside SignalsClient if both page and component render it.
text = re.sub(r"\s*<RangePicker\s+activeDays=\{activeDays\}\s*/>\s*", "", text)

# 3) Add helper functions before DataQuality.
helper = r'''

// V117_MISSING_ETF_LIST_HELPERS_START
const ACTIVE_ETF_CODES_V117 = [
  '00400A','00401A','00402A','00403A','00404A','00405A','00406A',
  '00980A','00981A','00982A','00983A','00984A','00985A','00986A','00987A','00988A','00989A','00990A',
  '00991A','00992A','00993A','00994A','00995A','00996A','00997A','00998A','00999A'
];

const ETF_NAME_HINT_V117: Record<string, string> = {
  '00400A': '主動國泰動能高息',
  '00401A': '主動摩根台灣鑫收',
  '00402A': '主動群益科技創新',
  '00403A': '主動統一升級50',
  '00404A': '主動聯博動能50',
  '00405A': '主動富邦台灣龍耀',
  '00406A': '主動中信台灣收益',
  '00980A': '主動野村臺灣優選',
  '00981A': '主動統一台股增長',
  '00982A': '主動群益台灣強棒',
  '00983A': '主動中信ARK創新',
  '00984A': '主動安聯台灣高息',
  '00985A': '主動野村台灣50',
  '00986A': '主動群益全球創新AI',
  '00987A': '主動群益美國增長',
  '00988A': '主動統一全球創新',
  '00989A': '主動摩根全球基建',
  '00990A': '主動元大AI新經濟',
  '00991A': '主動復華未來50',
  '00992A': '主動群益科技創新',
  '00993A': '主動安聯台灣',
  '00994A': '主動第一金台股優',
  '00995A': '主動中信小資高息',
  '00996A': '主動兆豐台灣豐收',
  '00997A': '主動群益美國增長',
  '00998A': '主動中信台灣高股息',
  '00999A': '主動野村臺灣高息'
};

function dateKeyV117(v: any): string {
  const s = String(v ?? '').trim();
  const full = s.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (full) return `${full[1]}-${full[2]}-${full[3]}`;
  const md = s.match(/(\d{2})-(\d{2})/);
  if (md) return `${md[1]}-${md[2]}`;
  return s;
}

function sameDateV117(a: any, b: any): boolean {
  const ak = dateKeyV117(a);
  const bk = dateKeyV117(b);
  if (!ak || !bk) return false;
  if (ak === bk) return true;
  if (ak.length === 10 && bk.length === 5) return ak.slice(5) === bk;
  if (bk.length === 10 && ak.length === 5) return bk.slice(5) === ak;
  return false;
}

function etfLatestDateV117(row: AnyRow): string {
  return String(row?.latest_date ?? row?.latestDate ?? row?.data_date ?? row?.dataDate ?? row?.date ?? '').trim();
}

async function loadMissingEtfsV117(targetDate: any): Promise<AnyRow[]> {
  const target = String(targetDate ?? '').trim();
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !anonKey || !target) return [];

  const headers = {
    apikey: anonKey,
    Authorization: `Bearer ${anonKey}`,
  };

  try {
    const codeExpr = ACTIVE_ETF_CODES_V117.join(',');
    const holdingUrl = `${supabaseUrl}/rest/v1/holdings?select=etf_code,data_date&etf_code=in.(${codeExpr})&order=data_date.desc&limit=8000`;
    const holdingRes = await fetch(holdingUrl, { headers, cache: 'no-store' });
    if (!holdingRes.ok) return [];
    const holdingRows = await holdingRes.json();

    const latest = new Map<string, string>();
    if (Array.isArray(holdingRows)) {
      for (const r of holdingRows) {
        const code = String(r?.etf_code ?? '').trim();
        const dt = String(r?.data_date ?? '').trim();
        if (code && dt && !latest.has(code)) latest.set(code, dt);
      }
    }

    const names = new Map<string, string>();
    try {
      const quoteUrl = `${supabaseUrl}/rest/v1/etf_quotes?select=etf_code,etf_name&etf_code=in.(${codeExpr})&limit=200`;
      const quoteRes = await fetch(quoteUrl, { headers, cache: 'no-store' });
      if (quoteRes.ok) {
        const quoteRows = await quoteRes.json();
        if (Array.isArray(quoteRows)) {
          for (const r of quoteRows) {
            const c = String(r?.etf_code ?? '').trim();
            const n = String(r?.etf_name ?? '').trim();
            if (c && n) names.set(c, n);
          }
        }
      }
    } catch (_) {}

    return ACTIVE_ETF_CODES_V117
      .filter((code) => !sameDateV117(latest.get(code), target))
      .map((code) => ({
        etf_code: code,
        etf_name: names.get(code) || ETF_NAME_HINT_V117[code] || '',
        latest_date: latest.get(code) || '',
      }));
  } catch (_) {
    return [];
  }
}
// V117_MISSING_ETF_LIST_HELPERS_END
'''

if 'V117_MISSING_ETF_LIST_HELPERS_START' not in text:
    m = re.search(r'function DataQuality\s*\(', text)
    if not m:
        raise SystemExit('❌ 找不到 function DataQuality，請貼 SignalsClient.tsx 給我。')
    text = text[:m.start()] + helper + '\n' + text[m.start():]

# 4) Replace DataQuality with a safer, compact modal that loads real missing ETFs when API lacks list.
new_data_quality = r'''function DataQuality({ data, activeDays }: { data: any; activeDays: number }) {
  const [open, setOpen] = useState(false);
  const [loadingMissing, setLoadingMissing] = useState(false);
  const [loadedMissing, setLoadedMissing] = useState<AnyRow[]>([]);
  const [loadedOnce, setLoadedOnce] = useState(false);

  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const missingEtfs = missingEtfsOf(data);
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';
  const shownMissingEtfs = missingEtfs.length > 0 ? missingEtfs : loadedMissing;

  useEffect(() => {
    if (!open || activeDays !== 1 || missing <= 0 || loadedOnce || missingEtfs.length > 0) return;
    setLoadingMissing(true);
    loadMissingEtfsV117(date)
      .then((rows) => {
        setLoadedMissing(rows);
        setLoadedOnce(true);
      })
      .finally(() => setLoadingMissing(false));
  }, [open, activeDays, missing, loadedOnce, missingEtfs.length, date]);

  if (activeDays !== 1) {
    return (
      <div className="signals-quality-v114 compact-v117">
        <span>資料區間：近 {activeDays} 日</span>
        <span>資料日 {mmdd(date)}</span>
      </div>
    );
  }

  return (
    <>
      <div className="signals-quality-v114 compact-v117">
        <span>資料日 <b>{mmdd(date)}</b></span>
        <span>已取得今日資料 <b>{today}</b> / {total} 檔 ETF</span>
        {missing > 0 && (
          <button type="button" className="signals-warning-link-v117" onClick={() => setOpen(true)}>
            未更新 {missing} 檔，查看清單
          </button>
        )}
      </div>

      {open && (
        <div className="signals-modal-mask-v117" onClick={() => setOpen(false)}>
          <div className="signals-modal-v117" onClick={(e) => e.stopPropagation()}>
            <div className="signals-modal-head-v117">
              <div>
                <h3>未更新 ETF 清單</h3>
                <p>今日訊號只使用 {mmdd(date)} 當日資料，不混入前一日。</p>
              </div>
              <button type="button" onClick={() => setOpen(false)} aria-label="關閉">×</button>
            </div>

            {loadingMissing ? (
              <div className="signals-modal-note-v117">正在查詢未更新 ETF 清單…</div>
            ) : shownMissingEtfs.length > 0 ? (
              <div className="signals-missing-list-v117">
                {shownMissingEtfs.map((row, idx) => {
                  const code = etfCodeOf(row) || `ETF ${idx + 1}`;
                  const name = etfNameOf(row);
                  const latest = etfLatestDateV117(row);
                  return (
                    <div className="signals-missing-row-v117" key={`${code}-${idx}`}>
                      <div>
                        <b>{code}</b>
                        {name && <span>{name}</span>}
                      </div>
                      <em>{latest ? `最新 ${mmdd(latest)}` : '尚無資料'}</em>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="signals-modal-note-v117">
                目前 API 只回傳「未更新 {missing} 檔」的數量，尚未回傳 ETF 代號清單。若仍看不到清單，請確認 Supabase 的 holdings / etf_quotes 已開啟 public read policy。
              </div>
            )}

            <button type="button" className="signals-modal-ok-v117" onClick={() => setOpen(false)}>我知道了</button>
          </div>
        </div>
      )}
    </>
  );
}
'''

pat = re.compile(r'function DataQuality\s*\([\s\S]*?\n?function FocusCard\s*\(')
match = pat.search(text)
if not match:
    raise SystemExit('❌ 找不到 DataQuality 到 FocusCard 區段，請貼 SignalsClient.tsx 給我。')
text = text[:match.start()] + new_data_quality + '\nfunction FocusCard(' + text[match.end():]

SIG.write_text(text, encoding='utf-8')

css = CSS.read_text(encoding='utf-8')
css_block = r'''

/* V117: compact signals data-quality area + real missing ETF modal */
.signals-range-card-v114 + .signals-range-card-v114 {
  display: none !important;
}
.signals-quality-v114.compact-v117 {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  align-items: center;
  font-size: clamp(15px, 3.6vw, 18px) !important;
  line-height: 1.35;
  color: #778295;
  margin: 4px 0 14px;
}
.signals-quality-v114.compact-v117 b {
  color: #121a2b;
  font-weight: 900;
}
.signals-warning-link-v117 {
  border: 0;
  background: transparent;
  color: #a9791e;
  font: inherit;
  font-weight: 900;
  padding: 0;
  text-align: left;
  cursor: pointer;
}
.signals-warning-link-v117::after {
  content: ' ›';
}
.signals-modal-mask-v117 {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(15, 23, 42, .44);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 18px;
}
.signals-modal-v117 {
  width: min(100%, 520px);
  max-height: 82vh;
  overflow: auto;
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 24px 80px rgba(15, 23, 42, .26);
  padding: 20px 18px 18px;
}
.signals-modal-head-v117 {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.signals-modal-head-v117 h3 {
  margin: 0 0 6px;
  font-size: clamp(26px, 6.8vw, 34px);
  line-height: 1.08;
  font-weight: 950;
  color: #111827;
}
.signals-modal-head-v117 p {
  margin: 0;
  font-size: clamp(15px, 4vw, 18px);
  line-height: 1.45;
  color: #687386;
  font-weight: 800;
}
.signals-modal-head-v117 button {
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 999px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 28px;
  font-weight: 900;
  line-height: 1;
}
.signals-missing-list-v117 {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  overflow: hidden;
  margin: 12px 0 16px;
}
.signals-missing-row-v117 {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid #edf2f7;
}
.signals-missing-row-v117:last-child {
  border-bottom: 0;
}
.signals-missing-row-v117 b {
  display: block;
  font-size: clamp(18px, 5vw, 24px);
  line-height: 1.05;
  color: #111827;
  font-weight: 950;
}
.signals-missing-row-v117 span {
  display: block;
  margin-top: 4px;
  font-size: clamp(13px, 3.8vw, 16px);
  line-height: 1.2;
  color: #687386;
  font-weight: 800;
}
.signals-missing-row-v117 em {
  white-space: nowrap;
  font-style: normal;
  color: #a9791e;
  font-size: clamp(13px, 3.6vw, 16px);
  font-weight: 900;
}
.signals-modal-note-v117 {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 16px;
  padding: 14px;
  color: #475569;
  font-size: clamp(15px, 4vw, 18px);
  line-height: 1.55;
  font-weight: 800;
  margin: 12px 0 16px;
}
.signals-modal-ok-v117 {
  width: 100%;
  height: 54px;
  border: 0;
  border-radius: 14px;
  background: #2f7df6;
  color: #fff;
  font-size: 20px;
  font-weight: 950;
}
@media (min-width: 768px) {
  .signals-modal-mask-v117 {
    align-items: center;
  }
}
'''
if 'V117: compact signals data-quality area' not in css:
    css += css_block
CSS.write_text(css, encoding='utf-8')

README.write_text('''# V117 Missing ETF List Modal\n\n修正內容：\n\n1. 未更新 ETF modal 不再顯示 ETF 1 / ETF 2 假資料。\n2. 若 /signals API 沒有回傳 non_today_etfs，前端會在打開 modal 時從 Supabase holdings 查各 ETF 最新 data_date，列出未更新清單。\n3. 壓低資料完整度文字與 modal 字級，避免手機上過大。\n4. 嘗試移除 SignalsClient 內重複的訊號區間入口，並用 CSS 防止連續重複顯示。\n\n注意：如果本機 npm run build 出現 supabaseUrl is required，代表本機 frontend/.env.local 沒有 NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY；Vercel 有環境變數則仍可部署。\n''', encoding='utf-8')

print('✅ V117 已完成：未更新 ETF 清單改為真實查詢、字級壓小、嘗試移除重複訊號區間。')
print('接著 git add / commit / push。')
