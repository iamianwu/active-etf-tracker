#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
api_path = ROOT / 'frontend' / 'lib' / 'api.ts'
comp_path = ROOT / 'frontend' / 'components' / 'SignalsClient.tsx'
css_path = ROOT / 'frontend' / 'app' / 'globals.css'

missing = [str(p) for p in [api_path, comp_path] if not p.exists()]
if missing:
    raise SystemExit('❌ 找不到必要檔案：\n' + '\n'.join(missing) + '\n請先 cd 到專案根目錄，例如：cd ~/Downloads/active-etf-tracker-fix')

# -----------------------------
# 1) api.ts：修正 metadata 語意
# -----------------------------
api = api_path.read_text(encoding='utf-8')
bak_api = api_path.with_suffix(api_path.suffix + '.bak_v110')
if not bak_api.exists():
    bak_api.write_text(api, encoding='utf-8')

# V109 可能把 fetched_etf_count 寫成 includedEtfs.length；這會讓 UI 顯示 18/18。
# V110：fetched_etf_count / today_etf_count = targetDate 當天有 holdings 的 ETF 數。
api = api.replace(
    'fetched_etf_count: includedEtfs.length,',
    'fetched_etf_count: todayEtfSet.size,',
)

if 'comparable_etf_count:' not in api:
    api = api.replace(
        'includedEtfCount: includedEtfs.length,\n      fetched_etf_count:',
        'includedEtfCount: includedEtfs.length,\n      comparable_etf_count: includedEtfs.length,\n      signal_etf_count: includedEtfs.length,\n      fetched_etf_count:',
        1,
    )

# 加入更清楚的排除統計欄位，供前端直接顯示。
if 'excluded_compare_etf_count:' not in api:
    api = api.replace(
        'no_compare_etf_count: noCompareEtfCodes.length,\n      no_compare_etf_codes:',
        'no_compare_etf_count: noCompareEtfCodes.length,\n      excluded_compare_etf_count: Math.max(0, universeEtfs.length - includedEtfs.length),\n      non_today_etf_count: missingTodayEtfCodes.length,\n      no_compare_etf_codes:',
        1,
    )

# 讓 data_note 文案也不要把 included/total 說成今日抓取數。
old_note = """data_note: missingTodayEtfCodes.length
        ? `只納入 ${targetDate} 有持股且可比較的 ${includedEtfs.length}/${universeEtfs.length} 檔 ETF；排除 ${missingTodayEtfCodes.length} 檔非本資料日 ETF。`
        : `只納入 ${targetDate} 有持股且可比較的 ${includedEtfs.length}/${universeEtfs.length} 檔 ETF。`,"""
new_note = """data_note: `今日有資料 ${todayEtfSet.size}/${universeEtfs.length} 檔 ETF；可計算訊號 ${includedEtfs.length} 檔；未納入 ${Math.max(0, universeEtfs.length - includedEtfs.length)} 檔（${missingTodayEtfCodes.length} 檔非今日資料、${noCompareEtfCodes.length} 檔缺前日比較）。`,"""
if old_note in api:
    api = api.replace(old_note, new_note, 1)

api_path.write_text(api, encoding='utf-8')

# -----------------------------
# 2) SignalsClient.tsx：改 UI 顯示 19/27 + 可計算 18
# -----------------------------
comp = comp_path.read_text(encoding='utf-8')
bak_comp = comp_path.with_suffix(comp_path.suffix + '.bak_v110')
if not bak_comp.exists():
    bak_comp.write_text(comp, encoding='utf-8')

# 找 dataDate / fetched / total 區塊，替換成更明確的 metadata。
new_meta = """  const dataDate = data?.data_date ?? data?.latestDataDate ?? data?.target_data_date ?? '';
  const totalEtfCount = Number(data?.total_etf_count ?? data?.totalEtfCount ?? 27) || 27;
  const todayEtfCount = Number(data?.today_etf_count ?? data?.todayEtfCount ?? data?.fetched_etf_count ?? 0) || 0;
  const comparableEtfCount = Number(data?.includedEtfCount ?? data?.comparable_etf_count ?? data?.signal_etf_count ?? 0) || 0;
  const nonTodayEtfCount = Number(data?.missing_today_etf_count ?? data?.non_today_etf_count ?? Math.max(0, totalEtfCount - todayEtfCount)) || 0;
  const noCompareEtfCount = Number(data?.no_compare_etf_count ?? Math.max(0, todayEtfCount - comparableEtfCount)) || 0;
  const excludedCompareCount = Math.max(0, totalEtfCount - comparableEtfCount);
  const hasSignalMeta = totalEtfCount > 0 || todayEtfCount > 0 || comparableEtfCount > 0;"""

