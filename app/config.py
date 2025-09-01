#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./news_scraper.db")

    #SMTP Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")

    N_ARTICLES: int = int(os.getenv("N_ARTICLES", "10"))
    APP_TIMEZONE: str = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "local-dev-secret-key")

    #Indian Express Categories
    CATEGORIES = {
        "india": "https://indianexpress.com/section/india/",
        "politics": "https://indianexpress.com/section/political-pulse/",
        "sports": "https://indianexpress.com/section/sports/",
        "technology": "https://indianexpress.com/section/technology/",
        "business": "https://indianexpress.com/section/business/",
        "world": "https://indianexpress.com/section/world/",
        "explained": "https://indianexpress.com/section/explained/",
        "lifestyle": "https://indianexpress.com/section/lifestyle/",
        "opinion": "https://indianexpress.com/section/opinion/",
        "cities": "https://indianexpress.com/section/cities/"
    }

    #Scraping Configuration
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    REQUEST_DELAY: float = 1.0  #Delay between requests in seconds

    #PDF Configuration
    PDF_OPTIONS = {
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'no-outline': None
    }

settings = Settings()