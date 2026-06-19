#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
COMP = FRONTEND / "components"
APP = FRONTEND / "app"

target = COMP / "EtfDetailClient.tsx"
if not FRONTEND.exists():
    raise SystemExit("❌ 找不到 frontend 目錄，請在 repo 根目錄執行。")
if not target.exists():
    raise SystemExit("❌ 找不到 frontend/components/EtfDetailClient.tsx")

def backup(path: Path, tag="v93"):
    bak = path.with_suffix(path.suffix + f".bak_{tag}")
    if not bak.exists():
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

backup(target)
s = target.read_text(encoding="utf-8")

helper = r"""
function opDeltaLots(r: any): number {
  const directLots = num(r?.delta_lots ?? r?.change_lots ?? r?.deltaLots ?? r?.changeLots);
  if (Number.isFinite(directLots)) {
    // 有些舊資料欄位名稱雖叫 lots，但實際塞的是股數；數字太大時自動換成張
    return Math.abs(directLots) >= 100000 ? directLots / 1000 : directLots;
  }

  const shares = num(
    r?.shares_change ??
    r?.delta_shares ??
    r?.sharesChange ??
    r?.deltaShares ??
    r?.change_shares ??
    r?.changeShares
  );
  if (Number.isFinite(shares)) return shares / 1000;

  return NaN;
}

function opAmountBillion(r: any, lots: number): number {
  const direct = num(
    r?.amount_billion ??
    r?.flow_billion ??
    r?.money_billion ??
    r?.delta_amount_billion ??
    r?.net_amount_billion ??
    r?.value_change_billion ??
    r?.market_value_change_billion
  );
  if (Number.isFinite(direct)) return direct;

  const raw = num(
    r?.amount ??
    r?.flow_amount ??
    r?.delta_amount ??
    r?.net_amount ??
    r?.value_change ??
    r?.market_value_change
  );
  if (Number.isFinite(raw)) return raw / 100000000;

  const px = priceOf(r);
  if (Number.isFinite(lots) && Number.isFinite(px)) return lots * 1000 * px / 100000000;

  return NaN;
}

function OperationRows({ changes }: { changes: any[] }) {
  if (!Array.isArray(changes) || changes.length === 0) {
    return <div className="v89-empty-box">目前沒有操作日報資料</div>;
  }

  return (
    <div className="v93-op-list">
      {changes.map((r: any, i: number) => {
        const s = statusOf(r);
        const code = stockCode(r);
        const lots = opDeltaLots(r);
        const amount = opAmountBillion(r, lots);
        const weight = weightOf(r);
        const positive = Number.isFinite(lots) ? lots >= 0 : s === '新增' || s === '加碼';

        return (
          <Link href={`/stock/${code}?from=etf`} key={`${code}-${i}`} className="v93-op-row">
            <div className="v93-op-main">
              <div className="v93-op-name">
                <b>{stockName(r)}</b>
                <span>{code}</span>
              </div>
              <div className={`v89-pill ${s}`}>{s}</div>
            </div>

            <div className="v93-op-metrics">
              <div>
                <span>持股變動</span>
                <b className={positive ? 'v89-red' : 'v89-green'}>
                  {Number.isFinite(lots) ? fmtSigned(lots, 0, ' 張') : '-'}
                </b>
              </div>
              <div>
                <span>估算金額</span>
                <b className={Number.isFinite(amount) ? (amount >= 0 ? 'v89-red' : 'v89-green') : ''}>
                  {Number.isFinite(amount) ? fmtSigned(amount, 2, ' 億') : '-'}
                </b>
              </div>
              <div>
                <span>目前權重</span>
                <b>{Number.isFinite(weight) ? `${fmtFree(weight, 2)}%` : '-'}</b>
              </div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
"""

if "function opDeltaLots" not in s:
    marker = "export default function EtfDetailClient"
    if marker not in s:
        raise SystemExit("❌ 找不到 export default function EtfDetailClient，請貼 EtfDetailClient.tsx 給我。")
    s = s.replace(marker, helper + "\n" + marker, 1)
    print("✅ 已加入操作日報 helper functions")
else:
    print("ℹ️ 操作日報 helper functions 已存在")

new_block = """{tab === 'operation' && <section className="v89-section"><h1>操作日報</h1><OperationRows changes={Array.isArray(changes) ? changes : []} /></section>}"""

