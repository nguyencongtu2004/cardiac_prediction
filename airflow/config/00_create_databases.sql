-- 00_create_databases.sql
-- ======================================
-- Create additional databases for the system
-- This runs on the default 'airflow' database first
-- ======================================

-- Create traffic_monitoring database if it doesn't exist
-- Note: PostgreSQL doesn't support IF NOT EXISTS for CREATE DATABASE in a script
-- So we use this workaround with DO block

SELECT 'CREATE DATABASE traffic_monitoring OWNER airflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'traffic_monitoring')\gexec

-- Grant all privileges to airflow user
GRANT ALL PRIVILEGES ON DATABASE traffic_monitoring TO airflow;