patterns = [
    re.compile(r"\s*const\s+dataDate\s*=\s*data\?\.data_date\s*\?\?\s*data\?\.latestDataDate\s*\?\?\s*'';\s*const\s+fetched\s*=\s*data\?\.fetched_etf_count\s*\?\?\s*data\?\.includedEtfCount\s*\?\?\s*0;\s*const\s+total\s*=\s*data\?\.total_etf_count\s*\?\?\s*data\?\.totalEtfCount\s*\?\?\s*0;", re.S),
    re.compile(r"\s*const\s+dataDate\s*=.*?;\s*const\s+rawFetched\s*=.*?;\s*const\s+rawTotal\s*=.*?;.*?const\s+displayTotal\s*=.*?;\s*const\s+displayFetched\s*=.*?;", re.S),
    re.compile(r"\s*const\s+dataDate\s*=.*?;\s*const\s+totalEtfCount\s*=.*?;\s*const\s+todayEtfCount\s*=.*?;\s*const\s+comparableEtfCount\s*=.*?;\s*const\s+nonTodayEtfCount\s*=.*?;\s*const\s+noCompareEtfCount\s*=.*?;\s*const\s+excludedCompareCount\s*=.*?;\s*const\s+hasSignalMeta\s*=.*?;", re.S),
]
replaced = False
for pat in patterns:
    comp2, n = pat.subn('\n' + new_meta, comp, count=1)
    if n:
        comp = comp2
        replaced = True
        break
if not replaced:
    # 保底：插在 toggleStatus 前面。
    marker = '  function toggleStatus'
    if marker not in comp:
        raise SystemExit('❌ 找不到 SignalsClient.tsx 的 metadata 區塊，請貼 dataDate 附近內容。')
    comp = comp.replace(marker, new_meta + '\n\n' + marker, 1)

# 替換狀態文字區塊。
status_re = re.compile(
    r'(<div\s+className="signals-data-status ok">)(.*?)(\n\s*</div>)',
    re.S,
)
new_status_inner = """
          {hasSignalMeta ? (
            <>
              今日有資料 {todayEtfCount} / {totalEtfCount} 檔 ETF
              {dataDate ? `，資料日期 ${mmdd(dataDate)}` : ''}
              <span className="signals-meta-subline">
                可計算訊號 {comparableEtfCount} 檔；未納入 {excludedCompareCount} 檔
                {excludedCompareCount > 0 ? `（${nonTodayEtfCount} 檔非今日資料、${noCompareEtfCount} 檔缺前日比較）` : ''}
              </span>
            </>
          ) : (
            <>
              今日訊號資料載入中
              {dataDate ? `，資料日期 ${mmdd(dataDate)}` : ''}
            </>
          )}"""
comp, n = status_re.subn(r'\1' + new_status_inner + r'\3', comp, count=1)
if n == 0:
    raise SystemExit('❌ 找不到 <div className="signals-data-status ok"> 區塊，請貼 SignalsClient.tsx 的 title block。')

# 避免殘留舊變數造成 TS/JS 報錯。若仍有 displayFetched/displayTotal/fetched/total 在 JSX 文案，替換掉。
comp = comp.replace('已納入訊號 {displayFetched} / {displayTotal} 檔 ETF', '今日有資料 {todayEtfCount} / {totalEtfCount} 檔 ETF')
comp = comp.replace('已抓取 {fetched || total || 0} / {total || fetched || 0} 檔 ETF', '今日有資料 {todayEtfCount} / {totalEtfCount} 檔 ETF')

comp_path.write_text(comp, encoding='utf-8')

# -----------------------------
# 3) CSS：小字說明
# -----------------------------
if css_path.exists():
    css = css_path.read_text(encoding='utf-8')
    bak_css = css_path.with_suffix(css_path.suffix + '.bak_v110')
    if not bak_css.exists():
        bak_css.write_text(css, encoding='utf-8')
    css_add = """

/* V110 今日訊號資料統計說明 */
.signals-meta-subline {
  display: block;
  margin-top: 4px;
  font-size: 0.82em;
  line-height: 1.35;
  color: #8b97a8;
  font-weight: 700;
}
"""
    if '.signals-meta-subline' not in css:
        css += css_add
        css_path.write_text(css, encoding='utf-8')

readme = ROOT / 'README_V110_SIGNAL_METADATA_DISPLAY.md'
readme.write_text('''# V110 Signal metadata display fix

修正今日訊號顯示邏輯：

- 不再顯示錯誤的 `18 / 18`。
- 改成顯示：`今日有資料 19 / 27 檔 ETF`。
- 另外顯示：`可計算訊號 18 檔；未納入 9 檔（8 檔非今日資料、1 檔缺前日比較）`。
- API metadata 分清楚：
  - `total_etf_count`: ETF 清單總數，例如 27。
  - `today_etf_count`: targetDate 當天有 holdings 的 ETF，例如 19。
  - `includedEtfCount` / `comparable_etf_count`: 有今日資料且有前日可比較的 ETF，例如 18。
''', encoding='utf-8')

print('✅ V110 已完成：修正今日訊號 metadata 與畫面顯示，不再出現 18/18。')
print('   已備份：', bak_api)
print('   已備份：', bak_comp)
print('   已新增：', readme)
