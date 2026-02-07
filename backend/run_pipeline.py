import os
import sys
import time

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_PATH)
sys.path.insert(0, os.path.join(BASE_PATH, "src"))

try:
    from image_processor import run_processor
    from database_sync import process_sync_pipeline
except ImportError as e:
    print(f"❌ Critical Import Error: {e}")
    sys.exit(1)

def main():
    print("🚀 Starting Financial Audit Pipeline...")
    run_processor()
    print("🔄 Running Typo Sentinel & DB Sync...")
    process_sync_pipeline()
    print("✨ Process Complete.")

if __name__ == "__main__":
    main()