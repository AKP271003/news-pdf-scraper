#!/usr/bin/env python3
import hashlib
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def normalize_url(url: str) -> str:
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url)
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        '',  #params
        '',  #query
        ''   #fragment
    ))

    return normalized.rstrip('/')

def calculate_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def clean_text(text: str) -> str:
    if not text:
        return ""

    #Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    #Remove common HTML elements
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")

    #Remove extra spaces around punctuation
    text = re.sub(r'\s+([.!?,:;])', r'\1', text)

    return text.strip()

def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_time_format(time_str: str) -> bool:
    try:
        hour, minute = map(int, time_str.split(':'))
        return 0 <= hour <= 23 and 0 <= minute <= 59
    except (ValueError, AttributeError):
        return False

def ensure_directory_exists(directory_path: str):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
        logger.info(f"Created directory: {directory_path}")

def safe_filename(filename: str) -> str:
    #Remove or replace invalid characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_name = re.sub(r'\s+', '_', safe_name)
    safe_name = safe_name.strip('._')

    if len(safe_name) > 200:
        safe_name = safe_name[:200]

    return safe_name or 'file'

def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    if not text or len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix

def parse_categories(categories_input) -> List[str]:
    if isinstance(categories_input, list):
        return categories_input

    if isinstance(categories_input, str):
        try:
            import json
            return json.loads(categories_input)
        except json.JSONDecodeError:
            return [cat.strip() for cat in categories_input.split(',') if cat.strip()]

    return []

def get_time_ago(timestamp: datetime) -> str:
    if not timestamp:
        return "Unknown"

    now = datetime.utcnow()
    diff = now - timestamp

    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"

class RateLimiter:

    def __init__(self, max_calls: int = 10, time_window: int = 60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []

    def can_proceed(self) -> bool:
        now = datetime.now()

        #Remove old calls
        self.calls = [call_time for call_time in self.calls 
                     if (now - call_time).seconds < self.time_window]

        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True

        return False

    def reset(self):
        self.calls = []

openai_rate_limiter = RateLimiter(max_calls=50, time_window=60)
