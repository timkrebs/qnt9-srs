import os
import io
import pandas as pd
from datetime import date
from prefect import flow, task, get_run_logger
from supabase import create_client, Client
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.massive import MassiveClient
from app.services.processor import DataProcessor
from app.models import MarketData
from app.database import SessionLocal

# --- Clients --- #
def get_supabase() -> Client:
    url = settings.SUPABASE_URL
    # Prefer Service Role Key for backend operations (bypassing RLS)
    key = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', settings.SUPABASE_KEY)
    return create_client(url, key)

def get_massive_client() -> MassiveClient:
    return MassiveClient(settings)

# --- Tasks --- #

@task(name="Fetch Data from Massive S3")
def fetch_to_storage(target_date: date) -> str:
    """
    Fetches raw data from Massive S3 and uploads it to Supabase Storage (Data Lake).
    Returns the path in Supabase Storage.
    """
    logger = get_run_logger()
    client = get_massive_client()
    sb_client = get_supabase()
    bucket_name = "raw-market-data"
    
    # 1. Fetch Bytes
    raw_bytes = client.get_raw_object(target_date)
    if not raw_bytes:
        logger.warning(f"No data found in Massive S3 for {target_date}")
        return None

    # 2. Upload to Supabase Storage
    path = f"market_data/{target_date.year}/{target_date.isoformat()}.csv.gz"
    
    # Check if bucket exists, if not... Supabase API doesn't easily let us check/create in one go via py client usually
    # assuming bucket exists as per user instruction capability
    
    try:
        # Upsert=true to overwrite
        sb_client.storage.from_(bucket_name).upload(
            path=path,
            file=raw_bytes,
            file_options={"content-type": "application/x-gzip", "upsert": "true"}
        )
        logger.info(f"Uploaded {len(raw_bytes)} bytes to Supabase Storage: {path}")
        return path
        
    except Exception as e:
        logger.error(f"Failed to upload to Supabase Storage: {e}")
        raise

@task(name="Process and Ingest Data")
def process_from_storage(storage_path: str, target_date: date):
    """
    Downloads raw data from Supabase Storage, processes it, and loads into Postgres.
    """
    logger = get_run_logger()
    sb_client = get_supabase()
    bucket_name = "raw-market-data"
    
    if not storage_path:
        logger.info("Skipping processing (no storage path)")
        return

    # 1. Download from Storage
    try:
        response = sb_client.storage.from_(bucket_name).download(storage_path)
        df_raw = pd.read_csv(io.BytesIO(response), compression='gzip')
    except Exception as e:
        logger.error(f"Failed to download/parse from Supabase: {e}")
        raise

    # 2. Inject Date (Fix metadata)
    df_raw['date'] = target_date
    
    # 3. Fetch Dynamic Watchlist from search-service
    # Fallback to hardcoded list if search-service unavailable
    import httpx
    default_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B', 'LLY', 'V']
    
    try:
        search_url = settings.SEARCH_SERVICE_URL or "http://search-service:8000"
        resp = httpx.get(f"{search_url}/api/v1/popular?limit=10", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            top_tickers = data.get("symbols", default_tickers)
            if not top_tickers:
                top_tickers = default_tickers
            logger.info(f"Fetched dynamic ticker list: {top_tickers}")
        else:
            logger.warning(f"Search service returned {resp.status_code}, using defaults")
            top_tickers = default_tickers
    except Exception as e:
        logger.warning(f"Failed to fetch from search-service: {e}, using defaults")
        top_tickers = default_tickers
    
    # Normalize columns first
    df_raw.columns = [c.lower() for c in df_raw.columns]
    
    # Filter
    df_filtered = df_raw[df_raw['ticker'].isin(top_tickers)].copy()
    
    if df_filtered.empty:
        logger.warning(f"No matching tickers found in data for {target_date}")
        return

    # 4. Transform (Clean & Compute Indicators)
    try:
        # Processor handles dropping extra columns now
        df_clean = DataProcessor.clean_and_normalize(df_filtered)
        df_final = DataProcessor.calculate_indicators(df_clean)
        logger.info(f"Processed {len(df_final)} rows for ingestion")
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise

    # 5. Load to DB
    records = df_final.to_dict(orient='records')
    
    stmt = insert(MarketData).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=['ticker', 'date'],
        set_={
            c.name: c for c in stmt.excluded 
            if c.name not in ['created_at']
        }
    )
    
    db: Session = SessionLocal()
    try:
        db.execute(stmt)
        db.commit()
        logger.info(f"Successfully ingested {len(records)} records into Postgres")
    except Exception as e:
        db.rollback()
        logger.error(f"DB Insert failed: {e}")
        raise
    finally:
        db.close()

# --- Flow --- #

@flow(name="Daily Market Data Pipeline")
def market_data_pipeline(target_date: date):
    logger = get_run_logger()
    logger.info(f"Starting pipeline for {target_date}")
    
    # Step 1: Ingest to Data Lake
    storage_path = fetch_to_storage(target_date)
    
    # Step 2: Process from Data Lake
    process_from_storage(storage_path, target_date)

if __name__ == "__main__":
    # Test run for a specific date
    from datetime import date
    market_data_pipeline(date(2024, 1, 31))
