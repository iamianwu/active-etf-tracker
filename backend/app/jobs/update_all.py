"""GitHub Actions / cron entry point.

Run examples:
  python -m app.jobs.update_all
  DT_RANGE=90 python -m app.jobs.update_all
"""
import json
import os

from app.database import init_db
from app.services.fetcher import update_all_etfs


def main():
    init_db()
    dt_range = int(os.getenv("DT_RANGE", "1"))
    sleep_sec = float(os.getenv("SLEEP_SEC", "0.7"))
    result = update_all_etfs(dt_range=dt_range, sleep_sec=sleep_sec)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
