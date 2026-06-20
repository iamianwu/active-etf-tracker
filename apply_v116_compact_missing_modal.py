#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path.cwd()
if not (ROOT / 'frontend').exists():
    print('❌ 請在 repo 根目錄執行，例如：cd ~/Downloads/active-etf-tracker-fix')
    sys.exit(1)

signals = ROOT / 'frontend' / 'components' / 'SignalsClient.tsx'
css = ROOT / 'frontend' / 'app' / 'globals.css'
page = ROOT / 'frontend' / 'app' / 'signals' / 'page.tsx'

if not signals.exists():
    print(f'❌ 找不到 {signals}')
    sys.exit(1)
if not css.exists():
    print(f'❌ 找不到 {css}')
    sys.exit(1)

# backup
signals.write_text(signals.read_text(encoding='utf-8'), encoding='utf-8')
(signals.with_suffix(signals.suffix + '.bak_v116')).write_text(signals.read_text(encoding='utf-8'), encoding='utf-8')
(css.with_suffix(css.suffix + '.bak_v116')).write_text(css.read_text(encoding='utf-8'), encoding='utf-8')
if page.exists():
    (page.with_suffix(page.suffix + '.bak_v116')).write_text(page.read_text(encoding='utf-8'), encoding='utf-8')

s = signals.read_text(encoding='utf-8')

# Keep only page-level range. If SignalsClient still renders a range block internally, hide/remove common duplicate patterns lightly.
# Main fix: replace DataQuality so it does not invent ETF 1 / ETF 2 placeholder rows.
new_helpers_and_quality = r'''
function missingEtfsOf(data: any): AnyRow[] {
  const candidates = [
    data?.non_today_etfs,
    data?.nonTodayEtfs,
    data?.missing_etfs,
    data?.missingEtfs,
    data?.outdated_etfs,
    data?.outdatedEtfs,
    data?.not_updated_etfs,
    data?.notUpdatedEtfs,
  ];
  const arr = candidates.find((x) => Array.isArray(x));
  if (!Array.isArray(arr)) return [];
  return arr.map((x: any) => {
    if (typeof x === 'string') return { etf_code: x };
    return x || {};
  });
}

function etfCodeOf(row: AnyRow): string {
  return String(row.etf_code ?? row.etfCode ?? row.code ?? row.id ?? '').trim();
}

function etfNameOf(row: AnyRow): string {
  return String(row.etf_name ?? row.etfName ?? row.name ?? row.title ?? '').trim();
}

function etfLatestDateOf(row: AnyRow): string {
  return mmdd(row.latest_date ?? row.latestDate ?? row.data_date ?? row.dataDate ?? row.date ?? '');
}

function DataQuality({ data, activeDays }: { data: any; activeDays: number }) {
  const [open, setOpen] = useState(false);
  const total = getTotalEtfs(data);
  const today = getTodayEtfs(data, total);
  const missing = Math.max(0, total - today);
  const missingEtfs = missingEtfsOf(data);
  const date = data?.target_date ?? data?.data_date ?? data?.latestDataDate ?? '';

  if (activeDays !== 1) {
    return (
      <div className="signals-quality-v114 signals-quality-v116">
        <span>資料區間：近 {activeDays} 日</span>
        <span>資料日 {mmdd(date)}</span>
      </div>
    );
  }

  return (
    <>
      <div className="signals-quality-v114 signals-quality-v116">
        <div className="quality-line-v116">資料日 <b>{mmdd(date)}</b></div>
        <div className="quality-line-v116">已取得今日資料 <b>{today}</b> / {total} 檔 ETF</div>
        {missing > 0 && (
          <button type="button" className="signals-warning-v114 signals-warning-v116" onClick={() => setOpen(true)}>
            未更新 {missing} 檔，查看清單
          </button>
        )}
      </div>

      {open && (
        <div className="missing-modal-mask-v116" role="dialog" aria-modal="true" onClick={() => setOpen(false)}>
          <div className="missing-modal-v116" onClick={(e) => e.stopPropagation()}>
            <div className="missing-modal-head-v116">
              <div>
                <div className="missing-modal-title-v116">未更新 ETF 清單</div>
                <div className="missing-modal-sub-v116">今日訊號只使用 {mmdd(date)} 當日資料，不混入前一日。</div>
              </div>
              <button type="button" className="missing-modal-x-v116" onClick={() => setOpen(false)} aria-label="關閉">×</button>
            </div>

            {missingEtfs.length > 0 ? (
              <div className="missing-list-v116">
                {missingEtfs.map((row, idx) => {
                  const code = etfCodeOf(row) || `第 ${idx + 1} 檔`;
                  const name = etfNameOf(row);
                  const latest = etfLatestDateOf(row);
                  return (
                    <div className="missing-row-v116" key={`${code}-${idx}`}>
                      <div>
                        <div className="missing-code-v116">{code}</div>
                        {name && <div className="missing-name-v116">{name}</div>}
                      </div>
                      <div className="missing-date-v116">{latest && latest !== '-' ? `最新 ${latest}` : '尚無日期'}</div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="missing-empty-v116">
                目前資料只回傳「未更新 {missing} 檔」的數量，尚未回傳 ETF 代號清單，所以不再用 ETF 1、ETF 2 這種假資料顯示。
                <br />下一步可在 /signals API 補回 non_today_etfs 清單。
              </div>
            )}

            <button type="button" className="missing-ok-v116" onClick={() => setOpen(false)}>我知道了</button>
          </div>
        </div>
      )}
    </>
  );
}
'''

