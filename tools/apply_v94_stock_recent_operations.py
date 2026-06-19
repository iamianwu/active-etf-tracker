#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
COMP = FRONTEND / "components"
APP = FRONTEND / "app"

target = COMP / "StockDetailClient.tsx"
if not FRONTEND.exists():
    raise SystemExit("❌ 找不到 frontend 目錄，請在 repo 根目錄執行。")
if not target.exists():
    raise SystemExit("❌ 找不到 frontend/components/StockDetailClient.tsx")

def backup(path: Path, tag="v94"):
    bak = path.with_suffix(path.suffix + f".bak_{tag}")
    if not bak.exists():
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

backup(target)
s = target.read_text(encoding="utf-8")

if "<StockRecentOperationRecords" not in s:
    pat = r"(<TopEtfPreview[\s\S]*?onMore=\{\(\) => setTab\('detail'\)\}\s*/>)"
    s2, n = re.subn(pat, r"\1\n        <StockRecentOperationRecords data={data} etfRows={etfRows} />", s, count=1)
    if n == 0:
        pat2 = r"(<h2>前五大持有 ETF</h2>[\s\S]*?</TopEtfPreview>)"
        s2, n = re.subn(pat2, r"\1\n        <StockRecentOperationRecords data={data} etfRows={etfRows} />", s, count=1)
    if n == 0:
        raise SystemExit("❌ 找不到前五大持有 ETF 區塊，請貼 StockDetailClient.tsx 中 TopEtfPreview 附近內容給我。")
    s = s2
    print("✅ 已在前五大持有 ETF 下方加入近30日操作記錄")
else:
    print("ℹ️ StockRecentOperationRecords 已存在")

