import os
import logging
from logging.handlers import TimedRotatingFileHandler
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def setup_daily_logger(name, folder):
    """Sets up a specific rolling logger for different pipeline streams."""
    os.makedirs(folder, exist_ok=True)
    log_file = os.path.join(folder, f"{name}.log")
    
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def generate_ai_log_msg(filename, status_msg, action_taken):
    """Uses AI to summarize complex events into audit sentences."""
    prompt = f"Context: Financial Audit. File: {filename}. Status: {status_msg}. Action: {action_taken}. Task: Write 1 professional sentence."
    try:
        resp = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50, temperature=0.3
        )
        return resp.choices[0].message.content.strip()
    except:
        return f"AUDIT | {filename} | {status_msg} | {action_taken}"