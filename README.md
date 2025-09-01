# News PDF Scraper

A Python web application that scrapes Indian Express articles, summarizes them using AI, and generates PDFs with email delivery functionality.

## Features

- **Web Scraping**: Scrapes articles from Indian Express website across multiple categories
- **AI Summarization**: Uses OpenAI GPT or local Sumy library for article summaries
- **PDF Generation**: Creates clean, formatted PDF reports using pdfkit
- **Email Delivery**: Sends PDFs via SMTP
- **Subscription System**: Users can subscribe for daily email delivery
- **Caching**: Avoids re-processing articles with caching

## Installation

### Prerequisites

1. **Python 3.10+**
2. **wkhtmltopdf** (for PDF generation)

#### Installing wkhtmltopdf

**Windows:**
Download from: https://wkhtmltopdf.org/downloads.html

**Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install wkhtmltopdf
```

### Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd news-pdf-scraper
```

2. **Create virtual environment:**
```bash
python -m venv venv
venv\Scripts\activate  # Or source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database:**
```bash
python db_init.py
```

6. **Start the application:**
```bash
uvicorn app.main:app --reload --port 8000
```

7. **Open in browser:**
```
http://localhost:8000
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with these settings:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for summarization | No (uses Sumy if not available) |
| `SMTP_HOST` | SMTP server (default: smtp.gmail.com) | Yes (for email) |
| `SMTP_PORT` | SMTP port (default: 587) | Yes (for email) |
| `SMTP_USER` | Your email address | Yes (for email) |
| `SMTP_PASS` | Email app password | Yes (for email) |
| `N_ARTICLES` | Articles per category (default: 10) | No |

### Gmail Setup
1. Enable 2-Factor Authentication
2. Generate App Password for mail
3. Use app password in `SMTP_PASS`

## 🎯 Usage

### Dashboard Operations

1. **Generate PDF:**
   - Select categories or leave empty for all
   - Choose number of articles per category
   - Enter email for immediate delivery

2. **Subscribe for Daily Delivery:**
   - Enter email address
   - Select delivery time
   - Choose categories

3. **Manage Subscribers:**
   - Visit `/subscribers` page
   - Send immediate PDFs or unsubscribe users

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard page |
| `/generate` | POST | Generate PDF |
| `/download/{filename}` | GET | Download PDF |
| `/subscribe` | POST | Create subscription |
| `/subscribers` | GET | Subscribers page |
| `/unsubscribe` | POST | Remove subscription |
| `/send_now/{id}` | POST | Manual delivery |
