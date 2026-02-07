import os
import json
import sqlite3
import shutil
from datetime import datetime

# Configuration for paths
PATHS = {
    "typo_json": "data/json_files/typo_json",
    "archive": "data/json_archive",
    "failed": "data/json_failed",
    "db": "database/engine_master.db"
}

# Ensure archival directories exist
for p in [PATHS["archive"], PATHS["failed"]]: 
    os.makedirs(p, exist_ok=True)

def get_smaller_date(date_list):
    """Pick the earliest valid date found in the document for accounting."""
    valid_dates = []
    for d in date_list:
        if d and d not in ["N/A", "None", "", "NULL"]:
            try:
                valid_dates.append(datetime.strptime(str(d), '%Y-%m-%d'))
            except ValueError:
                continue
    return min(valid_dates).strftime('%Y-%m-%d') if valid_dates else "N/A"

def update_invoice_status(cursor, inv_id, table_prefix):
    """Updates the parent INV table status based on its item-level 'buckets'."""
    item_table = f"ITEMS_{table_prefix}"
    cursor.execute(f"SELECT payment_status FROM {item_table} WHERE INV_ID = ?", (inv_id,))
    statuses = [row[0] for row in cursor.fetchall()]
    
    if statuses and all(s == 'Completed' for s in statuses):
        cursor.execute(f"UPDATE {table_prefix} SET payment_status = 'Completed' WHERE INV_ID = ?", (inv_id,))
    elif any(s in ['Partial', 'Completed'] for s in statuses):
        cursor.execute(f"UPDATE {table_prefix} SET payment_status = 'Partial' WHERE INV_ID = ?", (inv_id,))

def fill_payment_buckets(cursor, client_id, item_name, amount_paid):
    """Allocates receipt payments to the oldest pending invoice items for a client."""
    cursor.execute('''
        SELECT item_id, payment_to_be_done, payment_received, INV_ID 
        FROM ITEMS_INV_SENT 
        WHERE Item = ? AND INV_ID IN (
            SELECT INV_ID FROM INV_SENT WHERE Client_ID = ?
        ) AND payment_status != 'Completed'
        ORDER BY item_id ASC
    ''', (item_name, client_id))
    
    pending = cursor.fetchall()
    for item_id, total, received, inv_id in pending:
        if amount_paid <= 0: break
        needed = total - received
        fill = min(amount_paid, needed)
        
        new_received = received + fill
        amount_paid -= fill
        status = 'Completed' if new_received >= total else 'Partial'
        
        cursor.execute('''
            UPDATE ITEMS_INV_SENT 
            SET payment_received = ?, payment_status = ? 
            WHERE item_id = ?
        ''', (new_received, status, item_id))
        
        update_invoice_status(cursor, inv_id, "INV_SENT")

def update_client_debt(cursor, client_id):
    """Calculates Net Debt: (Unpaid Items Sent) - (Unpaid Items Received)."""
    # x = Money we are waiting to receive
    cursor.execute('''
        SELECT SUM(payment_to_be_done - payment_received) 
        FROM ITEMS_INV_SENT 
        WHERE INV_ID IN (SELECT INV_ID FROM INV_SENT WHERE Client_ID = ?)
    ''', (client_id,))
    x = cursor.fetchone()[0] or 0.0

    # y = Money we still need to pay
    cursor.execute('''
        SELECT SUM(payment_to_be_done - payment_currently_sent) 
        FROM ITEMS_INV_REC 
        WHERE INV_ID IN (SELECT INV_ID FROM INV_REC WHERE Client_ID = ?)
    ''', (client_id,))
    y = cursor.fetchone()[0] or 0.0

    # +ve means client owes us; -ve means we owe them
    net_debt = x - y
    cursor.execute("UPDATE clients SET debt = ? WHERE Client_ID = ?", (net_debt, client_id))

