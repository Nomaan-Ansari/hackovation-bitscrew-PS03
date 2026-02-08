import os
import json
import time
import PIL.Image
from dotenv import load_dotenv
from google import genai
from google.genai import errors # Import this to catch the 429 error

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def analyze_document(image_path):
    img = PIL.Image.open(image_path)
    
    prompt = """
    Analyze this document. Return a JSON object ONLY:
    {
      "type": "inv_rec" | "inv_sent" | "rec_rec" | "rec_sent",
      "vendor_name": "Official Name",
      "date": "YYYY-MM-DD",
      "total": 0.00,
      "items": [{"name": "item", "qty": 1, "price": 0.00}]
    }
    """

    # We will try 3 times before giving up
    for attempt in range(3):
        try:
            # SWITCHED TO LITE for better quota
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=[prompt, img]
            )
            raw_text = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(raw_text)

        except errors.ClientError as e:
            if "429" in str(e):
                print(f"⚠️ Quota hit! Waiting 60 seconds (Attempt {attempt+1}/3)...")
                time.sleep(60) # Wait for the rolling window to reset
            else:
                print(f"❌ Other Error: {e}")
                break 
    return None