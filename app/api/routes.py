#!/usr/bin/env python3
from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from sqlalchemy.orm import Session
import os
from datetime import datetime
from app.models import Subscription, get_db
from app.services.cache import cache_manager
from app.services.pdf_builder import pdf_builder
from app.services.mailer import email_service
from app.services.scheduler import subscription_scheduler
from app.config import settings

#Setup templates
templates = Jinja2Templates(directory="app/templates")

#Create router
router = APIRouter()

#Pydantic models for request validation
class GenerateRequest(BaseModel):
    categories: List[str]
    n: Optional[int] = 10
    email: Optional[EmailStr] = None

class SubscribeRequest(BaseModel):
    email: EmailStr
    categories: List[str]
    time_of_day: str  #HH:MM format
    timezone: Optional[str] = "Asia/Kolkata"

class UnsubscribeRequest(BaseModel):
    subscription_id: int

#API Endpoints
@router.post("/generate")
async def generate_pdf(request: GenerateRequest):
    try:
        #Validate categories
        valid_categories = list(settings.CATEGORIES.keys())
        invalid_categories = [c for c in request.categories if c not in valid_categories]
        if invalid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid categories: {invalid_categories}"
            )

        #Get articles using cache
        articles_by_category = cache_manager.get_articles_with_cache(
            request.categories,
            request.n or 10
        )

        if not any(articles_by_category.values()):
            raise HTTPException(
                status_code=404,
                detail="No articles found for the specified categories"
            )

        #Generate PDF
        pdf_path = pdf_builder.generate_pdf(articles_by_category)
        pdf_filename = os.path.basename(pdf_path)

        #Send email if requested
        if request.email:
            success = email_service.send_news_pdf(
                request.email,
                pdf_path,
                request.categories
            )

            if success:
                return {
                    "status": "success",
                    "message": f"PDF generated and sent to {request.email}",
                    "pdf_url": f"/download/{pdf_filename}"
                }
            else:
                return {
                    "status": "partial_success",
                    "message": "PDF generated but email sending failed",
                    "pdf_url": f"/download/{pdf_filename}"
                }

        return {
            "status": "success",
            "message": "PDF generated successfully",
            "pdf_url": f"/download/{pdf_filename}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{pdf_filename}")
async def download_pdf(pdf_filename: str):
    pdf_path = os.path.join("generated_pdfs", pdf_filename)

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=pdf_path,
        filename=pdf_filename,
        media_type='application/pdf'
    )

@router.post("/send_email")
async def send_email_form(
    categories: List[str] = Form(...),
    email: EmailStr = Form(...),
    n_articles: int = Form(10)
):
    request_data = GenerateRequest(
        categories=categories,
        email=email,
        n=n_articles
    )

    return await generate_pdf(request_data)

@router.post("/subscribe")
async def subscribe(request: SubscribeRequest, db: Session = Depends(get_db)):
    try:
        #Validate categories
        valid_categories = list(settings.CATEGORIES.keys())
        invalid_categories = [c for c in request.categories if c not in valid_categories]
        if invalid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid categories: {invalid_categories}"
            )

        #Validate time format
        try:
            hour, minute = map(int, request.time_of_day.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time range")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid time format. Use HH:MM (24-hour format)"
            )

        #Check if subscription already exists
        existing = db.query(Subscription).filter(
            Subscription.email == request.email,
            Subscription.active == True
        ).first()

        if existing:
            #Update existing subscription
            existing.categories = request.categories
            existing.time_of_day = request.time_of_day
            existing.timezone = request.timezone
            subscription_id = existing.id
        else:
            #Create new subscription
            subscription = Subscription(
                email=request.email,
                categories=request.categories,
                time_of_day=request.time_of_day,
                timezone=request.timezone
            )

            db.add(subscription)
            db.commit()
            db.refresh(subscription)
            subscription_id = subscription.id

        #Schedule the subscription
        subscription_scheduler.schedule_subscription(
            subscription_id,
            request.time_of_day,
            request.timezone
        )

        return {
            "status": "success",
            "message": f"Successfully subscribed {request.email} for daily delivery at {request.time_of_day}",
            "subscription_id": subscription_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#Subscribers Management Page
@router.get("/subscribers", response_class=HTMLResponse)
async def subscribers_page(request: Request, db: Session = Depends(get_db)):
    subscriptions = db.query(Subscription).filter(
        Subscription.active == True
    ).all()

    return templates.TemplateResponse(
        "subscribers.html",
        {
            "request": request,
            "subscriptions": subscriptions,
            "categories": list(settings.CATEGORIES.keys())
        }
    )

@router.post("/unsubscribe")
async def unsubscribe(request: UnsubscribeRequest, db: Session = Depends(get_db)):
    try:
        subscription = db.query(Subscription).filter(
            Subscription.id == request.subscription_id,
            Subscription.active == True
        ).first()

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        #Deactivate subscription
        subscription.active = False
        db.commit()

        #Remove from scheduler
        subscription_scheduler.unschedule_subscription(request.subscription_id)

        return {
            "status": "success",
            "message": f"Successfully unsubscribed {subscription.email}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#Manual trigger for a subscription
@router.post("/send_now/{subscription_id}")
async def send_now(subscription_id: int, db: Session = Depends(get_db)):
    try:
        subscription = db.query(Subscription).filter(
            Subscription.id == subscription_id,
            Subscription.active == True
        ).first()

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        subscription_scheduler.process_subscription_delivery(subscription_id)

        return {
            "status": "success",
            "message": f"PDF sent to {subscription.email}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/categories")
async def get_categories():
    return {
        "categories": list(settings.CATEGORIES.keys()),
        "category_urls": settings.CATEGORIES
    }

@router.get("/api/status")
async def get_status():
    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "scheduler_running": subscription_scheduler.scheduler.running,
        "scheduled_jobs": len(subscription_scheduler.get_scheduled_jobs()),
        "openai_available": bool(settings.OPENAI_API_KEY),
        "email_configured": bool(settings.SMTP_USER and settings.SMTP_PASS)
    }

    return status
