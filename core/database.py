import sqlite3
from pathlib import Path
import json

DB_PATH = Path("./data/inventory.db")
DB_PATH.parent.mkdir(exist_ok=True)


# -------------------- Core helpers --------------------

def get_connection():
    """Open SQLite connection to the main inventory database."""
    return sqlite3.connect(DB_PATH)


def table_columns(conn, table):
    """Return list of column names for a given table."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    return [r[1] for r in cur.fetchall()]


# -------------------- Schema management --------------------

def create_schema(conn):
    """Create all tables if they do not exist."""
    cur = conn.cursor()

    # --- main products table ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            code TEXT UNIQUE NOT NULL,
            gemeinde TEXT NOT NULL,
            einsatzort TEXT,
            kategorie TEXT,
            produkttyp TEXT,
            produktdetails TEXT,
            anzahl INTEGER DEFAULT 1,
            hersteller TEXT,
            lieferant TEXT,
            shop_link TEXT,
            preis_netto REAL,
            preis_brutto REAL,
            bezahlt TEXT,
            bestellt_am TEXT,
            geliefert_am TEXT,
            uebergeben_am TEXT,
            projekt TEXT,
            bemerkungen TEXT
        )
    """)

    # --- dropdown options table ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS options (
            field TEXT NOT NULL,
            value TEXT NOT NULL,
            UNIQUE(field, value)
        )
    """)

    conn.commit()

def create_users_table(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        );
    """)
    conn.commit()


def migrate_old_schema(conn):
    """If old 'products' schema exists, migrate to new one."""
    cur = conn.cursor()
    cols = table_columns(conn, "inventory")
    if not cols:
        return False

    print("Old schema detected, migrating...")
    cur.execute("ALTER TABLE inventory RENAME TO products_old;")
    create_schema(conn)

    # Copy overlapping fields
    existing = table_columns(conn, "products_old")
    common = [c for c in existing if c in ("code", "bemerkungen", "gemeinde")]
    if common:
        fields = ", ".join(common)
        cur.execute(f"INSERT INTO inventory ({fields}) SELECT {fields} FROM products_old;")

    conn.commit()
    return True


def init_db():
    """Initialize DB and ensure all required tables exist."""
    conn = get_connection()
    cur = conn.cursor()
    create_users_table(conn)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inventory';")
    if cur.fetchone():
        # Products table exists — check for migration and ensure options table
        cols = table_columns(conn, "inventory")
        if len(cols) < 10:  # very old schema heuristic
            migrate_old_schema(conn)
        else:
            # Ensure 'options' table exists even in existing DB
            cur.execute("""
                CREATE TABLE IF NOT EXISTS options (
                    field TEXT NOT NULL,
                    value TEXT NOT NULL,
                    UNIQUE(field, value)
                )
            """)
            conn.commit()
    else:
        # Fresh DB
        create_schema(conn)

    conn.close()


# -------------------- CRUD helpers --------------------

def add_product_safe(**kwargs):
    """Safely insert a product record into the database."""
    conn = get_connection()
    try:
        with conn:
            fields = ", ".join(kwargs.keys())
            placeholders = ", ".join(["?"] * len(kwargs))
            conn.execute(f"INSERT INTO inventory ({fields}) VALUES ({placeholders})", tuple(kwargs.values()))
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_all_products():
    """Return all product rows sorted by newest first."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM inventory ORDER BY code ASC;")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_product_by_code(code):
    """Return one product row by its barcode/code as dictionary-like object."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row   # 👈 THIS IS THE MAGIC LINE
    cur = conn.cursor()

    cur.execute("SELECT * FROM inventory WHERE code=?;", (code,))
    row = cur.fetchone()

    conn.close()
    return row


# -------------------- Dropdown Options --------------------

def get_options(field):
    """Return all saved dropdown options for a given field name."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM options WHERE field=? ORDER BY value COLLATE NOCASE;", (field,))
    values = [r[0] for r in cur.fetchall()]
    conn.close()
    return values


def add_option(field, value):
    """Add a new dropdown option if it does not exist."""
    if not value or not value.strip():
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO options(field, value) VALUES (?, ?);", (field, value.strip()))
    conn.commit()
    conn.close()


def get_all_gemeinden():
    data_path = Path("./data/gemeinden.json")
    with open(data_path, "r", encoding="utf-8") as f:
        gdata = json.load(f)
    return list(gdata["Gemeinden"].keys()) + list(gdata["VGs"].keys())
