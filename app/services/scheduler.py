#!/usr/bin/env python3
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, time
import pytz
import logging
from typing import List
from sqlalchemy.orm import Session
from app.models import Subscription, get_db
from app.services.cache import cache_manager
from app.services.pdf_builder import pdf_builder
from app.services.mailer import email_service

#Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SubscriptionScheduler:

    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def process_subscription_delivery(self, subscription_id: int):
        db = next(get_db())

        try:
            subscription = db.query(Subscription).filter(
                Subscription.id == subscription_id,
                Subscription.active == True
            ).first()

            if not subscription:
                logger.warning(f"Subscription {subscription_id} not found or inactive")
                return

            logger.info(f"Processing delivery for subscription {subscription_id}: {subscription.email}")

            categories = subscription.categories if isinstance(subscription.categories, list) else []
            if not categories:
                logger.warning(f"No categories found for subscription {subscription_id}")
                return

            #Fetch and summarize articles
            articles_by_category = cache_manager.get_articles_with_cache(categories)

            if not any(articles_by_category.values()):
                logger.warning(f"No articles found for subscription {subscription_id}")
                return

            pdf_path = pdf_builder.generate_pdf(articles_by_category)

            success = email_service.send_news_pdf(
                subscription.email,
                pdf_path,
                categories
            )

            if success:
                logger.info(f"Successfully delivered PDF to {subscription.email}")
            else:
                logger.error(f"Failed to deliver PDF to {subscription.email}")

        except Exception as e:
            logger.error(f"Error processing subscription {subscription_id}: {e}")

        finally:
            db.close()

    def schedule_subscription(self, subscription_id: int, time_of_day: str, timezone_str: str = "Asia/Kolkata"):
        try:
            #Parse time
            hour, minute = map(int, time_of_day.split(':'))

            #Create timezone object
            tz = pytz.timezone(timezone_str)

            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=tz
            )

            #Add job to scheduler
            job_id = f"subscription_{subscription_id}"

            #Remove existing job if it exists
            try:
                self.scheduler.remove_job(job_id)
                logger.info(f"Removed existing job for subscription {subscription_id}")
            except:
                pass

            #Add new job
            self.scheduler.add_job(
                func=self.process_subscription_delivery,
                trigger=trigger,
                args=[subscription_id],
                id=job_id,
                name=f"Daily delivery for subscription {subscription_id}",
                replace_existing=True
            )

            logger.info(f"Scheduled subscription {subscription_id} for daily delivery at {time_of_day} {timezone_str}")

        except Exception as e:
            logger.error(f"Failed to schedule subscription {subscription_id}: {e}")

    def unschedule_subscription(self, subscription_id: int):
        try:
            job_id = f"subscription_{subscription_id}"
            self.scheduler.remove_job(job_id)
            logger.info(f"Unscheduled subscription {subscription_id}")
        except:
            logger.warning(f"No scheduled job found for subscription {subscription_id}")

    def load_all_subscriptions(self):
        db = next(get_db())

        try:
            subscriptions = db.query(Subscription).filter(
                Subscription.active == True
            ).all()

            for subscription in subscriptions:
                self.schedule_subscription(
                    subscription.id,
                    subscription.time_of_day,
                    subscription.timezone
                )

            logger.info(f"Loaded {len(subscriptions)} active subscriptions")

        except Exception as e:
            logger.error(f"Failed to load subscriptions: {e}")

        finally:
            db.close()

    def process_all_due_subscriptions(self):
        db = next(get_db())
        current_time = datetime.now()

        try:
            subscriptions = db.query(Subscription).filter(
                Subscription.active == True
            ).all()

            processed_count = 0

            for subscription in subscriptions:
                try:
                    hour, minute = map(int, subscription.time_of_day.split(':'))
                    sub_tz = pytz.timezone(subscription.timezone)

                    #Get current time
                    current_in_tz = datetime.now(sub_tz)

                    if (current_in_tz.hour == hour and 
                        abs(current_in_tz.minute - minute) <= 2):

                        self.process_subscription_delivery(subscription.id)
                        processed_count += 1

                except Exception as e:
                    logger.error(f"Error checking subscription {subscription.id}: {e}")

            logger.info(f"Processed {processed_count} due subscriptions")

        except Exception as e:
            logger.error(f"Failed to process due subscriptions: {e}")

        finally:
            db.close()

    def get_scheduled_jobs(self) -> List[dict]:
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs

subscription_scheduler = SubscriptionScheduler()
subscription_scheduler.start()