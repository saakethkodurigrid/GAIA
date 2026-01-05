-- Migration: Create analysis_status table for tracking analysis execution status
-- Created: 2024
-- Description: Adds explicit status tracking for section analysis (MCQ, CODING, SYSTEM_DESIGN) 
--              and final analysis with states: not_started, in_progress, completed, failed

-- Create analysis_status table
CREATE TABLE IF NOT EXISTS analysis_status (
    id VARCHAR(36) PRIMARY KEY,
    candidate_id VARCHAR(36) NOT NULL,
    section_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraint
    CONSTRAINT fk_analysis_status_candidate 
        FOREIGN KEY (candidate_id) 
        REFERENCES candidate(candidate_id) 
        ON DELETE CASCADE,
    
    -- Check constraints
    CONSTRAINT check_analysis_status 
        CHECK (status IN ('not_started', 'in_progress', 'completed', 'failed')),
    CONSTRAINT check_section_type 
        CHECK (section_type IN ('MCQ', 'CODING', 'SYSTEM_DESIGN', 'FINAL')),
    
    -- Unique constraint: one status record per candidate per section type
    CONSTRAINT uq_candidate_section 
        UNIQUE (candidate_id, section_type)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_candidate_id ON analysis_status(candidate_id);
CREATE INDEX IF NOT EXISTS idx_section_type ON analysis_status(section_type);
CREATE INDEX IF NOT EXISTS idx_status ON analysis_status(status);
CREATE INDEX IF NOT EXISTS idx_candidate_section ON analysis_status(candidate_id, section_type);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_analysis_status_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_analysis_status_updated_at
    BEFORE UPDATE ON analysis_status
    FOR EACH ROW
    EXECUTE FUNCTION update_analysis_status_updated_at();

-- Add comment to table
COMMENT ON TABLE analysis_status IS 'Tracks the execution status of analysis for each section (MCQ, CODING, SYSTEM_DESIGN) and final analysis per candidate';
COMMENT ON COLUMN analysis_status.candidate_id IS 'Foreign key to candidate table';
COMMENT ON COLUMN analysis_status.section_type IS 'Type of section: MCQ, CODING, SYSTEM_DESIGN, or FINAL';
COMMENT ON COLUMN analysis_status.status IS 'Current status: not_started, in_progress, completed, or failed';
COMMENT ON COLUMN analysis_status.started_at IS 'Timestamp when analysis started';
COMMENT ON COLUMN analysis_status.completed_at IS 'Timestamp when analysis completed (or failed)';

