#!/usr/bin/env python3
import json
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Article, CategoryCache, get_db
from app.services.scraper import IndianExpressScraper
from app.services.summarizer import summarizer
import logging

#Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheManager:

    def __init__(self):
        self.scraper = IndianExpressScraper()

    def get_cached_articles(self, category: str, db: Session) -> Optional[List[Dict]]:
        cache_entry = db.query(CategoryCache).filter(
            CategoryCache.category_name == category
        ).first()

        if not cache_entry:
            return None

        #Check if cache is fresh (within last 4 hours)
        cache_age = datetime.utcnow() - cache_entry.cached_at
        if cache_age > timedelta(hours=4):
            logger.info(f"Cache expired for category {category}")
            return None

        if not cache_entry.cached_articles_json:
            return None

        article_ids = cache_entry.cached_articles_json
        cached_articles = db.query(Article).filter(
            Article.id.in_(article_ids)
        ).order_by(Article.scraped_at.desc()).all()

        articles_data = []
        for article in cached_articles:
            articles_data.append({
                'url': article.url,
                'title': article.title,
                'summary': article.summary,
                'content': article.content,
                'category': article.category,
                'heading': article.title,
                'scraped_at': article.scraped_at
            })

        logger.info(f"Retrieved {len(articles_data)} cached articles for {category}")
        return articles_data

    def get_latest_article_url(self, category: str) -> Optional[str]:
        try:
            articles = self.scraper.get_category_articles(category, limit=1)
            if articles:
                return articles[0]['url']
            return None
        except Exception as e:
            logger.error(f"Failed to get latest article URL for {category}: {e}")
            return None

    #Check if cache has to be updated
    def should_update_cache(self, category: str, db: Session) -> Tuple[bool, Optional[str]]:
        cache_entry = db.query(CategoryCache).filter(
            CategoryCache.category_name == category
        ).first()

        current_latest_url = self.get_latest_article_url(category)

        if not cache_entry:
            logger.info(f"No cache found for {category}, will create new cache")
            return True, None

        #Check cache age first (4 hours)
        cache_age = datetime.utcnow() - cache_entry.cached_at
        if cache_age > timedelta(hours=4):
            logger.info(f"Cache expired for {category} (age: {cache_age})")
            return True, cache_entry.latest_article_url

        if cache_entry.latest_article_url != current_latest_url:
            logger.info(f"New articles detected for {category}")
            return True, cache_entry.latest_article_url

        logger.info(f"Cache is fresh for {category}, using cached articles")
        return False, cache_entry.latest_article_url

    def get_incremental_articles(self, category: str, latest_cached_url: str, limit: int) -> List[Dict]:
        try:
            all_articles = self.scraper.get_category_articles(category, limit * 3)

            cached_index = None
            for i, article in enumerate(all_articles):
                if article['url'] == latest_cached_url:
                    cached_index = i
                    break

            if cached_index is not None:
                new_articles = all_articles[:cached_index]
                logger.info(f"Found {len(new_articles)} new articles since last cache for {category}")
            else:
                #Cached article not found, get top articles
                new_articles = all_articles[:limit]
                logger.warning(f"Cached article not found in current listings for {category}, fetching top {limit}")

            return new_articles

        except Exception as e:
            logger.error(f"Failed to get incremental articles for {category}: {e}")
            return []

    def store_articles_in_db(self, articles_with_content: List[Dict], db: Session) -> List[int]:
        article_ids = []

        #Check if article already exists
        for article_data in articles_with_content:
            existing = db.query(Article).filter(
                Article.url == article_data['url']
            ).first()

            if existing:
                article_ids.append(existing.id)
                continue

            #Create new article
            article = Article(
                url=article_data['url'],
                category=article_data['category'],
                title=article_data.get('title', ''),
                summary=article_data.get('summary', ''),
                content=article_data.get('content', ''),
                content_hash=article_data.get('content_hash', '')
            )

            db.add(article)
            db.commit()
            db.refresh(article)

            article_ids.append(article.id)
            logger.info(f"Stored new article: {article.title[:50]}...")

        return article_ids

    def update_category_cache(self, category: str, article_ids: List[int], latest_url: str, db: Session):
        cache_entry = db.query(CategoryCache).filter(
            CategoryCache.category_name == category
        ).first()

        if cache_entry:
            #Update existing cache
            cache_entry.latest_article_url = latest_url
            cache_entry.cached_articles_json = article_ids
            cache_entry.cached_at = datetime.utcnow()
        else:
            #Create new cache entry
            cache_entry = CategoryCache(
                category_name=category,
                latest_article_url=latest_url,
                cached_articles_json=article_ids,
                cached_at=datetime.utcnow()
            )
            db.add(cache_entry)

        db.commit()
        logger.info(f"Updated cache for category {category} with {len(article_ids)} articles")

    def get_articles_with_cache(self, categories: List[str], limit_per_category: int = 10) -> Dict[str, List[Dict]]:
        results = {}
        db = next(get_db())

        try:
            for category in categories:
                logger.info(f"Processing category: {category}")

                #Check if cache should be updated
                should_update, latest_cached_url = self.should_update_cache(category, db)

                if not should_update:
                    #Use cached articles
                    cached_articles = self.get_cached_articles(category, db)
                    if cached_articles:
                        results[category] = cached_articles[:limit_per_category]
                        logger.info(f"Using {len(results[category])} cached articles for {category}")
                        continue

                #Need to fetch new articles
                new_article_links = []
                cached_articles = []

                if latest_cached_url:
                    #Get new articles + combine with cached
                    new_article_links = self.get_incremental_articles(
                        category, latest_cached_url, limit_per_category
                    )
                    cached_articles = self.get_cached_articles(category, db) or []
                else:
                    #Full fetch
                    new_article_links = self.scraper.get_category_articles(
                        category, limit_per_category
                    )

                new_articles_with_content = []
                for article_link in new_article_links:
                    article_content = self.scraper.get_article_content(article_link['url'])
                    if article_content:
                        article_content['category'] = category
                        new_articles_with_content.append(article_content)

                #Summarize new articles
                for article in new_articles_with_content:
                    if article.get('content'):
                        summary_result = summarizer.summarize_text(
                            article['content'], 
                            article.get('title', '')
                        )
                        article['heading'] = summary_result['heading']
                        article['summary'] = summary_result['summary']

                all_articles = []

                all_articles.extend(new_articles_with_content)

                #Add articles that are not in new articles
                if cached_articles:
                    new_urls = {a['url'] for a in new_articles_with_content}
                    filtered_cached = [a for a in cached_articles if a['url'] not in new_urls]
                    all_articles.extend(filtered_cached)

                final_articles = all_articles[:limit_per_category]

                #If no enough articles, fetch more
                if len(final_articles) < limit_per_category and len(new_articles_with_content) < limit_per_category:
                    logger.info(f"Only have {len(final_articles)} articles for {category}, trying to fetch more...")
                    additional_links = self.scraper.get_category_articles(
                        category, limit_per_category * 2
                    )

                    existing_urls = {a['url'] for a in all_articles}
                    for article_link in additional_links:
                        if len(final_articles) >= limit_per_category:
                            break
                        if article_link['url'] not in existing_urls:
                            article_content = self.scraper.get_article_content(article_link['url'])
                            if article_content:
                                article_content['category'] = category
                                if article_content.get('content'):
                                    summary_result = summarizer.summarize_text(
                                        article_content['content'], 
                                        article_content.get('title', '')
                                    )
                                    article_content['heading'] = summary_result['heading']
                                    article_content['summary'] = summary_result['summary']
                                final_articles.append(article_content)
                                existing_urls.add(article_link['url'])

                articles_to_store = [a for a in final_articles if a.get('content')]
                if articles_to_store:
                    article_ids = self.store_articles_in_db(articles_to_store, db)

                    if final_articles:
                        latest_url = final_articles[0]['url']
                        self.update_category_cache(category, article_ids, latest_url, db)

                results[category] = final_articles
                logger.info(f"Completed processing {category}: {len(final_articles)} articles total")

        finally:
            db.close()

        return results

cache_manager = CacheManager()