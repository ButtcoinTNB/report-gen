-- This migration script updates RLS policies for the documents table to handle null created_by values
-- This allows anonymous access while maintaining RLS for authenticated users

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view their own documents" ON documents;
DROP POLICY IF EXISTS "Users can create their own documents" ON documents;
DROP POLICY IF EXISTS "Users can update their own documents" ON documents;
DROP POLICY IF EXISTS "Users can delete their own documents" ON documents;

-- Create updated policies
-- For select, allow users to see their own documents or public documents (null created_by)
CREATE POLICY "Users can view their own or public documents"
    ON documents FOR SELECT
    USING (auth.uid() = created_by OR created_by IS NULL);

-- For insert, allow creating documents with user's id or null (for anonymous)
CREATE POLICY "Users can create their own or public documents"
    ON documents FOR INSERT
    WITH CHECK (auth.uid() = created_by OR created_by IS NULL);

-- For update, allow updating own documents or public documents
CREATE POLICY "Users can update their own or public documents"
    ON documents FOR UPDATE
    USING (auth.uid() = created_by OR created_by IS NULL);

-- For delete, allow deleting own documents or public documents
CREATE POLICY "Users can delete their own or public documents"
    ON documents FOR DELETE
    USING (auth.uid() = created_by OR created_by IS NULL);

-- Add helpful comments
COMMENT ON TABLE documents IS 'Document records that support both authenticated and anonymous access'; 