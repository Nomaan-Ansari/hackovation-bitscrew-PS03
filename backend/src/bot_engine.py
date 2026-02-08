import os
import time
from groq import Groq
from dotenv import load_dotenv
from src.database_manager import get_conn
from src.market_watcher import get_inflation_rate

load_dotenv()

# Initialize Groq Client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_db_schema():
    """Reads the database structure."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    return "\n".join([t[0] for t in tables if t[0] is not None])

def get_code_context():
    """Reads key logic files."""
    files_to_read = ['src/merit_logic.py', 'src/analyzer.py', 'src/logic_gate.py']
    context = ""
    for fname in files_to_read:
        if os.path.exists(fname):
            with open(fname, 'r', encoding='utf-8') as f:
                context += f"\n--- {fname} ---\n{f.read()}\n"
    return context

def ask_financial_bot(user_query, chat_history):
    """
    Master Bot Function using Groq (Llama 3.3).
    """
    try:
        # 1. GATHER CONTEXT
        schema = get_db_schema()
        code_logic = get_code_context()
        inflation = get_inflation_rate()
        
        # 2. SYSTEM PROMPT
        system_prompt = f"""
        You are the AI Financial Controller for this Micro-ERP system.
        
        [YOUR KNOWLEDGE BASE]
        1. **Live Market Data**: Current Inflation Rate is {inflation}%.
        2. **Database Schema**: 
        {schema}
        3. **System Logic (Python Code)**:
        {code_logic}
        
        [YOUR CAPABILITIES]
        - Analyze the DB schema to answer questions about debts/invoices.
        - Explain the 'Merit System' (Fibonacci penalties).
        - Check fair pricing using inflation rates.
        - Generate SQL queries for SQLite if asked.
        
        Answer concisely and professionally.
        """
        
        # 3. PREPARE MESSAGES
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history (Groq format)
        if chat_history:
            for msg in chat_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current query
        messages.append({"role": "user", "content": user_query})

        # 4. CALL GROQ (UPDATED MODEL NAME HERE)
        response = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile", # <--- CHANGED THIS
        )
        
        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Groq Error: {e}"