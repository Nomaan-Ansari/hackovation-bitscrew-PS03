import sqlite3
import os

def initialize_erp_database():
    # Ensure the database directory exists
    os.makedirs('database', exist_ok=True)
    db_path = os.path.join('database', 'engine_master.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # --- CORE CLIENT TABLE (Updated with Debt) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            Client_ID TEXT PRIMARY KEY,
            Client_name TEXT NOT NULL,
            Merit INTEGER DEFAULT 100,
            counter INTEGER DEFAULT 0,
            debt REAL DEFAULT 0.0
        )
    ''')

    # --- TABLE 1 & 2: INVOICES (SENT & RECEIVED) ---
    for table_name in ["INV_SENT", "INV_REC"]:
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                INV_ID TEXT PRIMARY KEY,
                Client_ID TEXT,
                Client_name TEXT,
                Client_GST_ID TEXT,
                INV_Date TEXT,
                INV_time TEXT,
                Due_date TEXT,
                type TEXT,
                currency_mode TEXT,
                T_GST REAL,
                Total REAL,
                FOREIGN KEY (Client_ID) REFERENCES clients (Client_ID)
            )
        ''')

    # --- TABLE 3 & 4: RECEIPTS (SENT & RECEIVED) ---
    for table_name in ["REC_SENT", "REC_REC"]:
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                REC_ID TEXT PRIMARY KEY,
                Client_ID TEXT,
                Client_name TEXT,
                Client_GST_ID TEXT,
                REC_Date TEXT,
                REC_time TEXT,
                type TEXT,
                currency_mode TEXT,
                T_GST REAL,
                Total REAL,
                FOREIGN KEY (Client_ID) REFERENCES clients (Client_ID)
            )
        ''')

    # --- TABLE 5 & 6: INVOICE ITEMS (SENT & RECEIVED) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ITEMS_INV_SENT (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            Item TEXT,
            type TEXT,
            qty REAL,
            CP REAL,
            gst REAL,
            gst_rate REAL,
            INV_ID TEXT,
            payment_to_be_done REAL,
            payment_received REAL,
            payment_status TEXT,
            FOREIGN KEY (INV_ID) REFERENCES INV_SENT (INV_ID)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ITEMS_INV_REC (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            Item TEXT,
            type TEXT,
            qty REAL,
            CP REAL,
            gst REAL,
            gst_rate REAL,
            INV_ID TEXT,
            payment_to_be_done REAL,
            payment_currently_sent REAL,
            payment_status TEXT,
            FOREIGN KEY (INV_ID) REFERENCES INV_REC (INV_ID)
        )
    ''')

    # --- TABLE 7 & 8: RECEIPT ITEMS (RECEIVED & SENT) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ITEMS_REC_REC (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            Item TEXT,
            type TEXT,
            qty REAL,
            CP REAL,
            gst REAL,
            gst_rate REAL,
            REC_ID TEXT,
            payment_done REAL,
            FOREIGN KEY (REC_ID) REFERENCES REC_REC (REC_ID)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ITEMS_REC_SENT (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            Item TEXT,
            type TEXT,
            qty REAL,
            CP REAL,
            gst REAL,
            gst_rate REAL,
            REC_ID TEXT,
            payment_sent REAL,
            FOREIGN KEY (REC_ID) REFERENCES REC_SENT (REC_ID)
        )
    ''')

    # --- TABLE 9: AUDITS ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Audits (
            AUDIT_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            INV_ID TEXT,
            description TEXT,
            severity TEXT,
            merit_change INTEGER
        )
    ''')

    # --- TABLE 11: MARKET ANALYSIS ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS MARKET (
            ITEM TEXT PRIMARY KEY,
            category TEXT,
            inflation_rate REAL,
            avg_price REAL,
            max_price REAL,
            min_price REAL
        )
    ''')

    conn.commit()
    conn.close()
    print("💎 ERP Database Schema fully initialized with 11 tables (Client Debt included).")

if __name__ == "__main__":
    initialize_erp_database()