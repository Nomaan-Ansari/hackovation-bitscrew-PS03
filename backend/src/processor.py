from src.database_manager import save_audit_package, get_conn
from src.merit_logic import check_administrative_merit, apply_merit_change
from src.extractor import analyze_document  # Import the extractor!

def process_scanned_document(file_path):
    """The central coordinator that links Audit, Buckets, and Merit."""
    
    print(f"🔍 AI Processor analyzing: {file_path}")
    
    # 1. EXTRACT DATA (Call the AI)
    ai_json_result = analyze_document(file_path)
    
    if not ai_json_result:
        print(f"❌ Failed to extract data from {file_path}")
        return # Stop if extraction failed

    # 2. Save Audit & Open Buckets
    save_audit_package(ai_json_result)
    
    # Handle Vendor/Client Name
    entity_name = ai_json_result.get('vendor_name') or ai_json_result.get('client_name')
    if not entity_name:
        entity_name = "Unknown Entity"

    conn = get_conn()
    cursor = conn.cursor()
    
    # Ensure entity exists in Master Registry
    cursor.execute("INSERT OR IGNORE INTO entity_master (name) VALUES (?)", (entity_name,))
    conn.commit()
    
    # Get Entity ID
    res = cursor.execute("SELECT id FROM entity_master WHERE name = ?", (entity_name,)).fetchone()
    entity_id = res[0] if res else None
    conn.close()

    if entity_id:
        # 3. Administrative Audit (Confidence check)
        confidence = ai_json_result.get('confidence_score', 100)
        check_administrative_merit(entity_id, error_found=(confidence < 90))
        
        # 4. Fulfillment Reward
        apply_merit_change(entity_id, 1, "New document processed successfully")