import sqlite3
import os

def hard_reset_db():
    db_path = 'database/engine_master.db'
    
    # 1. Delete the old database to clear the 'missing column' error
    if os.path.exists(db_path):
        os.remove(db_path)
        print("🗑️ Old database deleted.")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # --- LAYER 1: AUDIT TABLES (With Status Columns) ---
    cursor.execute("CREATE TABLE inv_rec (id TEXT PRIMARY KEY, vendor_id INTEGER, date TEXT, total REAL, items_json TEXT, status TEXT DEFAULT 'Incomplete')")
    cursor.execute("CREATE TABLE inv_sent (id TEXT PRIMARY KEY, client_id INTEGER, date TEXT, total REAL, items_json TEXT, status TEXT DEFAULT 'Incomplete')")
    cursor.execute("CREATE TABLE rec_rec (id TEXT PRIMARY KEY, inv_id TEXT, date TEXT, amount REAL, items_json TEXT, status TEXT DEFAULT 'Completed')")
    cursor.execute("CREATE TABLE rec_sent (id TEXT PRIMARY KEY, inv_id TEXT, date TEXT, amount REAL, items_json TEXT, status TEXT DEFAULT 'Completed')")

    # --- LAYER 2: ITEM BUCKETS (With parent_id Links) ---
    bucket_tables = ["payment_to_be_sent_inv", "payment_to_be_done_rec", "payment_to_be_received_inv", "payment_received_rec"]
    for table in bucket_tables:
        cursor.execute(f"""
            CREATE TABLE {table} (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id TEXT, 
                item_name TEXT,
                qty_total INTEGER,
                qty_fulfilled INTEGER DEFAULT 0,
                unit_price REAL,
                status TEXT DEFAULT 'Incomplete'
            )
        """)

    # --- LAYER 3: INTELLIGENCE ---
    cursor.execute("CREATE TABLE entity_master (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, merit INTEGER DEFAULT 100, streak INTEGER DEFAULT 0)")
    cursor.execute("CREATE TABLE merit_audit_trail (entity_id INTEGER, change INTEGER, reason TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE market_index (item_name TEXT PRIMARY KEY, avg_price REAL, last_updated TEXT)")

    conn.commit()
    conn.close()
    print("💎 Database rebuilt with all 11 tables and 'status' columns!")

if __name__ == "__main__":
    hard_reset_db()