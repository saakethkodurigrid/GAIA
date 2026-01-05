-- Migration: Fix analysis_status foreign key to cascade on delete
-- This ensures that when a candidate is deleted, their analysis_status records are automatically deleted

-- Drop the existing foreign key constraint
ALTER TABLE analysis_status 
DROP CONSTRAINT IF EXISTS analysis_status_candidate_id_fkey;

-- Add the foreign key constraint with CASCADE delete
ALTER TABLE analysis_status 
ADD CONSTRAINT analysis_status_candidate_id_fkey 
FOREIGN KEY (candidate_id) 
REFERENCES candidate(candidate_id) 
ON DELETE CASCADE;

