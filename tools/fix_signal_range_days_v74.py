#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
api_path = ROOT / "frontend/lib/api.ts"
signals_page = ROOT / "frontend/app/signals/page.tsx"
signals_type_page = ROOT / "frontend/app/signals/[type]/page.tsx"

if not api_path.exists():
    raise SystemExit("找不到 frontend/lib/api.ts，請確認在 repo 根目錄執行。")

changed = []

def has_signal_def(text: str) -> bool:
    return bool(re.search(r"\b(const|let|var)\s+signalRangeDays\b", text))

def add_local_signal_range_days_to_api(text: str) -> str:
    if "signalRangeDays" not in text:
        return text

    if has_signal_def(text):
        return text

    helper = '''
  const signalRangeDays = (() => {
    try {
      const query = String(path || '').includes('?') ? String(path || '').split('?')[1] : '';
      const params = new URLSearchParams(query);
      const raw =
        params.get('days') ||
        params.get('rangeDays') ||
        params.get('signalRangeDays') ||
        '1';
      const n = Number(raw);
      return Number.isFinite(n) && n > 0 ? n : 1;
    } catch {
      return 1;
    }
  })();

'''

    patterns = [
        r"(export\s+async\s+function\s+apiGet\s*\([^)]*\)\s*\{)",
        r"(async\s+function\s+apiGet\s*\([^)]*\)\s*\{)",
        r"(export\s+const\s+apiGet\s*=\s*async\s*\([^)]*\)\s*=>\s*\{)",
        r"(const\s+apiGet\s*=\s*async\s*\([^)]*\)\s*=>\s*\{)",
    ]

    for pat in patterns:
        if re.search(pat, text):
            return re.sub(pat, r"\1" + helper, text, count=1)

    return "const signalRangeDays = 1;\n" + text


def add_module_level_default_if_needed(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    original = text

    if "signalRangeDays" in text and not has_signal_def(text):
        insert = "const signalRangeDays = 1;\n\n"
        imports = list(re.finditer(r"^import .+?;\s*$", text, flags=re.M))
        if imports:
            pos = imports[-1].end()
            text = text[:pos] + "\n" + insert + text[pos:]
        else:
            text = insert + text

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


api_text = api_path.read_text(encoding="utf-8")
new_api_text = add_local_signal_range_days_to_api(api_text)
if new_api_text != api_text:
    api_path.write_text(new_api_text, encoding="utf-8")
    changed.append(str(api_path.relative_to(ROOT)))

for p in [signals_page, signals_type_page]:
    if add_module_level_default_if_needed(p):
        changed.append(str(p.relative_to(ROOT)))

print("✅ v74 已修正 signalRangeDays undefined 風險。")
if changed:
    print("已修改：")
    for c in changed:
        print(" -", c)
else:
    print("沒有檔案需要修改，可能已經修過。")

print("\n目前 signalRangeDays 出現位置：")
found = False
for p in [api_path, signals_page, signals_type_page]:
    if not p.exists():
        continue
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if "signalRangeDays" in line:
            found = True
            print(f"{p.relative_to(ROOT)}:{i}: {line.strip()}")
if not found:
    print(" - 沒有找到 signalRangeDays")

print("\n接著請 npm run build，然後 commit / push。")
