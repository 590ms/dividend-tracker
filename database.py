import sqlite3
import threading
from datetime import datetime
from config import DB_FILE

class Database:
    def __init__(self):
        self._lock = threading.Lock()
        self.conn  = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS purchases (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker      TEXT NOT NULL,
                shares      REAL NOT NULL,
                price_paid  REAL NOT NULL,
                date_bought TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS price_cache (
                ticker      TEXT PRIMARY KEY,
                price_usd   REAL DEFAULT 0,
                div_usd     REAL DEFAULT 0,
                div_yield   REAL DEFAULT 0,
                ex_div_date TEXT,
                updated_at  TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        self.conn.commit()

    # ── Settings ────────────────────────────────────────────────────
    def get(self, key, default=None):
        r = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r['value'] if r else default

    def set(self, key, value):
        with self._lock:
            self.conn.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, str(value)))
            self.conn.commit()

    # ── Purchases ───────────────────────────────────────────────────
    def add_purchase(self, ticker, shares, price_paid, date_bought):
        with self._lock:
            self.conn.execute(
                "INSERT INTO purchases (ticker, shares, price_paid, date_bought) VALUES (?,?,?,?)",
                (ticker.upper(), float(shares), float(price_paid), date_bought)
            )
            self.conn.commit()

    def delete_purchase(self, pid):
        with self._lock:
            self.conn.execute("DELETE FROM purchases WHERE id=?", (pid,))
            self.conn.commit()

    def get_purchases(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM purchases ORDER BY date_bought DESC"
        ).fetchall()]

    def get_holdings(self):
        """Aggregated shares + avg cost + total cost per ticker."""
        rows = self.conn.execute("""
            SELECT ticker,
                   SUM(shares)                             AS shares,
                   SUM(shares * price_paid) / SUM(shares) AS avg_cost,
                   SUM(shares * price_paid)                AS total_cost
            FROM purchases GROUP BY ticker
        """).fetchall()
        return {r['ticker']: dict(r) for r in rows}

    # ── Price cache ─────────────────────────────────────────────────
    def cache_price(self, ticker, price_usd, div_usd, div_yield, ex_div_date):
        with self._lock:
            self.conn.execute("""
                INSERT OR REPLACE INTO price_cache
                VALUES (?,?,?,?,?,?)
            """, (ticker, price_usd, div_usd, div_yield, ex_div_date,
                  datetime.now().isoformat()))
            self.conn.commit()

    def get_cache(self):
        return {r['ticker']: dict(r)
                for r in self.conn.execute("SELECT * FROM price_cache").fetchall()}

    def close(self):
        self.conn.close()
