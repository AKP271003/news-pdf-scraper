#!/usr/bin/env python3
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.routes import router
from app.models import create_tables

#Initialize FastAPI app
app = FastAPI(
    title="News PDF Scraper",
    description="Scrapes Indian Express articles, summarizes with AI, and generates PDFs",
    version="1.0.0"
)

#Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

#Set up templates
templates = Jinja2Templates(directory="app/templates")

app.include_router(router)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    create_tables()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    categories = [
        "india", "politics", "sports", "technology",
        "business", "world", "explained", "lifestyle",
        "opinion", "cities"
    ]

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "categories": categories}
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "news-pdf-scraper"}
