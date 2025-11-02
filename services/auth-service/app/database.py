import os

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

# Check for local development mode
USE_LOCAL_DB = os.getenv("USE_LOCAL_DB", "false").lower() == "true"

if USE_LOCAL_DB:
    print("🔧 LOCAL DEVELOPMENT MODE - Using local database")
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://srs_admin:local_dev_password@localhost:5432/srs_db",
    )
    print(f"Using local database: {db_url.split('@')[0] if '@' in db_url else db_url}")
else:
    # Try to get connection string from Vault, fallback to environment variables
    try:
        print("Attempting to import Vault KV module...")
        from .vault_kv import get_db_connection_string

        print("Vault KV module imported successfully")
        try:
            print("Calling get_db_connection_string()...")
            db_url = get_db_connection_string()
            print("Using database credentials from Vault")
        except Exception as vault_error:
            print(f"Could not read from Vault KV: {vault_error}")
            print("   Falling back to environment variables...")
            # Fallback to environment variables or SQLite for development
            db_url = os.getenv(
                "DATABASE_URL",
                "sqlite:///./test.db",  # Default to SQLite for local development
            )
            print(
                f"Using database URL: {db_url.split('@')[0] if '@' in db_url else db_url}"
            )
    except ImportError as e:
        print(f"Vault module not available: {e}")
        # Fallback to environment variables or SQLite for development
        db_url = os.getenv(
            "DATABASE_URL",
            "sqlite:///./test.db",  # Default to SQLite for local development
        )
        print(
            f"Using database URL: {db_url.split('@')[0] if '@' in db_url else db_url}"
        )

# Use with SQLAlchemy
print("Creating SQLAlchemy engine...")

# Add connection settings with timeout
connect_args = {}
if db_url.startswith("postgresql"):
    # PostgreSQL-specific settings
    connect_args = {
        "connect_timeout": 10,  # 10 second connection timeout
    }
    print("Connecting to PostgreSQL with 10s timeout...")
elif db_url.startswith("sqlite"):
    # SQLite-specific settings
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
)
print("SQLAlchemy engine created successfully")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Association table for many-to-many relationship between users and roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("role_id", Integer, ForeignKey("roles.id")),
)


class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    roles = relationship("DBRole", secondary=user_roles, back_populates="users")


class DBRole(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)

    users = relationship("DBUser", secondary=user_roles, back_populates="roles")


# Create tables
Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
