import os
import time
from pprint import pprint

from app.config import ETF_CODES
from app.services.fetcher import update_one_etf


def _unique(seq):
    out = []
    seen = set()
    for x in seq:
        x = str(x or '').strip().upper()
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _selected_codes():
    env_codes = os.environ.get('ETF_CODES', '').strip()
    all_codes = _unique(ETF_CODES)

    if env_codes:
        return _unique(env_codes.replace('\n', ',').replace(' ', ',').split(','))

    batch_index = int(os.environ.get('BATCH_INDEX', '0') or '0')
    batch_size = int(os.environ.get('BATCH_SIZE', '2') or '2')
    start = batch_index * batch_size
    end = start + batch_size
    return all_codes[start:end]


def main():
    dt_range = int(os.environ.get('DT_RANGE', '9999') or '9999')
    sleep_sec = float(os.environ.get('SLEEP_SEC', '0.8') or '0.8')
    batch_index = os.environ.get('BATCH_INDEX', '')
    batch_size = os.environ.get('BATCH_SIZE', '')

    codes = _selected_codes()

    print('DATABASE_URL:', 'set' if os.environ.get('DATABASE_URL') else 'missing', flush=True)
    print(f'DT_RANGE: {dt_range}', flush=True)
    print(f'BATCH_INDEX: {batch_index}', flush=True)
    print(f'BATCH_SIZE: {batch_size}', flush=True)
    print(f'Selected ETF count: {len(codes)}', flush=True)
    print(f'Selected ETFs: {codes}', flush=True)

    if not codes:
        print('No ETF selected for this batch. Done.', flush=True)
        return

    results = []
    errors = []

    for i, code in enumerate(codes, start=1):
        print(f'[{i}/{len(codes)}] Fetching {code}...', flush=True)
        try:
            result = update_one_etf(code, dt_range=dt_range)
            results.append(result)
            print(
                f'[{i}/{len(codes)}] Done {code}: rows={result.get("rows")}, dates={result.get("dates")}',
                flush=True,
            )
        except Exception as e:
            msg = f'{code}: {e}'
            errors.append(msg)
            results.append({'etf_code': code, 'error': str(e)})
            print(f'[{i}/{len(codes)}] Error {msg}', flush=True)
        time.sleep(sleep_sec)

    print('Backfill batch finished.', flush=True)
    pprint({'results': results, 'errors': errors})

    # 不直接 exit 1：避免某一檔暫時沒有資料導致整批矩陣 workflow 中斷。
    # 錯誤可從 log 的 errors 欄位檢查。


if __name__ == '__main__':
    main()
