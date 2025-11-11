-- Initialize QNT9 Search Database
-- This script is automatically run when the PostgreSQL container starts

-- Create database if it doesn't exist (handled by POSTGRES_DB env var)
-- This file can be used for additional initialization

-- Set default configuration
ALTER DATABASE qnt9_search SET timezone TO 'UTC';

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE qnt9_search TO qnt9_user;

-- Log initialization
SELECT 'Database qnt9_search initialized successfully' AS status;
