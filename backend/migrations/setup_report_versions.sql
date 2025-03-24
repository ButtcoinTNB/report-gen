-- Create report_versions table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'report_versions'
    ) THEN
        CREATE TABLE report_versions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            report_id UUID NOT NULL REFERENCES reports(id),
            version_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            created_by UUID REFERENCES auth.users(id),
            changes_description TEXT,
            UNIQUE(report_id, version_number)
        );

        -- Add indexes
        CREATE INDEX idx_report_versions_report_id ON report_versions(report_id);
        CREATE INDEX idx_report_versions_version_number ON report_versions(version_number);
        CREATE INDEX idx_report_versions_created_at ON report_versions(created_at);

        -- Add current_version column to reports if it doesn't exist
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'reports' AND column_name = 'current_version'
        ) THEN
            ALTER TABLE reports
            ADD COLUMN current_version INTEGER NOT NULL DEFAULT 1;
        END IF;

        -- Enable RLS
        ALTER TABLE report_versions ENABLE ROW LEVEL SECURITY;

        -- Create RLS policies
        CREATE POLICY "Allow public to read report versions"
        ON report_versions FOR SELECT
        TO public
        USING (true);  -- Anyone can read report versions

        CREATE POLICY "Allow public to create report versions"
        ON report_versions FOR INSERT
        TO public
        WITH CHECK (true);  -- Anyone can create report versions

        -- Add comment
        COMMENT ON TABLE report_versions IS 'Stores version history for reports';
    END IF;
END $$; 