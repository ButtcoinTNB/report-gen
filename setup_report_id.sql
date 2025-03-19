-- This SQL script adds the report_id column to your reports table
-- Run this in the Supabase SQL Editor

-- Only add the column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'reports' AND column_name = 'report_id'
    ) THEN
        -- Add the report_id column
        ALTER TABLE reports
        ADD COLUMN report_id UUID NOT NULL DEFAULT gen_random_uuid();
        
        -- Add UNIQUE constraint
        ALTER TABLE reports 
        ADD CONSTRAINT reports_report_id_unique UNIQUE (report_id);
        
        -- Add comment
        COMMENT ON COLUMN reports.report_id IS 'UUID identifier for reports, used as external ID';
    END IF;
END $$;

-- Create the UUID generation function for the trigger
CREATE OR REPLACE FUNCTION set_report_uuid()
RETURNS TRIGGER AS $$
BEGIN
  -- Only set report_id if it's NULL
  IF NEW.report_id IS NULL THEN
    NEW.report_id := gen_random_uuid();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Only create the trigger if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_trigger 
        WHERE tgname = 'ensure_report_has_uuid'
    ) THEN
        CREATE TRIGGER ensure_report_has_uuid
        BEFORE INSERT ON reports
        FOR EACH ROW
        EXECUTE FUNCTION set_report_uuid();
    END IF;
END $$;

-- Create indexes (using IF NOT EXISTS)
CREATE INDEX IF NOT EXISTS reports_id_idx ON reports(id);
CREATE INDEX IF NOT EXISTS reports_report_id_idx ON reports(report_id);

-- Verify the setup
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM 
    information_schema.columns
WHERE 
    table_name = 'reports' AND column_name = 'report_id';

-- Verify the index
SELECT 
    indexname, 
    indexdef
FROM 
    pg_indexes
WHERE 
    tablename = 'reports' AND indexdef LIKE '%report_id%';

-- Verify the trigger
SELECT 
    trigger_name, 
    event_manipulation, 
    action_statement
FROM 
    information_schema.triggers
WHERE 
    event_object_table = 'reports'; 