if "function StockRecentOperationRecords" not in s:
    marker = "\nfunction TopEtfPreview"
    if marker not in s:
        marker = "\nfunction EtfHoldingList"
    if marker not in s:
        raise SystemExit("❌ 找不到可插入 component 的位置。")

    insert = r'''
function pickObjValue(obj: any, keys: string[]): any {
  for (const k of keys) {
    if (obj && obj[k] !== undefined && obj[k] !== null && obj[k] !== '') return obj[k];
  }
  return undefined;
}

function asLotsSmart(v: any): number {
  const n = num(v);
  if (!Number.isFinite(n)) return NaN;
  return Math.abs(n) >= 100000 ? n / 1000 : n;
}

function recordDateOf(r: any): string {
  return String(pickObjValue(r, ['data_date', 'date', 'trade_date', 'updated_date', 'dt']) || '');
}

function recordEtfCodeOf(r: any): string {
  return String(pickObjValue(r, ['etf_code', 'etfCode', 'code', 'fund_code']) || '');
}

function recordEtfNameOf(r: any, etfMap: Record<string, any>): string {
  const code = recordEtfCodeOf(r);
  return String(pickObjValue(r, ['etf_name', 'etfName', 'name', 'fund_name']) || etfMap[code]?.name || etfMap[code]?.etf_name || '');
}

function recordLotsOf(r: any): number {
  return asLotsSmart(pickObjValue(r, ['shares', 'shares_lots', 'lots', 'holding_lots', 'quantity', 'qty']));
}

function buildStockOperationRecords(data: any, etfRows: any[]) {
  const raw = ([] as any[]).concat(
    Array.isArray(data?.operation_records) ? data.operation_records : [],
    Array.isArray(data?.operationRecords) ? data.operationRecords : [],
    Array.isArray(data?.recent_operations) ? data.recent_operations : [],
    Array.isArray(data?.recentOperations) ? data.recentOperations : []
  );

  const etfMap: Record<string, any> = {};
  for (const e of etfRows || []) etfMap[String(e.code || e.etf_code || '')] = e;

  if (raw.length) {
    return raw.map((r: any) => {
      const code = recordEtfCodeOf(r);
      const lots = asLotsSmart(pickObjValue(r, [
        'delta_lots', 'change_lots', 'deltaLots', 'changeLots',
        'shares_change', 'delta_shares', 'sharesChange', 'deltaShares',
        'change_shares', 'changeShares'
      ]));
      const pct = num(pickObjValue(r, ['change_pct', 'delta_pct', 'changePct', 'deltaPct', 'change_percent']));
      return {
        date: recordDateOf(r),
        code,
        name: recordEtfNameOf(r, etfMap),
        lots,
        pct,
        status: String(pickObjValue(r, ['status', 'action']) || (lots >= 0 ? '加碼' : '減碼')),
      };
    }).filter((r: any) => r.code && Number.isFinite(r.lots) && r.lots !== 0);
  }

  const hist = ([] as any[]).concat(
    Array.isArray(data?.holding_history) ? data.holding_history : [],
    Array.isArray(data?.holdingHistory) ? data.holdingHistory : [],
    Array.isArray(data?.historyRows) ? data.historyRows : [],
    Array.isArray(data?.history) ? data.history : []
  );

  const grouped: Record<string, any[]> = {};
  for (const r of hist) {
    const code = recordEtfCodeOf(r);
    const date = recordDateOf(r);
    if (!code || !date) continue;
    if (!grouped[code]) grouped[code] = [];
    grouped[code].push(r);
  }

  const out: any[] = [];
  for (const code of Object.keys(grouped)) {
    const rows = grouped[code].sort((a, b) => recordDateOf(a).localeCompare(recordDateOf(b)));
    for (let i = 1; i < rows.length; i++) {
      const prevLots = recordLotsOf(rows[i - 1]);
      const currLots = recordLotsOf(rows[i]);
      if (!Number.isFinite(prevLots) || !Number.isFinite(currLots)) continue;
      const delta = currLots - prevLots;
      if (Math.abs(delta) < 0.0001) continue;
      out.push({
        date: recordDateOf(rows[i]),
        code,
        name: recordEtfNameOf(rows[i], etfMap),
        lots: delta,
        pct: prevLots ? (delta / Math.abs(prevLots)) * 100 : NaN,
        status: delta >= 0 ? '加碼' : '減碼',
      });
    }
  }

  return out.sort((a, b) => String(b.date).localeCompare(String(a.date)) || Math.abs(b.lots) - Math.abs(a.lots));
}

function StockRecentOperationRecords({ data, etfRows }: { data: any; etfRows: any[] }) {
  const records = buildStockOperationRecords(data, etfRows).slice(0, 30);
  const [openInfo, setOpenInfo] = useState(false);

  if (!records.length) return null;

  return (
    <section className="v94-op-section">
      <div className="v94-op-title-row">
        <h2>近30日操作記錄</h2>
        <button type="button" className="v94-info-btn" onClick={() => setOpenInfo(true)}>i</button>
      </div>

      <div className="v94-op-table">
        <div className="v94-op-head">
          <span>日期</span>
          <span>ETF</span>
          <span>變動張數<br />變動幅度</span>
          <span>狀態</span>
        </div>

        {records.map((r: any, i: number) => {
          const positive = r.lots >= 0;
          const mmdd = String(r.date || '').slice(5, 10).replace('-', '/');
          const pctText = Number.isFinite(r.pct) ? `${fmtFree(r.pct, Math.abs(r.pct) >= 10 ? 1 : 2)}%` : '-';

          return (
            <Link key={`${r.date}-${r.code}-${i}`} href={`/etf/${r.code}?from=stock`} className="v94-op-tr">
              <div className="v94-date">{mmdd || '-'}</div>
              <div className="v94-etf">
                <b>{r.code}</b>
                <span>{r.name || '-'}</span>
              </div>
              <div className={`v94-change ${positive ? 'red' : 'green'}`}>
                <b>{fmtSigned(r.lots, Math.abs(r.lots) < 1 ? 1 : 0, ' 張')}</b>
                <span>{pctText}</span>
              </div>
              <div className={`v94-status ${positive ? 'red' : 'green'}`}>{r.status}</div>
            </Link>
          );
        })}
      </div>

      {openInfo && (
        <div className="v94-modal-mask" onClick={() => setOpenInfo(false)}>
          <div className="v94-modal" onClick={(e) => e.stopPropagation()}>
            <h3>變動資料說明</h3>
            <ul>
              <li><b>變動張數：</b>以 1 張為最小顯示單位，原始資料若為股數會自動換算為張數，例如 600,000 股會顯示為 600 張。</li>
              <li><b>變動幅度：</b>用於衡量加減碼強度。當變動幅度超過 100% 時，通常代表原始持股基數較小，請搭配變動張數判讀。</li>
              <li><b>判讀提醒：</b>ETF 持股變化不等於立即買賣建議，建議搭配股價、權重與連續多日趨勢一起看。</li>
            </ul>
            <button type="button" onClick={() => setOpenInfo(false)}>我知道了</button>
          </div>
        </div>
      )}
    </section>
  );
}
'''
    s = s.replace(marker, "\n" + insert + marker, 1)
    print("✅ 已加入 StockRecentOperationRecords component")
