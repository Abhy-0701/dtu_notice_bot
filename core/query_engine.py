import os
import json
import chromadb
from chromadb.utils import embedding_functions
from google import genai
from google.genai import errors
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing! Please add it to your .env file.")

# Initialize Gemini Client
client = genai.Client(api_key=API_KEY)

# Configuration Paths
DB_JSON_PATH = os.path.join("data", "notices.json")
CHROMA_DIR = os.path.join("data", "chroma_db")

# 1. Connect to ChromaDB (Storage B for Search)
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
collection = chroma_client.get_collection(
    name="dtu_notices",
    embedding_function=embedding_fn
)

def format_date(date_int):
    """Converts 20260625 into 2026-06-25 for easier reading."""
    d_str = str(date_int)
    if len(d_str) == 8:
        return f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
    return d_str

def search_notices(user_query):
    """
    RAG Search Workflow:
    1. Embeds the user query and pulls top matches from ChromaDB.
    2. Returns a list of notices with their metadata.
    """
    try:
        results = collection.query(
            query_texts=[user_query],
            n_results=5 
        )
        
        retrieved_metadata = results['metadatas'][0] if results['metadatas'] else []
        
        if not retrieved_metadata:
            return None

        # Open Storage A so we can look up the titles
        with open(DB_JSON_PATH, 'r', encoding='utf-8') as f:
            full_db = json.load(f)

        formatted_notices = []
        for meta in retrieved_metadata:
            date_str = format_date(meta['date'])
            notice_id = meta['notice_id']
            
            raw_title = full_db.get(notice_id, {}).get("title", "Official Notice")
            clean_title = raw_title.replace("_", " ").replace("*", "").replace("`", "").replace("[", "").replace("]", "")
            
            formatted_notice = (
                f"📌 **{clean_title}**\n"
                f"Section: {meta['section']} | Date: {date_str} | ID: `{notice_id}`\n"
                f"[Open Document]({meta['url']})"
            )
            formatted_notices.append((formatted_notice, notice_id))
            
        return formatted_notices
            
    except Exception as e:
        return f"Error during search: {str(e)}"

def summarize_notice(notice_id):
    """
    Direct Lookup Workflow:
    1. Grabs the complete document from Storage A (notices.json).
    2. Asks Gemini to provide a structured summary without breaking Markdown.
    3. Sanitizes the output to prevent Telegram crashes.
    """
    try:
        if not os.path.exists(DB_JSON_PATH):
            return "The notice database is currently empty."
            
        with open(DB_JSON_PATH, 'r', encoding='utf-8') as f:
            db = json.load(f)
            
        if notice_id not in db:
            return f"Sorry, I couldn't find a notice with the ID: {notice_id}"
            
        notice_data = db[notice_id]
        full_text = notice_data['full_text']
        date_str = format_date(notice_data['date'])
        
        # Strict System Prompt forbidding dangerous Markdown characters
        system_instruction = (
            "You are a helpful college assistant. Your job is to read the provided official "
            "notice and summarize it clearly for a student. Extract key dates, deadlines, and rules.\n\n"
            "CRITICAL FORMATTING RULES:\n"
            "1. Use standard hyphens (-) for bullet points.\n"
            "2. DO NOT use asterisks (*) for bolding or bullet points.\n"
            "3. DO NOT use underscores (_) anywhere in your response.\n"
            "4. Keep the text clean, plain, and professional."
        )
        
        prompt = (
            f"Please summarize this notice.\n"
            f"Title: {notice_data['title']}\n"
            f"Date: {date_str}\n"
            f"Section: {notice_data['section']}\n"
            f"Full Text:\n{full_text}"
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={"system_instruction": system_instruction}
        )
        
        # PYTHON SANITIZATION: Forcefully strip any rogue characters Gemini tried to sneak in
        safe_summary = response.text.replace("_", "-").replace("*", "").replace("`", "'")
        
        # Prepend the official link (Removed the double asterisks from the link formatting!)
        final_output = f"📄 [Open Original Document]({notice_data['url']})\n\n{safe_summary}"
        return final_output
        
    except Exception as e:
        return f"Error generating summary: {str(e)}"