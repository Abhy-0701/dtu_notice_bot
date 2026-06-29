import os
import json
import re
from pdf2image import convert_from_path
import pytesseract
import chromadb
from chromadb.utils import embedding_functions

# Configuration Paths
DB_JSON_PATH = os.path.join("data", "notices.json")
CHROMA_DIR = os.path.join("data", "chroma_db")

# Ensure the database directory exists
os.makedirs("data", exist_ok=True)

# Initialize ChromaDB Client with a persistent local directory
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

# Using a lightweight, high-performance local embedding model
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Get or create our vector search collection
collection = chroma_client.get_or_create_collection(
    name="dtu_notices",
    embedding_function=embedding_fn
)

def extract_text_from_pdf(pdf_path):
    """
    Pure OCR Extraction:
    Converts every single page of the PDF into an image and runs Tesseract.
    This guarantees that no text—whether digital or trapped in an image—is ever skipped.
    """
    print(f"   [OCR] Converting all pages to images for: {os.path.basename(pdf_path)}")
    try:
        # Convert the entire PDF into a list of high-res images
        images = convert_from_path(pdf_path)
        ocr_text = ""
        
        # Read the text straight out of the pixels for every page
        for i, img in enumerate(images):
            page_text = pytesseract.image_to_string(img)
            ocr_text += f"\n--- Page {i+1} ---\n" + page_text
            
        return ocr_text.strip()
        
    except Exception as e:
        print(f"   [OCR Error] Severe failure processing images for {pdf_path}: {e}")
        return ""

def clean_text(text):
    """Removes excessive whitespace and structural noise from OCR text output."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text, words_per_chunk=100, overlap=20):
    """Splits full text into ~100 word chunks with a 20-word overlap for context preservation."""
    words = text.split()
    chunks = []
    
    if len(words) <= words_per_chunk:
        return [" ".join(words)]
        
    i = 0
    while i < len(words):
        chunk_words = words[i:i + words_per_chunk]
        chunks.append(" ".join(chunk_words))
        i += (words_per_chunk - overlap)
        
    return chunks

def save_to_full_text_db(notice_metadata, full_text):
    """Storage A: Saves the complete, unmodified text to a single master JSON file."""
    db = {}
    if os.path.exists(DB_JSON_PATH):
        try:
            with open(DB_JSON_PATH, 'r', encoding='utf-8') as f:
                db = json.load(f)
        except Exception:
            db = {}
            
    # Add complete data map to the unique notice record
    db[notice_metadata['notice_id']] = {
        "date": notice_metadata['date'],
        "title": notice_metadata['title'],
        "section": notice_metadata['section'],
        "url": notice_metadata['url'],
        "full_text": full_text
    }
    
    with open(DB_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def save_to_vector_db(notice_metadata, chunks):
    """Storage B: Embeds text chunks and uploads them into ChromaDB for semantic search queries."""
    documents = []
    metadatas = []
    ids = []
    
    for idx, chunk in enumerate(chunks):
        documents.append(chunk)
        ids.append(f"{notice_metadata['notice_id']}_chunk_{idx}")
        metadatas.append({
            "notice_id": notice_metadata['notice_id'],
            "date": notice_metadata['date'],
            "section": notice_metadata['section'],
            "url": notice_metadata['url']
        })
        
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

def process_and_ingest(new_notices_list):
    """Loops over downloaded files, extracts text, populates dual databases, and deletes temp PDFs."""
    if not new_notices_list:
        print("\n--- ENGINE 2: No new notices to process. ---")
        return

    print(f"\n--- ENGINE 2: Processing {len(new_notices_list)} new documents ---")
    
    for notice in new_notices_list:
        pdf_path = notice['file_path']
        
        if not os.path.exists(pdf_path):
            print(f"   [Error] File not found at path: {pdf_path}")
            continue

        # 1. Extract complete text using pure OCR
        raw_text = extract_text_from_pdf(pdf_path)
        if not raw_text:
            print(f"   [Skipped] No text could be parsed from: {notice['notice_id']}")
            continue
            
        cleaned = clean_text(raw_text)
        
        # 2. Populate Storage A: Full text for high-fidelity summaries
        save_to_full_text_db(notice, cleaned)
        
        # 3. Slice text into semantic fragments
        chunks = chunk_text(cleaned)
        
        # 4. Populate Storage B: Vectors for intent match search
        save_to_vector_db(notice, chunks)
        print(f"   [Success] Ingested and chunked: {notice['notice_id']}")
        
        # 5. Housekeeping: Remove local PDF file to save workspace storage
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            
    print("--- ENGINE 2 COMPLETE: Databases updated and synchronized ---")