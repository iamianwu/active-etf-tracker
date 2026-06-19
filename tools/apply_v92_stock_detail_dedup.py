#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
COMP = FRONTEND / "components"
APP = FRONTEND / "app"

if not FRONTEND.exists():
    raise SystemExit("❌ 找不到 frontend 目錄，請在 repo 根目錄執行。")
target = COMP / "StockDetailClient.tsx"
if not target.exists():
    raise SystemExit("❌ 找不到 frontend/components/StockDetailClient.tsx")

def backup(path: Path, tag="v92"):
    bak = path.with_suffix(path.suffix + f".bak_{tag}")
    if not bak.exists():
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

backup(target)
s = target.read_text(encoding="utf-8")

# 1) 總覽頁不要再放完整「持有 ETF 明細」表，改成前五大摘要卡
old1 = """        <h2>持有 ETF 明細</h2>
        <EtfHoldingList rows={sortedEtfRows.slice(0, 8)} />"""
new1 = """        <h2>前五大持有 ETF</h2>
        <TopEtfPreview
          rows={[...etfRows].sort((a: any, b: any) => (Number.isFinite(b.value) ? b.value : 0) - (Number.isFinite(a.value) ? a.value : 0)).slice(0, 5)}
          totalValue={totalValue}
          onMore={() => setTab('detail')}
        />"""
if old1 in s:
    s = s.replace(old1, new1)
else:
    # fallback：移除總覽中的 EtfHoldingList rows={sortedEtfRows.slice(...)}
    s = re.sub(
        r"\s*<h2>持有 ETF 明細</h2>\s*<EtfHoldingList rows=\{sortedEtfRows\.slice\(0,\s*8\)\} />",
        "\n        <h2>前五大持有 ETF</h2>\n        <TopEtfPreview rows={[...etfRows].sort((a: any, b: any) => (Number.isFinite(b.value) ? b.value : 0) - (Number.isFinite(a.value) ? a.value : 0)).slice(0, 5)} totalValue={totalValue} onMore={() => setTab('detail')} />",
        s,
        flags=re.S
    )

# 2) 插入 TopEtfPreview function，避免重複插入
if "function TopEtfPreview" not in s:
    marker = "\nfunction EtfHoldingList({ rows }: { rows: any[] }) {"
    insert = r"""
function TopEtfPreview({ rows, totalValue, onMore }: { rows: any[]; totalValue: number; onMore: () => void }) {
  if (!rows?.length) return <div className="v89-empty-box">目前沒有 ETF 持股資料</div>;
  const maxValue = Math.max(...rows.map((r) => Number.isFinite(r.value) ? r.value : 0), 1);

  return (
    <section className="v92-top-etf-preview">
      <div className="v92-preview-note">依目前持股市值排序。完整清單與近 5 / 20 / 60 日排序請到「持股明細」。</div>
      {rows.map((r) => {
        const pct = totalValue > 0 && Number.isFinite(r.value) ? (r.value / totalValue) * 100 : NaN;
        const width = Math.max(8, Math.min(100, ((Number.isFinite(r.value) ? r.value : 0) / maxValue) * 100));
        return (
          <Link key={r.code} href={`/etf/${r.code}?from=stock`} className="v92-top-etf-row">
            <div className="v92-top-etf-main">
              <b>{r.code}</b>
              <span>{r.name}</span>
            </div>
            <div className="v92-top-etf-value">
              <b>{fmtFree(r.value, 2)} 億</b>
              <span>{fmtFree(r.lots, 0)} 張{Number.isFinite(pct) ? `｜占 ${fmtFree(pct, 1)}%` : ''}</span>
            </div>
            <div className="v92-top-etf-bar"><i style={{ width: `${width}%` }} /></div>
          </Link>
        );
      })}
      <button className="v92-more-btn" onClick={onMore}>查看完整持股明細與排序 ›</button>
    </section>
  );
}
"""
    if marker in s:
        s = s.replace(marker, "\n" + insert + marker)
    else:
        raise SystemExit("❌ 找不到 EtfHoldingList function 插入位置，請貼 StockDetailClient.tsx 相關段落給我。")

target.write_text(s, encoding="utf-8")
print("✅ 已修正 StockDetailClient：總覽頁不再重複顯示完整持股明細，改成前五大摘要。")

# 3) CSS
css_path = APP / "globals.css"
if css_path.exists():
    backup(css_path)
    old_css = css_path.read_text(encoding="utf-8")
    css = r"""
/* ===== V92 stock detail de-duplicate overview ===== */
.v92-top-etf-preview {
  border: 1px solid #e3eaf3;
  border-radius: 18px;
  background: #fff;
  padding: 12px;
  margin: 8px 0 22px;
}
.v92-preview-note {
  color: #7b8797;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.35;
  margin: 2px 2px 10px;
}
.v92-top-etf-row {
  display: block;
  text-decoration: none;
  color: inherit;
  padding: 10px 2px 12px;
  border-top: 1px solid #edf2f7;
}
.v92-top-etf-row:first-of-type {
  border-top: 0;
}
.v92-top-etf-main {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}
.v92-top-etf-main b {
  font-size: 18px;
  font-weight: 950;
  color: #121826;
}
.v92-top-etf-main span {
  color: #7b8797;
  font-size: 14px;
  font-weight: 850;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.v92-top-etf-value {
  margin-top: 6px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: baseline;
}
.v92-top-etf-value b {
  font-size: 17px;
  font-weight: 950;
  color: #121826;
}
.v92-top-etf-value span {
  font-size: 13px;
  font-weight: 800;
  color: #7b8797;
  white-space: nowrap;
}
.v92-top-etf-bar {
  height: 8px;
  background: #edf3fb;
  border-radius: 999px;
  margin-top: 8px;
  overflow: hidden;
}
.v92-top-etf-bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: #2d73d5;
}
.v92-more-btn {
  width: 100%;
  border: 0;
  background: #eef6ff;
  color: #2d73d5;
  border-radius: 14px;
  font-size: 16px;
  font-weight: 950;
  padding: 12px 10px;
  margin-top: 12px;
}
"""
    if "V92 stock detail de-duplicate overview" not in old_css:
        css_path.write_text(old_css + "\n\n" + css, encoding="utf-8")
        print("✅ 已加入 V92 CSS")
    else:
        print("ℹ️ V92 CSS 已存在")

readme = ROOT / "README_V92_STOCK_DETAIL_DEDUP.md"
readme.write_text("""# V92 Stock Detail De-duplicate

修正原因：
- 原本「總覽」底部顯示一份持有 ETF 明細。
- 「持股明細」分頁也顯示一份完整持有 ETF 明細。
- 兩邊排序依據不同，看起來像相同資訊卻數字或順序不一致。

修正內容：
1. 總覽頁只保留「前五大持有 ETF」摘要。
2. 完整持股列表只放在「持股明細」分頁。
3. 排序功能保留在「持股明細」分頁。
4. 前五大摘要與完整明細共用同一份 etfRows 資料來源。
""", encoding="utf-8")
print("✅ wrote README_V92_STOCK_DETAIL_DEDUP.md")

print("\n下一步：")
print("cd frontend")
print("[ -d node_modules ] || npm install")
print("npm run build")
