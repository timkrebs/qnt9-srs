"""
Integration test fixtures and configuration.

Provides:
- Docker service health checks
- Test data fixtures (AAPL, MSFT 90-day sample data)
- Mock external APIs (Yahoo Finance, Alpha Vantage)
- Kafka producers/consumers
- Database connections (TimescaleDB, Redis)
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
import redis.asyncio as redis
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

# ==================== Configuration ====================

# Service URLs (adjust if running locally vs Docker)
TIMESCALEDB_URL = os.getenv(
    "TIMESCALEDB_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/qnt9_timeseries"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://:qnt9_redis_password@localhost:6379/0")

# Kafka connection - try localhost first, fallback handled in fixture
KAFKA_BOOTSTRAP_DEFAULT = "localhost:9092"
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", KAFKA_BOOTSTRAP_DEFAULT)

# Kafka topics
KAFKA_TOPICS = {
    "raw": "raw-stock-data",
    "processed": "processed-stock-data",
    "features": "ml-features",
}

# Service endpoints
SERVICE_URLS = {
    "ingestion": "http://localhost:8001",
    "etl": "http://localhost:8002",
    "features": "http://localhost:8003",
    "training": "http://localhost:8004",
}

# Test configuration
TEST_TIMEOUT = 30  # seconds
KAFKA_POLL_TIMEOUT = 5000  # milliseconds


# ==================== Health Check Fixtures ====================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def check_services_health():
    """Verify all required services are healthy before running tests."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        services_to_check = [
            ("TimescaleDB", TIMESCALEDB_URL.replace("+asyncpg", "").replace("postgresql", "http")),
            ("Ingestion Service", f"{SERVICE_URLS['ingestion']}/health"),
            ("ETL Service", f"{SERVICE_URLS['etl']}/health"),
            ("Feature Engineering", f"{SERVICE_URLS['features']}/health"),
            ("ML Training Service", f"{SERVICE_URLS['training']}/health"),
        ]

        unhealthy_services = []

        for service_name, url in services_to_check:
            if "postgresql" in url or "TimescaleDB" in service_name:
                # Skip HTTP check for database
                continue

            try:
                response = await client.get(url)
                if response.status_code != 200:
                    unhealthy_services.append(f"{service_name} ({response.status_code})")
            except Exception as e:
                unhealthy_services.append(f"{service_name} (unreachable: {e})")

        if unhealthy_services:
            pytest.skip(f"Services not healthy: {', '.join(unhealthy_services)}")

    return True


# ==================== Database Fixtures ====================


