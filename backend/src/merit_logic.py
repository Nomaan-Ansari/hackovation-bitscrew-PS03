from src.database_manager import get_conn
from datetime import datetime

def apply_merit_change(entity_id, amount, reason):
    """Updates the master score and logs the specific reason in the audit trail."""
    conn = get_conn()
    cursor = conn.cursor()
    
    # 1. Update Master Score (Table #9)
    cursor.execute("UPDATE entity_master SET merit = merit + ? WHERE id = ?", (amount, entity_id))
    
    # 2. Log the Trail (Table #11)
    cursor.execute("""
        INSERT INTO merit_audit_trail (entity_id, change, reason, timestamp)
        VALUES (?, ?, ?, ?)
    """, (entity_id, amount, reason, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def check_administrative_merit(entity_id, error_found=False):
    """Implements the $1, 2, 2, 3, 5 penalty logic for streaks of errors."""
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT streak FROM entity_master WHERE id = ?", (entity_id,))
    res = cursor.fetchone()
    streak = res[0] if res else 0
    
    if error_found:
        new_streak = streak + 1
        # Penalty progression: -1, -2, -2, -3, -5
        penalty = -1 if new_streak == 1 else -2 if new_streak <= 3 else -3 if new_streak == 4 else -5
        
        cursor.execute("UPDATE entity_master SET streak = ? WHERE id = ?", (new_streak, entity_id))
        conn.commit()
        conn.close()
        apply_merit_change(entity_id, penalty, f"Administrative error (Streak {new_streak})")
    else:
        # Reset streak on a perfect scan
        cursor.execute("UPDATE entity_master SET streak = 0 WHERE id = ?", (entity_id,))
        conn.commit()
        conn.close()