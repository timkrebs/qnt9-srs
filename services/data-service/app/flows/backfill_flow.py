"""
Backfill Flow for 5-Year Historical Data (Incremental).

This flow:
1. Fetches top 10 searched tickers from search-service
2. Checks what data already exists in Supabase Storage
3. Only downloads missing dates from Massive S3
"""
import httpx
import re
from datetime import date, timedelta
from typing import List, Set
from prefect import flow, task, get_run_logger

from app.core.config import settings
from app.infrastructure.massive import MassiveClient
from app.flows.etl_flow import get_supabase

# --- Constants --- #
YEARS_TO_BACKFILL = 5
BUCKET_NAME = "raw-market-data"

# --- Tasks --- #

@task(name="Get Top Tickers from Search Service")
def get_top_tickers(limit: int = 10) -> List[str]:
    """
    Fetch top searched tickers from search-service.
    Falls back to defaults if service unavailable.
    """
    logger = get_run_logger()
    default_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B', 'LLY', 'V']
    
    try:
        search_url = settings.SEARCH_SERVICE_URL or "http://search-service:8000"
        resp = httpx.get(f"{search_url}/api/v1/popular?limit={limit}", timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            tickers = data.get("symbols", default_tickers)
            if tickers:
                logger.info(f"Fetched top {len(tickers)} tickers: {tickers}")
                return tickers
    except Exception as e:
        logger.warning(f"Failed to fetch from search-service: {e}")
    
    logger.info(f"Using default tickers: {default_tickers}")
    return default_tickers


@task(name="Get Existing Dates from Storage")
def get_existing_dates() -> Set[date]:
    """
    List all files in Supabase Storage and extract dates that already exist.
    Returns a set of dates that have already been downloaded.
    """
    logger = get_run_logger()
    sb_client = get_supabase()
    existing_dates = set()
    
    try:
        # List all files in the bucket (paginated by year folders)
        # Supabase Storage list returns files in a folder
        years_to_check = range(date.today().year - YEARS_TO_BACKFILL, date.today().year + 1)
        
        for year in years_to_check:
            try:
                files = sb_client.storage.from_(BUCKET_NAME).list(f"market_data/{year}")
                for file_info in files:
                    name = file_info.get("name", "")
                    # Extract date from filename like "2024-01-31.csv.gz"
                    match = re.match(r"(\d{4}-\d{2}-\d{2})\.csv\.gz", name)
                    if match:
                        existing_dates.add(date.fromisoformat(match.group(1)))
            except Exception as e:
                logger.debug(f"No data for year {year}: {e}")
        
        logger.info(f"Found {len(existing_dates)} dates already in storage")
        return existing_dates
        
    except Exception as e:
        logger.warning(f"Failed to list existing files: {e}")
        return set()


@task(name="Fetch and Store Single Day", retries=2, retry_delay_seconds=5)
def fetch_and_store_day(target_date: date) -> bool:
    """
    Fetch raw data for a single day from Massive S3 and upload to Supabase Storage.
    Returns True if successful, False if no data found.
    """
    logger = get_run_logger()
    
    # Skip weekends
    if target_date.weekday() >= 5:
        return False
    
    client = MassiveClient(settings)
    sb_client = get_supabase()
    
    try:
        raw_bytes = client.get_raw_object(target_date)
        if not raw_bytes:
            logger.debug(f"No data for {target_date}")
            return False
        
        path = f"market_data/{target_date.year}/{target_date.isoformat()}.csv.gz"
        
        sb_client.storage.from_(BUCKET_NAME).upload(
            path=path,
            file=raw_bytes,
            file_options={"content-type": "application/x-gzip", "upsert": "true"}
        )
        logger.info(f"Uploaded {len(raw_bytes)} bytes: {path}")
        return True
        
    except Exception as e:
        # Log but don't fail the entire backfill
        logger.warning(f"Failed to process {target_date}: {e}")
        return False


def generate_date_range(start_date: date, end_date: date) -> List[date]:
    """Generate list of dates between start and end (inclusive)."""
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


# --- Flows --- #

@flow(name="5-Year Backfill Pipeline (Incremental)")
def backfill_pipeline(years: int = YEARS_TO_BACKFILL, force: bool = False):
    """
    Main backfill flow that downloads historical data from Massive S3 to Supabase Storage.
    
    Args:
        years: Number of years to backfill (default: 5)
        force: If True, re-download all dates even if they exist
    """
    logger = get_run_logger()
    
    # Calculate date range
    end_date = date.today() - timedelta(days=1)  # Yesterday
    start_date = date(end_date.year - years, end_date.month, end_date.day)
    
    logger.info(f"Starting backfill from {start_date} to {end_date} ({years} years)")
    
    # Get top tickers (for logging/future use)
    top_tickers = get_top_tickers(limit=10)
    logger.info(f"Will filter for tickers: {top_tickers}")
    
    # Generate all dates
    all_dates = generate_date_range(start_date, end_date)
    
    # Get existing dates from storage
    if force:
        existing_dates = set()
        logger.info("Force mode: will re-download all dates")
    else:
        existing_dates = get_existing_dates()
    
    # Filter out dates that already exist and weekends
    missing_dates = [
        d for d in all_dates 
        if d not in existing_dates and d.weekday() < 5
    ]
    
    logger.info(f"Total dates: {len(all_dates)}, Already have: {len(existing_dates)}, Missing: {len(missing_dates)}")
    
    if not missing_dates:
        logger.info("All data already exists in storage. Nothing to download.")
        return {
            "success": 0,
            "skipped": len(all_dates),
            "failed": 0,
            "total": len(all_dates),
            "already_exists": len(existing_dates),
        }
    
    # Process each missing date
    success_count = 0
    fail_count = 0
    
    for i, d in enumerate(missing_dates):
        if i % 50 == 0:
            logger.info(f"Progress: {i}/{len(missing_dates)} ({i*100//len(missing_dates) if missing_dates else 0}%)")
        
        result = fetch_and_store_day(d)
        if result:
            success_count += 1
        else:
            fail_count += 1
    
    logger.info(f"Backfill complete: {success_count} uploaded, {len(existing_dates)} already existed, {fail_count} failed")
    
    return {
        "success": success_count,
        "skipped": len(all_dates) - len(missing_dates),
        "failed": fail_count,
        "total": len(all_dates),
        "already_exists": len(existing_dates),
    }


if __name__ == "__main__":
    # Run backfill
    result = backfill_pipeline()
    print(f"Backfill result: {result}")
