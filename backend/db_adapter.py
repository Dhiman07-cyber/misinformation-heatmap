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

class PostgresWrapper:
    """Wrapper that mimics SQLite connection and cursor behaviors for PostgreSQL"""
    
    def __init__(self, conn):
        self.conn = conn
        self.conn.autocommit = True
        
    def cursor(self):
        return self.conn.cursor()
        
    def execute(self, query, params=()):
        # Translate SQLite '?' to Postgres '%s' for parameterized queries
        pg_query = query.replace("?", "%s")
        
        # Translate SQLite datetime functions to Postgres
        if "datetime('now'" in pg_query:
            pg_query = pg_query.replace("datetime('now', '-24 hours')", "NOW() - INTERVAL '24 hours'")
            pg_query = pg_query.replace("datetime('now', '-6 hours')", "NOW() - INTERVAL '6 hours'")
            pg_query = pg_query.replace("datetime('now', '-7 days')", "NOW() - INTERVAL '7 days'")
            import re
            pg_query = re.sub(r"datetime\('now', '-(\d+) days'\)", r"NOW() - INTERVAL '\1 days'", pg_query)
        
        # Translate SQLite INSERT OR REPLACE to Postgres INSERT ... ON CONFLICT DO NOTHING
        # SQLite: INSERT OR REPLACE INTO table (cols) VALUES (...)
        # Postgres: INSERT INTO table (cols) VALUES (...) ON CONFLICT (event_id) DO NOTHING
        if "INSERT OR REPLACE INTO" in pg_query:
            pg_query = pg_query.replace("INSERT OR REPLACE INTO", "INSERT INTO")
            # Find the last closing paren and insert the ON CONFLICT clause before any trailing whitespace
            last_paren = pg_query.rfind(")")
            if last_paren != -1:
                pg_query = pg_query[:last_paren + 1] + " ON CONFLICT (event_id) DO NOTHING" + pg_query[last_paren + 1:]
            
        cursor = self.conn.cursor()
        try:
            cursor.execute(pg_query, params)
        except Exception as e:
            logger.error(f"Postgres execution error: {e}\nQuery: {pg_query}\nParams: {params}")
            self.conn.rollback()
            raise
        return cursor
        
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
