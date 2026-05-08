-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create database role for application
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'adwp_app') THEN
    CREATE ROLE adwp_app WITH LOGIN PASSWORD 'adwp_dev_password';
  END IF;
END
$$;

GRANT ALL PRIVILEGES ON DATABASE adwp_dev TO adwp_app;
