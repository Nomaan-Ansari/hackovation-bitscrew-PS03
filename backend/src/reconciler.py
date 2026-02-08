from src.database_manager import get_conn

def pour_into_bucket(inv_id, item_name, qty_received):
    """Fills the 'Payment Due' buckets when a receipt/invoice arrives."""
    conn = get_conn()
    cursor = conn.cursor()
    
    # 1. Look for the item in our 'Due' tracker
    cursor.execute("SELECT qty_due, qty_paid FROM due_rec WHERE inv_id = ? AND item = ?", (inv_id, item_name))
    result = cursor.fetchone()
    
    if result:
        qty_due, qty_paid = result
        new_paid = qty_paid + qty_received
        
        # 2. Update the bucket
        cursor.execute("UPDATE due_rec SET qty_paid = ? WHERE inv_id = ? AND item = ?", (new_paid, inv_id, item_name))
        
        # 3. Check if 'Paid' equals 'Due' to mark as COMPLETED
        if new_paid >= qty_due:
            print(f"✓ Item {item_name} fully settled!")
            
    conn.commit()
    conn.close()