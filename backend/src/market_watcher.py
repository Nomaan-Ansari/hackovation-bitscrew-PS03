import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_inflation_rate():
    """Fetches current inflation data using your RapidAPI key."""
    url = "https://cpi-inflation-calculator.p.rapidapi.com/inflation" # Example API URL
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
        "X-RapidAPI-Host": "cpi-inflation-calculator.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        return data.get('rate', 4.0) # Default to 4.0 if API fails
    except Exception as e:
        print(f"❌ RapidAPI Error: {e}")
        return 4.0