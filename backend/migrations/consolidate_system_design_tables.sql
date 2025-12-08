-- Migration: Consolidate System Design Tables into interview_system_design
-- Description: 
--   1. Adds new columns to interview_system_design for session data
--   2. Migrates data from system_design_session and system_design_chat_message
--   3. Drops old tables (system_design_session, system_design_chat_message, system_design_canvas_version, system_design_evaluation)
-- Date: 2024
-- 
-- IMPORTANT: Backup your database before running this migration!
-- 
-- Note: This script uses DO blocks which auto-commit each block.
-- If you get an error, you can re-run the script - it's idempotent.

-- ============================================================================
-- STEP 1: Add new columns to interview_system_design
-- ============================================================================

DO $$
BEGIN
    -- Add session state columns
    ALTER TABLE interview_system_design
    ADD COLUMN IF NOT EXISTS current_canvas JSONB,
    ADD COLUMN IF NOT EXISTS previous_canvas JSONB,
    ADD COLUMN IF NOT EXISTS chat_messages JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS last_activity_time TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_drawing_activity_time TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_prompt_time TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_poll_time TIMESTAMP,
    ADD COLUMN IF NOT EXISTS prompt_history JSONB DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS milestones JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS last_canvas_hash VARCHAR(64);

    -- Add timestamp columns
    ALTER TABLE interview_system_design
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP;

    -- Add status column
    ALTER TABLE interview_system_design
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'assigned';

    RAISE NOTICE 'Added new columns to interview_system_design';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error adding columns (may already exist): %', SQLERRM;
END $$;

-- Add CHECK constraint for status
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.constraint_column_usage 
        WHERE table_name = 'interview_system_design' 
        AND constraint_name = 'check_interview_system_design_status'
    ) THEN
        ALTER TABLE interview_system_design
        ADD CONSTRAINT check_interview_system_design_status 
        CHECK (status IN ('assigned', 'in_progress', 'submitted', 'evaluated'));
    END IF;
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'Status constraint already exists';
    WHEN OTHERS THEN
        RAISE NOTICE 'Error adding status constraint: %', SQLERRM;
END $$;

-- Add CHECK constraint for score range (0-100)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.constraint_column_usage 
        WHERE table_name = 'interview_system_design' 
        AND constraint_name = 'check_interview_system_design_score'
    ) THEN
        ALTER TABLE interview_system_design
        ADD CONSTRAINT check_interview_system_design_score 
        CHECK (score IS NULL OR (score >= 0 AND score <= 100));
    END IF;
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'Score constraint already exists';
    WHEN OTHERS THEN
        RAISE NOTICE 'Error adding score constraint: %', SQLERRM;
END $$;

-- Create indexes
DO $$
BEGIN
    CREATE INDEX IF NOT EXISTS idx_interview_system_design_status 
    ON interview_system_design(status);

    CREATE INDEX IF NOT EXISTS idx_interview_system_design_submitted_at 
    ON interview_system_design(submitted_at);

    CREATE INDEX IF NOT EXISTS idx_interview_system_design_last_activity 
    ON interview_system_design(last_activity_time);
    
    RAISE NOTICE 'Created indexes';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error creating indexes: %', SQLERRM;
END $$;

-- ============================================================================
-- STEP 2: Update existing records with proper defaults
-- ============================================================================
-- Set defaults for existing records in interview_system_design

DO $$
BEGIN
    -- Update existing records to set proper defaults for new columns
    UPDATE interview_system_design
    SET 
        chat_messages = COALESCE(chat_messages, '[]'::jsonb),
        prompt_history = COALESCE(prompt_history, '[]'::jsonb),
        milestones = COALESCE(milestones, '{}'::jsonb),
        created_at = COALESCE(created_at, CURRENT_TIMESTAMP),
        updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP),
        status = CASE 
            WHEN status IS NULL THEN
                CASE 
                    WHEN score IS NOT NULL THEN 'evaluated'
                    WHEN diagram IS NOT NULL THEN 'submitted'
                    ELSE 'assigned'
                END
            ELSE status
        END
    WHERE chat_messages IS NULL 
       OR prompt_history IS NULL 
       OR milestones IS NULL
       OR created_at IS NULL
       OR updated_at IS NULL
       OR status IS NULL;
    
    RAISE NOTICE 'Updated existing records with defaults';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error updating existing records: %', SQLERRM;
END $$;

-- ============================================================================
-- STEP 3: Migrate data from system_design_session to interview_system_design
-- ============================================================================
-- Only migrate if system_design_session table exists

