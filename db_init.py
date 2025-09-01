#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models import create_tables, engine
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    try:
        logger.info(f"Initializing database at: {settings.DATABASE_URL}")
        create_tables()
        logger.info("Database tables created successfully!")

        #Test database connection
        with engine.connect() as conn:
            logger.info("Database connection test successful!")

        return True

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
