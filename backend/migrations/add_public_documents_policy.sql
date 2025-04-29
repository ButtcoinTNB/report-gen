-- Migration to add a more permissive policy for anonymous document creation

-- First check if policies exist before attempting to drop
DROP POLICY IF EXISTS "Users can view their own or public documents" ON documents;
DROP POLICY IF EXISTS "Users can create their own or public documents" ON documents;
DROP POLICY IF EXISTS "Users can update their own or public documents" ON documents;
DROP POLICY IF EXISTS "Users can delete their own or public documents" ON documents;

-- Drop old policies if they still exist
DROP POLICY IF EXISTS "Users can view their own documents" ON documents;
DROP POLICY IF EXISTS "Users can create their own documents" ON documents;
DROP POLICY IF EXISTS "Users can update their own documents" ON documents;
DROP POLICY IF EXISTS "Users can delete their own documents" ON documents;

-- Completely public policy for the demo environment
CREATE POLICY "Public documents access policy"
    ON documents FOR ALL
    USING (true)
    WITH CHECK (true);

-- Add comment to explain the policy
COMMENT ON TABLE documents IS 'Document records with public access for development; use stricter policies in production';

-- Set the created_by column to be nullable explicitly
ALTER TABLE documents 
ALTER COLUMN created_by DROP NOT NULL; 