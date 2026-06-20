from pathlib import Path
import re

path = Path("frontend/components/SignalsClient.tsx")
s = path.read_text()

new_func = """function etfLatestDateOf(row: AnyRow): string {
  if (typeof row === 'string') return '尚無日期';
  const raw = row?.latest_date ?? row?.latestDate ?? row?.data_date ?? row?.dataDate ?? row?.date ?? '';
  const d = mmdd(raw);
  return d && d !== '-' ? d : '尚無日期';
}
"""

pattern = re.compile(r"function\s+etfLatestDateOf\s*\([^)]*\)\s*:\s*string\s*\{[\s\S]*?\n\}", re.M)

matches = list(pattern.finditer(s))
if not matches:
    raise SystemExit("❌ 找不到 etfLatestDateOf function，請貼 SignalsClient.tsx 220-250 行")

# 保留第一個，其他如果還有殘留重複，也一起移除
first = matches[0]
s = s[:first.start()] + new_func + s[first.end():]

# 再刪掉後面可能殘留的重複 etfLatestDateOf
s = re.sub(r"\nfunction\s+etfLatestDateOf\s*\([^)]*\)\s*:\s*string\s*\{[\s\S]*?\n\}", "\n", s)

path.write_text(s)

print("✅ 已修正 etfLatestDateOf 語法錯誤")
print("etfLatestDateOf count =", len(re.findall(r"function\s+etfLatestDateOf\s*\(", s)))
