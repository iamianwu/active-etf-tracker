export type ReferenceEtf = {
  code: string;
  name: string;
  market: string;
  role: string;
  include_in_today_signal: false;
};

export const REFERENCE_ETFS: ReferenceEtf[] = [
  { code: '0050', name: '元大台灣50', market: '台灣', role: '大盤權值股對照', include_in_today_signal: false },
  { code: '0051', name: '元大中型100', market: '台灣', role: '中型股對照', include_in_today_signal: false },
  { code: '0052', name: '富邦科技', market: '台灣', role: '科技族群對照', include_in_today_signal: false },
  { code: '0053', name: '元大電子', market: '台灣', role: '電子族群對照', include_in_today_signal: false },
  { code: '0055', name: '元大MSCI金融', market: '台灣', role: '金融族群對照', include_in_today_signal: false },
  { code: '0056', name: '元大高股息', market: '台灣', role: '高股息族群對照', include_in_today_signal: false },
  { code: '0057', name: '富邦摩台', market: '台灣', role: '大盤權值股對照', include_in_today_signal: false },
  { code: '006201', name: '元大富櫃50', market: '台灣', role: '上櫃權值股對照', include_in_today_signal: false },
  { code: '006203', name: '元大MSCI台灣', market: '台灣', role: '大盤權值股對照', include_in_today_signal: false },
  { code: '006204', name: '永豐臺灣加權', market: '台灣', role: '大盤權值股對照', include_in_today_signal: false },
  { code: '006208', name: '富邦台50', market: '台灣', role: '大盤權值股對照', include_in_today_signal: false },
  { code: '00690', name: '兆豐藍籌30', market: '台灣', role: '藍籌股對照', include_in_today_signal: false },
  { code: '00692', name: '富邦公司治理', market: '台灣', role: '公司治理對照', include_in_today_signal: false },
  { code: '00701', name: '國泰股利精選30', market: '台灣', role: '股利族群對照', include_in_today_signal: false },
  { code: '00713', name: '元大台灣高息低波', market: '台灣', role: '低波動高息對照', include_in_today_signal: false },
  { code: '00728', name: '第一金工業30', market: '台灣', role: '工業股對照', include_in_today_signal: false },
  { code: '00730', name: '富邦臺灣優質高息', market: '台灣', role: '高股息族群對照', include_in_today_signal: false },
  { code: '00731', name: '復華富時高息低波', market: '台灣', role: '低波動高息對照', include_in_today_signal: false },
  { code: '00733', name: '富邦臺灣中小', market: '台灣', role: '中小型股對照', include_in_today_signal: false },
  { code: '00850', name: '元大臺灣ESG永續', market: '台灣', role: 'ESG永續對照', include_in_today_signal: false },
  { code: '00878', name: '國泰永續高股息', market: '台灣', role: '高股息族群對照', include_in_today_signal: false },
  { code: '00881', name: '國泰台灣科技龍頭', market: '台灣', role: '科技族群對照', include_in_today_signal: false },
  { code: '00888', name: '永豐台灣ESG', market: '台灣', role: 'ESG永續對照', include_in_today_signal: false },
  { code: '00891', name: '中信關鍵半導體', market: '台灣', role: '半導體族群對照', include_in_today_signal: false },
  { code: '00892', name: '富邦台灣半導體', market: '台灣', role: '半導體族群對照', include_in_today_signal: false },
  { code: '00894', name: '中信小資高價30', market: '台灣', role: '高價股對照', include_in_today_signal: false },
  { code: '00896', name: '中信綠能及電動車', market: '台灣', role: '綠能電動車對照', include_in_today_signal: false },
  { code: '00900', name: '富邦特選高股息30', market: '台灣', role: '高股息族群對照', include_in_today_signal: false },
  { code: '00901', name: '永豐智能車供應鏈', market: '台灣', role: '智能車供應鏈對照', include_in_today_signal: false },
  { code: '00904', name: '新光臺灣半導體30', market: '台灣', role: '半導體族群對照', include_in_today_signal: false },
  { code: '00905', name: 'FT臺灣Smart', market: '台灣', role: 'Smart Beta 對照', include_in_today_signal: false },
  { code: '00907', name: '永豐優息存股', market: '台灣', role: '高股息族群對照', include_in_today_signal: false },
  { code: '00912', name: '中信臺灣智慧50', market: '台灣', role: '智慧50對照', include_in_today_signal: false },
  { code: '00913', name: '兆豐台灣晶圓製造', market: '台灣', role: '半導體族群對照', include_in_today_signal: false },
  { code: '00915', name: '凱基優選高股息30', market: '台灣', role: '高股息族群對照', include_in_today_signal: false },
  { code: '00918', name: '大華優利高填息30', market: '台灣', role: '高股息族群對照', include_in_today_signal: false },
  { code: '00919', name: '群益台灣精選高息', market: '台灣', role: '高股息族群對照', include_in_today_signal: false },
  { code: '00921', name: '兆豐龍頭等權重', market: '台灣', role: '龍頭股對照', include_in_today_signal: false },
  { code: '00922', name: '國泰台灣領袖50', market: '台灣', role: '大盤權值股對照', include_in_today_signal: false },
  { code: '00923', name: '群益台ESG低碳50', market: '台灣', role: 'ESG低碳對照', include_in_today_signal: false },
  { code: '00927', name: '群益半導體收益', market: '台灣', role: '半導體收益對照', include_in_today_signal: false },
  { code: '00928', name: '中信上櫃ESG30', market: '台灣', role: '上櫃ESG對照', include_in_today_signal: false },
  { code: '00929', name: '復華台灣科技優息', market: '台灣', role: '科技高息對照', include_in_today_signal: false },
  { code: '00930', name: '永豐ESG低碳高息', market: '台灣', role: 'ESG高息對照', include_in_today_signal: false },
  { code: '00932', name: '兆豐永續高息等權', market: '台灣', role: '永續高息對照', include_in_today_signal: false },
  { code: '00934', name: '中信成長高股息', market: '台灣', role: '成長高息對照', include_in_today_signal: false },
  { code: '00935', name: '野村臺灣新科技50', market: '台灣', role: '科技族群對照', include_in_today_signal: false },
  { code: '00936', name: '台新永續高息中小', market: '台灣', role: '中小高息對照', include_in_today_signal: false },
  { code: '00938', name: '凱基優選30', market: '台灣', role: '優選股對照', include_in_today_signal: false },
  { code: '00939', name: '統一台灣高息動能', market: '台灣', role: '高息動能對照', include_in_today_signal: false },
  { code: '00940', name: '元大台灣價值高息', market: '台灣', role: '價值高息對照', include_in_today_signal: false },
  { code: '00943', name: '兆豐電子高息等權', market: '台灣', role: '電子高息對照', include_in_today_signal: false },
  { code: '00944', name: '野村趨勢動能高息', market: '台灣', role: '趨勢動能高息對照', include_in_today_signal: false },
  { code: '00946', name: '群益科技高息成長', market: '台灣', role: '科技高息對照', include_in_today_signal: false },
  { code: '00947', name: '台新臺灣IC設計', market: '台灣', role: 'IC設計族群對照', include_in_today_signal: false },
  { code: '00952', name: '凱基台灣AI50', market: '台灣', role: 'AI族群對照', include_in_today_signal: false },
  { code: '00961', name: 'FT臺灣永續高息', market: '台灣', role: '永續高息對照', include_in_today_signal: false },
  { code: '00962', name: '台新AI優息動能', market: '台灣', role: 'AI優息動能對照', include_in_today_signal: false },
  { code: '009802', name: '富邦旗艦50', market: '台灣', role: '旗艦50對照', include_in_today_signal: false },
  { code: '009803', name: '玉山市值動能50', market: '台灣', role: '市值動能50對照', include_in_today_signal: false },
  { code: '009804', name: '聯邦台精彩50', market: '台灣', role: '台股50對照', include_in_today_signal: false },
  { code: '009808', name: '華南永昌優選50', market: '台灣', role: '優選50對照', include_in_today_signal: false },
  { code: '00735', name: '國泰臺韓科技', market: '台灣', role: '跨市場科技對照', include_in_today_signal: false },
  { code: '009809', name: '富邦淨零ESG50', market: '台灣', role: 'ESG低碳對照', include_in_today_signal: false },
  { code: '009816', name: '凱基台灣TOP 50', market: '台灣', role: '大盤權值股對照', include_in_today_signal: false },
];

export const REFERENCE_ETF_CODES = REFERENCE_ETFS.map((x) => x.code);

export const REFERENCE_ETF_NAMES: Record<string, string> = Object.fromEntries(
  REFERENCE_ETFS.map((x) => [x.code, x.name])
);

export function isReferenceEtf(code: string) {
  return REFERENCE_ETF_CODES.includes(String(code || '').trim());
}
