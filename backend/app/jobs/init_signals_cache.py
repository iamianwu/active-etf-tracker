import os
from datetime import datetime
import psycopg


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Missing DATABASE_URL")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS signals_cache (
                    cache_key TEXT PRIMARY KEY,
                    data_date TEXT,
                    holdings_row_count INTEGER,
                    days INTEGER,
                    signal_type TEXT,
                    payload JSONB NOT NULL,
                    updated_at TEXT
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_cache_data_date
                ON signals_cache(data_date)
            """)
        conn.commit()

    print({"ok": True, "table": "signals_cache", "updated_at": datetime.now().isoformat(timespec="seconds")})


if __name__ == "__main__":
    main()
