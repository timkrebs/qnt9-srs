import io
import datetime
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
import httpx
import pandas as pd
import structlog
from app.core.config import Settings

logger = structlog.get_logger()

class MassiveClient:
    """
    Client for interacting with Massive Data APIs.
    - S3: Historical market data (CSV files)
    - REST: Real-time news and other API data
    """
    def __init__(self, settings: Settings):
        self.settings = settings
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.MASSIVE_S3_ENDPOINT,
            aws_access_key_id=settings.MASSIVE_S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.MASSIVE_S3_SECRET_ACCESS_KEY,
        )
        self.bucket_name = settings.MASSIVE_S3_BUCKET
        # Base URL for Massive REST API (Assuming a standard structure or mock)
        self.api_base_url = "https://api.massive.example.com/v1" 

    def get_raw_object(self, date: datetime.date) -> bytes:
        """
        Fetches raw bytes (gzip compressed CSV) from Massive S3.
        Used for streaming data to another storage (Data Lake).
        """
        date_str = date.isoformat()
        year = date.year
        month = f"{date.month:02d}"
        key = f"us_stocks_sip/day_aggs_v1/{year}/{month}/{date_str}.csv.gz"
        
        logger.info("fetching_s3_raw", date=date, bucket=self.bucket_name, key=key)
        
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except ClientError as e:
            logger.error("s3_fetch_raw_error", error=str(e), key=key)
            if e.response['Error']['Code'] == "NoSuchKey":
                return None
            raise

    def fetch_historical_data(self, date: datetime.date) -> pd.DataFrame:
        """
        Fetches historical market data (OHLCV) for a specific date from Massive S3.
        Expected format: CSV compressed with gzip.
        """
        content = self.get_raw_object(date)
        if not content:
            return pd.DataFrame()
            
        return pd.read_csv(io.BytesIO(content), compression='gzip')

    async def fetch_news(self, ticker: str, days_back: int = 3) -> List[Dict[str, Any]]:
        """
        Fetches news articles for a specific ticker from Massive REST API.
        """
        url = f"{self.api_base_url}/news"
        params = {
            "ticker": ticker,
            "limit": 50,
            "api_key": self.settings.MASSIVE_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json().get("results", [])
            except httpx.HTTPError as e:
                logger.error("news_fetch_error", error=str(e), ticker=ticker)
                return []
