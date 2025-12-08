-- NyayamGPT Database Initialization Script
-- This script runs when PostgreSQL container starts for the first time

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better search performance
-- (These will be created after tables are created by SQLAlchemy migrations)

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE nyayamgpt TO nyayam;

-- Create a read-only user for analytics (optional)
-- CREATE USER nyayam_readonly WITH PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE nyayamgpt TO nyayam_readonly;
-- GRANT USAGE ON SCHEMA public TO nyayam_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO nyayam_readonly;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'NyayamGPT database initialized successfully';
END $$;