else:
    print("ℹ️ StockRecentOperationRecords component 已存在")

target.write_text(s, encoding="utf-8")
print("✅ StockDetailClient.tsx 已完成 v94")

css_path = APP / "globals.css"
if css_path.exists():
    backup(css_path)
    css_old = css_path.read_text(encoding="utf-8")
    css = r'''
/* ===== V94 stock recent operation records ===== */
.v94-op-section { margin: 20px 0 28px; }
.v94-op-title-row { display: flex; align-items: center; gap: 8px; }
.v94-op-title-row h2 { margin: 0; }
.v94-info-btn {
  width: 26px; height: 26px; border-radius: 999px; border: 2px solid #9aa5b5;
  background: #fff; color: #7b8797; font-size: 16px; font-weight: 950; line-height: 1;
}
.v94-op-table { margin-top: 12px; overflow: hidden; border: 1px solid #e6edf5; border-radius: 16px; background: #fff; }
.v94-op-head {
  display: grid; grid-template-columns: 52px minmax(0, 1fr) 112px 60px; gap: 8px;
  padding: 12px 10px; background: #f4f6f8; color: #4b5563; font-size: 14px; font-weight: 950; line-height: 1.25;
}
.v94-op-tr {
  display: grid; grid-template-columns: 52px minmax(0, 1fr) 112px 60px; gap: 8px; align-items: center;
  padding: 14px 10px; border-top: 1px solid #edf2f7; text-decoration: none; color: inherit;
}
.v94-date { font-size: 16px; font-weight: 850; color: #2b2f36; }
.v94-etf { min-width: 0; }
.v94-etf b { display: block; font-size: 19px; line-height: 1.1; font-weight: 950; color: #222831; }
.v94-etf span { display: block; margin-top: 4px; font-size: 14px; font-weight: 800; color: #666f7c; white-space: normal; line-height: 1.25; }
.v94-change { text-align: right; }
.v94-change b { display: block; font-size: 17px; line-height: 1.15; font-weight: 950; white-space: nowrap; }
.v94-change span { display: block; margin-top: 4px; font-size: 15px; font-weight: 850; color: #5d6470; }
.v94-status { font-size: 17px; font-weight: 950; text-align: right; }
.v94-change.red, .v94-status.red { color: #e15661; }
.v94-change.green, .v94-status.green { color: #2fa67c; }
.v94-modal-mask {
  position: fixed; inset: 0; z-index: 9999; background: rgba(15,23,42,.35);
  display: flex; align-items: center; justify-content: center; padding: 22px;
}
.v94-modal { width: min(520px, 100%); max-height: 82vh; overflow: auto; border-radius: 18px; background: #fff; padding: 22px; box-shadow: 0 20px 60px rgba(15,23,42,.25); }
.v94-modal h3 { text-align: center; font-size: 24px; margin: 0 0 18px; }
.v94-modal ul { padding-left: 20px; margin: 0; }
.v94-modal li { margin: 14px 0; font-size: 17px; line-height: 1.7; font-weight: 650; }
.v94-modal button { width: 100%; margin-top: 20px; border: 0; border-radius: 12px; background: #5798e8; color: white; padding: 14px 12px; font-size: 19px; font-weight: 950; }
@media(max-width:390px){
  .v94-op-head, .v94-op-tr { grid-template-columns: 46px minmax(0, 1fr) 96px 52px; gap: 6px; padding-left: 8px; padding-right: 8px; }
  .v94-etf b { font-size: 17px; }
  .v94-etf span { font-size: 13px; }
  .v94-change b, .v94-status { font-size: 15px; }
}
'''
    if "V94 stock recent operation records" not in css_old:
        css_path.write_text(css_old + "\n\n" + css, encoding="utf-8")
        print("✅ 已加入 V94 CSS")
    else:
        print("ℹ️ V94 CSS 已存在")

readme = ROOT / "README_V94_STOCK_RECENT_OPERATION_RECORDS.md"
readme.write_text("# V94 Stock Recent Operation Records\n\n在個股詳情頁「前五大持有 ETF」下方新增近30日操作記錄、變動張數、變動幅度、狀態與資料說明 popup。\n\n單位修正：原始資料若是股數，會自動換算成張數，例如 600,000 股會顯示成 600 張。\n", encoding="utf-8")
print("✅ wrote README_V94_STOCK_RECENT_OPERATION_RECORDS.md")