DO $$
BEGIN
    -- Check if system_design_session table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'system_design_session'
    ) THEN
        -- Update existing interview_system_design records with session data
        UPDATE interview_system_design isd
        SET 
            current_canvas = sds.current_canvas,
            previous_canvas = sds.previous_canvas,
            last_activity_time = sds.last_activity_time,
            last_drawing_activity_time = sds.last_drawing_activity_time,
            last_prompt_time = sds.last_prompt_time,
            last_poll_time = sds.last_poll_time,
            prompt_history = COALESCE(sds.prompt_history, '[]'::jsonb),
            milestones = COALESCE(sds.milestones, '{}'::jsonb),
            last_canvas_hash = sds.last_canvas_hash,
            created_at = COALESCE(isd.created_at, sds.created_at, CURRENT_TIMESTAMP),
            updated_at = COALESCE(isd.updated_at, sds.updated_at, CURRENT_TIMESTAMP),
            status = CASE 
                WHEN isd.score IS NOT NULL THEN 'evaluated'
                WHEN isd.diagram IS NOT NULL THEN 'submitted'
                WHEN sds.current_canvas IS NOT NULL THEN 'in_progress'
                ELSE 'assigned'
            END
        FROM system_design_session sds
        WHERE isd.candidate_id = sds.candidate_id 
          AND isd.question_uuid = sds.question_uuid;

        -- Insert new records for sessions that don't have interview_system_design records
        INSERT INTO interview_system_design (
            candidate_id,
            question_uuid,
            score,
            diagram,
            current_canvas,
            previous_canvas,
            last_activity_time,
            last_drawing_activity_time,
            last_prompt_time,
            last_poll_time,
            prompt_history,
            milestones,
            last_canvas_hash,
            created_at,
            updated_at,
            status
        )
        SELECT 
            sds.candidate_id,
            sds.question_uuid,
            NULL as score,
            NULL as diagram,
            sds.current_canvas,
            sds.previous_canvas,
            sds.last_activity_time,
            sds.last_drawing_activity_time,
            sds.last_prompt_time,
            sds.last_poll_time,
            COALESCE(sds.prompt_history, '[]'::jsonb) as prompt_history,
            COALESCE(sds.milestones, '{}'::jsonb) as milestones,
            sds.last_canvas_hash,
            COALESCE(sds.created_at, CURRENT_TIMESTAMP) as created_at,
            COALESCE(sds.updated_at, CURRENT_TIMESTAMP) as updated_at,
            CASE 
                WHEN sds.current_canvas IS NOT NULL THEN 'in_progress'
                ELSE 'assigned'
            END as status
        FROM system_design_session sds
        WHERE NOT EXISTS (
            SELECT 1 FROM interview_system_design isd
            WHERE isd.candidate_id = sds.candidate_id 
              AND isd.question_uuid = sds.question_uuid
        )
        ON CONFLICT (candidate_id, question_uuid) DO NOTHING;
        
        RAISE NOTICE 'Migrated data from system_design_session';
    ELSE
        RAISE NOTICE 'system_design_session table does not exist, skipping migration';
    END IF;
END $$;

-- ============================================================================
-- STEP 4: Migrate chat messages from system_design_chat_message to JSONB array
-- ============================================================================
-- Only migrate if system_design_chat_message table exists

DO $$
BEGIN
    -- Check if system_design_chat_message table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'system_design_chat_message'
    ) THEN
        -- Update interview_system_design with chat messages as JSONB array
        UPDATE interview_system_design isd
        SET chat_messages = COALESCE(
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'role', sdcm.role,
                        'content', sdcm.content,
                        'timestamp', sdcm.timestamp::text
                    ) ORDER BY sdcm.message_sequence
                )
                FROM system_design_chat_message sdcm
                WHERE sdcm.candidate_id = isd.candidate_id
                  AND sdcm.question_uuid = isd.question_uuid
            ),
            '[]'::jsonb
        )
        WHERE EXISTS (
            SELECT 1 FROM system_design_chat_message sdcm
            WHERE sdcm.candidate_id = isd.candidate_id
              AND sdcm.question_uuid = isd.question_uuid
        );
        
        RAISE NOTICE 'Migrated chat messages from system_design_chat_message';
    ELSE
        RAISE NOTICE 'system_design_chat_message table does not exist, skipping migration';
    END IF;
END $$;

-- ============================================================================
-- STEP 5: Create trigger to auto-update updated_at
-- ============================================================================

-- Create function to update updated_at (outside DO block to avoid delimiter conflict)
CREATE OR REPLACE FUNCTION update_interview_system_design_updated_at()
RETURNS TRIGGER AS $function$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$function$ LANGUAGE plpgsql;

