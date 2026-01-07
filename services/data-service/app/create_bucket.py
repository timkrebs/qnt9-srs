from supabase import create_client
from app.core.config import settings
import structlog

logger = structlog.get_logger()

def create_bucket():
    url = settings.SUPABASE_URL
    # Prefer Service Role Key for Admin tasks
    key = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', settings.SUPABASE_KEY)
    
    supabase = create_client(url, key)
    bucket_name = "raw-market-data"

    try:
        buckets = supabase.storage.list_buckets()
        existing = [b.name for b in buckets]
        if bucket_name not in existing:
            supabase.storage.create_bucket(bucket_name, options={"public": False})
            logger.info(f"Bucket '{bucket_name}' created.")
        else:
            logger.info(f"Bucket '{bucket_name}' already exists.")
    except Exception as e:
        logger.error(f"Error creating bucket: {e}")

if __name__ == "__main__":
    create_bucket()