pattern = re.compile(r"function DataQuality\(\{ data, activeDays \}: \{ data: any; activeDays: number \}\) \{.*?\n\}\n\nfunction FocusCard", re.S)
if not pattern.search(s):
    print('❌ 找不到 DataQuality 區塊，請貼 SignalsClient.tsx 的 DataQuality 附近內容。')
    sys.exit(1)
s = pattern.sub(new_helpers_and_quality + "\nfunction FocusCard", s, count=1)

# Replace sort glyphs if any button uses unicode arrow icon-only; keep ▲▼ convention preferred by user.
s = s.replace('↕', '▲▼')
s = s.replace('⇅', '▲▼')
s = s.replace('⬍', '▲▼')

signals.write_text(s, encoding='utf-8')

# Remove duplicated range block from page if current design already has it twice? Keep page range as canonical.
# We won't remove page range; CSS will make it compact.

append_css = r'''

/* ===== V116: compact signals UI and readable missing ETF modal ===== */
@media (max-width: 640px) {
  html, body {
    overflow-x: hidden !important;
  }

  main, .app-shell, .page-shell, .signals-page-v114, .signals-shell-v114, .signals-main-v114 {
    max-width: 100vw !important;
    overflow-x: hidden !important;
  }

  section[aria-label="訊號區間"],
  .signals-range-card-v114 {
    margin: 14px 16px 22px !important;
    padding: 0 !important;
  }

  .signals-range-label-v114,
  section[aria-label="訊號區間"] > div:first-child {
    font-size: 20px !important;
    line-height: 1.25 !important;
    margin-bottom: 10px !important;
  }

  .signals-range-tabs-v114,
  section[aria-label="訊號區間"] nav,
  section[aria-label="訊號區間"] .range-tabs {
    height: 48px !important;
    min-height: 48px !important;
    border-radius: 999px !important;
  }

  .signals-range-tabs-v114 a,
  .signals-range-tabs-v114 button,
  section[aria-label="訊號區間"] a,
  section[aria-label="訊號區間"] button {
    font-size: 20px !important;
    line-height: 1 !important;
    min-height: 38px !important;
    padding: 0 14px !important;
    border-radius: 999px !important;
  }

  .signals-title-v114,
  .signals-section-title-v114,
  .signals-page-v114 h1,
  .signals-main-v114 h1 {
    font-size: 42px !important;
    line-height: 1.05 !important;
    letter-spacing: -0.04em !important;
  }

  .signals-quality-v116 {
    font-size: 18px !important;
    line-height: 1.45 !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 2px !important;
    margin: 6px 0 16px !important;
  }

  .signals-warning-v116 {
    appearance: none !important;
    border: 0 !important;
    background: transparent !important;
    color: #a97719 !important;
    font-weight: 800 !important;
    text-align: left !important;
    padding: 2px 0 !important;
    font-size: 18px !important;
    line-height: 1.35 !important;
  }

  .focus-grid-v114,
  .signals-focus-grid-v114 {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 12px !important;
    width: 100% !important;
  }

  .focus-card-v114 {
    min-width: 0 !important;
    min-height: 176px !important;
    padding: 16px !important;
    border-radius: 18px !important;
    overflow: hidden !important;
  }

  .focus-title-v114 {
    font-size: 20px !important;
    line-height: 1.2 !important;
    margin-bottom: 12px !important;
    white-space: normal !important;
  }

  .focus-name-v114,
  .focus-card-v114 .stock-name,
  .focus-card-v114 .name {
    font-size: 22px !important;
    line-height: 1.15 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
  }

  .focus-code-v114,
  .focus-card-v114 .code {
    font-size: 16px !important;
  }

  .focus-price-v114,
  .focus-card-v114 .price {
    font-size: 36px !important;
    line-height: 1 !important;
    letter-spacing: -0.04em !important;
  }

  .focus-card-v114 .pct,
  .focus-pct-v114 {
    font-size: 18px !important;
  }

  .focus-card-v114 .metric,
  .focus-meta-v114,
  .focus-card-v114 small {
    font-size: 15px !important;
    line-height: 1.35 !important;
  }

  .signals-filter-row-v114,
  .signals-sort-row-v114,
  .signal-sort-row-v114,
  .signals-pills-v114 {
    display: flex !important;
    flex-wrap: nowrap !important;
    gap: 8px !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    max-width: 100% !important;
    padding-bottom: 6px !important;
    -webkit-overflow-scrolling: touch !important;
  }

  .signals-filter-row-v114 > *,
  .signals-sort-row-v114 > *,
  .signal-sort-row-v114 > *,
  .signals-pills-v114 > * {
    flex: 0 0 auto !important;
    white-space: nowrap !important;
    font-size: 18px !important;
    min-height: 38px !important;
    padding: 0 14px !important;
  }

  .signals-table-head-v114,
  .signals-row-v114,
  .signal-row-v114 {
    max-width: 100% !important;
    box-sizing: border-box !important;
  }

  .missing-modal-mask-v116 {
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(15, 23, 42, 0.46);
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding: 16px;
  }

  .missing-modal-v116 {
    width: min(100%, 430px);
    max-height: min(78vh, 620px);
    overflow: auto;
    background: #fff;
    border-radius: 24px;
    padding: 22px 18px 18px;
    box-shadow: 0 20px 60px rgba(15, 23, 42, 0.24);
  }

  .missing-modal-head-v116 {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
  }

  .missing-modal-title-v116 {
    font-size: 26px;
    line-height: 1.15;
    font-weight: 900;
    color: #111827;
    letter-spacing: -0.03em;
  }

  .missing-modal-sub-v116 {
    margin-top: 8px;
    font-size: 15px;
    line-height: 1.45;
    color: #6b7280;
    font-weight: 700;
  }

  .missing-modal-x-v116 {
    flex: 0 0 auto;
    border: 0;
    background: #f1f5f9;
    color: #475569;
    width: 34px;
    height: 34px;
    border-radius: 999px;
    font-size: 24px;
    line-height: 1;
    font-weight: 700;
  }

  .missing-list-v116 {
    display: flex;
    flex-direction: column;
    border-top: 1px solid #e5e7eb;
  }

  .missing-row-v116 {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid #e5e7eb;
  }

  .missing-code-v116 {
    font-size: 20px;
    line-height: 1.1;
    font-weight: 900;
    color: #111827;
  }

  .missing-name-v116 {
    margin-top: 3px;
    max-width: 210px;
    font-size: 14px;
    line-height: 1.25;
    font-weight: 700;
    color: #6b7280;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .missing-date-v116 {
    flex: 0 0 auto;
    font-size: 14px;
    font-weight: 800;
    color: #a97719;
    white-space: nowrap;
  }

  .missing-empty-v116 {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 14px;
    font-size: 15px;
    line-height: 1.6;
    color: #475569;
    font-weight: 700;
  }

  .missing-ok-v116 {
    width: 100%;
    height: 48px;
    margin-top: 16px;
    border: 0;
    border-radius: 14px;
    background: #2f7df6;
    color: #fff;
    font-size: 18px;
    font-weight: 900;
  }
}
'''

c = css.read_text(encoding='utf-8')
# avoid duplicate append
c = re.sub(r"\n/\* ===== V116: compact signals UI and readable missing ETF modal ===== \*/.*$", "", c, flags=re.S)
c += append_css
css.write_text(c, encoding='utf-8')

# README
(ROOT / 'README_V116_COMPACT_SIGNAL_MODAL.md').write_text('''# V116 Compact Signal Modal\n\n修正：\n- 未更新 ETF 清單不再顯示 ETF 1 / ETF 2 假資料。\n- 若 API 有回傳 non_today_etfs / missing_etfs 等清單，會顯示實際 ETF 代號、名稱與最新日期。\n- 若 API 只有回傳數量，會明確顯示目前尚未回傳清單。\n- 手機版今日訊號字體縮小，避免資訊超出頁面。\n- 排序符號改回 ▲ / ▼。\n''', encoding='utf-8')

print('✅ V116 已完成：字體縮小、未更新清單不再顯示假 ETF、排序符號改回 ▲/▼、手機版避免超出頁面')
print('接著執行：cd frontend && npm run build')
