#!/usr/bin/env python3
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.config import settings

#Create database engine
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    category = Column(String, index=True)
    title = Column(Text)
    summary = Column(Text)
    content = Column(Text)
    content_hash = Column(String)
    scraped_at = Column(DateTime, default=datetime.utcnow)

class CategoryCache(Base):
    __tablename__ = "category_cache"

    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String, unique=True, index=True)
    latest_article_url = Column(String)
    cached_articles_json = Column(JSON)  #List of article IDs
    cached_pdf_path = Column(String)
    cached_at = Column(DateTime, default=datetime.utcnow)

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    categories = Column(JSON)  #Array of category names
    time_of_day = Column(String)  #HH:MM format
    timezone = Column(String, default="Asia/Kolkata")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=True)
    action = Column(String)  #download/send
    categories = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    used_cache = Column(Boolean, default=False)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
