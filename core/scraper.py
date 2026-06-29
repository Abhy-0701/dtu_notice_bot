import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dateutil import parser as date_parser

# Configuration
MAIN_URL = "https://www.dtu.ac.in/"
EXAM_URL = "https://exam.dtu.ac.in/"
TRUE_EXAM_URL = "https://exam.dtu.ac.in/result.htm"

TEMP_PDF_DIR = os.path.join("data", "temp_pdfs")
DB_JSON_PATH = os.path.join("data", "notices.json")

# Ensure our temporary holding zone exists
os.makedirs(TEMP_PDF_DIR, exist_ok=True)

def get_2_month_cutoff():
    """Calculates the integer date cutoff (YYYYMMDD) exactly 60 days ago from today."""
    cutoff_datetime = datetime.now() - timedelta(days=60)
    return int(cutoff_datetime.strftime("%Y%m%d"))

def parse_clean_date(date_str):
    """Converts messy website strings into clean YYYYMMDD integers."""
    try:
        clean_str = date_str.strip().replace('.', '-').replace('/', '-')
        parsed_dt = date_parser.parse(clean_str, dayfirst=True)
        return int(parsed_dt.strftime("%Y%m%d"))
    except Exception:
        return int(datetime.now().strftime("%Y%m%d"))

def notice_already_processed(notice_id):
    """
    Checks Storage A (JSON) to see if we've already ingested this notice.
    This prevents duplicate downloads and wasted processing power.
    """
    if not os.path.exists(DB_JSON_PATH):
        return False
        
    try:
        with open(DB_JSON_PATH, 'r', encoding='utf-8') as f:
            db = json.load(f)
            return notice_id in db
    except Exception:
        return False

def download_pdf(url, target_path):
    """Downloads a PDF cleanly without overflowing RAM."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url, headers=headers, stream=True, timeout=15)
        r.raise_for_status()
        with open(target_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"   [Error] Download failed for {url}: {e}")
        return False

def fetch_new_notices():
    """
    The main Engine 1 workflow. 
    Returns a list of dictionaries containing metadata for all NEW downloads.
    """
    cutoff_date = get_2_month_cutoff()
    new_downloads = []
    
    print(f"--- ENGINE 1: Fetching notices from {cutoff_date} to Today ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # 1. SCRAPE MAIN SITE
    try:
        response = requests.get(MAIN_URL, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tabs = {"tab1": "Notices", "tab2": "Jobs", "tab3": "Tenders", "tab4": "Latest News", "tab5": "Forthcoming Events"}
        
        for tab_id, tab_name in tabs.items():
            tab_container = soup.find('div', id=tab_id)
            if not tab_container:
                continue
                
            for notice in tab_container.find_all('li'):
                link_tag = notice.find('a', class_='colr')
                date_tag = notice.find('i')
                
                if link_tag and link_tag.get('href') and link_tag['href'].lower().endswith('.pdf'):
                    title = link_tag.text.strip()
                    raw_date = date_tag.text.strip() if date_tag else ""
                    date_int = parse_clean_date(raw_date)
                    
                    if date_int < cutoff_date:
                        continue
                        
                    full_link = MAIN_URL + link_tag['href'].strip('./')
                    notice_id = f"main_{hashlib.md5(full_link.encode('utf-8')).hexdigest()}"
                    
                    if notice_already_processed(notice_id):
                        continue
                        
                    local_path = os.path.join(TEMP_PDF_DIR, f"{notice_id}.pdf")
                    print(f" [NEW] Downloading: {title[:40]}... ({date_int})")
                    
                    if download_pdf(full_link, local_path):
                        new_downloads.append({
                            "notice_id": notice_id,
                            "date": date_int,
                            "title": title,
                            "section": tab_name,
                            "url": full_link,
                            "file_path": local_path
                        })
    except Exception as e:
        print(f"Main Site Error: {e}")

    # 2. SCRAPE EXAM SITE
    try:
        response = requests.get(TRUE_EXAM_URL, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        main_table = soup.find('table', id='AutoNumber1')
        
        if main_table:
            for row in main_table.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue
                    
                exam_type = cols[0].text.strip()
                if exam_type in ["EXAM.", "", "Internal Assessment", "Result"]:
                    continue
                    
                date_int = parse_clean_date(cols[3].text.strip())
                if date_int < cutoff_date:
                    continue
                    
                for link in cols[1].find_all('a'):
                    if link.get('href'):
                        title = link.text.strip()
                        full_link = EXAM_URL + link['href'].strip('./')
                        notice_id = f"exam_{hashlib.md5(full_link.encode('utf-8')).hexdigest()}"
                        
                        if notice_already_processed(notice_id):
                            continue
                            
                        local_path = os.path.join(TEMP_PDF_DIR, f"{notice_id}.pdf")
                        print(f" [NEW] Downloading Exam Result: {title[:40]}... ({date_int})")
                        
                        if download_pdf(full_link, local_path):
                            new_downloads.append({
                                "notice_id": notice_id,
                                "date": date_int,
                                "title": title,
                                "section": f"Exam - {exam_type}",
                                "url": full_link,
                                "file_path": local_path
                            })
    except Exception as e:
        print(f"Exam Site Error: {e}")

    print(f"--- ENGINE 1 COMPLETE: {len(new_downloads)} new PDFs ready for processing ---")
    return new_downloads

if __name__ == "__main__":
    # Test run
    fetched = fetch_new_notices()