from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Float, Date, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class MarketData(Base):
    """
    Stores daily OHLCV and calculated technical indicators for stocks.
    Acts as the 'Feature Store' for the ML models.
    """
    __tablename__ = "market_data"
    
    # Composite Primary Key: Ticker + Date
    ticker: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    
    # Raw Market Data
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    vwap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Technical Indicators (Features)
    rsi_14: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sma_50: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sma_200: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bollinger_upper: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bollinger_lower: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class NewsSentiment(Base):
    """
    Stores sentiment scores for news articles associated with stocks.
    """
    __tablename__ = "news_sentiment"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    
    title: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Sentiment Scores (e.g., from VADER or BERT)
    sentiment_score: Mapped[float] = mapped_column(Float)  # -1.0 to 1.0
    sentiment_label: Mapped[str] = mapped_column(String)   # positive, negative, neutral
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('ticker', 'url', name='uix_ticker_url'),
    )
