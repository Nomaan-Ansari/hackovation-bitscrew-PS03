import os
import json
import base64
import shutil
import cv2
import fitz
import numpy as np
import io
import time
from PIL import Image
from src.logger_engine import setup_daily_logger, generate_ai_log_msg
from dotenv import load_dotenv
from groq import Groq

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
extract_logger = setup_daily_logger("extraction", PATHS["logs"])

def get_sharpness(img_cv):
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    score = cv2.Laplacian(gray, cv2.CV_64F).var()
    print(f"🔍 DEBUG: Sharpness score: {score:.2f}")
    return score

def get_llama4_vision(b64_image, retries=3, delay=5):
    """
    Retries with backoff and stricter JSON instructions.
    Ensures 'N/A' is used instead of leaving fields blank to avoid 400 errors.
    """
    prompt = """Return ONLY a valid JSON object. 
    CRITICAL: Every field must have a value. Use "N/A" if a value is missing. 
    DO NOT leave a colon followed by a blank space.
    
    Fields:
    INV_ID, INV_date, INV_time, Due_date, type, client_name, client_id, client_gst_id, 
    item: [{name, type, qty, cp, gst_rate, gst, tp}], current_mode, t_gst, total."""
    
    for i in range(retries):
        try:
            resp = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                ]}],
                response_format={"type": "json_object"}, 
                temperature=0.1
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            err_str = str(e).lower()
            if "json_validate_failed" in err_str or "400" in err_str:
                print(f"⚠️ AI JSON Formatting Error (Attempt {i+1}). Retrying...")
                time.sleep(1)
            elif "503" in err_str or "over capacity" in err_str:
                print(f"⏳ Server Busy (Attempt {i+1}/{retries}). Waiting {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"❌ Error: {e}")
                break
    return None

def process_img_logic(img_pil, filename):
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    if get_sharpness(img_cv) < 30: 
        return False

    buffered = io.BytesIO()
    img_pil.save(buffered, format="JPEG")
    b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    data = get_llama4_vision(b64)
    
    # Check that we got the minimum required fields to satisfy the DB
    if data and data.get("client_name") and data.get("client_id"):
        try:
            out_name = filename.rsplit('.', 1)[0] + ".json"
            save_path = os.path.join(PATHS["raw_json"], out_name)
            with open(save_path, "w") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"❌ Failed to save JSON for {filename}: {e}")
            return False
    return False

def run_processor():
    print("🚦 Scanning data/input...")
    files = [f for f in os.listdir(PATHS["input"]) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf'))]
    
    if not files:
        print("📭 No files found to process.")
        return

    for filename in files:
        src = os.path.join(PATHS["input"], filename)
        ext = filename.lower().split('.')[-1]
        success = False
        
        print(f"🚀 Processing: {filename}")
        
        try:
            if ext in ['png', 'jpg', 'jpeg']:
                with Image.open(src) as img: 
                    success = process_img_logic(img, filename)
            elif ext == 'pdf':
                doc = fitz.open(src)
                results = []
                for i in range(len(doc)):
                    pix = doc.load_page(i).get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    results.append(process_img_logic(img, f"{filename}_p{i+1}.jpg"))
                doc.close()
                success = any(results)
        except Exception as e:
            print(f"❌ System Error processing {filename}: {e}")
        
        # Determine movement
        dest_folder = PATHS["archive"] if success else PATHS["failed"]
        shutil.move(src, os.path.join(dest_folder, filename))
        print(f"✅ Finished: {filename} moved to {dest_folder.split('/')[-1]}")

if __name__ == "__main__":
    run_processor()