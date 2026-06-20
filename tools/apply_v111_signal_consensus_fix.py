#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
api_path = ROOT / 'frontend' / 'lib' / 'api.ts'
comp_path = ROOT / 'frontend' / 'components' / 'SignalsClient.tsx'

missing = [str(p) for p in [api_path, comp_path] if not p.exists()]
if missing:
    raise SystemExit('❌ 找不到必要檔案：\n' + '\n'.join(missing) + '\n請先 cd 到專案根目錄，例如：cd ~/Downloads/active-etf-tracker-fix')


def backup(path: Path, tag: str):
    bak = path.with_suffix(path.suffix + f'.bak_{tag}')
    if not bak.exists():
        bak.write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
    return bak


def find_function_span(text: str, names):
    """Return (start,end,name) for first matching JS function by brace counting."""
    for name in names:
        m = re.search(r'function\s+' + re.escape(name) + r'\s*\([^)]*\)\s*(:\s*[^\{]+)?\{', text)
        if not m:
            continue
        brace_start = text.find('{', m.start())
        level = 0
        in_str = None
        escape = False
        in_line = False
        in_block = False
        for i in range(brace_start, len(text)):
            ch = text[i]
            nxt = text[i+1] if i+1 < len(text) else ''
            if in_line:
                if ch == '\n': in_line = False
                continue
            if in_block:
                if ch == '*' and nxt == '/': in_block = False
                continue
            if in_str:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == in_str:
                    in_str = None
                continue
            if ch == '/' and nxt == '/':
                in_line = True
                continue
            if ch == '/' and nxt == '*':
                in_block = True
                continue
            if ch in ('"', "'", '`'):
                in_str = ch
                continue
            if ch == '{':
                level += 1
            elif ch == '}':
                level -= 1
                if level == 0:
                    return m.start(), i + 1, name
    return None

# -------------------------------------------------------------------
# 1) frontend/lib/api.ts：讓每筆 signal row 明確帶 buy/sell count aliases
# -------------------------------------------------------------------
api = api_path.read_text(encoding='utf-8')
bak_api = backup(api_path, 'v111')

# 在 getSignals 的 row return 裡加入所有前端可能會讀的 alias。
# 這樣「買賣檔數」不會 fallback 到持有 ETF 總數。
if 'buy_count: g.buy_etf_count' not in api and 'sell_count: g.sell_etf_count' not in api:
    # 優先找 v109 結構：status, 後面接 delta_shares。
    pattern = re.compile(r'(\n\s*status,\n)(\s*delta_shares:)')
    repl = ("\\1"
            "        buy_count: g.buy_etf_count,\n"
            "        sell_count: g.sell_etf_count,\n"
            "        add_etf_count: g.buy_etf_count,\n"
            "        reduce_etf_count: g.sell_etf_count,\n"
            "        increase_etf_count: g.increase_count,\n"
            "        decrease_etf_count: g.decrease_count,\n"
            "        add_count: g.add_count,\n"
            "        delete_count: g.delete_count,\n"
            "        increase_count: g.increase_count,\n"
            "        decrease_count: g.decrease_count,\n"
            "        etf_count: g.etf_change_count,\n"
            "\\2")
    api, n = pattern.subn(repl, api, count=1)
    if n == 0:
        # 保底：放在 consensus 前面。
        pattern2 = re.compile(r'(\n\s*consensus:\s*`買賣檔數 \$\{g\.buy_etf_count\}:\$\{g\.sell_etf_count\}`,)')
        repl2 = ("\n        buy_count: g.buy_etf_count,"
                 "\n        sell_count: g.sell_etf_count,"
                 "\n        add_etf_count: g.buy_etf_count,"
                 "\n        reduce_etf_count: g.sell_etf_count,"
                 "\n        increase_etf_count: g.increase_count,"
                 "\n        decrease_etf_count: g.decrease_count,"
                 "\n        add_count: g.add_count,"
                 "\n        delete_count: g.delete_count,"
                 "\n        increase_count: g.increase_count,"
                 "\n        decrease_count: g.decrease_count,"
                 "\n        etf_count: g.etf_change_count,"
                 "\\1")
        api, n2 = pattern2.subn(repl2, api, count=1)
        if n2 == 0:
            print('⚠️ api.ts：找不到 v109 row return 的插入點，已略過 API alias patch。')

# 修正可能殘留的 fetched_etf_count 語意。
api = api.replace('fetched_etf_count: includedEtfs.length,', 'fetched_etf_count: todayEtfSet.size,')

api_path.write_text(api, encoding='utf-8')

# -------------------------------------------------------------------
# 2) frontend/components/SignalsClient.tsx：多空共識不可 fallback 成「持有 ETF 總數」
# -------------------------------------------------------------------
comp = comp_path.read_text(encoding='utf-8')
bak_comp = backup(comp_path, 'v111')

