import os
import sqlite3
from contextlib import contextmanager
from urllib.parse import urlparse

from .config import DB_PATH, DATABASE_URL

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # psycopg is optional for local SQLite mode
    psycopg = None
    dict_row = None

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS holdings (
    etf_code TEXT NOT NULL,
    data_date TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    weight REAL,
    shares REAL,
    unit TEXT,
    PRIMARY KEY (etf_code, data_date, stock_code)
);

CREATE TABLE IF NOT EXISTS etf_quotes (
    etf_code TEXT PRIMARY KEY,
    etf_name TEXT,
    price REAL,
    change REAL,
    change_pct REAL,
    volume REAL,
    amount REAL,
    nav REAL,
    premium_pct REAL,
    aum_billion REAL,
    expense_ratio REAL,
    inception_date TEXT,
    holder_count INTEGER,
    dividend_frequency TEXT,
    week_return REAL,
    total_return REAL,
    annualized_return REAL,
    dividend_yield REAL,
    region TEXT,
    currency TEXT,
    manager TEXT,
    company TEXT,
    custodian TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS stock_quotes (
    stock_code TEXT PRIMARY KEY,
    stock_name TEXT,
    price REAL,
    change REAL,
    change_pct REAL,
    market_cap_billion REAL,
    market_cap_source TEXT,
    market_cap_updated_at TEXT,
    industry_code TEXT,
    industry_name TEXT,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_holdings_stock ON holdings(stock_code, data_date);
CREATE INDEX IF NOT EXISTS idx_holdings_etf_date ON holdings(etf_code, data_date);
"""

SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS holdings (
    etf_code TEXT NOT NULL,
    data_date TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    weight DOUBLE PRECISION,
    shares DOUBLE PRECISION,
    unit TEXT,
    PRIMARY KEY (etf_code, data_date, stock_code)
);

CREATE TABLE IF NOT EXISTS etf_quotes (
    etf_code TEXT PRIMARY KEY,
    etf_name TEXT,
    price DOUBLE PRECISION,
    change DOUBLE PRECISION,
    change_pct DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    amount DOUBLE PRECISION,
    nav DOUBLE PRECISION,
    premium_pct DOUBLE PRECISION,
    aum_billion DOUBLE PRECISION,
    expense_ratio DOUBLE PRECISION,
    inception_date TEXT,
    holder_count INTEGER,
    dividend_frequency TEXT,
    week_return DOUBLE PRECISION,
    total_return DOUBLE PRECISION,
    annualized_return DOUBLE PRECISION,
    dividend_yield DOUBLE PRECISION,
    region TEXT,
    currency TEXT,
    manager TEXT,
    company TEXT,
    custodian TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS stock_quotes (
    stock_code TEXT PRIMARY KEY,
    stock_name TEXT,
    price DOUBLE PRECISION,
    change DOUBLE PRECISION,
    change_pct DOUBLE PRECISION,
    market_cap_billion DOUBLE PRECISION,
    market_cap_source TEXT,
    market_cap_updated_at TEXT,
    industry_code TEXT,
    industry_name TEXT,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_holdings_stock ON holdings(stock_code, data_date);
CREATE INDEX IF NOT EXISTS idx_holdings_etf_date ON holdings(etf_code, data_date);
"""


def is_postgres() -> bool:
    return bool(DATABASE_URL and DATABASE_URL.startswith(("postgresql://", "postgres://")))


def normal_stock_condition(alias: str = "h") -> str:
    if is_postgres():
        return f"{alias}.stock_code ~ '^[0-9]{{4}}$'"
    return f"{alias}.stock_code GLOB '[0-9][0-9][0-9][0-9]'"


def _postgres_url(url: str) -> str:
    # Supabase / Heroku sometimes uses postgres://, psycopg accepts postgresql:// more reliably.
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


class CompatConnection:
    def __init__(self, conn, postgres: bool):
        self.conn = conn
        self.postgres = postgres

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.postgres else sql

    def execute(self, sql: str, params=()):
        return self.conn.execute(self._sql(sql), params)

    def executemany(self, sql: str, seq):
        return self.conn.executemany(self._sql(sql), seq)

    def executescript(self, sql: str):
        if self.postgres:
            # psycopg execute can run multi-statements when there are no parameters.
            return self.conn.execute(sql)
        return self.conn.executescript(sql)

    def commit(self):
        return self.conn.commit()

    def close(self):
        return self.conn.close()


@contextmanager
def get_conn():
    if is_postgres():
        if psycopg is None:
            raise RuntimeError("psycopg is not installed. Run: pip install 'psycopg[binary]'")
        conn = psycopg.connect(_postgres_url(DATABASE_URL), row_factory=dict_row)
        compat = CompatConnection(conn, postgres=True)
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        compat = CompatConnection(conn, postgres=False)
    try:
        yield compat
        compat.commit()
    finally:
        compat.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA_POSTGRES if is_postgres() else SCHEMA_SQLITE)


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


def upsert_holding(conn, r: dict):
    if conn.postgres:
        conn.execute(
            """
            INSERT INTO holdings
            (etf_code, data_date, stock_code, stock_name, weight, shares, unit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (etf_code, data_date, stock_code)
            DO UPDATE SET stock_name=EXCLUDED.stock_name, weight=EXCLUDED.weight,
                          shares=EXCLUDED.shares, unit=EXCLUDED.unit
            """,
            (r["etf_code"], r["data_date"], r["stock_code"], r["stock_name"], r["weight"], r["shares"], r["unit"]),
        )
    else:
        conn.execute(
            """
            INSERT OR REPLACE INTO holdings
            (etf_code, data_date, stock_code, stock_name, weight, shares, unit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (r["etf_code"], r["data_date"], r["stock_code"], r["stock_name"], r["weight"], r["shares"], r["unit"]),
        )


def upsert_etf_quote(conn, row: tuple):
    # row = (etf_code, etf_name, price, change_pct, updated_at)
    if conn.postgres:
        conn.execute(
            """
            INSERT INTO etf_quotes(etf_code, etf_name, price, change_pct, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (etf_code) DO UPDATE SET
              etf_name=EXCLUDED.etf_name,
              price=COALESCE(EXCLUDED.price, etf_quotes.price),
              change_pct=COALESCE(EXCLUDED.change_pct, etf_quotes.change_pct),
              updated_at=EXCLUDED.updated_at
            """,
            row,
        )
    else:
        conn.execute(
            "INSERT OR IGNORE INTO etf_quotes(etf_code, etf_name, price, change_pct, updated_at) VALUES (?, ?, ?, ?, ?)",
            row,
        )


def upsert_stock_quote(conn, row: tuple):
    # row = (stock_code, stock_name, price, change_pct, updated_at)
    if conn.postgres:
        conn.execute(
            """
            INSERT INTO stock_quotes(stock_code, stock_name, price, change_pct, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (stock_code) DO UPDATE SET
              stock_name=EXCLUDED.stock_name,
              price=EXCLUDED.price,
              change_pct=EXCLUDED.change_pct,
              updated_at=EXCLUDED.updated_at
            """,
            row,
        )
    else:
        conn.execute(
            "INSERT OR REPLACE INTO stock_quotes(stock_code, stock_name, price, change_pct, updated_at) VALUES (?, ?, ?, ?, ?)",
            row,
        )
