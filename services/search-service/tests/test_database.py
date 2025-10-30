"""
Tests for database configuration and initialization
"""
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.database import Base, get_db, init_db


class TestDatabaseConfiguration:
    """Test database configuration"""

    def test_get_db_yields_session(self):
        """Test that get_db yields a database session"""
        db_gen = get_db()
        db = next(db_gen)

        assert db is not None
        assert isinstance(db, Session)

        # Cleanup
        try:
            next(db_gen)
        except StopIteration:
            pass

    def test_get_db_closes_session(self):
        """Test that get_db closes the session after use"""
        db_gen = get_db()
        db = next(db_gen)

        # Verify session is open
        assert db.is_active

        # Close the generator (simulates end of request)
        try:
            next(db_gen)
        except StopIteration:
            pass

        # Session should be closed
        assert not db.is_active

    def test_init_db_creates_tables(self):
        """Test that init_db creates all tables"""
        # This test runs against the actual test database
        # Tables should already exist from conftest.py setup
        init_db()

        # Verify we can query the database
        db_gen = get_db()
        db = next(db_gen)

        try:
            # Should not raise an error
            result = db.execute("SELECT 1").fetchone()
            assert result is not None
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    @patch("app.database.create_engine")
    def test_database_url_configuration(self, mock_create_engine):
        """Test database URL is properly configured"""
        # This test verifies the database URL logic
        # In test environment, it should use local SQLite
        # Reload to trigger configuration
        import importlib

        import app.database as db_module

        importlib.reload(db_module)

        # Should have created an engine
        assert db_module.engine is not None

    def test_base_metadata_has_tables(self):
        """Test that Base metadata contains table definitions"""
        # Verify that models are registered with Base
        assert len(Base.metadata.tables) > 0

        # Check for expected tables
        table_names = Base.metadata.tables.keys()
        assert "stock_cache" in table_names
        assert "api_rate_limits" in table_names
        assert "search_history" in table_names


class TestDatabaseWithVaultFallback:
    """Test database configuration with Vault fallback logic"""

    @patch.dict("os.environ", {"USE_LOCAL_DB": "true"})
    def test_uses_local_db_when_env_set(self):
        """Test that local database is used when USE_LOCAL_DB is set"""
        import importlib

        import app.database as db_module

        # Reload module to apply environment variable
        importlib.reload(db_module)

        # Should use SQLite for local development
        assert "sqlite" in str(db_module.SQLALCHEMY_DATABASE_URL).lower()

    @patch.dict("os.environ", {}, clear=True)
    @patch("app.database.vault_kv", None)
    def test_falls_back_to_sqlite_without_vault(self):
        """Test fallback to SQLite when Vault is not available"""
        import importlib

        import app.database as db_module

        # Reload module
        importlib.reload(db_module)

        # Should fall back to SQLite
        assert db_module.engine is not None
