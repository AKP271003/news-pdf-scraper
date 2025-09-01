#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import time
import hashlib
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import logging
from app.config import settings

#Setup logging
logger = logging.getLogger(__name__)

class IndianExpressScraper:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def get_category_articles(self, category: str, limit: int = None) -> List[Dict]:
        if limit is None:
            limit = settings.N_ARTICLES

        category_url = settings.CATEGORIES.get(category)
        if not category_url:
            logger.error(f"Category '{category}' not found")
            return []

        try:
            response = self.session.get(category_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            articles = []
            found_urls = set()

            #Find all headline and title links
            headline_selectors = [
                'h2 a', 'h3 a', 'h4 a', 'h5 a', 'h6 a',
                '.title a', '.headline a', '.story-title a'
            ]

            for selector in headline_selectors:
                links = soup.select(selector)

                for link in links:
                    href = link.get('href', '').strip()
                    if not href:
                        continue

                    #Build full URL
                    if href.startswith('/'):
                        full_url = 'https://indianexpress.com' + href
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue

                    #Check if valid article URL
                    if ('indianexpress.com' in full_url and full_url not in found_urls and self._is_valid_article_url(full_url) and len(found_urls) < limit * 2 ):
                        title = self._extract_title_from_link(link)

                        if title and len(title.strip()) > 15:
                            found_urls.add(full_url)
                            articles.append({
                                'url': full_url,
                                'title': title.strip(),
                                'category': category
                            })

            #When not enough articles
            if len(articles) < limit:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    if len(articles) >= limit:
                        break

                    href = link.get('href', '').strip()
                    if not href:
                        continue

                    if href.startswith('/'):
                        full_url = 'https://indianexpress.com' + href
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue

                    if ('indianexpress.com' in full_url and full_url not in found_urls and self._is_valid_article_url(full_url)):
                        title = self._extract_title_from_link(link)

                        if title and len(title.strip()) > 15:
                            found_urls.add(full_url)
                            articles.append({
                                'url': full_url,
                                'title': title.strip(),
                                'category': category
                            })

            #Remove duplicates
            final_articles = self._deduplicate_articles(articles)
            final_articles = final_articles[:limit]

            logger.info(f"Found {len(final_articles)} articles for {category}")
            return final_articles

        except Exception as e:
            logger.error(f"Error scraping category {category}: {e}")
            return []

    def _is_valid_article_url(self, url: str) -> bool:
        #Skip these patterns
        skip_patterns = [
            '/videos/', '/photos/', '/gallery/', '/live-blog/',
            '/subscribe', '/newsletter', '/contact', '/about',
            '/privacy', '/terms', '/advertise', '/jobs',
            'facebook.com', 'twitter.com', 'instagram.com',
            'youtube.com', 'whatsapp.com', 'telegram.me'
        ]

        url_lower = url.lower()
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False

        #Valid article patterns
        valid_patterns = [
            '/section/', '/article/', '/explained/', '/opinion/',
            '/sports/', '/business/', '/cities/', '/lifestyle/',
            '/entertainment/', '/technology/', '/world/'
        ]

        for pattern in valid_patterns:
            if pattern in url_lower:
                return True

        #Additional check for stories
        if 'indianexpress.com' in url_lower and len(url.split('/')) >= 4:
            return True

        return False

    def _extract_title_from_link(self, link_element) -> str:
        title = ""

        #Try direct text content
        title = link_element.get_text(strip=True)

        #Try title attribute
        if not title or len(title) < 10:
            title = link_element.get('title', '')

        #Try alt text if image link
        if not title or len(title) < 10:
            img = link_element.find('img')
            if img:
                title = img.get('alt', '') or img.get('title', '')

        #Look in parent context
        if not title or len(title) < 10:
            parent = link_element.parent
            if parent:
                for sibling in parent.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'p']):
                    sibling_text = sibling.get_text(strip=True)
                    if sibling_text and len(sibling_text) > len(title) and len(sibling_text) < 200:
                        title = sibling_text
                        break

        return self._clean_title(title)

    def _clean_title(self, title: str) -> str:
        if not title:
            return ""

        #Remove extra whitespace
        title = ' '.join(title.split())

        artifacts = [
            'Read More', 'READ MORE', 'Continue Reading',
            'Click here', 'View Details', 'Share', 'Tweet',
            'Advertisement', 'Sponsored', '|', '–'
        ]

        for artifact in artifacts:
            title = title.replace(artifact, '')

        #Remove leading/trailing punctuation
        title = title.strip(' .,;:-–|')

        #Limit length
        if len(title) > 150:
            truncated = title[:150]
            last_space = truncated.rfind(' ')
            if last_space > 100:
                title = truncated[:last_space] + "..."

        return title

    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        if not articles:
            return []

        unique_articles = []
        seen_titles = set()

        for article in articles:
            title_normalized = article['title'].lower().strip()
            title_words = set(title_normalized.split())

            #Check similarity with existing titles
            is_duplicate = False
            for seen_title in seen_titles:
                seen_words = set(seen_title.split())

                if len(title_words) > 0 and len(seen_words) > 0:
                    common_words = title_words.intersection(seen_words)
                    similarity = len(common_words) / max(len(title_words), len(seen_words))

                    if similarity > 0.7:
                        is_duplicate = True
                        break

            if not is_duplicate:
                unique_articles.append(article)
                seen_titles.add(title_normalized)

        return unique_articles

    def get_article_content(self, article_url: str) -> Optional[Dict]:
        try:
            time.sleep(settings.REQUEST_DELAY)
            response = self.session.get(article_url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            #Extract title
            title_selectors = [
                'h1.story-heading', 'h1.article-title', 'h1.headline',
                'h1.entry-title', '.story-element-heading h1', 'h1'
            ]

            title = "Untitled Article"
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element:
                    title = element.get_text(strip=True)
                    if title and len(title) > 10:
                        break

            content_selectors = [
                '.story-element-text', '.full-details p', '.article-body p',
                '.story-content p', '.entry-content p'
            ]

            content_paragraphs = []
            for selector in content_selectors:
                paragraphs = soup.select(selector)
                if paragraphs and len(paragraphs) > 2:
                    content_paragraphs = paragraphs
                    break

            content = ""
            for p in content_paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    content += text + "\n\n"

            if not content.strip():
                return None

            content_hash = hashlib.sha256(content.encode()).hexdigest()

            return {
                'url': article_url,
                'title': title,
                'content': content.strip(),
                'content_hash': content_hash
            }

        except Exception as e:
            logger.error(f"Error scraping article {article_url}: {e}")
            return None

    def scrape_articles(self, categories: List[str], limit_per_category: int = None) -> Dict[str, List[Dict]]:
        if limit_per_category is None:
            limit_per_category = settings.N_ARTICLES

        results = {}

        for category in categories:
            article_links = self.get_category_articles(category, limit_per_category)
            articles_with_content = []

            for article_link in article_links:
                article_content = self.get_article_content(article_link['url'])
                if article_content:
                    article_content['category'] = category
                    articles_with_content.append(article_content)
                time.sleep(settings.REQUEST_DELAY)

            results[category] = articles_with_content

        return results
