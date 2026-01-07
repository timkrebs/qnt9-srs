"""
Pipeline Runner CLI.

Usage:
    python -m app.run_pipeline daily YYYY-MM-DD YYYY-MM-DD   # Run daily pipeline for date range
    python -m app.run_pipeline backfill [years]              # Run 5-year backfill (default 5)
"""
import sys
from datetime import date, timedelta


def run_daily(start_date: date, end_date: date):
    """Run daily pipeline for date range."""
    from app.flows.etl_flow import market_data_pipeline
    
    current = start_date
    while current <= end_date:
        print(f"Triggering pipeline for {current}")
        market_data_pipeline(current)
        current += timedelta(days=1)


def run_backfill(years: int = 5):
    """Run 5-year backfill pipeline."""
    from app.flows.backfill_flow import backfill_pipeline
    
    print(f"Starting {years}-year backfill...")
    result = backfill_pipeline(years=years)
    print(f"Backfill complete: {result}")


def print_usage():
    print(__doc__)
    print("Examples:")
    print("  python -m app.run_pipeline daily 2024-01-01 2024-01-31")
    print("  python -m app.run_pipeline backfill")
    print("  python -m app.run_pipeline backfill 3")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "daily":
        if len(sys.argv) != 4:
            print("Usage: python -m app.run_pipeline daily YYYY-MM-DD YYYY-MM-DD")
            sys.exit(1)
        start = date.fromisoformat(sys.argv[2])
        end = date.fromisoformat(sys.argv[3])
        run_daily(start, end)
    
    elif command == "backfill":
        years = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        run_backfill(years)
    
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)
