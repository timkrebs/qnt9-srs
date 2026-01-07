"""
Prefect Deployments for scheduled ETL pipelines.

To deploy:
    prefect deployment build app/deployments.py:market_data_pipeline -n daily-etl --apply
    
Or run inside container:
    python -m app.deployments
"""
from datetime import date, timedelta
from prefect import serve
from prefect.schedules import CronSchedule

from app.flows.etl_flow import market_data_pipeline

# --- Deployment Configuration --- #

def deploy_daily_pipeline():
    """
    Create and deploy the daily market data pipeline.
    Runs every day at 6 AM UTC (after US market close + processing time).
    """
    # Using Prefect 2.x serve pattern for simplicity
    # In production, use `prefect deploy` for workers/queues
    
    market_data_pipeline.serve(
        name="daily-etl",
        tags=["data-pipeline", "market-data"],
        description="Daily ingestion of top 10 searched stocks from Massive S3 to Postgres",
        # Run at 6 AM UTC daily (covers previous day's data)
        cron="0 6 * * *",
        # Also allow manual runs
        parameters={"target_date": (date.today() - timedelta(days=1)).isoformat()},
    )

if __name__ == "__main__":
    print("Starting Prefect deployment server...")
    print("Pipeline will run daily at 6 AM UTC")
    print("Manual trigger: prefect deployment run 'Daily Market Data Pipeline/daily-etl'")
    deploy_daily_pipeline()
