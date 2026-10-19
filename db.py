"""SQLite backend for storing product name + quantity records."""
import sqlite3
from pathlib import Path


def get_data_dir() -> Path:
    """Per-user, per-OS app data directory that survives independent of where the exe is run from."""
    home = Path.home()
    data_dir = home / ".indian_tester_app"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_path() -> Path:
    return get_data_dir() / "products.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                description TEXT NOT NULL DEFAULT '',
                amazon_link TEXT NOT NULL DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                contact_name TEXT NOT NULL,
                contact_phone TEXT NOT NULL,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Upgrade path for databases created before description/amazon_link existed.
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(products)")}
        if "description" not in existing_cols:
            conn.execute("ALTER TABLE products ADD COLUMN description TEXT NOT NULL DEFAULT ''")
        if "amazon_link" not in existing_cols:
            conn.execute("ALTER TABLE products ADD COLUMN amazon_link TEXT NOT NULL DEFAULT ''")
        conn.commit()
    finally:
        conn.close()


def get_all_products():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, product_name, quantity, description, amazon_link "
            "FROM products ORDER BY product_name COLLATE NOCASE"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_product_by_id(product_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, product_name, quantity, description, amazon_link "
            "FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def find_products_by_name(name: str):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, product_name, quantity, description, amazon_link "
            "FROM products WHERE product_name = ? COLLATE NOCASE",
            (name,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_product_details(product_id: int, description: str, amazon_link: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE products SET description = ?, amazon_link = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?",
            (description, amazon_link, product_id),
        )
        conn.commit()
    finally:
        conn.close()


def insert_product(name: str, quantity: int) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO products (product_name, quantity) VALUES (?, ?)",
            (name, quantity),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_product(product_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM message_log WHERE product_id = ?", (product_id,))
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
    finally:
        conn.close()


def increase_quantity(product_id: int, add_quantity: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE products SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (add_quantity, product_id),
        )
        conn.commit()
    finally:
        conn.close()


def decrement_quantity(product_id: int, subtract: int = 1) -> None:
    """Reduces quantity by `subtract`, never going below zero."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE products SET quantity = MAX(quantity - ?, 0), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (subtract, product_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---- WhatsApp message log ----------------------------------------------

def log_message_sent(product_id: int, contact_name: str, contact_phone: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO message_log (product_id, contact_name, contact_phone) VALUES (?, ?, ?)",
            (product_id, contact_name, contact_phone),
        )
        conn.commit()
    finally:
        conn.close()


def get_message_log_for_product(product_id: int):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT contact_name, contact_phone, sent_at FROM message_log "
            "WHERE product_id = ? ORDER BY sent_at DESC",
            (product_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---- Contacts ----------------------------------------------------------

def get_all_contacts():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, name, phone FROM contacts ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def insert_contact(name: str, phone: str) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO contacts (name, phone) VALUES (?, ?)", (name, phone)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_contact(contact_id: int, name: str, phone: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE contacts SET name = ?, phone = ? WHERE id = ?",
            (name, phone, contact_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_contact(contact_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        conn.commit()
    finally:
        conn.close()


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit() or ch == "+")


def find_contact_by_phone(phone: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, name, phone FROM contacts WHERE phone = ?",
            (_normalize_phone(phone),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def sync_contacts_bulk(contacts):
    """Inserts (name, phone) pairs, skipping any phone number already saved
    (deduped by phone, so re-running a sync/import never creates duplicates).
    Returns (added_count, skipped_count)."""
    conn = get_connection()
    added = 0
    skipped = 0
    try:
        for name, phone in contacts:
            clean_phone = _normalize_phone(phone)
            if not name or not clean_phone:
                skipped += 1
                continue
            existing = conn.execute(
                "SELECT id FROM contacts WHERE phone = ?", (clean_phone,)
            ).fetchone()
            if existing:
                skipped += 1
                continue
            conn.execute(
                "INSERT INTO contacts (name, phone) VALUES (?, ?)", (name, clean_phone)
            )
            added += 1
        conn.commit()
    finally:
        conn.close()
    return added, skipped
