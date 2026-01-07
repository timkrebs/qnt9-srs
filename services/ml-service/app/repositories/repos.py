from datetime import date
from typing import Optional, List
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models import TrainingRun

class FeatureRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_features(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Fetches the most recent market data row for a ticker.
        Used for inference.
        """
        query = text("""
            SELECT open, high, low, close, volume, 
                   rsi_14, sma_50, sma_200, macd, macd_signal
            FROM market_data
            WHERE ticker = :ticker
            ORDER BY date DESC
            LIMIT 1
        """)
        
        result = self.db.execute(query, {"ticker": ticker}).fetchone()
        if not result:
            return None
            
        # Convert to DataFrame (1 row)
        # We need columns to match model input order exactly
        columns = ['open', 'high', 'low', 'close', 'volume', 'rsi_14', 'sma_50', 'sma_200', 'macd', 'macd_signal']
        # Note: Ensure these match what the XGBoost model expects!
        # The notebook used: ['rsi_14', 'sma_50', 'sma_200', 'macd', 'macd_signal', 'volume']
        # Let's filter to those specific features for safety in the service layer
        return pd.DataFrame([result], columns=['open', 'high', 'low', 'close', 'volume', 'rsi_14', 'sma_50', 'sma_200', 'macd', 'macd_signal'])

class ModelRegistryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_successful_run(self, ticker: str) -> Optional[TrainingRun]:
        """
        Finds the latest completed training run for a ticker.
        """
        return self.db.query(TrainingRun).filter(
            TrainingRun.ticker == ticker,
            TrainingRun.status == 'completed'
        ).order_by(TrainingRun.created_at.desc()).first()