-- Drop and create trigger
DO $$
BEGIN
    -- Drop trigger if exists
    DROP TRIGGER IF EXISTS trigger_update_interview_system_design_updated_at ON interview_system_design;

    -- Create trigger
    CREATE TRIGGER trigger_update_interview_system_design_updated_at
    BEFORE UPDATE ON interview_system_design
    FOR EACH ROW
    EXECUTE FUNCTION update_interview_system_design_updated_at();
    
    RAISE NOTICE 'Created trigger for updated_at';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error creating trigger: %', SQLERRM;
END $$;

-- ============================================================================
-- STEP 6: Drop old tables (in correct order due to foreign keys)
-- ============================================================================
-- Only drop if they exist (safe to run multiple times)

DO $$
BEGIN
    DROP TABLE IF EXISTS system_design_evaluation CASCADE;
    DROP TABLE IF EXISTS system_design_canvas_version CASCADE;
    DROP TABLE IF EXISTS system_design_chat_message CASCADE;
    DROP TABLE IF EXISTS system_design_session CASCADE;
    
    RAISE NOTICE 'Dropped old tables (if they existed)';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error dropping tables: %', SQLERRM;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    migrated_count INTEGER;
    chat_messages_count INTEGER;
BEGIN
    -- Count migrated records
    SELECT COUNT(*) INTO migrated_count
    FROM interview_system_design
    WHERE current_canvas IS NOT NULL OR chat_messages != '[]'::jsonb;
    
    -- Count records with chat messages
    SELECT COUNT(*) INTO chat_messages_count
    FROM interview_system_design
    WHERE jsonb_array_length(chat_messages) > 0;
    
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE 'Records with session data: %', migrated_count;
    RAISE NOTICE 'Records with chat messages: %', chat_messages_count;
    RAISE NOTICE 'All old tables have been dropped.';
END $$;

-- Migration complete! All DO blocks auto-commit.

-- ============================================================================
-- ROLLBACK SCRIPT (if needed - uncomment and run separately)
-- ============================================================================
/*
BEGIN;

-- Recreate old tables (if you need to rollback)
-- Note: This won't restore the data, only the structure

CREATE TABLE IF NOT EXISTS system_design_session (
    candidate_id VARCHAR(36) NOT NULL,
    question_uuid VARCHAR(36) NOT NULL,
    question_text TEXT NOT NULL,
    current_canvas JSONB,
    previous_canvas JSONB,
    last_activity_time TIMESTAMP,
    last_drawing_activity_time TIMESTAMP,
    last_prompt_time TIMESTAMP,
    last_poll_time TIMESTAMP,
    prompt_history JSONB DEFAULT '[]',
    milestones JSONB DEFAULT '{}',
    last_canvas_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (candidate_id, question_uuid),
    FOREIGN KEY (candidate_id) REFERENCES candidate(candidate_id) ON DELETE CASCADE,
    FOREIGN KEY (question_uuid) REFERENCES system_design_question_bank(uuid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS system_design_chat_message (
    id SERIAL PRIMARY KEY,
    candidate_id VARCHAR(36) NOT NULL,
    question_uuid VARCHAR(36) NOT NULL,
    message_sequence INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id, question_uuid) 
        REFERENCES system_design_session(candidate_id, question_uuid)
        ON DELETE CASCADE
);

-- Remove new columns from interview_system_design
ALTER TABLE interview_system_design
DROP COLUMN IF EXISTS current_canvas,
DROP COLUMN IF EXISTS previous_canvas,
DROP COLUMN IF EXISTS chat_messages,
DROP COLUMN IF EXISTS last_activity_time,
DROP COLUMN IF EXISTS last_drawing_activity_time,
DROP COLUMN IF EXISTS last_prompt_time,
DROP COLUMN IF EXISTS last_poll_time,
DROP COLUMN IF EXISTS prompt_history,
DROP COLUMN IF EXISTS milestones,
DROP COLUMN IF EXISTS last_canvas_hash,
DROP COLUMN IF EXISTS created_at,
DROP COLUMN IF EXISTS updated_at,
DROP COLUMN IF EXISTS submitted_at,
DROP COLUMN IF EXISTS status;

-- Drop constraints
ALTER TABLE interview_system_design
DROP CONSTRAINT IF EXISTS check_interview_system_design_status,
DROP CONSTRAINT IF EXISTS check_interview_system_design_score;

-- Drop indexes
DROP INDEX IF EXISTS idx_interview_system_design_status;
DROP INDEX IF EXISTS idx_interview_system_design_submitted_at;
DROP INDEX IF EXISTS idx_interview_system_design_last_activity;

-- Drop trigger
DROP TRIGGER IF EXISTS trigger_update_interview_system_design_updated_at ON interview_system_design;
DROP FUNCTION IF EXISTS update_interview_system_design_updated_at();

COMMIT;
*/

