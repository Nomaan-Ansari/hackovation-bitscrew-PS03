import os
import logging
from logging.handlers import TimedRotatingFileHandler
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def setup_daily_logger(name, folder):
    """Sets up a rolling logger that creates a new file every midnight."""
    os.makedirs(folder, exist_ok=True)
    log_file = os.path.join(folder, f"{name}.log")
    
    # Keeps logs for 30 days before rotating
    handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)
    handler.suffix = "%Y-%m-%d"
    
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def generate_ai_log_msg(filename, status_msg, action_taken):
    """
    Uses Llama 4 Scout to summarize complex pipeline events into 
    simple human-readable audit sentences.
    """
    prompt = (
        f"Context: Financial Audit Pipeline. "
        f"File: {filename}. Status: {status_msg}. Action: {action_taken}. "
        f"Task: Write a 1-sentence professional log entry."
    )
    
    try:
        resp = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.3
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        # Fallback if the AI is over capacity
        return f"AUDIT | File: {filename} | Status: {status_msg} | Action: {action_taken}"