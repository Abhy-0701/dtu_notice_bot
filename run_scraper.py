# run_scraper.py (Save this in your main NoticeBot_2 folder)
from core.scraper import fetch_new_notices
from core.processor import process_and_ingest

if __name__ == "__main__":
    # Step 1: Engine 1 discovers and downloads new files
    new_downloads = fetch_new_notices()
    
    # Step 2: Engine 2 parses OCR, builds vector space, and updates full-text records
    process_and_ingest(new_downloads)
    
    print("\n[System Initialization Log] Update cycle successfully closed.")