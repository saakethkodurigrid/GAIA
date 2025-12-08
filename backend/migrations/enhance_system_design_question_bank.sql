-- Migration: Enhance system_design_question_bank table for better chat conversations
-- Description: Adds columns to make AI responses more contextual and question-specific
-- Run this in pgAdmin Query Tool

-- ============================================================================
-- STEP 1: Add new columns to system_design_question_bank
-- ============================================================================

DO $$ 
BEGIN
    -- Domain/Category: Categorize questions (e.g., 'hld', 'agentic-ai', 'distributed-systems')
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' AND column_name = 'domain'
    ) THEN
        ALTER TABLE system_design_question_bank 
        ADD COLUMN domain VARCHAR(50);
        
        RAISE NOTICE 'Added domain column';
    ELSE
        RAISE NOTICE 'Column domain already exists';
    END IF;

    -- Complexity: Explicit complexity level (e.g., 'easy', 'normal', 'hard')
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' AND column_name = 'complexity'
    ) THEN
        ALTER TABLE system_design_question_bank 
        ADD COLUMN complexity VARCHAR(20);
        
        RAISE NOTICE 'Added complexity column';
    ELSE
        RAISE NOTICE 'Column complexity already exists';
    END IF;

    -- Estimated time: Expected interview duration in minutes
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' AND column_name = 'estimated_time_minutes'
    ) THEN
        ALTER TABLE system_design_question_bank 
        ADD COLUMN estimated_time_minutes INTEGER;
        
        RAISE NOTICE 'Added estimated_time_minutes column';
    ELSE
        RAISE NOTICE 'Column estimated_time_minutes already exists';
    END IF;

    -- Guidance prompts: Question-specific guidance for AI interviewer (JSONB)
    -- Structure: {"core_functionality": ["guidance1", "guidance2"], "architecture": [...], ...}
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' AND column_name = 'guidance_prompts'
    ) THEN
        ALTER TABLE system_design_question_bank 
        ADD COLUMN guidance_prompts JSONB DEFAULT '{}'::jsonb;
        
        RAISE NOTICE 'Added guidance_prompts column';
    ELSE
        RAISE NOTICE 'Column guidance_prompts already exists';
    END IF;

    -- Expected components: Key components that should appear in the design (JSONB array)
    -- Example: ["load balancer", "cache", "database", "CDN"]
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' AND column_name = 'expected_components'
    ) THEN
        ALTER TABLE system_design_question_bank 
        ADD COLUMN expected_components JSONB DEFAULT '[]'::jsonb;
        
        RAISE NOTICE 'Added expected_components column';
    ELSE
        RAISE NOTICE 'Column expected_components already exists';
    END IF;

    -- Common pitfalls: What candidates often miss (JSONB object)
    -- Structure: {"pitfall_name": "description", ...}
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' AND column_name = 'common_pitfalls'
    ) THEN
        ALTER TABLE system_design_question_bank 
        ADD COLUMN common_pitfalls JSONB DEFAULT '{}'::jsonb;
        
        RAISE NOTICE 'Added common_pitfalls column';
    ELSE
        RAISE NOTICE 'Column common_pitfalls already exists';
    END IF;

    -- Hints: Progressive hints for stuck candidates (JSONB object)
    -- Structure: {"level_1": "hint1", "level_2": "hint2", ...}
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' AND column_name = 'hints'
    ) THEN
        ALTER TABLE system_design_question_bank 
        ADD COLUMN hints JSONB DEFAULT '{}'::jsonb;
        
        RAISE NOTICE 'Added hints column';
    ELSE
        RAISE NOTICE 'Column hints already exists';
    END IF;

    -- Proactive prompt templates: Templates for proactive prompts (JSONB object)
    -- Structure: {"canvas_change": "template", "milestone": "template", ...}
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' AND column_name = 'proactive_prompt_templates'
    ) THEN
        ALTER TABLE system_design_question_bank 
        ADD COLUMN proactive_prompt_templates JSONB DEFAULT '{}'::jsonb;
        
        RAISE NOTICE 'Added proactive_prompt_templates column';
    ELSE
        RAISE NOTICE 'Column proactive_prompt_templates already exists';
    END IF;

    -- Functional requirements template: Template to guide candidates on functional requirements
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' AND column_name = 'functional_requirements_template'
    ) THEN
        ALTER TABLE system_design_question_bank 
        ADD COLUMN functional_requirements_template TEXT;
        
        RAISE NOTICE 'Added functional_requirements_template column';
    ELSE
        RAISE NOTICE 'Column functional_requirements_template already exists';
    END IF;

    -- Non-functional requirements template: Template to guide candidates on non-functional requirements
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' AND column_name = 'non_functional_requirements_template'
    ) THEN
        ALTER TABLE system_design_question_bank 
        ADD COLUMN non_functional_requirements_template TEXT;
        
        RAISE NOTICE 'Added non_functional_requirements_template column';
    ELSE
        RAISE NOTICE 'Column non_functional_requirements_template already exists';
    END IF;

    -- Evaluation context: Additional context for evaluator (JSONB)
    -- Structure: {"domain_specific_notes": "...", "scoring_tips": "...", ...}
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' AND column_name = 'evaluation_context'
    ) THEN
        ALTER TABLE system_design_question_bank 
        ADD COLUMN evaluation_context JSONB DEFAULT '{}'::jsonb;
        
        RAISE NOTICE 'Added evaluation_context column';
    ELSE
        RAISE NOTICE 'Column evaluation_context already exists';
    END IF;

END $$;

