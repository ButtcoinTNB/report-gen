-- Add document_ids column to reports table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'reports' AND column_name = 'document_ids'
    ) THEN
        -- Add the document_ids column as a UUID array
        ALTER TABLE reports
        ADD COLUMN document_ids UUID[] DEFAULT ARRAY[]::UUID[];
        
        -- Add index for faster lookups
        CREATE INDEX IF NOT EXISTS idx_reports_document_ids ON reports USING GIN (document_ids);
        
        -- Add comment
        COMMENT ON COLUMN reports.document_ids IS 'Array of document UUIDs associated with this report';
    END IF;
END $$; 