# Project Documentation: DTU Notice Board Bot

This project is an automated system designed to track, process, and provide AI-powered search/summarization for university notices via a Telegram bot.

## Project Structure

- `run_bot.py`: Entry point for the Telegram bot interface.
- `run_scraper.py`: Entry point for the automated data ingestion pipeline.
- `core/`: Core business logic modules.
  - `scraper.py`: Handles web scraping and downloading of notices.
  - `processor.py`: Handles document parsing, OCR, and database ingestion.
  - `query_engine.py`: Handles RAG (Retrieval-Augmented Generation) for search and summarization.
- `test_brain.py`: Contains test cases for core functionalities of the bot.

---

## Workflow Overview

The application operates in three main interaction modes via the Telegram bot, powered by RAG (Retrieval-Augmented Generation):

### 1. Semantic Search (`search_notices`)
- Users send plain-text queries to find relevant university notices.
- The system embeds the query and retrieves the top 5 matches from the Vector Database (ChromaDB).
- Returns a list of notices with titles, dates, and links to the original documents.

### 2. Question Answering (`answer_question`)
- Users can ask specific questions about university procedures, deadlines, or rules.
- **RAG Implementation**:
    - The engine performs an expanded search, retrieving the top 10 relevant document snippets.
    - These snippets, along with their associated metadata (like dates), are passed into Gemini 2.0-flash as context.
    - A specialized system instruction ensures the AI answers only using the provided context, acting as a DTU student counselor, while maintaining strict formatting (plain text, no Markdown).

### 3. Detailed Summarization (`summarize_notice`)
- Users request a summary of a specific notice using its unique ID.
- The engine performs a direct lookup in the `notices.json` file.
- Gemini processes the full document text to provide a structured, concise summary of key dates, deadlines, and rules, ensuring output safety for Telegram.
---

## Setup Requirements

- **Environment**: Ensure a `.env` file is present with your `TELEGRAM_BOT_TOKEN`.
- **Dependencies**: Refer to `requirements.txt` for necessary Python packages.
- **Running**:
  - To update data: `python run_scraper.py`
  - To start the bot: `python run_bot.py`