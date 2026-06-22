import os
from datetime import datetime
import psycopg


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Missing DATABASE_URL")

    now = datetime.now().isoformat(timespec="seconds")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stock_search_index (
                    stock_code TEXT PRIMARY KEY,
                    stock_name TEXT,
                    data_date TEXT,
                    etf_count INTEGER,
                    total_weight DOUBLE PRECISION,
                    updated_at TEXT
                )
            """)

            cur.execute("DELETE FROM stock_search_index")

            cur.execute("""
                WITH latest AS (
                    SELECT
                        etf_code::text AS etf_code,
                        MAX(data_date) AS data_date
                    FROM holdings
                    WHERE etf_code IS NOT NULL
                    GROUP BY etf_code::text
                ),
                latest_holdings AS (
                    SELECT
                        h.etf_code::text AS etf_code,
                        h.data_date::text AS data_date,
                        h.stock_code::text AS stock_code,
                        h.stock_name::text AS stock_name,
                        COALESCE(
                            NULLIF(regexp_replace(h.weight::text, '[^0-9.\\-]', '', 'g'), '')::double precision,
                            0
                        ) AS weight
                    FROM holdings h
                    JOIN latest l
                      ON h.etf_code::text = l.etf_code
                     AND h.data_date = l.data_date
                    WHERE h.stock_code::text ~ '^[0-9]{4}$'
                ),
                by_etf_stock AS (
                    SELECT
                        etf_code,
                        stock_code,
                        COALESCE(MAX(stock_name), stock_code) AS stock_name,
                        MAX(data_date) AS data_date,
                        SUM(weight) AS weight
                    FROM latest_holdings
                    GROUP BY etf_code, stock_code
                ),
                agg AS (
                    SELECT
                        stock_code,
                        COALESCE(MAX(stock_name), stock_code) AS stock_name,
                        MAX(data_date) AS data_date,
                        COUNT(DISTINCT etf_code) AS etf_count,
                        SUM(weight) AS total_weight
                    FROM by_etf_stock
                    GROUP BY stock_code
                )
                INSERT INTO stock_search_index (
                    stock_code,
                    stock_name,
                    data_date,
                    etf_count,
                    total_weight,
                    updated_at
                )
                SELECT
                    stock_code,
                    stock_name,
                    data_date,
                    etf_count,
                    total_weight,
                    %(now)s
                FROM agg
                ON CONFLICT (stock_code) DO UPDATE SET
                    stock_name = EXCLUDED.stock_name,
                    data_date = EXCLUDED.data_date,
                    etf_count = EXCLUDED.etf_count,
                    total_weight = EXCLUDED.total_weight,
                    updated_at = EXCLUDED.updated_at
            """, {"now": now})

            cur.execute("SELECT COUNT(*) FROM stock_search_index")
            count = cur.fetchone()[0]

        conn.commit()

    print({"ok": True, "stock_search_index_rows": count, "updated_at": now})


if __name__ == "__main__":
    main()
