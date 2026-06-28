import { REFERENCE_ETFS } from '@/lib/referenceEtfs';

export default function ReferenceEtfsPage() {
  return (
    <main className="ref-etf-page">
      <div className="ref-etf-head">
        <div>
          <a className="ref-etf-back" href="/admin">← 管理</a>
          <h1>一般 ETF 參考清單</h1>
          <p>
            這些 ETF 只作為大盤、高股息、科技等背景參考，不納入主動式 ETF 今日訊號計算。
          </p>
        </div>
        <a className="ref-etf-api" href="/api/reference-etfs">查看 API</a>
      </div>

      <section className="ref-etf-summary">
        <div>
          <span>參考 ETF</span>
          <b>{REFERENCE_ETFS.length}</b>
        </div>
        <div>
          <span>今日訊號</span>
          <b>不納入</b>
        </div>
        <div>
          <span>用途</span>
          <b>對照組</b>
        </div>
      </section>

      <section className="ref-etf-section">
        <div className="ref-etf-table-wrap">
          <table className="ref-etf-table">
            <thead>
              <tr>
                <th>代號</th>
                <th>名稱</th>
                <th>市場</th>
                <th>參考用途</th>
                <th>今日訊號</th>
              </tr>
            </thead>
            <tbody>
              {REFERENCE_ETFS.map((etf) => (
                <tr key={etf.code}>
                  <td>{etf.code}</td>
                  <td>{etf.name}</td>
                  <td>{etf.market}</td>
                  <td>{etf.role}</td>
                  <td>
                    <span className="ref-etf-pill">不納入</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="ref-etf-note">
        下一階段可以把這些 ETF 接上持股資料，放到個股頁作為「一般 ETF 參考持股」。
      </div>
    </main>
  );
}