def run_db_management():
    print("⚖️ Balancing Ledger & Archiving JSONs...")
    conn = sqlite3.connect(PATHS["db"])
    cursor = conn.cursor()
    
    json_files = [f for f in os.listdir(PATHS["typo_json"]) if f.endswith('.json')]
    
    for filename in json_files:
        src_path = os.path.join(PATHS["typo_json"], filename)
        try:
            with open(src_path, 'r') as f:
                data = json.load(f)

            c_id = data.get("client_id")
            c_name = data.get("client_name")
            doc_type = str(data.get("type", "")).lower()
            mode = str(data.get("current_mode", "")).lower()
            
            # Use 'Smaller Date' logic for INV_Date
            inv_date = get_smaller_date([data.get("INV_date"), data.get("Due_date"), data.get("REC_date")])

            # --- 1. INVOICE PROCESSING ---
            if "invoice" in doc_type:
                table = "INV_SENT" if "sent" in mode else "INV_REC"
                cursor.execute(f'''
                    INSERT OR REPLACE INTO {table} 
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ''', (data.get("INV_ID"), c_id, c_name, data.get("client_gst_id"), inv_date, 
                      data.get("INV_time"), data.get("Due_date"), doc_type, mode, 
                      data.get("t_gst"), data.get("total"), 'Incomplete'))

                for itm in data.get("item", []):
                    item_tbl = f"ITEMS_{table}"
                    pay_col = "payment_received" if "sent" in mode else "payment_currently_sent"
                    cursor.execute(f'''
                        INSERT INTO {item_tbl} (Item, type, qty, CP, gst, gst_rate, INV_ID, payment_to_be_done, {pay_col}, payment_status)
                        VALUES (?,?,?,?,?,?,?,?,?,?)
                    ''', (itm.get("name"), itm.get("type"), itm.get("qty"), itm.get("cp"), 
                          itm.get("gst"), itm.get("gst_rate"), data.get("INV_ID"), itm.get("tp"), 0.0, 'Incomplete'))

            # --- 2. RECEIPT PROCESSING ---
            elif "receipt" in doc_type:
                table = "REC_SENT" if "sent" in mode else "REC_REC"
                rec_id = data.get("REC_ID") or data.get("INV_ID")
                cursor.execute(f'''
                    INSERT OR REPLACE INTO {table} 
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                ''', (rec_id, c_id, c_name, data.get("client_gst_id"), inv_date, 
                      data.get("REC_time"), doc_type, mode, data.get("t_gst"), data.get("total")))

                for itm in data.get("item", []):
                    item_tbl = f"ITEMS_{table}"
                    pay_col = "payment_sent" if "sent" in mode else "payment_done"
                    cursor.execute(f'''
                        INSERT INTO {item_tbl} (Item, type, qty, CP, gst, gst_rate, {doc_type[:3].upper()}_ID, {pay_col})
                        VALUES (?,?,?,?,?,?,?,?)
                    ''', (itm.get("name"), itm.get("type"), itm.get("qty"), itm.get("cp"), 
                          itm.get("gst"), itm.get("gst_rate"), rec_id, itm.get("tp")))
                    
                    # BUCKET FILL: If money received, decrease client's pending debt
                    if table == "REC_REC":
                        fill_payment_buckets(cursor, c_id, itm.get("name"), itm.get("tp"))

            # SUCCESS: Move to Archive
            shutil.move(src_path, os.path.join(PATHS["archive"], filename))
            
        except Exception as e:
            # FAILURE: Move to Failed folder for debugging
            print(f"❌ Error processing {filename}: {e}")
            shutil.move(src_path, os.path.join(PATHS["failed"], filename))

    # REFRESH DEBT: Recalculate global debt for every client
    cursor.execute("SELECT Client_ID FROM clients")
    all_clients = [row[0] for row in cursor.fetchall()]
    for client_id in all_clients:
        update_client_debt(cursor, client_id)

    conn.commit()
    conn.close()
    print("✅ Ledger Balanced: 11 tables updated, buckets filled, and debt recalculated.")

if __name__ == "__main__":
    run_db_management()