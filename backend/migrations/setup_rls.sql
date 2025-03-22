-- Create extension for UUID generation if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create extension for cron jobs if not exists
CREATE EXTENSION IF NOT EXISTS "pg_cron";

-- Create tables if they don't exist
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT,
    description TEXT,
    reference_report_id UUID REFERENCES reference_reports(id),
    storage_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),
    files_cleaned BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS reference_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT,
    description TEXT,
    template_id UUID REFERENCES templates(id),
    storage_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);

CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT,
    description TEXT,
    storage_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at);
CREATE INDEX IF NOT EXISTS idx_reports_reference_report_id ON reports(reference_report_id);
CREATE INDEX IF NOT EXISTS idx_reports_created_by ON reports(created_by);

CREATE INDEX IF NOT EXISTS idx_reference_reports_template_id ON reference_reports(template_id);
CREATE INDEX IF NOT EXISTS idx_reference_reports_created_by ON reference_reports(created_by);

CREATE INDEX IF NOT EXISTS idx_templates_created_by ON templates(created_by);

-- Enable RLS on all tables
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE reference_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;

-- Drop existing policies before recreating them
DROP POLICY IF EXISTS "Allow public to create reports" ON reports;
DROP POLICY IF EXISTS "Allow public to read reports" ON reports;
DROP POLICY IF EXISTS "Allow public to update their own reports" ON reports;
DROP POLICY IF EXISTS "Allow public to create reports with rate limit" ON reports;

DROP POLICY IF EXISTS "Allow public to read reference reports" ON reference_reports;
DROP POLICY IF EXISTS "Allow public to read templates" ON templates;

-- Create policies for public access to reports table
CREATE POLICY "Allow public to read reports"
ON reports FOR SELECT
TO public
USING (true);  -- Anyone can read reports

CREATE POLICY "Allow public to update their own reports"
ON reports FOR UPDATE
TO public
USING (created_at > NOW() - INTERVAL '24 hours')  -- Can only update reports created in last 24 hours
WITH CHECK (created_at > NOW() - INTERVAL '24 hours');

-- Create policies for public access to reference_reports table
CREATE POLICY "Allow public to read reference reports"
ON reference_reports FOR SELECT
TO public
USING (true);  -- Anyone can read reference reports

-- Create policies for public access to templates table
CREATE POLICY "Allow public to read templates"
ON templates FOR SELECT
TO public
USING (true);  -- Anyone can read templates

-- Add rate limiting function
CREATE OR REPLACE FUNCTION check_rate_limit(
    ip_address text,
    requests_limit integer DEFAULT 100,
    time_window interval DEFAULT interval '1 hour'
)
RETURNS boolean AS $$
DECLARE
    recent_requests integer;
BEGIN
    -- Get count of requests from this IP in the time window
    SELECT COUNT(*)
    INTO recent_requests
    FROM (
        SELECT created_at
        FROM reports
        WHERE metadata->>'ip_address' = ip_address
        AND created_at > NOW() - time_window
        LIMIT requests_limit + 1
    ) AS recent;

    -- Return true if under limit
    RETURN recent_requests <= requests_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add cleanup function for old data
CREATE OR REPLACE FUNCTION cleanup_old_data(max_age_hours integer DEFAULT 24)
RETURNS void AS $$
BEGIN
    -- Soft delete old reports by marking files_cleaned
    UPDATE reports
    SET files_cleaned = true
    WHERE created_at < NOW() - (max_age_hours || ' hours')::interval
    AND files_cleaned = false;

    -- Hard delete very old reports (7 days)
    DELETE FROM reports
    WHERE created_at < NOW() - INTERVAL '7 days'
    AND files_cleaned = true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop existing cron job if it exists
SELECT cron.unschedule('cleanup-old-data');

-- Create a cron job to run cleanup every hour
SELECT cron.schedule(
    'cleanup-old-data',         -- job name
    '0 * * * *',               -- run every hour
    'SELECT cleanup_old_data(24);'  -- SQL command to run
);

-- Create rate-limited insert policy
CREATE POLICY "Allow public to create reports with rate limit"
ON reports FOR INSERT
TO public
WITH CHECK (
    check_rate_limit(current_setting('request.headers')::json->>'x-real-ip')
);

-- Add comment explaining the setup
COMMENT ON TABLE reports IS 'Public reports table with rate limiting. No authentication required.';
COMMENT ON TABLE reference_reports IS 'Public reference reports table. Read-only access.';
COMMENT ON TABLE templates IS 'Public templates table. Read-only access.'; 