@pytest_asyncio.fixture(scope="function", autouse=False)
async def timescaledb_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide async TimescaleDB session for tests.

    Uses function scope with NullPool to avoid event loop conflicts.
    Each test gets a fresh connection that's immediately disposed.
    Tests should explicitly commit if they want changes persisted.
    """
    engine = create_async_engine(
        TIMESCALEDB_URL,
        echo=False,
        poolclass=NullPool,  # No connection pooling - immediate disposal
    )

    async_sessionmaker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )

    session = async_sessionmaker()

    try:
        yield session
    finally:
        # Clean shutdown sequence
        try:
            # Don't commit or rollback - just close
            await session.close()
        except Exception:
            pass

        try:
            # Dispose engine immediately
            await engine.dispose()
        except Exception:
            pass


@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[redis.Redis, None]:
    """Provide Redis client for feature store access."""
    client = redis.from_url(REDIS_URL, decode_responses=True)

    try:
        await client.ping()
        yield client
    finally:
        await client.close()


# ==================== Kafka Fixtures ====================


@pytest_asyncio.fixture(scope="function")
async def kafka_producer() -> AsyncGenerator[AIOKafkaProducer, None]:
    """Provide Kafka producer for publishing test messages."""
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        request_timeout_ms=10000,
        metadata_max_age_ms=5000,
    )

    try:
        await producer.start()
        yield producer
    except Exception as e:
        logger.error(f"Failed to start Kafka producer: {e}")
        pytest.skip(f"Kafka not available: {e}")
    finally:
        try:
            await producer.stop()
        except Exception:
            pass  # Ignore cleanup errors


@pytest_asyncio.fixture(scope="function")
async def kafka_consumer_raw() -> AsyncGenerator[AIOKafkaConsumer, None]:
    """Consumer for raw-stock-data topic."""
    consumer = AIOKafkaConsumer(
        KAFKA_TOPICS["raw"],
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="test-consumer-raw",
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        request_timeout_ms=10000,
        metadata_max_age_ms=5000,
    )

    try:
        await consumer.start()
        yield consumer
    except Exception as e:
        logger.error(f"Failed to start Kafka consumer (raw): {e}")
        pytest.skip(f"Kafka not available: {e}")
    finally:
        try:
            await consumer.stop()
        except Exception:
            pass  # Ignore cleanup errors


@pytest_asyncio.fixture(scope="function")
async def kafka_consumer_processed() -> AsyncGenerator[AIOKafkaConsumer, None]:
    """Consumer for processed-stock-data topic."""
    consumer = AIOKafkaConsumer(
        KAFKA_TOPICS["processed"],
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="test-consumer-processed",
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        request_timeout_ms=10000,
        metadata_max_age_ms=5000,
    )

    try:
        await consumer.start()
        yield consumer
    except Exception as e:
        logger.error(f"Failed to start Kafka consumer (processed): {e}")
        pytest.skip(f"Kafka not available: {e}")
    finally:
        try:
            await consumer.stop()
        except Exception:
            pass  # Ignore cleanup errors


@pytest_asyncio.fixture(scope="function")
async def kafka_consumer_features() -> AsyncGenerator[AIOKafkaConsumer, None]:
    """Consumer for ml-features topic."""
    consumer = AIOKafkaConsumer(
        KAFKA_TOPICS["features"],
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="test-consumer-features",
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        request_timeout_ms=10000,
        metadata_max_age_ms=5000,
    )

    try:
        await consumer.start()
        yield consumer
    except Exception as e:
        logger.error(f"Failed to start Kafka consumer (features): {e}")
        pytest.skip(f"Kafka not available: {e}")
    finally:
        try:
            await consumer.stop()
        except Exception:
            pass  # Ignore cleanup errors


# ==================== Test Data Fixtures ====================


@pytest.fixture
def sample_stock_symbols() -> List[str]:
    """Stock symbols for testing."""
    return ["AAPL", "MSFT"]


@pytest_asyncio.fixture
async def clean_database(timescaledb_session: AsyncSession):
    """Clean all test data from tables before tests."""
    from sqlalchemy import text

    # Truncate in correct order (respecting foreign keys)
    cleanup_queries = [
        "TRUNCATE TABLE technical_indicators CASCADE;",
        "TRUNCATE TABLE stock_features CASCADE;",
        "TRUNCATE TABLE daily_ohlcv CASCADE;",
        "DELETE FROM stocks_master WHERE symbol IN ('AAPL', 'MSFT');",
    ]

    for query in cleanup_queries:
        await timescaledb_session.execute(text(query))

    await timescaledb_session.commit()
    yield


@pytest_asyncio.fixture
async def setup_test_stocks(
    clean_database, timescaledb_session: AsyncSession, sample_stock_symbols: List[str]
):
    """Ensure test stocks exist in stocks_master table after cleanup."""
    from sqlalchemy import text

    insert_query = text(
        """
        INSERT INTO stocks_master (symbol, name, sector, exchange)
        VALUES (:symbol, :name, :sector, :exchange)
        ON CONFLICT (symbol) DO NOTHING;
    """
    )

    stock_data = {
        "AAPL": {"name": "Apple Inc.", "sector": "Technology", "exchange": "NASDAQ"},
        "MSFT": {"name": "Microsoft Corporation", "sector": "Technology", "exchange": "NASDAQ"},
    }

    for symbol in sample_stock_symbols:
        data = stock_data.get(symbol, {"name": symbol, "sector": "Unknown", "exchange": "NYSE"})
        await timescaledb_session.execute(
            insert_query,
            {
                "symbol": symbol,
                "name": data["name"],
                "sector": data["sector"],
                "exchange": data["exchange"],
            },
        )

    await timescaledb_session.commit()
    yield
    # Cleanup not needed - tests should use rollback


@pytest.fixture
def sample_date_range() -> tuple:
    """90-day date range for historical data."""
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=90)
    return start_date, end_date


@pytest.fixture
def sample_ohlcv_data(sample_stock_symbols, sample_date_range) -> Dict[str, List[Dict]]:
    """
    Generate 90 days of synthetic OHLCV data for AAPL and MSFT.

    Returns dict with symbol keys and list of daily OHLCV records.
    """
    start_date, end_date = sample_date_range

    # Base prices
    base_prices = {"AAPL": 175.0, "MSFT": 380.0}

    data = {}

    for symbol in sample_stock_symbols:
        base_price = base_prices[symbol]
        records = []

        current_date = start_date
        current_price = base_price

        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:
                # Add random walk
                change_pct = (hash(f"{symbol}{current_date}") % 200 - 100) / 1000.0
                current_price = current_price * (1 + change_pct)

                # Generate OHLCV
                daily_range = current_price * 0.02

                record = {
                    "symbol": symbol,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "timestamp": current_date.isoformat(),
                    "open": round(current_price - daily_range * 0.3, 2),
                    "high": round(current_price + daily_range * 0.7, 2),
                    "low": round(current_price - daily_range * 0.8, 2),
                    "close": round(current_price, 2),
                    "volume": int(50000000 + (hash(f"{symbol}{current_date}vol") % 30000000)),
                    "adjusted_close": round(current_price, 2),
                }

                records.append(record)

            current_date += timedelta(days=1)

        data[symbol] = records

    return data


@pytest.fixture
def sample_raw_kafka_message(sample_ohlcv_data) -> Dict[str, Any]:
    """Sample Kafka message for raw-stock-data topic."""
    aapl_data = sample_ohlcv_data["AAPL"]

    return {
        "symbol": "AAPL",
        "provider": "yahoo_finance",
        "data_type": "daily_ohlcv",
        "timestamp": datetime.now().isoformat(),
        "data": aapl_data[:5],  # Last 5 days
        "metadata": {"currency": "USD", "exchange": "NASDAQ", "timezone": "America/New_York"},
    }


# ==================== Mock External APIs ====================


@pytest.fixture
def mock_yahoo_finance():
    """Mock Yahoo Finance API responses."""

    def create_mock_ticker_data(symbol: str, price: float) -> Dict:
        return {
            "symbol": symbol,
            "longName": f"{symbol} Corporation",
            "currentPrice": price,
            "regularMarketPrice": price,
            "currency": "USD",
            "exchange": "NASDAQ",
            "marketCap": int(price * 1_000_000_000),
            "sector": "Technology",
            "industry": "Software",
            "regularMarketVolume": 50_000_000,
            "averageVolume": 45_000_000,
            "fiftyTwoWeekHigh": price * 1.15,
            "fiftyTwoWeekLow": price * 0.85,
            "trailingPE": 25.5,
            "dividendYield": 0.015,
            "beta": 1.2,
        }

    with patch("yfinance.Ticker") as mock_ticker:
        # Configure mock for different symbols
        def ticker_factory(symbol):
            mock_instance = MagicMock()
            prices = {"AAPL": 175.0, "MSFT": 380.0}
            mock_instance.info = create_mock_ticker_data(symbol, prices.get(symbol, 100.0))
            return mock_instance

        mock_ticker.side_effect = ticker_factory
        yield mock_ticker


@pytest.fixture
def mock_alpha_vantage():
    """Mock Alpha Vantage API responses."""

    async def mock_get(*args, **kwargs):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Meta Data": {
                "1. Information": "Daily Prices",
                "2. Symbol": "AAPL",
                "3. Last Refreshed": datetime.now().strftime("%Y-%m-%d"),
                "4. Output Size": "Compact",
            },
            "Time Series (Daily)": {
                datetime.now().strftime("%Y-%m-%d"): {
                    "1. open": "175.50",
                    "2. high": "178.25",
                    "3. low": "174.80",
                    "4. close": "177.10",
                    "5. volume": "52000000",
                }
            },
        }
        return mock_response

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        yield


# ==================== Helper Functions ====================


async def wait_for_kafka_message(
    consumer: AIOKafkaConsumer,
    timeout_ms: int = KAFKA_POLL_TIMEOUT,
    match_condition: callable = None,
) -> Dict[str, Any]:
    """
    Wait for a Kafka message matching condition.

    Args:
        consumer: Kafka consumer instance
        timeout_ms: Maximum wait time in milliseconds
        match_condition: Optional function to filter messages

    Returns:
        Decoded message data

    Raises:
        TimeoutError: If no matching message received
    """
    start_time = asyncio.get_event_loop().time()

    while True:
        elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
        if elapsed > timeout_ms:
            raise TimeoutError(f"No message received within {timeout_ms}ms")

        remaining_timeout = int(timeout_ms - elapsed)
        msg = await consumer.getone(timeout_ms=remaining_timeout)

        if msg:
            if match_condition is None or match_condition(msg.value):
                return msg.value

    raise TimeoutError("No matching message found")


async def verify_timescale_table_exists(session: AsyncSession, table_name: str) -> bool:
    """Check if TimescaleDB table exists."""
    query = text(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name = :table_name
        );
    """
    )

    result = await session.execute(query, {"table_name": table_name})
    return result.scalar()


async def count_timescale_records(
    session: AsyncSession, table_name: str, symbol: str = None
) -> int:
    """Count records in TimescaleDB table."""
    if symbol:
        query = text(f"SELECT COUNT(*) FROM {table_name} WHERE symbol = :symbol")
        result = await session.execute(query, {"symbol": symbol})
    else:
        query = text(f"SELECT COUNT(*) FROM {table_name}")
        result = await session.execute(query)

    return result.scalar()


@pytest.fixture
def cleanup_test_data(timescaledb_session, redis_client):
    """Cleanup test data after tests."""
    yield

    # Note: Actual cleanup would happen here if needed
    # For integration tests, we typically want to preserve data for debugging
    pass
