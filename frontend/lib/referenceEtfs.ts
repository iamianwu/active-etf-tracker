export type ReferenceEtf = {
  code: string;
  name: string;
  market: string;
  role: string;
  include_in_today_signal: false;
};

export const REFERENCE_ETFS: ReferenceEtf[] = [
  {
    code: '0050',
    name: '元大台灣50',
    market: '台灣',
    role: '大盤權值股對照',
    include_in_today_signal: false,
  },
  {
    code: '006208',
    name: '富邦台50',
    market: '台灣',
    role: '大盤權值股對照',
    include_in_today_signal: false,
  },
  {
    code: '0056',
    name: '元大高股息',
    market: '台灣',
    role: '高股息族群對照',
    include_in_today_signal: false,
  },
  {
    code: '00878',
    name: '國泰永續高股息',
    market: '台灣',
    role: '高股息族群對照',
    include_in_today_signal: false,
  },
  {
    code: '00919',
    name: '群益台灣精選高息',
    market: '台灣',
    role: '高股息族群對照',
    include_in_today_signal: false,
  },
  {
    code: '00713',
    name: '元大台灣高息低波',
    market: '台灣',
    role: '低波動高息對照',
    include_in_today_signal: false,
  },
  {
    code: '00881',
    name: '國泰台灣5G+',
    market: '台灣',
    role: '科技題材對照',
    include_in_today_signal: false,
  },
];

export const REFERENCE_ETF_CODES = REFERENCE_ETFS.map((x) => x.code);

export const REFERENCE_ETF_NAMES: Record<string, string> = Object.fromEntries(
  REFERENCE_ETFS.map((x) => [x.code, x.name])
);

export function isReferenceEtf(code: string) {
  return REFERENCE_ETF_CODES.includes(String(code || '').trim());
}
