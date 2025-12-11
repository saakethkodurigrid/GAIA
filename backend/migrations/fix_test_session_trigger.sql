-- ============================================================================
-- Migration: Fix test_session trigger error
-- Purpose: Drop the update_test_session_updated_at trigger that references
--          a non-existent 'updated_at' column
-- Date: 2025-12-11
-- ============================================================================

-- Drop the problematic trigger if it exists
-- Note: The actual trigger name is 'trigger_update_test_session_updated_at'
DROP TRIGGER IF EXISTS trigger_update_test_session_updated_at ON test_session;

-- Drop the trigger function if it exists (CASCADE to handle dependencies)
DROP FUNCTION IF EXISTS update_test_session_updated_at() CASCADE;

-- Note: The test_session table uses 'last_activity' column instead of 'updated_at'
-- The application code already updates last_activity manually when needed.
-- Therefore, this trigger is not required.

-- Verification query (uncomment to run):
-- SELECT trigger_name, event_object_table, action_statement 
-- FROM information_schema.triggers 
-- WHERE event_object_table = 'test_session';

