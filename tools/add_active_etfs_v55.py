from __future__ import annotations

import re
from pathlib import Path

NEW_ETF_NAMES = {
    "00402A": "主動安聯美國科技",
    "00404A": "主動聯博動能50",
    "00405A": "主動富邦台灣龍耀",
    "00406A": "主動中信台灣收益",
    "00998A": "主動復華金融股息",
    "00980D": "主動聯博投等入息",
    "00981D": "主動中信非投等債",
    "00982D": "主動富邦動態入息",
    "00983D": "主動富邦複合收益",
    "00984D": "主動聯博全球非投",
    "00985D": "主動貝萊德優投等",
    "00986D": "主動復華金融債息",
}

# Keep A-class ETF navigation together, then D-class income/bond ETFs.
PREFERRED_ORDER = [
    "00400A", "00401A", "00402A", "00403A", "00404A", "00405A", "00406A",
    "00980A", "00981A", "00982A", "00983A", "00984A", "00985A", "00986A",
    "00987A", "00988A", "00989A", "00990A", "00991A", "00992A", "00993A",
    "00994A", "00995A", "00996A", "00997A", "00998A", "00999A",
    "00980D", "00981D", "00982D", "00983D", "00984D", "00985D", "00986D",
]


def unique_keep_order(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        s = str(item).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def ordered_codes(existing: list[str]) -> list[str]:
    merged = unique_keep_order(existing + list(NEW_ETF_NAMES.keys()))
    preferred = [c for c in PREFERRED_ORDER if c in merged]
    rest = [c for c in merged if c not in preferred]
    return preferred + rest


def format_code_list(codes: list[str]) -> str:
    lines = ["ETF_CODES = ["]
    for i in range(0, len(codes), 7):
        chunk = codes[i:i + 7]
        lines.append("    " + ", ".join(f'\"{c}\"' for c in chunk) + ",")
    lines.append("]")
    return "\n".join(lines)


def format_nav_list(codes: list[str]) -> str:
    lines = ["const ETF_NAV_CODES = ["]
    for i in range(0, len(codes), 7):
        chunk = codes[i:i + 7]
        lines.append("  " + ", ".join(f"'{c}'" for c in chunk) + ",")
    lines.append("];" )
    return "\n".join(lines)


def patch_config(repo: Path) -> list[str]:
    path = repo / "backend" / "app" / "config.py"
    if not path.exists():
        raise FileNotFoundError(f"找不到 {path}")
    text = path.read_text(encoding="utf-8")
    msgs: list[str] = []

    m = re.search(r"ETF_CODES\s*=\s*\[(.*?)\]", text, flags=re.S)
    if not m:
        raise RuntimeError("backend/app/config.py 找不到 ETF_CODES = [...]")
    existing = re.findall(r"['\"]([0-9]{5}[A-Z])['\"]", m.group(1))
    codes = ordered_codes(existing)
    text = text[:m.start()] + format_code_list(codes) + text[m.end():]
    msgs.append(f"ETF_CODES: {len(existing)} -> {len(codes)}")

    m = re.search(r"ETF_NAMES\s*=\s*\{(.*?)\}\s*", text, flags=re.S)
    if not m:
        raise RuntimeError("backend/app/config.py 找不到 ETF_NAMES = {...}")

    body = m.group(1)
    for code, name in NEW_ETF_NAMES.items():
        # Replace old entry if exists, otherwise append.
        pattern = rf"([ \t]*['\"]{re.escape(code)}['\"]\s*:\s*)['\"][^'\"]*['\"]\s*,?"
        repl = rf"\1\"{name}\","
        if re.search(pattern, body):
            body = re.sub(pattern, repl, body)
        else:
            if not body.endswith("\n"):
                body += "\n"
            body += f'    "{code}": "{name}",\n'

    # Reorder ETF_NAMES entries roughly by PREFERRED_ORDER while preserving any unknown names.
    entries = re.findall(r"['\"]([0-9]{5}[A-Z])['\"]\s*:\s*['\"]([^'\"]*)['\"]\s*,?", body)
    name_map = {code: name for code, name in entries}
    for code, name in NEW_ETF_NAMES.items():
        name_map[code] = name
    ordered = [c for c in PREFERRED_ORDER if c in name_map] + [c for c in name_map if c not in PREFERRED_ORDER]
    new_body = "\n".join(f'    "{c}": "{name_map[c]}",' for c in ordered) + "\n"
    text = text[:m.start()] + "ETF_NAMES = {\n" + new_body + "}\n" + text[m.end():]

    path.write_text(text, encoding="utf-8")
    msgs.append("ETF_NAMES 已新增/更新 12 檔")
    return msgs


def patch_frontend_nav(repo: Path, codes: list[str]) -> list[str]:
    msgs: list[str] = []
    candidates = list((repo / "frontend").glob("**/*.tsx")) + list((repo / "frontend").glob("**/*.ts"))
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        if "ETF_NAV_CODES" not in text:
            continue
        new_text = re.sub(
            r"const\s+ETF_NAV_CODES\s*=\s*\[(.*?)\]\s*;",
            format_nav_list(codes),
            text,
            flags=re.S,
        )
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            msgs.append(f"更新 ETF_NAV_CODES: {path.relative_to(repo)}")
    if not msgs:
        msgs.append("未找到 frontend ETF_NAV_CODES，略過前端切換順序更新")
    return msgs


def main() -> None:
    repo = Path.cwd()
    if not (repo / "backend" / "app" / "config.py").exists():
        raise SystemExit("請在 repo 根目錄執行，例如 active-etf-tracker-fix 資料夾內。")

    config_msgs = patch_config(repo)

    # Re-read final codes from config for frontend nav.
    config_text = (repo / "backend" / "app" / "config.py").read_text(encoding="utf-8")
    m = re.search(r"ETF_CODES\s*=\s*\[(.*?)\]", config_text, flags=re.S)
    final_codes = re.findall(r"['\"]([0-9]{5}[A-Z])['\"]", m.group(1)) if m else PREFERRED_ORDER
    nav_msgs = patch_frontend_nav(repo, final_codes)

    print("✅ ETF 清單更新完成")
    for msg in config_msgs + nav_msgs:
        print("- " + msg)
    print("\n新增 ETF：")
    for code, name in NEW_ETF_NAMES.items():
        print(f"  {code} {name}")


if __name__ == "__main__":
    main()
