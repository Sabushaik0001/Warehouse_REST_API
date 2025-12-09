"""
Database connection management
"""

import psycopg2
from psycopg2.extensions import connection
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def get_connection() -> connection:
    """
    Create and return a PostgreSQL database connection
    
    Returns:
        connection: PostgreSQL database connection
    """
    try:
        conn = psycopg2.connect(
            host=settings.PG_HOST,
            port=settings.PG_PORT,
            user=settings.PG_USER,
            password=settings.PG_PASSWORD,
            database=settings.PG_DATABASE
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
