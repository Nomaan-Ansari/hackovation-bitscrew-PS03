from src.database_manager import get_conn
from datetime import datetime  # ADDED THIS IMPORT

def update_parent_status(parent_id, audit_table, bucket_table):
    """
    Checks if all child items are 'Completed' to update the parent header status.
    """
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT COUNT(*) FROM {bucket_table} WHERE parent_id = ? AND status != 'Completed'", (parent_id,))
    remaining_items = cursor.fetchone()[0]
    
    new_status = "Completed" if remaining_items == 0 else "Partial"
    
    cursor.execute(f"UPDATE {audit_table} SET status = ? WHERE id = ?", (new_status, parent_id))
    
    conn.commit()
    conn.close()
    return new_status

def reconcile_with_payment(item_name, qty_received, unit_price, parent_id):
    """
    Matches received items against open Invoices and updates the ledger.
    """
    conn = get_conn()
    cursor = conn.cursor()
    
    # --- PART A: FIND THE TARGET INVOICE BUCKET ---
    cursor.execute("""
        SELECT item_id, parent_id, qty_total, qty_fulfilled 
        FROM payment_to_be_received_inv 
        WHERE item_name = ? AND status != 'Completed'
        ORDER BY item_id ASC LIMIT 1
    """, (item_name,))
    
    row = cursor.fetchone()
    if row:
        item_id, invoice_id, total, fulfilled = row
        new_fulfilled = fulfilled + qty_received
        item_status = "Completed" if new_fulfilled >= total else "Partial"
        
        # --- FIXED: DYNAMIC DATE ---
        current_date_str = datetime.now().strftime("%Y-%m-%d")

        # --- PART B: MIRROR TO AUDIT LEDGER (Layer 1) ---
        cursor.execute("""
            INSERT OR IGNORE INTO rec_sent (id, inv_id, date, amount, status)
            VALUES (?, ?, ?, ?, ?)
        """, (parent_id, invoice_id, current_date_str, (qty_received * unit_price), 'Completed'))

        # --- PART C: UPDATE ITEM BUCKETS (Layer 2) ---
        cursor.execute("""
            UPDATE payment_to_be_received_inv 
            SET qty_fulfilled = ?, status = ? 
            WHERE item_id = ?
        """, (new_fulfilled, item_status, item_id))

        cursor.execute("""
            INSERT INTO payment_received_rec (parent_id, item_name, qty_total, qty_fulfilled, unit_price, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (parent_id, item_name, qty_received, qty_received, unit_price, 'Completed'))
        
        conn.commit()
        conn.close()

        # --- PART D: PARENT STATUS ROLL-UP ---
        update_parent_status(invoice_id, "inv_sent", "payment_to_be_received_inv")
        
        print(f"✅ Reconciled {qty_received} units of {item_name} for {invoice_id}. Status: {item_status}")
    else:
        print(f"⚠️ No open invoice found for item: {item_name}. Recording as orphan payment.")
        conn.close()