# 優先替換 v89 單行舊區塊
old_exact = """{tab === 'operation' && <section className="v89-section"><h1>操作日報</h1><div className="v89-dense-list">{(Array.isArray(changes) ? changes : []).map((r: any, i: number) => { const s=statusOf(r); const delta=num(r?.delta_lots ?? r?.change_lots ?? r?.shares_change ?? r?.delta_shares); return <Link href={`/stock/${stockCode(r)}?from=etf`} key={`${stockCode(r)}-${i}`} className="v89-signal-row"><div className="v89-name-cell"><b>{stockName(r)}</b><span>{stockCode(r)}</span></div><div className={`v89-pill ${s}`}>{s}</div><div className={delta>=0?'v89-red':'v89-green'}>{Number.isFinite(delta)?fmtSigned(delta,0,' 張'):'-'}</div><div>{fmtFree(weightOf(r),2)}%</div></Link>; })}</div></section>}"""

if old_exact in s:
    s = s.replace(old_exact, new_block, 1)
    print("✅ 已替換舊的操作日報單行區塊")
elif "<OperationRows changes=" in s:
    print("ℹ️ 操作日報區塊已經使用 OperationRows")
else:
    # fallback：抓 tab === 'operation' 的 section，直到下一個 {tab ===
    pat = r"\{tab === 'operation' && <section className=\"v89-section\">.*?</section>\}\s*(?=\{tab === '|</main>)"
    s2, n = re.subn(pat, new_block + "\n      ", s, count=1, flags=re.S)
    if n == 0:
        raise SystemExit("❌ 找不到可替換的操作日報區塊。請貼 frontend/components/EtfDetailClient.tsx 中 tab === 'operation' 那段給我。")
    s = s2
    print("✅ 已用 fallback 替換操作日報區塊")

target.write_text(s, encoding="utf-8")
print("✅ EtfDetailClient.tsx 已完成 v93 操作日報修正")

css_path = APP / "globals.css"
if css_path.exists():
    backup(css_path)
    css_old = css_path.read_text(encoding="utf-8")
    css = r"""
/* ===== V93 ETF operation report mobile layout ===== */
.v93-op-list {
  display: grid;
  gap: 12px;
  margin-top: 12px;
}
.v93-op-row {
  display: block;
  text-decoration: none;
  color: inherit;
  border: 1px solid #e3eaf3;
  border-radius: 16px;
  background: #fff;
  padding: 14px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, .03);
}
.v93-op-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
}
.v93-op-name {
  min-width: 0;
}
.v93-op-name b {
  display: block;
  font-size: 20px;
  line-height: 1.15;
  font-weight: 950;
  color: #121826;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.v93-op-name span {
  display: block;
  margin-top: 3px;
  color: #8994a6;
  font-size: 14px;
  font-weight: 850;
}
.v93-op-metrics {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #edf2f7;
}
.v93-op-metrics span {
  display: block;
  color: #7b8797;
  font-size: 12px;
  font-weight: 900;
  line-height: 1.2;
}
.v93-op-metrics b {
  display: block;
  margin-top: 5px;
  color: #121826;
  font-size: 16px;
  line-height: 1.15;
  font-weight: 950;
  word-break: keep-all;
}
@media(max-width:390px){
  .v93-op-row { padding: 12px; }
  .v93-op-metrics {
    grid-template-columns: 1fr;
    gap: 10px;
  }
  .v93-op-metrics div {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    align-items: baseline;
  }
  .v93-op-metrics b {
    text-align: right;
    margin-top: 0;
    font-size: 16px;
  }
}
"""
    if "V93 ETF operation report mobile layout" not in css_old:
        css_path.write_text(css_old + "\n\n" + css, encoding="utf-8")
        print("✅ 已加入 V93 CSS")
    else:
        print("ℹ️ V93 CSS 已存在")

readme = ROOT / "README_V93_OPERATION_REPORT_FIX.md"
readme.write_text("""# V93 Operation Report Fix

修正 ETF 詳情頁 > 操作日報：

1. 不再用擠在一起的 4 欄列表。
2. 改成手機卡片式：
   - 股票名稱 / 代號
   - 狀態
   - 持股變動
   - 估算金額
   - 目前權重
3. 修正股數被誤顯示成張數：
   - 600,000 股會顯示成 600 張
   - 2,839,000 股會顯示成 2,839 張
4. 若後端沒有直接提供金額，會用：變動張數 × 1000 × 股價 / 1億 估算。
""", encoding="utf-8")
print("✅ wrote README_V93_OPERATION_REPORT_FIX.md")

print("\n下一步：")
print("cd frontend")
print("[ -d node_modules ] || npm install")
print("npm run build")
