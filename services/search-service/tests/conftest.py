"""
Test configuration and fixtures
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.app import app
from app.database import get_db
from app.models import Base

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Drop all tables first to ensure clean state
    Base.metadata.drop_all(bind=engine)
    # Create all tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Mock init_db to prevent creating production database tables
    with patch("app.app.init_db"):
        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()


@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing"""
    return {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "isin": "US0378331005",
        "wkn": "865985",
        "current_price": 175.50,
        "currency": "USD",
        "exchange": "NASDAQ",
        "market_cap": 2800000000000,
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "source": "yahoo",
        "raw_data": {},
    }


@pytest.fixture
def mock_yahoo_response():
    """Mock Yahoo Finance API response"""
    return {
        "symbol": "AAPL",
        "longName": "Apple Inc.",
        "currentPrice": 175.50,
        "currency": "USD",
        "exchange": "NASDAQ",
        "marketCap": 2800000000000,
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "isin": "US0378331005",
    }
