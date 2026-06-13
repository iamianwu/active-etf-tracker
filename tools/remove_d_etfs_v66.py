#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

D_ETF_CODES = [
    "00980D",
    "00981D",
    "00982D",
    "00983D",
    "00984D",
    "00985D",
    "00986D",
]

D_SET = set(D_ETF_CODES)


def unique_keep_order(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        item = str(item).strip().upper()
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def format_py_list(name: str, codes: list[str]) -> str:
    lines = [f"{name} = ["]
    for i in range(0, len(codes), 7):
        chunk = codes[i:i + 7]
        lines.append("    " + ", ".join(f'"{c}"' for c in chunk) + ",")
    lines.append("]")
    return "\n".join(lines)


def format_ts_list(name: str, codes: list[str]) -> str:
    lines = [f"const {name} = ["]
    for i in range(0, len(codes), 7):
        chunk = codes[i:i + 7]
        lines.append("  " + ", ".join(f"'{c}'" for c in chunk) + ",")
    lines.append("];")
    return "\n".join(lines)


def patch_backend_config(repo: Path) -> list[str]:
    path = repo / "backend/app/config.py"
    if not path.exists():
        raise FileNotFoundError("找不到 backend/app/config.py")

    text = path.read_text(encoding="utf-8")
    msgs: list[str] = []

    # Remove D ETF codes from ETF_CODES.
    m = re.search(r"ETF_CODES\s*=\s*\[(.*?)\]", text, flags=re.S)
    if m:
        existing = re.findall(r"['\"]([0-9]{5}[A-Z])['\"]", m.group(1))
        filtered = [c for c in unique_keep_order(existing) if c not in D_SET]
        text = text[:m.start()] + format_py_list("ETF_CODES", filtered) + text[m.end():]
        msgs.append(f"ETF_CODES: {len(existing)} -> {len(filtered)}，已移除 D 類 ETF")
    else:
        msgs.append("警告：找不到 ETF_CODES，略過")

    # Remove D ETF names from ETF_NAMES dict by deleting any line containing the code.
    for code in D_ETF_CODES:
        text = re.sub(rf"^[ \t]*['\"]{code}['\"]\s*:\s*['\"][^'\"]*['\"]\s*,?\s*\n", "", text, flags=re.M)

    path.write_text(text, encoding="utf-8")
    msgs.append("ETF_NAMES：已移除 D 類 ETF 名稱")
    return msgs


def patch_frontend_nav_and_static_codes(repo: Path) -> list[str]:
    msgs: list[str] = []
    frontend = repo / "frontend"
    if not frontend.exists():
        return ["找不到 frontend，略過前端"]

    targets = list(frontend.glob("**/*.tsx")) + list(frontend.glob("**/*.ts")) + list(frontend.glob("**/*.jsx")) + list(frontend.glob("**/*.js"))

    for path in targets:
        text = path.read_text(encoding="utf-8")
        original = text

        # If this file defines ETF_NAV_CODES, remove D codes from that array only.
        def replace_nav(match: re.Match) -> str:
            body = match.group(1)
            codes = re.findall(r"['\"]([0-9]{5}[A-Z])['\"]", body)
            filtered = [c for c in unique_keep_order(codes) if c not in D_SET]
            return format_ts_list("ETF_NAV_CODES", filtered)

        text = re.sub(
            r"const\s+ETF_NAV_CODES\s*=\s*\[(.*?)\]\s*;",
            replace_nav,
            text,
            flags=re.S,
        )

        # Remove individual hard-coded D ETF list entries or hot-search items.
        for code in D_ETF_CODES:
            # Remove object/list lines containing the code.
            text = re.sub(rf"^[^\n]*['\"]{code}['\"][^\n]*\n", "", text, flags=re.M)
            # Remove simple string in comma list if still present.
            text = re.sub(rf"\s*['\"]{code}['\"]\s*,?", "", text)

        if text != original:
            path.write_text(text, encoding="utf-8")
            msgs.append(f"前端已移除 D 類 ETF：{path.relative_to(repo)}")

    if not msgs:
        msgs.append("前端沒有找到 D 類 ETF 硬編碼，略過")
    return msgs


def patch_workflow_defaults(repo: Path) -> list[str]:
    msgs: list[str] = []
    workflows = repo / ".github/workflows"
    if not workflows.exists():
        return msgs

    for path in workflows.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        original = text

        # Remove D ETF default values from v64/v65 skip lists, because D codes should no longer be in ETF_CODES.
        # Keep this simple: delete explicit D code strings from workflow defaults.
        for code in D_ETF_CODES:
            text = text.replace(code + ",", "")
            text = text.replace("," + code, "")
            text = text.replace(code, "")

        # Clean accidental double commas.
        text = re.sub(r",\s*,+", ",", text)
        text = re.sub(r"default:\s*['\"]\s*['\"]", 'default: ""', text)

        if text != original:
            path.write_text(text, encoding="utf-8")
            msgs.append(f"workflow 已清掉 D 類 ETF 文字：{path.relative_to(repo)}")

    return msgs


def main() -> None:
    repo = Path.cwd()
    if not (repo / "backend/app/config.py").exists():
        raise SystemExit("請在 repo 根目錄執行，例如 active-etf-tracker-fix 資料夾內。")

    all_msgs: list[str] = []
    all_msgs += patch_backend_config(repo)
    all_msgs += patch_frontend_nav_and_static_codes(repo)
    all_msgs += patch_workflow_defaults(repo)

    print("✅ v66：D 類 ETF 已從網站清單移除")
    print("移除代號：", ", ".join(D_ETF_CODES))
    for msg in all_msgs:
        print("- " + msg)

    print("\n下一步：")
    print("1. commit / push")
    print("2. 到 Supabase 跑 README 裡的 SQL，刪除已經寫入資料庫的 D 類 ETF 資料")
    print("3. 之後 Update ETF Data / Backfill ETF History Batches 就不會再跑 D 類 ETF")


if __name__ == "__main__":
    main()
