from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb


CACHE_KEY = "search:index:v1"


def table_columns(
    cur: psycopg.Cursor,
    table_name: str,
) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        """,
        (table_name,),
    )

    return {
        str(row[0])
        for row in cur.fetchall()
    }


def first_column(
    columns: set[str],
    candidates: list[str],
) -> str | None:
    for name in candidates:
        if name in columns:
            return name

    return None


def load_etf_quote_names(
    cur: psycopg.Cursor,
) -> dict[str, str]:
    columns = table_columns(
        cur,
        "etf_quotes",
    )

    code_column = first_column(
        columns,
        [
            "etf_code",
            "security_code",
            "code",
        ],
    )

    name_column = first_column(
        columns,
        [
            "etf_name",
            "security_name",
            "fund_name",
            "name",
        ],
    )

    if not code_column or not name_column:
        return {}

    query = sql.SQL(
        """
        SELECT
            {code_column}::text,
            MAX(
                NULLIF(
                    BTRIM({name_column}::text),
                    ''
                )
            )
        FROM etf_quotes
        WHERE {code_column} IS NOT NULL
        GROUP BY {code_column}::text
        """
    ).format(
        code_column=sql.Identifier(
            code_column
        ),
        name_column=sql.Identifier(
            name_column
        ),
    )

    cur.execute(query)

    return {
        str(row[0]).strip().upper():
            str(row[1]).strip()
        for row in cur.fetchall()
        if row[0] and row[1]
    }


def main() -> None:
    database_url = os.getenv(
        "DATABASE_URL",
        "",
    ).strip()

    if not database_url:
        raise RuntimeError(
            "Missing DATABASE_URL"
        )

    now = datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")

    with psycopg.connect(
        database_url
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                stock_search_index (
                    stock_code TEXT PRIMARY KEY,
                    stock_name TEXT,
                    data_date TEXT,
                    etf_count INTEGER,
                    total_weight DOUBLE PRECISION,
                    updated_at TEXT
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                app_cache (
                    cache_key TEXT PRIMARY KEY,
                    data_date TEXT,
                    payload JSONB NOT NULL,
                    updated_at TEXT
                )
                """
            )

            cur.execute(
                "DELETE FROM stock_search_index"
            )

            cur.execute(
                """
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
                        h.etf_code::text
                            AS etf_code,
                        h.data_date::text
                            AS data_date,
                        h.stock_code::text
                            AS stock_code,
                        h.stock_name::text
                            AS stock_name,
                        COALESCE(
                            NULLIF(
                                regexp_replace(
                                    h.weight::text,
                                    '[^0-9.\\-]',
                                    '',
                                    'g'
                                ),
                                ''
                            )::double precision,
                            0
                        ) AS weight
                    FROM holdings h
                    JOIN latest l
                      ON h.etf_code::text =
                         l.etf_code
                     AND h.data_date =
                         l.data_date
                    WHERE h.stock_code::text
                          ~ '^[0-9]{4}$'
                ),
                by_etf_stock AS (
                    SELECT
                        etf_code,
                        stock_code,
                        COALESCE(
                            MAX(stock_name),
                            stock_code
                        ) AS stock_name,
                        MAX(data_date)
                            AS data_date,
                        SUM(weight)
                            AS weight
                    FROM latest_holdings
                    GROUP BY
                        etf_code,
                        stock_code
                ),
                agg AS (
                    SELECT
                        stock_code,
                        COALESCE(
                            MAX(stock_name),
                            stock_code
                        ) AS stock_name,
                        MAX(data_date)
                            AS data_date,
                        COUNT(
                            DISTINCT etf_code
                        ) AS etf_count,
                        SUM(weight)
                            AS total_weight
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
                ON CONFLICT (stock_code)
                DO UPDATE SET
                    stock_name =
                        EXCLUDED.stock_name,
                    data_date =
                        EXCLUDED.data_date,
                    etf_count =
                        EXCLUDED.etf_count,
                    total_weight =
                        EXCLUDED.total_weight,
                    updated_at =
                        EXCLUDED.updated_at
                """,
                {
                    "now": now,
                },
            )

            cur.execute(
                """
                SELECT
                    stock_code,
                    stock_name,
                    data_date,
                    etf_count,
                    total_weight
                FROM stock_search_index
                ORDER BY stock_code
                """
            )

            stock_rows = [
                {
                    "stock_code":
                        str(row[0] or ""),
                    "stock_name":
                        str(
                            row[1] or row[0] or ""
                        ),
                    "data_date":
                        row[2],
                    "etf_count":
                        int(row[3] or 0),
                    "total_weight":
                        float(row[4] or 0),
                }
                for row in cur.fetchall()
            ]

            holdings_columns = table_columns(
                cur,
                "holdings",
            )

            etf_name_column = first_column(
                holdings_columns,
                [
                    "etf_name",
                    "fund_name",
                    "security_name",
                    "name",
                ],
            )

            if etf_name_column:
                name_expression = sql.SQL(
                    """
                    COALESCE(
                        MAX(
                            NULLIF(
                                BTRIM(
                                    h.{column}::text
                                ),
                                ''
                            )
                        ),
                        h.etf_code::text
                    )
                    """
                ).format(
                    column=sql.Identifier(
                        etf_name_column
                    )
                )
            else:
                name_expression = sql.SQL(
                    "h.etf_code::text"
                )

            if "weight" in holdings_columns:
                weight_expression = sql.SQL(
                    """
                    COALESCE(
                        NULLIF(
                            regexp_replace(
                                h.weight::text,
                                '[^0-9.\\-]',
                                '',
                                'g'
                            ),
                            ''
                        )::double precision,
                        0
                    )
                    """
                )
            else:
                weight_expression = sql.SQL(
                    "0::double precision"
                )

            etf_query = sql.SQL(
                """
                WITH latest AS (
                    SELECT
                        etf_code::text
                            AS etf_code,
                        MAX(data_date)
                            AS data_date
                    FROM holdings
                    WHERE etf_code IS NOT NULL
                    GROUP BY etf_code::text
                )
                SELECT
                    h.etf_code::text
                        AS etf_code,
                    {name_expression}
                        AS etf_name,
                    COUNT(
                        DISTINCT
                        NULLIF(
                            BTRIM(
                                h.stock_code::text
                            ),
                            ''
                        )
                    ) AS holding_count,
                    SUM(
                        {weight_expression}
                    ) AS stock_weight,
                    MAX(h.data_date)::text
                        AS data_date
                FROM holdings h
                JOIN latest l
                  ON h.etf_code::text =
                     l.etf_code
                 AND h.data_date =
                     l.data_date
                WHERE h.etf_code IS NOT NULL
                GROUP BY h.etf_code::text
                ORDER BY h.etf_code::text
                """
            ).format(
                name_expression=
                    name_expression,
                weight_expression=
                    weight_expression,
            )

            cur.execute(etf_query)

            quote_names = (
                load_etf_quote_names(cur)
            )

            etf_rows: list[
                dict[str, Any]
            ] = []

            for row in cur.fetchall():
                code = str(
                    row[0] or ""
                ).strip().upper()

                name = str(
                    row[1] or ""
                ).strip()

                if (
                    not name
                    or name == code
                ):
                    name = quote_names.get(
                        code,
                        code,
                    )

                etf_rows.append({
                    "etf_code": code,
                    "etf_name": name,
                    "holding_count":
                        int(row[2] or 0),
                    "stock_weight":
                        float(row[3] or 0),
                    "data_date":
                        row[4],
                })

            data_dates = [
                str(
                    row.get("data_date") or ""
                )
                for row in (
                    stock_rows + etf_rows
                )
                if row.get("data_date")
            ]

            latest_data_date = (
                max(data_dates)
                if data_dates
                else None
            )

            payload = {
                "version": 1,
                "generated_at": now,
                "etfs": etf_rows,
                "stocks": stock_rows,
            }

            cur.execute(
                """
                INSERT INTO app_cache (
                    cache_key,
                    data_date,
                    payload,
                    updated_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s
                )
                ON CONFLICT (cache_key)
                DO UPDATE SET
                    data_date =
                        EXCLUDED.data_date,
                    payload =
                        EXCLUDED.payload,
                    updated_at =
                        EXCLUDED.updated_at
                """,
                (
                    CACHE_KEY,
                    latest_data_date,
                    Jsonb(payload),
                    now,
                ),
            )

        conn.commit()

    print({
        "ok": True,
        "cache_key": CACHE_KEY,
        "stock_count": len(stock_rows),
        "etf_count": len(etf_rows),
        "data_date": latest_data_date,
        "updated_at": now,
    })


if __name__ == "__main__":
    main()
