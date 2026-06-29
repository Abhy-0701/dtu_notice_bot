import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

# Import our Phase 3 search and summary tools
from core.query_engine import search_notices, summarize_notice

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing! Please check your .env file.")

# Configure logging for production monitoring
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcoming guide when a user initializes the bot."""
    welcome_text = (
        "👋 **Welcome to the DTU Notice Board Bot!**\n\n"
        "I automatically track, OCR-parse, and analyze official university notices "
        "published within the last 2 months.\n\n"
        "🔍 **How to use me:**\n"
        "1. **Search:** Just type any normal question (e.g., `Are there any exam dates out?` "
        "or `Any news about summer registration?`). I will search the vector database and return relevant links.\n"
        "2. **Summarize:** Every notice listed during a search contains a unique **Notice ID**. "
        "To read the complete details, use the summary command followed by the ID:\n"
        "   `/summary <notice_id>`"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_summary_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles explicit requests to extract full-text files and compile comprehensive summaries."""
    # Check if the user actually passed an ID parameter
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a Notice ID.\nExample: `/summary main_52a8f3a...`",
            parse_mode="Markdown"
        )
        return

    target_id = context.args[0].strip()
    await update.message.reply_text("📥 *Fetching the full document and generating summary...*", parse_mode="Markdown")
    
    # Run the direct lookup workflow from Storage A (notices.json)
    summary_response = summarize_notice(target_id)
    await update.message.reply_text(summary_response, parse_mode="Markdown")

async def handle_incoming_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Intercepts all standard text entries and treats them as semantic queries for ChromaDB."""
    user_message = update.message.text.strip()
    
    # Direct acknowledgment to manage user expectations during LLM latency
    await update.message.reply_text("🔍 *Searching recent university notices...*", parse_mode="Markdown")
    
    # Run the RAG workflow from Storage B (ChromaDB)
    search_response = search_notices(user_message)
    
    # THE FIX: If Gemini returns an empty string, provide a fallback message!
    if not search_response or not search_response.strip():
        search_response = "🤖 *I couldn't find any recent notices that directly answer that query.* Try rephrasing or using broader keywords!"
        
    await update.message.reply_text(search_response, parse_mode="Markdown")

def main():
    """Initializes and kicks off the asynchronous polling engine."""
    print("--- STARTING TELEGRAM INTERFACE LAYER ---")
    
    # Build the application container using the token
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Register command handshakes
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("summary", handle_summary_request))
    
    # Route all non-command text inputs directly to the semantic search channel
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_incoming_text))
    
    # Keep the application running, listening for server requests indefinitely
    print("[System Active] Bot is listening for incoming Telegram updates...")
    application.run_polling()

if __name__ == '__main__':
    main()