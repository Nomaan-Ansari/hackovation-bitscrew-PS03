import sqlite3
import json

def get_conn():
    return sqlite3.connect('database/engine_master.db')

def save_audit_package(ai_data, file_path=None):
    """
    Ensures 'Double-Entry' integrity: 
    1. Saves the Header to the Audit Table (Layer 1 - The Tabs).
    2. Opens the initial Buckets in the Item Tables (Layer 2 - The Math).
    """
    conn = get_conn()
    cursor = conn.cursor()
    
    doc_id = ai_data.get('id')
    doc_type = ai_data.get('type') # e.g., 'inv_rec', 'inv_sent'
    items = ai_data.get('items', [])
    items_json = json.dumps(items)
    
    try:
        # --- 1. SYNC TO AUDIT LAYER (Layer 1) ---
        # This makes the entry appear in your 'Invoices' or 'Receipts' tabs.
        cursor.execute(f"""
            INSERT OR IGNORE INTO {doc_type} (id, date, total, items_json, status)
            VALUES (?, ?, ?, ?, ?)
        """, (doc_id, ai_data.get('date'), ai_data.get('total'), items_json, 'Incomplete'))

        # --- 2. SYNC TO BUCKET LAYER (Layer 2) ---
        # Only create new buckets for INVOICES.
        if doc_type in ['inv_rec', 'inv_sent']:
            bucket_table = "payment_to_be_sent_inv" if doc_type == "inv_rec" else "payment_to_be_received_inv"
            
            for item in items:
                cursor.execute(f"""
                    INSERT OR IGNORE INTO {bucket_table} 
                    (parent_id, item_name, qty_total, qty_fulfilled, unit_price, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (doc_id, item.get('name'), item.get('qty'), 0, item.get('price'), 'Incomplete'))
        
        conn.commit()
        print(f"✅ Full-Bake Sync Complete for {doc_id}")
    except Exception as e:
        print(f"❌ Sync Error: {e}")
    finally:
        conn.close()