helper = r'''
function countChangedEtfs(row: AnyRow, positive: boolean): number {
  const list = Array.isArray(row?.changed_etfs)
    ? row.changed_etfs
    : Array.isArray(row?.changedEtfs)
      ? row.changedEtfs
      : Array.isArray(row?.etf_changes)
        ? row.etf_changes
        : [];

  if (!list.length) return 0;

  return list.filter((x: AnyRow) => {
    const s = String(x?.status ?? x?.type ?? '').trim();
    const raw = firstNum(x, ['delta_shares_lots', 'delta_lots', 'delta_shares', 'shares_change', 'net_lots', 'delta_raw_shares'], NaN);
    let lots = Number.isFinite(raw) ? raw : 0;
    if (Math.abs(lots) >= 100000) lots = lots / 1000;

    if (positive) {
      return ['新增', '加碼', 'add', 'added', 'new', 'increase', 'inc', 'buy'].includes(s) || lots > 0;
    }
    return ['刪除', '減碼', 'remove', 'removed', 'delete', 'deleted', 'decrease', 'dec', 'sell'].includes(s) || lots < 0;
  }).length;
}
'''

if 'function countChangedEtfs(row: AnyRow' not in comp:
    # 插在 getBuyCount 前面；若找不到，插在 getConsensusScore 前面。
    marker = 'function getBuyCount'
    if marker in comp:
        comp = comp.replace(marker, helper + '\n' + marker, 1)
    elif 'function getConsensusScore' in comp:
        comp = comp.replace('function getConsensusScore', helper + '\nfunction getConsensusScore', 1)
    else:
        print('⚠️ SignalsClient.tsx：找不到插入 countChangedEtfs 的位置。')

new_buy = r'''function getBuyCount(row: AnyRow): number {
  const direct = firstNum(row, [
    'buy_etf_count',
    'buy_count',
    'add_etf_count',
    'increase_etf_count',
    'increase_count',
    'add_count',
  ], NaN);
  if (Number.isFinite(direct)) return Math.max(0, Math.round(direct));

  const changed = countChangedEtfs(row, true);
  if (changed > 0) return changed;

  // 最後保底只回傳 1，不可用 etf_count/count，否則會把「持有 18 檔」誤判成「18 檔買/賣」。
  const status = String(row.status ?? row.type ?? '').trim();
  const lots = getLots(row);
  return (['新增', '加碼'].includes(status) || lots > 0) ? 1 : 0;
}'''

new_sell = r'''function getSellCount(row: AnyRow): number {
  const direct = firstNum(row, [
    'sell_etf_count',
    'sell_count',
    'reduce_etf_count',
    'decrease_etf_count',
    'decrease_count',
    'delete_count',
    'remove_count',
  ], NaN);
  if (Number.isFinite(direct)) return Math.max(0, Math.round(direct));

  const changed = countChangedEtfs(row, false);
  if (changed > 0) return changed;

  // 最後保底只回傳 1，不可用 etf_count/count，否則會把「持有 18 檔」誤判成「18 檔買/賣」。
  const status = String(row.status ?? row.type ?? '').trim();
  const lots = getLots(row);
  return (['刪除', '減碼'].includes(status) || lots < 0) ? 1 : 0;
}'''

span = find_function_span(comp, ['getBuyCount'])
if span:
    s, e, _ = span
    comp = comp[:s] + new_buy + comp[e:]
else:
    raise SystemExit('❌ 找不到 SignalsClient.tsx 的 getBuyCount，請貼 getBuyCount/getSellCount 附近內容。')

span = find_function_span(comp, ['getSellCount'])
if span:
    s, e, _ = span
    comp = comp[:s] + new_sell + comp[e:]
else:
    raise SystemExit('❌ 找不到 SignalsClient.tsx 的 getSellCount，請貼 getBuyCount/getSellCount 附近內容。')

# 清掉最危險的舊 fallback 片段，避免重複函式或殘留 inline 計算。
comp = comp.replace("firstNum(row, ['etf_count', 'count'], 0)", "firstNum(row, ['__do_not_use_etf_count_for_consensus__'], 0)")
comp = comp.replace('買賣檔數 {buy}:{sell}', '{buy}:{sell}')
comp = comp.replace('多空共識 <b>買賣檔數 {buy}:{sell}</b>', '多空共識 <b>{buy}:{sell}</b>')

comp_path.write_text(comp, encoding='utf-8')

readme = ROOT / 'README_V111_SIGNAL_CONSENSUS_FIX.md'
readme.write_text('''# V111 Signal consensus fix

修正今日訊號的「多空共識」邏輯。

問題：
- 舊版在缺少 buy/sell count 時，會 fallback 到 `etf_count` / `count`。
- 這會把「持有這檔股票的 ETF 總數」誤當成「今天買賣的 ETF 數」。
- 例如聯發科 2454 在 06/18 只有 1 檔 ETF 減碼，卻顯示 `0:18`。

修正：
- API row 明確輸出：`buy_count`、`sell_count`、`add_etf_count`、`reduce_etf_count`。
- 前端 getBuyCount/getSellCount 優先讀 API 的實際買賣檔數。
- 若沒有欄位，改從 `changed_etfs` 計算。
- 最後保底最多只顯示 1，不再使用 `etf_count/count` 當共識數。

預期：
- 2454 若 06/18 只有一檔 ETF 賣，應顯示 `0:1`，不會再是 `0:18`。
''', encoding='utf-8')

print('✅ V111 已完成：修正今日訊號多空共識，不再把持有 ETF 總數誤當買賣檔數。')
print('   已備份：', bak_api)
print('   已備份：', bak_comp)
print('   已新增：', readme)
