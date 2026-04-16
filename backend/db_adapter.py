"""
Database adapter to seamlessly support both local SQLite and remote PostgreSQL (Supabase).
It uses the `DATABASE_URL` environment variable to determine which driver to use.
"""
import os
import logging

logger = logging.getLogger(__name__)

# Parse Postgres connection from environment
DATABASE_URL = os.environ.get("DATABASE_URL")

# Try to import psycopg2 if postgres is needed
if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        HAS_POSTGRES = True
    except ImportError:
        logger.warning("DATABASE_URL is set to postgres, but psycopg2 is not installed!")
        HAS_POSTGRES = False
else:
    HAS_POSTGRES = False

def _translate_query(query: str) -> str:
    """Translate SQLite-flavoured SQL to PostgreSQL."""
    pg = query.replace("?", "%s")

    # datetime() → INTERVAL
    if "datetime('now'" in pg:
        import re
        pg = pg.replace("datetime('now', '-24 hours')", "NOW() - INTERVAL '24 hours'")
        pg = pg.replace("datetime('now', '-6 hours')",  "NOW() - INTERVAL '6 hours'")
        pg = pg.replace("datetime('now', '-7 days')",   "NOW() - INTERVAL '7 days'")
        pg = re.sub(r"datetime\('now', '-(\d+) days'\)", r"NOW() - INTERVAL '\1 days'", pg)

    # INSERT OR REPLACE → INSERT ... ON CONFLICT DO NOTHING
    if "INSERT OR REPLACE INTO" in pg:
        pg = pg.replace("INSERT OR REPLACE INTO", "INSERT INTO")
        last_paren = pg.rfind(")")
        if last_paren != -1:
            pg = pg[:last_paren + 1] + " ON CONFLICT (event_id) DO NOTHING" + pg[last_paren + 1:]

    return pg


class PostgresCursor:
    """Thin cursor wrapper that applies SQL translation before every execute()."""

    def __init__(self, raw_cursor):
        self._cur = raw_cursor

    def execute(self, query, params=()):
        try:
            self._cur.execute(_translate_query(query), params)
        except Exception as e:
            logger.error(f"Postgres cursor error: {e}\nQuery: {_translate_query(query)}")
            raise

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def rowcount(self):
        return self._cur.rowcount

    def __iter__(self):
        return iter(self._cur)


class PostgresWrapper:
    """Wrapper that mimics SQLite connection and cursor behaviors for PostgreSQL"""

    def __init__(self, conn):
        self.conn = conn
        self.conn.autocommit = True

    def cursor(self):
        return PostgresCursor(self.conn.cursor())
        
    def execute(self, query, params=()):
        """Translate and execute directly on the connection (for conn.execute() callers)."""
        pg_query = _translate_query(query)
        raw_cursor = self.conn.cursor()
        try:
            raw_cursor.execute(pg_query, params)
        except Exception as e:
            logger.error(f"Postgres execution error: {e}\nQuery: {pg_query}\nParams: {params}")
            self.conn.rollback()
            raise
        return PostgresCursor(raw_cursor)
        
    def commit(self):
        # We set autocommit=True, so this is just a dummy method for compatibility
        pass
        
    def close(self):
        self.conn.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()

def get_db_connection(sqlite_path: str):
    """
    Returns either a psycopg2-backed PostgresWrapper or standard sqlite3 connection.
    This provides a zero-friction fallback/revert to SQLite if deployed locally.
    """
    if HAS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return PostgresWrapper(conn)
    else:
        import sqlite3
        conn = sqlite3.connect(sqlite_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
