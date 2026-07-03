# Project Documentation: DTU Notice Board Bot

This project is an automated system designed to track, process, and provide AI-powered search/summarization for university notices via a Telegram bot.

## Project Structure

- `run_bot.py`: Entry point for the Telegram bot interface.
- `run_scraper.py`: Entry point for the automated data ingestion pipeline.
- `core/`: Core business logic modules.
  - `scraper.py`: Handles web scraping and downloading of notices.
  - `processor.py`: Handles document parsing, OCR, and database ingestion.
  - `query_engine.py`: Handles RAG (Retrieval-Augmented Generation) for search and summarization.

---

## Workflow Overview

The application operates in two distinct workflows:

### 1. Data Ingestion Pipeline (`run_scraper.py`)
This workflow is typically triggered on a schedule to keep the bot's knowledge base current.

1.  **Discovery (`core/scraper.py`)**: The script crawls the university notice board to identify and download new files.
2.  **Processing & Indexing (`core/processor.py`)**: 
    - The downloaded files are parsed (utilizing OCR where necessary).
    - Data is stored in two formats:
        - **Full-text storage**: A JSON file for quick record retrieval.
        - **Vector Database**: An index (ChromaDB) created to support semantic search.

### 2. User Interaction (`run_bot.py`)
This workflow runs as a persistent service listening for updates from Telegram.

1.  **Semantic Search**:
    - Users send plain-text queries to the bot.
    - `run_bot.py` triggers `core/query_engine.py:search_notices()`.
    - The engine performs a semantic search against the Vector Database and returns relevant notice information.
2.  **Detailed Summarization**:
    - Users request a summary of a specific notice using the `/summary <notice_id>` command.
    - `run_bot.py` triggers `core/query_engine.py:summarize_notice()`.
    - The engine retrieves the full document record and generates a concise summary.

---

## Setup Requirements

- **Environment**: Ensure a `.env` file is present with your `TELEGRAM_BOT_TOKEN`.
- **Dependencies**: Refer to `requirements.txt` for necessary Python packages.
- **Running**:
  - To update data: `python run_scraper.py`
  - To start the bot: `python run_bot.py`
