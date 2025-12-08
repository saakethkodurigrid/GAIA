-- Script: Ensure evaluation_criteria column exists
-- This script checks if evaluation_criteria exists and adds it if missing
-- Run this in pgAdmin if evaluation_criteria is missing

-- ============================================================================
-- STEP 1: Check if evaluation_criteria exists
-- ============================================================================

DO $$ 
BEGIN
    -- Check if column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' 
        AND column_name = 'evaluation_criteria'
    ) THEN
        -- Column doesn't exist, add it
        RAISE NOTICE 'evaluation_criteria column does NOT exist. Adding it now...';
        
        ALTER TABLE system_design_question_bank 
        ADD COLUMN evaluation_criteria TEXT NOT NULL DEFAULT '';
        
        RAISE NOTICE '✅ Added evaluation_criteria column';
        
        -- Warn that existing rows have empty evaluation_criteria
        RAISE WARNING '⚠️  WARNING: Existing rows now have empty evaluation_criteria. You need to populate them manually.';
    ELSE
        RAISE NOTICE '✅ evaluation_criteria column already exists';
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Verify the column exists and show its properties
-- ============================================================================

SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    CASE 
        WHEN column_name = 'evaluation_criteria' THEN '✅ FOUND'
        ELSE ''
    END as status
FROM information_schema.columns
WHERE table_name = 'system_design_question_bank'
AND column_name = 'evaluation_criteria';

-- ============================================================================
-- STEP 3: Show current data (if column exists)
-- ============================================================================

SELECT 
    uuid,
    LEFT(question, 60) as question_preview,
    CASE 
        WHEN evaluation_criteria IS NULL THEN 'NULL'
        WHEN evaluation_criteria = '' THEN 'EMPTY'
        ELSE LEFT(evaluation_criteria, 100) || '...'
    END as evaluation_criteria_status,
    LENGTH(COALESCE(evaluation_criteria, '')) as criteria_length
FROM system_design_question_bank
ORDER BY uuid
LIMIT 5;