-- ============================================================================
-- STEP 2: Populate domain and complexity from existing UUIDs
-- ============================================================================

DO $$ 
BEGIN
    -- Extract domain and complexity from UUID patterns
    -- Pattern: "q{number}-{complexity}-{domain}-{description}"
    UPDATE system_design_question_bank
    SET 
        domain = CASE 
            WHEN uuid LIKE 'q1-%' OR uuid LIKE 'q2-%' OR uuid LIKE 'q3-%' OR uuid LIKE 'q4-%' OR uuid LIKE 'q5-%' THEN 'hld'
            WHEN uuid LIKE 'q6-%' OR uuid LIKE 'q7-%' OR uuid LIKE 'q8-%' OR uuid LIKE 'q9-%' OR uuid LIKE 'q10-%' THEN 'agentic-ai'
            ELSE 'general'
        END,
        complexity = CASE 
            WHEN uuid LIKE '%-easy-%' THEN 'easy'
            WHEN uuid LIKE '%-normal-%' OR uuid LIKE '%-medium-%' THEN 'normal'
            WHEN uuid LIKE '%-hard-%' THEN 'hard'
            ELSE 'normal'
        END,
        estimated_time_minutes = CASE 
            WHEN uuid LIKE '%-easy-%' THEN 30
            WHEN uuid LIKE '%-normal-%' OR uuid LIKE '%-medium-%' THEN 45
            WHEN uuid LIKE '%-hard-%' THEN 60
            ELSE 45
        END
    WHERE domain IS NULL OR complexity IS NULL;
    
    RAISE NOTICE 'Populated domain, complexity, and estimated_time_minutes from UUID patterns';
END $$;

-- ============================================================================
-- STEP 3: Add indexes for better query performance
-- ============================================================================

DO $$ 
BEGIN
    -- Index on domain for filtering
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'system_design_question_bank' AND indexname = 'idx_system_design_question_bank_domain'
    ) THEN
        CREATE INDEX idx_system_design_question_bank_domain ON system_design_question_bank(domain);
        RAISE NOTICE 'Created index on domain';
    END IF;

    -- Index on complexity for filtering
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'system_design_question_bank' AND indexname = 'idx_system_design_question_bank_complexity'
    ) THEN
        CREATE INDEX idx_system_design_question_bank_complexity ON system_design_question_bank(complexity);
        RAISE NOTICE 'Created index on complexity';
    END IF;

    -- GIN index on JSONB columns for efficient JSON queries
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'system_design_question_bank' AND indexname = 'idx_system_design_question_bank_tags_gin'
    ) THEN
        CREATE INDEX idx_system_design_question_bank_tags_gin ON system_design_question_bank USING GIN(tags);
        RAISE NOTICE 'Created GIN index on tags';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'system_design_question_bank' AND indexname = 'idx_system_design_question_bank_guidance_prompts_gin'
    ) THEN
        CREATE INDEX idx_system_design_question_bank_guidance_prompts_gin ON system_design_question_bank USING GIN(guidance_prompts);
        RAISE NOTICE 'Created GIN index on guidance_prompts';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'system_design_question_bank' AND indexname = 'idx_system_design_question_bank_expected_components_gin'
    ) THEN
        CREATE INDEX idx_system_design_question_bank_expected_components_gin ON system_design_question_bank USING GIN(expected_components);
        RAISE NOTICE 'Created GIN index on expected_components';
    END IF;

END $$;

-- ============================================================================
-- STEP 4: Verify migration and check ALL columns including evaluation_criteria
-- ============================================================================

DO $$ 
BEGIN
    RAISE NOTICE 'Migration completed. Verifying columns...';
    
    -- Check if evaluation_criteria exists (it should - it's an original column)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'system_design_question_bank' 
        AND column_name = 'evaluation_criteria'
    ) THEN
        RAISE WARNING '⚠️  WARNING: evaluation_criteria column is MISSING! This is a critical column.';
        RAISE WARNING 'Run ensure_evaluation_criteria.sql to add it back.';
    ELSE
        RAISE NOTICE '✅ evaluation_criteria column exists (as expected)';
    END IF;
    
    -- Check all new columns exist
    PERFORM column_name 
    FROM information_schema.columns 
    WHERE table_name = 'system_design_question_bank' 
    AND column_name IN (
        'domain', 'complexity', 'estimated_time_minutes', 
        'guidance_prompts', 'expected_components', 'common_pitfalls', 
        'hints', 'proactive_prompt_templates', 
        'functional_requirements_template', 'non_functional_requirements_template',
        'evaluation_context'
    );
    
    RAISE NOTICE 'All new columns verified successfully!';
END $$;

-- ============================================================================
-- View ALL columns including evaluation_criteria
-- ============================================================================

-- Show all columns in the table
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'system_design_question_bank'
ORDER BY ordinal_position;

-- ============================================================================
-- View current data structure (including evaluation_criteria)
-- ============================================================================

SELECT 
    uuid,
    LEFT(question, 50) as question_preview,
    CASE 
        WHEN evaluation_criteria IS NOT NULL THEN 
            LEFT(evaluation_criteria, 80) || '...'
        ELSE 'NULL'
    END as evaluation_criteria_preview,
    domain,
    complexity,
    estimated_time_minutes,
    CASE WHEN guidance_prompts IS NOT NULL AND guidance_prompts != '{}'::jsonb THEN 'Yes' ELSE 'No' END as has_guidance,
    CASE WHEN expected_components IS NOT NULL AND expected_components != '[]'::jsonb THEN 'Yes' ELSE 'No' END as has_components
FROM system_design_question_bank
ORDER BY uuid;

