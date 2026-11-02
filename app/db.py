import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "keuangan.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL UNIQUE,
            tipe TEXT NOT NULL DEFAULT 'bank',
            saldo_awal INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipe TEXT NOT NULL
                CHECK (tipe IN ('pemasukan','pengeluaran','transfer')),
            nominal INTEGER NOT NULL CHECK (nominal > 0),
            kategori TEXT,
            catatan TEXT,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            to_account_id INTEGER REFERENCES accounts(id),
            tanggal TEXT NOT NULL DEFAULT (date('now','localtime')),
            dibuat TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """)


SQL_SALDO = """
SELECT a.id, a.nama, a.tipe,
  a.saldo_awal
  + COALESCE((SELECT SUM(nominal) FROM transactions
              WHERE account_id = a.id AND tipe = 'pemasukan'), 0)
  - COALESCE((SELECT SUM(nominal) FROM transactions
              WHERE account_id = a.id
              AND tipe IN ('pengeluaran','transfer')), 0)
  + COALESCE((SELECT SUM(nominal) FROM transactions
              WHERE to_account_id = a.id AND tipe = 'transfer'), 0)
  AS saldo
FROM accounts a
ORDER BY a.nama
"""


def hitung_saldo():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(SQL_SALDO)]