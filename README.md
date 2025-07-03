# NITC Chatbot - powered by FOSSCell Wiki

A Python-based chatbot that can answer questions about NIT Calicut using scraped wiki data. The project includes a web scraper to collect wiki pages and an AI-powered chatbot to provide intelligent responses.

## Features

- **Wiki Scraper**: Asynchronously scrapes FOSSCELL wiki pages (oldid 1-2606)
- **AI Chatbot**: Uses AI-generated keywords to find relevant wiki pages and provide answers
- **Web Interface**: Optional web-based chat interface
- **Smart Search**: Weighted keyword matching for better search results

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd wiki-scrap
```

### 2. Create a Virtual Environment

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Linux/macOS:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

### 4. Run the Chatbot

The chatbot uses pre-scraped wiki data stored in `wiki_data.json`. To start the chatbot:

```bash
python chatbot.py
```

This will start an interactive chat session where you can ask questions about FOSSCELL.

## Scraping Your Own Data

If you want to scrape the wiki data yourself or update the existing data:

### 1. Modify the Scraper (Optional)

Open `scraper.py` and modify the `end_oldid` value on line 30:

```python
# Change from 2606 to your desired end page
self.end_oldid = 2606  # Modify this value
```

### 2. Run the Scraper

```bash
python scraper.py
```

**Note**: The scraper will:
- Start from where it left off if interrupted
- Save progress every 50 pages
- Use concurrent requests for faster scraping
- Create/update `wiki_data.json` with scraped content

### 3. Filter Irrelevant Pages (Optional)

After scraping, you may want to remove irrelevant pages like "Module:" pages and "Terms of Service" pages:

```bash
python removeTitles.py
```

When prompted, enter the text to filter out:
- Enter `Module:` to remove all pages starting with "Module:"
- Enter `Terms of Service` to remove terms of service pages
- You can run this multiple times to remove different types of irrelevant pages

### 4. Scraping Progress

The scraper shows real-time progress:
- Current batch being processed
- Pages collected so far
- Progress percentage
- Any errors encountered

You can stop the scraper anytime with `Ctrl+C` and resume later - it will continue from where it left off.

## Project Structure

```
wiki-scrap/
├── chatbot.py          # Main chatbot application
├── scraper.py          # Wiki scraper
├── removeTitles.py     # Filter irrelevant pages
├── requirements.txt    # Python dependencies
├── wiki_data.json     # Scraped wiki data
├── README.md          # This file
└── .venv/             # Virtual environment (created during setup)
```

## Dependencies

Key dependencies include:
- `aiohttp`: Asynchronous HTTP client for scraping
- `beautifulsoup4`: HTML parsing
- `requests`: HTTP requests for AI API
- `json`: Data serialization

See `requirements.txt` for the complete list.

## Troubleshooting

### Common Issues

1. **Virtual Environment Not Activated**
   - Make sure you see `(.venv)` in your terminal prompt
   - Run `source .venv/bin/activate` (Linux/macOS) or `.venv\Scripts\activate` (Windows)

2. **Missing Dependencies**
   - Ensure you've run `pip install -r requirements.txt`
   - Check that your virtual environment is activated

3. **Wiki Data Not Found**
   - Run the scraper first: `python scraper.py`
   - Ensure `wiki_data.json` exists in the project directory

4. **Scraping Errors**
   - The scraper handles network errors gracefully
   - It will continue from where it left off if interrupted
   - Check your internet connection

### Getting Help

If you encounter issues:
1. Check that all dependencies are installed
2. Ensure your virtual environment is activated
3. Verify that `wiki_data.json` exists (run scraper if needed)
4. Check the console output for error messages

## Contributing

We welcome contributions to make this project better!

### Goals for Contributors
[  ] **Run the AI Locally**: Replace the current remote AI API with a local AI model for keyword extraction and response generation.

[  ] **Better Web Interface**: Improve or redesign the web interface for a more user-friendly and interactive experience.

If you have ideas, bug fixes, or improvements, feel free to open a Pull Request (PR)!

**PRs are welcome!**
