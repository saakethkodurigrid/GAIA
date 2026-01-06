-- Migration: Add submission_json column to interview_coding table
-- Purpose: Store detailed submission data for each coding question
-- Date: 2026-01-05

-- Add submission_json column to store submission details
ALTER TABLE interview_coding
ADD COLUMN IF NOT EXISTS submission_json JSONB DEFAULT NULL;

-- Add comment to explain the column
COMMENT ON COLUMN interview_coding.submission_json IS 'Stores detailed submission data including test results, execution metadata, and errors. NULL indicates question was not submitted.';

-- Create index for faster queries on submission status
CREATE INDEX IF NOT EXISTS idx_interview_coding_submission_status 
ON interview_coding ((submission_json IS NOT NULL));

