import asyncio
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
import structlog
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.infrastructure.massive import MassiveClient
from app.services.processor import DataProcessor
from app.models import MarketData, NewsSentiment
from app.core.config import settings

logger = structlog.get_logger()

class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.client = MassiveClient(settings)
        self.analyzer = SentimentIntensityAnalyzer()

    def ingest_daily_market_data(self, target_date: date):
        """
        Orchestrates fetching, processing, and storing market data.
        """
        logger.info("ingestion_start", date=target_date)
        
        # 1. Fetch from S3
        try:
            df_raw = self.client.fetch_historical_data(target_date)
            
            # Inject date column since it's not in the CSV but implied by filename
            if not df_raw.empty:
                df_raw['date'] = target_date
                
        except Exception as e:
            logger.error("ingestion_fetch_failed", error=str(e))
            raise

        if df_raw.empty:
            logger.warning("ingestion_no_data", date=target_date)
            return

        # 2. Process
        try:
            df_clean = DataProcessor.clean_and_normalize(df_raw)
            df_final = DataProcessor.calculate_indicators(df_clean)
        except Exception as e:
            logger.error("ingestion_processing_failed", error=str(e))
            raise

        # 3. Store (Bulk Upsert)
        # Convert DF to list of dicts
        records = df_final.to_dict(orient='records')
        
        stmt = insert(MarketData).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=['ticker', 'date'],
            set_={
                c.name: c for c in stmt.excluded 
                if c.name not in ['created_at']
            }
        )
        
        try:
            self.db.execute(stmt)
            self.db.commit()
            logger.info("ingestion_success", count=len(records))
        except Exception as e:
            self.db.rollback()
            logger.error("ingestion_db_error", error=str(e))
            raise

    async def ingest_news_sentiment(self, ticker: str):
        """
        Fetches news, computes sentiment, and saves to DB.
        """
        logger.info("news_ingestion_start", ticker=ticker)
        
        articles = await self.client.fetch_news(ticker)
        if not articles:
            return

        sentiment_records = []
        for article in articles:
            # Calculate Sentiment
            text = f"{article.get('title', '')} {article.get('description', '')}"
            scores = self.analyzer.polarity_scores(text)
            compound = scores['compound']
            
            label = "neutral"
            if compound >= 0.05: label = "positive"
            elif compound <= -0.05: label = "negative"
            
            # Massive API might use 'published_utc' or similar
            pub_date = article.get('published_utc', article.get('date'))
            
            sentiment_records.append({
                "ticker": ticker,
                "published_at": pub_date,
                "title": article.get('title'),
                "source": article.get('publisher', {}).get('name', 'Unknown'),
                "url": article.get('article_url'),
                "sentiment_score": compound,
                "sentiment_label": label
            })
            
        if not sentiment_records:
            return

        # Bulk Insert
        stmt = insert(NewsSentiment).values(sentiment_records)
        # Avoid duplicate articles based on ticker+url
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['ticker', 'url']
        )
        
        try:
            self.db.execute(stmt)
            self.db.commit()
            logger.info("news_ingestion_success", count=len(sentiment_records))
        except Exception as e:
            self.db.rollback()
            logger.error("news_ingestion_db_error", error=str(e))
            # Don't raise, just log error for news mainly
