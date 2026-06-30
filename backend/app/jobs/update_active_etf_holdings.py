import os
from pprint import pprint

from ..services.fetcher import update_all_etfs


def main() -> None:
    dt_range = int(os.environ.get("DT_RANGE", "1"))
    sleep_sec = float(os.environ.get("SLEEP_SEC", "0.8"))

    print(
        f"Run active ETF holdings only: dt_range={dt_range}, sleep_sec={sleep_sec}",
        flush=True,
    )
    pprint(update_all_etfs(dt_range=dt_range, sleep_sec=sleep_sec))


if __name__ == "__main__":
    main()
