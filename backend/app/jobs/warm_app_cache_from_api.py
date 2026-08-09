import os
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode

import requests


def get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def fetch_json(url: str, timeout: int = 90):
    res = requests.get(url, timeout=timeout)
    res.raise_for_status()
    return res.json()


def warm_url(url: str, timeout: int = 90):
    started = time.time()
    try:
        res = requests.get(url, timeout=timeout)
        ok = 200 <= res.status_code < 300
        return {
            "ok": ok,
            "status": res.status_code,
            "url": url,
            "seconds": round(time.time() - started, 3),
            "size": len(res.content or b""),
        }
    except Exception as e:
        return {
            "ok": False,
            "url": url,
            "seconds": round(time.time() - started, 3),
            "error": str(e),
        }


def main():
    site_url = get_env("SITE_URL", "https://active-etf-tracker.vercel.app").rstrip("/")
    max_workers = int(get_env("MAX_WORKERS", "4"))
    max_stocks = int(get_env("MAX_STOCKS", "0"))
    sleep_sec = float(get_env("SLEEP_SEC", "0.05"))

    print({
        "site_url": site_url,
        "max_workers": max_workers,
        "max_stocks": max_stocks,
        "sleep_sec": sleep_sec,
    }, flush=True)

    # 先 warm 主頁 cache
    for path in ["/etfs", "/holdings"]:
        url = f"{site_url}{path}"
        print({"stage": "warm_page", **warm_url(url, timeout=180)}, flush=True)

    # 取得所有 holdings 個股代碼
    codes_payload = fetch_json(f"{site_url}/api/stock-cache-codes", timeout=180)
    codes = codes_payload.get("codes") or []

    if max_stocks > 0:
        codes = codes[:max_stocks]

    print({
        "stage": "codes",
        "count": len(codes),
        "sample": codes[:20],
    }, flush=True)

    urls = [
        f"{site_url}/api/stock-detail?{urlencode({'code': code, 'fresh': '1'})}"
        for code in codes
    ]

    ok_count = 0
    fail_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = []

        for url in urls:
            futures.append(ex.submit(warm_url, url, 120))
            if sleep_sec > 0:
                time.sleep(sleep_sec)

        for i, fut in enumerate(as_completed(futures), 1):
            result = fut.result()
            if result.get("ok"):
                ok_count += 1
            else:
                fail_count += 1

            if i <= 20 or not result.get("ok") or i % 25 == 0:
                print({"stage": "warm_stock", "i": i, "total": len(urls), **result}, flush=True)

    print({
        "stage": "done",
        "total": len(urls),
        "ok": ok_count,
        "failed": fail_count,
    }, flush=True)


if __name__ == "__main__":
    main()
