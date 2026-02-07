import os
import json
import sqlite3
import shutil
import uuid
from thefuzz import fuzz
from src.logger_engine import setup_daily_logger, generate_ai_log_msg

PATHS = {
    "raw": "data/json_files/raw_json",
    "typo_fixed": "data/json_files/typo_json",
    "check_json": "data/json_files/typo_checking_needed_json",
    "fraud_json": "data/json_files/potential_typo_fraud_json",
    "db": "database/engine_master.db",
    "fraud_logs": "logs/fraud_logs",
    "check_logs": "logs/checking_logs"
}

fraud_logger = setup_daily_logger("fraud", PATHS["fraud_logs"])
check_logger = setup_daily_logger("checking", PATHS["check_logs"])

def process_sync_pipeline():
    conn = sqlite3.connect(PATHS["db"])
    cursor = conn.cursor()
    raw_files = [f for f in os.listdir(PATHS["raw"]) if f.endswith('.json')]
    
    for filename in raw_files:
        path = os.path.join(PATHS["raw"], filename)
        with open(path, 'r') as f: data = json.load(f)
        
        c_id, c_name = str(data.get("client_id", "")).strip(), str(data.get("client_name", "")).strip()
        forbidden = ["N/A", "UNKNOWN", "NONE", "", "NULL"]

        # Logic: Both missing -> Fraud
        if c_name.upper() in forbidden and c_id.upper() in forbidden:
            shutil.move(path, os.path.join(PATHS["fraud_json"], filename))
            fraud_logger.warning(generate_ai_log_msg(filename, "Identity Missing", "Moved to Fraud"))
            continue

        # Healing: Name exists, ID missing -> Generate New
        if c_name.upper() not in forbidden and c_id.upper() in forbidden:
            cursor.execute("SELECT Client_ID FROM clients WHERE Client_name = ?", (c_name,))
            row = cursor.fetchone()
            if row: data["client_id"] = row[0]
            else:
                new_id = f"CL-{uuid.uuid4().hex[:6].upper()}"
                cursor.execute("INSERT INTO clients (Client_ID, Client_name) VALUES (?, ?)", (new_id, c_name))
                conn.commit()
                data["client_id"] = new_id
            shutil.move(path, os.path.join(PATHS["typo_fixed"], filename))
            continue

        # Standard check
        cursor.execute("SELECT Client_name FROM clients WHERE Client_ID = ?", (c_id,))
        row = cursor.fetchone()
        if row:
            similarity = fuzz.ratio(c_name.lower(), row[0].lower())
            if (100 - similarity) > 15:
                shutil.move(path, os.path.join(PATHS["check_json"], filename))
                check_logger.info(generate_ai_log_msg(filename, "Typo Found", f"{100-similarity}% error"))
            else:
                data["client_name"] = row[0]
                with open(os.path.join(PATHS["typo_fixed"], filename), 'w') as f: json.dump(data, f, indent=4)
                os.remove(path)
        else:
            cursor.execute("INSERT INTO clients (Client_ID, Client_name) VALUES (?, ?)", (c_id, c_name))
            conn.commit()
            shutil.move(path, os.path.join(PATHS["typo_fixed"], filename))
    
    conn.close()