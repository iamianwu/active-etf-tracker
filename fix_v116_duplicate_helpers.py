from pathlib import Path
import re

path = Path("frontend/components/SignalsClient.tsx")
s = path.read_text()

names = ["missingEtfsOf", "etfCodeOf", "etfNameOf", "etfLatestDateOf"]

def remove_function(src, name):
    pattern = re.compile(r"\nfunction\s+" + re.escape(name) + r"\s*\(")
    while True:
        m = pattern.search(src)
        if not m:
            return src

        start = m.start()
        brace = src.find("{", m.end())
        if brace == -1:
            raise RuntimeError(f"Cannot find body for {name}")

        depth = 0
        i = brace
        in_str = None
        esc = False
        in_line_comment = False
        in_block_comment = False

        while i < len(src):
            ch = src[i]
            nxt = src[i + 1] if i + 1 < len(src) else ""

            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
            elif in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    i += 1
            elif in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == in_str:
                    in_str = None
            else:
                if ch == "/" and nxt == "/":
                    in_line_comment = True
                    i += 1
                elif ch == "/" and nxt == "*":
                    in_block_comment = True
                    i += 1
                elif ch in ("'", '"', "`"):
                    in_str = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        while end < len(src) and src[end] in " \t\r\n":
                            end += 1
                        src = src[:start] + "\n" + src[end:]
                        break
            i += 1
        else:
            raise RuntimeError(f"Cannot parse function {name}")

for n in names:
    s = remove_function(s, n)

block = r'''
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
    data?.stale_etfs,
    data?.staleEtfs,
    data?.etf_status,
    data?.etfStatus,
  ];

  for (const c of candidates) {
    if (Array.isArray(c)) {
      return c.map((x: any) => {
        if (typeof x === 'string') return { etf_code: x };
        return x || {};
      });
    }

    if (c && typeof c === 'object') {
      return Object.values(c).map((x: any) => {
        if (typeof x === 'string') return { etf_code: x };
        return x || {};
      });
    }
  }

  return [];
}

function etfCodeOf(row: AnyRow): string {
  if (typeof row === 'string') return row.trim();
  return String(row?.etf_code ?? row?.etfCode ?? row?.code ?? row?.id ?? '').trim();
}

function etfNameOf(row: AnyRow): string {
  if (typeof row === 'string') return '';
  return String(row?.etf_name ?? row?.etfName ?? row?.name ?? row?.title ?? '').trim();
}

function etfLatestDateOf(row: AnyRow): string {
  if (typeof row === 'string') return '尚無日期';
  return mmdd(row?.latest_date ?? row?.latestDate ?? row?.data_date ?? row?.string') return '尚無日期';
  return mmdd(row?.latest_date ?? row?.latestDate ?? row?.data_date ?? row?.dataDate ?? row?.date ?? '') || '尚無日期';
}
'''.strip() + "\n\n"

anchor = "function RangePicker("
idx = s.find(anchor)

if idx == -1:
    raise SystemExit("❌ 找不到 function RangePicker，請貼 SignalsClient.tsx 前 320 行")

s = s[:idx] + block + s[idx:]
s = re.sub(r"\n{4,}", "\n\n\n", s)
path.write_text(s)

print("✅ 已移除重複 helper，並保留單一 missing ETF helper block")

for n in names:
    cnt = len(re.findall(r"function\s+" + re.escape(n) + r"\s*\(", s))
    print(f"{n}: {cnt}")
    if cnt != 1:
        raise SystemExit(f"❌ {n} 還不是 1 個")
