import os
import json
import base64
import shutil
import cv2
import logging
import fitz  # PyMuPDF for portable PDF handling
import numpy as np
import io
from PIL import Image
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
from groq import Groq

# 1. INITIALIZATION & PATHS
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

PATHS = {
    "input": "data/input",
    "raw_json": "data/json_files/raw_json",
    "archive": "data/input_archive",
    "failed": "data/input_failed",
    "logs": "logs/extraction_logs"
}

for folder in PATHS.values():
    os.makedirs(folder, exist_ok=True)

# 2. DAILY AI LOGGING SETUP
log_file = os.path.join(PATHS["logs"], "extraction.log")
handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)
handler.suffix = "%Y-%m-%d"
logger = logging.getLogger("AI_Extractor")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

def get_ai_log_entry(filename, sharpness, success, dest):
    """Generates human-readable log entry via Llama 4."""
    status = "scanned successfully" if success else "failed quality check"
    instruct = "stored in archive" if success else "please reupload"
    prompt = f"Write one short human log sentence for: File {filename}, Sharpness {sharpness:.1f}, Status {status}, Action {dest}, Instruction {instruct}."
    try:
        resp = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50
        )
        return resp.choices[0].message.content.strip()
    except:
        return f"File: {filename} | Sharpness: {sharpness:.1f} | Status: {'Success' if success else 'Fail'}"

# 3. CORE EXTRACTION LOGIC
def get_sharpness(img_cv):
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def get_llama4_vision(b64_image):
    """Dual-schema extractor for Invoices and Receipts."""
    prompt = """Return ONLY a JSON object. 
    1. If Invoice: INV_ID, INV_date, INV_time, Due_date, type (received/sent), client_name, client_id (CL-XXX), client_gst_id, item: [{name, type, qty, cp, gst_rate, gst, tp}], current_mode, t_gst, total.
    2. If Receipt: REC_ID, REC_date, REC_time, type (received/sent), client_name, client_id, client_gst_id, item: [{name, type, qty, cp, gst_rate, gst, tp}], current_mode, t_gst, total.
    Use NULL for missing fields."""
    
    try:
        resp = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                ]
            }],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(resp.choices[0].message.content)
    except:
        return None

def process_single_image(img_pil, filename):
    """Handles sharpness check, AI call, and JSON saving."""
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    sharpness = get_sharpness(img_cv)
    
    if sharpness < 75:
        msg = get_ai_log_entry(filename, sharpness, False, "input_failed")
        logger.info(msg)
        print(f"⚠️ {msg}")
        return False

    # Convert PIL to Base64
    buffered = io.BytesIO()
    img_pil.save(buffered, format="JPEG")
    b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    data = get_llama4_vision(b64)
    if data:
        out_name = filename.rsplit('.', 1)[0] + ".json"
        with open(os.path.join(PATHS["raw_json"], out_name), "w") as f:
            json.dump(data, f, indent=4)
        msg = get_ai_log_entry(filename, sharpness, True, "input_archive")
        logger.info(msg)
        print(f"✅ {msg}")
        return True
    return False

def run_extractor():
    print("🚦 ERP Extractor Engine Active (PDF & Image Support)...")
    for filename in os.listdir(PATHS["input"]):
        src_path = os.path.join(PATHS["input"], filename)
        ext = filename.lower().split('.')[-1]
        
        overall_success = False

        if ext in ['png', 'jpg', 'jpeg']:
            with Image.open(src_path) as img:
                overall_success = process_single_image(img, filename)
        
        elif ext == 'pdf':
            doc = fitz.open(src_path)
            page_successes = []
            for i in range(len(doc)):
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_name = f"{filename}_page_{i+1}.jpg"
                page_successes.append(process_single_image(img, page_name))
            doc.close()
            overall_success = any(page_successes)

        # Archive or Fail routing
        if overall_success:
            shutil.move(src_path, os.path.join(PATHS["archive"], filename))
        else:
            shutil.move(src_path, os.path.join(PATHS["failed"], filename))

if __name__ == "__main__":
    run_extractor()