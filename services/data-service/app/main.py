"""Finio Data Service - Main FastAPI Application.

Provides data ingestion and ETL functionality for market data and news.
"""

import logging
import os
import sys
from datetime import date

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
import structlog

from app.database import get_db, engine, Base
from app.services.ingestion import IngestionService

# Configuration
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Configure logging - output to stdout for Docker visibility
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Configure structlog to use standard logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Create Tables (for dev/scaffolding - in prod use Alembic)
Base.metadata.create_all(bind=engine)

logger = structlog.get_logger(__name__)
logger.info("Data Service starting up...")

app = FastAPI(
    title="Finio Data Service",
    description="Data ingestion and ETL service for market data and news",
    version="1.0.0",
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "data-service"}

@app.post("/ingest/market-data")
async def trigger_market_ingestion(
    target_date: date, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Triggers background ingestion of historical market data for a specific date.
    """
    service = IngestionService(db)
    
    # Run in background to avoid blocking
    background_tasks.add_task(service.ingest_daily_market_data, target_date)
    
    return {"message": f"Ingestion triggered for {target_date}", "status": "processing"}

@app.post("/ingest/news")
async def trigger_news_ingestion(
    ticker: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Triggers background ingestion of news for a ticker.
    """
    service = IngestionService(db)
    
    # Note: ingest_news_sentiment is async, but background_tasks handles async defs too
    background_tasks.add_task(service.ingest_news_sentiment, ticker)
    
    return {"message": f"News ingestion triggered for {ticker}", "status": "processing"}
