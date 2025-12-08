-- Data Population Script: Populate enhanced columns for system_design_question_bank
-- Description: Adds question-specific guidance, components, pitfalls, and hints based on existing questions
-- Run this AFTER running enhance_system_design_question_bank.sql

-- ============================================================================
-- URL Shortener (q1-normal-hld-url-shortener)
-- ============================================================================

UPDATE system_design_question_bank
SET 
    guidance_prompts = '{
        "core_functionality": [
            "URL encoding/decoding mechanism (hash function, base62/base64, etc.)",
            "Short URL generation and storage",
            "Original URL retrieval and redirection"
        ],
        "architecture": [
            "API design (RESTful endpoints)",
            "Database schema and data modeling",
            "Caching strategy (for frequently accessed URLs)",
            "Load balancing and horizontal scaling"
        ],
        "scalability": [
            "Handling high write throughput (URL creation)",
            "Handling high read throughput (URL redirection)",
            "Database partitioning/sharding strategy",
            "CDN usage for static content"
        ]
    }'::jsonb,
    expected_components = '["API Gateway", "Load Balancer", "Application Server", "Database", "Cache (Redis)", "CDN"]'::jsonb,
    common_pitfalls = '{
        "hash_collisions": "Not considering hash collisions and how to handle them",
        "url_expiration": "Not discussing URL expiration or TTL",
        "custom_urls": "Missing discussion of custom/short URLs",
        "rate_limiting": "Not mentioning rate limiting for abuse prevention",
        "redirect_301_vs_302": "Not explaining 301 (permanent) vs 302 (temporary) redirects"
    }'::jsonb,
    hints = '{
        "level_1": "Think about how you would convert a long URL into a short one. What mathematical operation could help?",
        "level_2": "Consider what happens when multiple users try to shorten the same URL. How would you handle duplicates?",
        "level_3": "What if someone wants a custom short URL? How would that change your design?"
    }'::jsonb,
    functional_requirements_template = 'Consider: URL shortening, URL redirection, custom URLs, URL expiration, analytics',
    non_functional_requirements_template = 'Consider: Scale (billions of URLs), Performance (low latency redirects), Availability (99.9%+), Security (prevent abuse)',
    evaluation_context = '{
        "domain_specific_notes": "URL shorteners are classic distributed systems problems. Focus on hash algorithms, collision handling, and read/write optimization.",
        "scoring_tips": "Strong candidates will discuss base62/base64 encoding, hash collision strategies, and CDN for redirects."
    }'::jsonb
WHERE uuid = 'q1-normal-hld-url-shortener';

-- ============================================================================
-- Distributed Cache (q2-normal-hld-distributed-cache)
-- ============================================================================

UPDATE system_design_question_bank
SET 
    guidance_prompts = '{
        "core_functionality": [
            "Cache operations (get, set, delete, update)",
            "Data structure support (strings, lists, sets, hashes)",
            "Expiration and TTL management",
            "Cache eviction policies (LRU, LFU, FIFO)"
        ],
        "architecture": [
            "Distributed architecture and clustering",
            "Replication and consistency models",
            "Sharding and data partitioning",
            "Client-server communication protocol"
        ],
        "scalability": [
            "Horizontal scaling with multiple nodes",
            "Load distribution across cache nodes",
            "Memory management and capacity planning",
            "Handling cache stampede and thundering herd"
        ]
    }'::jsonb,
    expected_components = '["Cache Nodes", "Consistent Hashing Ring", "Replication Layer", "Client Library", "Configuration Service"]'::jsonb,
    common_pitfalls = '{
        "cache_invalidation": "Not discussing cache invalidation strategies",
        "consistency": "Not explaining consistency model (strong vs eventual)",
        "cache_penetration": "Missing discussion of cache penetration and null caching",
        "hot_keys": "Not addressing hot key problem",
        "network_partition": "Missing CAP theorem considerations"
    }'::jsonb,
    hints = '{
        "level_1": "Think about how data would be distributed across multiple cache servers. What algorithm helps distribute keys evenly?",
        "level_2": "What happens when a cache node fails? How would you ensure data availability?",
        "level_3": "How would you handle a situation where all clients try to access the same key simultaneously?"
    }'::jsonb,
    functional_requirements_template = 'Consider: Get/Set/Delete operations, TTL support, Data structure support, Atomic operations',
    non_functional_requirements_template = 'Consider: Low latency (<1ms), High throughput, High availability, Memory efficiency',
    evaluation_context = '{
        "domain_specific_notes": "Distributed caches require deep understanding of consistent hashing, replication, and consistency models.",
        "scoring_tips": "Strong candidates will discuss consistent hashing, cache eviction policies, and handling cache stampede."
    }'::jsonb
WHERE uuid = 'q2-normal-hld-distributed-cache';

-- ============================================================================
-- Chat Messaging (q3-normal-hld-chat-messaging)
-- ============================================================================

UPDATE system_design_question_bank
SET 
    guidance_prompts = '{
        "core_functionality": [
            "Message sending and delivery",
            "Real-time message synchronization",
            "Presence indicators (online/offline status)",
            "Message ordering and sequencing"
        ],
        "architecture": [
            "WebSocket or long-polling for real-time communication",
            "Message queue system for reliable delivery",
            "User session management",
            "Group chat and direct messaging support"
        ],
        "scalability": [
            "Handling millions of concurrent connections",
            "Message fan-out for group chats",
            "Database sharding for message storage",
            "Horizontal scaling of chat servers"
        ]
    }'::jsonb,
    expected_components = '["WebSocket Server", "Message Queue", "Presence Service", "Message Store", "Notification Service", "Load Balancer"]'::jsonb,
    common_pitfalls = '{
        "message_ordering": "Not discussing message ordering guarantees",
        "delivery_guarantees": "Missing discussion of at-least-once vs exactly-once delivery",
        "offline_messages": "Not addressing offline message synchronization",
        "group_chat_fanout": "Not explaining fan-out strategy for group chats",
        "connection_scaling": "Missing discussion of connection pooling and scaling"
    }'::jsonb,
    hints = '{
        "level_1": "How would you ensure messages are delivered in the correct order? What mechanisms could help?",
        "level_2": "What happens when a user is offline? How would you handle message delivery when they come back online?",
        "level_3": "In a group chat with 1000 members, how would you efficiently deliver a message to everyone?"
    }'::jsonb,
    functional_requirements_template = 'Consider: Send/receive messages, Group chats, Presence (online/offline), Message history, Read receipts',
    non_functional_requirements_template = 'Consider: Low latency (<100ms), High concurrency (millions of connections), Message durability, Real-time delivery',
    evaluation_context = '{
        "domain_specific_notes": "Chat systems require real-time communication, message ordering, and efficient fan-out for group chats.",
        "scoring_tips": "Strong candidates will discuss WebSocket vs long-polling, message queues, and fan-out strategies."
    }'::jsonb
WHERE uuid = 'q3-normal-hld-chat-messaging';

-- ============================================================================
-- Video Streaming (q4-normal-hld-video-streaming)
-- ============================================================================

UPDATE system_design_question_bank
SET 
    guidance_prompts = '{
        "core_functionality": [
            "Video upload and storage",
            "Video transcoding and encoding",
            "Adaptive bitrate streaming",
            "Video playback and buffering"
        ],
        "architecture": [
            "CDN for video content delivery",
            "Transcoding pipeline and job queue",
            "Metadata storage and search",
            "Recommendation engine"
        ],
        "scalability": [
            "Handling massive video storage (petabytes)",
            "Global content distribution via CDN",
            "Horizontal scaling of transcoding workers",
            "Database sharding for metadata"
        ]
    }'::jsonb,
    expected_components = '["Upload Service", "Transcoding Service", "CDN", "Video Storage", "Metadata DB", "Recommendation Engine"]'::jsonb,
    common_pitfalls = '{
        "transcoding_time": "Not discussing transcoding time and how to handle it asynchronously",
        "adaptive_bitrate": "Missing discussion of adaptive bitrate streaming (HLS/DASH)",
        "storage_cost": "Not addressing storage costs and archival strategies",
        "concurrent_uploads": "Not discussing handling multiple concurrent uploads",
        "video_quality": "Missing discussion of quality vs bandwidth trade-offs"
    }'::jsonb,
    hints = '{
        "level_1": "Videos are large files. How would you handle uploading and storing petabytes of video data?",
        "level_2": "Different users have different internet speeds. How would you ensure smooth playback for everyone?",
        "level_3": "Transcoding a video can take hours. How would you design the system to handle this asynchronously?"
    }'::jsonb,
    functional_requirements_template = 'Consider: Video upload, Video playback, Video search, Recommendations, User profiles',
    non_functional_requirements_template = 'Consider: Massive storage (petabytes), Low latency streaming, Global distribution, Cost optimization',
    evaluation_context = '{
        "domain_specific_notes": "Video streaming requires CDN, transcoding pipelines, and adaptive bitrate streaming for optimal user experience.",
        "scoring_tips": "Strong candidates will discuss HLS/DASH, transcoding queues, and CDN strategies."
    }'::jsonb
WHERE uuid = 'q4-normal-hld-video-streaming';

-- ============================================================================
-- Social Feed (q5-normal-hld-social-feed)
-- ============================================================================

UPDATE system_design_question_bank
SET 
    guidance_prompts = '{
        "core_functionality": [
            "Feed generation and ranking",
            "Post creation and publishing",
            "User follow/following relationships",
            "Real-time feed updates"
        ],
        "architecture": [
            "Feed generation strategies (push vs pull, hybrid)",
            "Timeline service and ranking algorithms",
            "Graph database for social connections",
            "Content storage and indexing"
        ],
        "scalability": [
            "Handling millions of posts per day",
            "Fan-out for popular users (write amplification)",
            "Feed pre-computation and caching",
            "Database sharding by user or content"
        ]
    }'::jsonb,
    expected_components = '["Feed Service", "Post Service", "Graph Service", "Ranking Service", "Cache", "Message Queue"]'::jsonb,
    common_pitfalls = '{
        "push_vs_pull": "Not explaining push vs pull trade-offs and when to use hybrid",
        "fanout_problem": "Missing discussion of fan-out problem for celebrities",
        "feed_ranking": "Not discussing feed ranking algorithms",
        "consistency": "Not addressing feed consistency and ordering",
        "new_users": "Missing discussion of cold start for new users"
    }'::jsonb,
    hints = '{
        "level_1": "When a user posts something, how would you ensure all their followers see it? What are the trade-offs?",
        "level_2": "A celebrity with 10 million followers posts something. How would you handle the fan-out efficiently?",
        "level_3": "How would you rank posts in a feed? What factors would influence the ranking?"
    }'::jsonb,
    functional_requirements_template = 'Consider: Post creation, Feed generation, Follow/unfollow, Like/comment, Real-time updates',
    non_functional_requirements_template = 'Consider: Low latency feed (<200ms), High write throughput, Feed freshness, Personalization',
    evaluation_context = '{
        "domain_specific_notes": "Social feeds require understanding push vs pull strategies, fan-out optimization, and ranking algorithms.",
        "scoring_tips": "Strong candidates will discuss hybrid push/pull, fan-out optimization, and feed ranking strategies."
    }'::jsonb
WHERE uuid = 'q5-normal-hld-social-feed';

-- ============================================================================
-- AI Customer Support (q6-agentic-ai-customer-support)
-- ============================================================================

UPDATE system_design_question_bank
SET 
    guidance_prompts = '{
        "core_functionality": [
            "Natural language understanding and intent detection",
            "Multi-turn conversation management",
            "Tool/API calling for information retrieval",
            "Escalation to human agents"
        ],
        "architecture": [
            "LLM integration and prompt management",
            "Agent orchestration and workflow engine",
            "Knowledge base and context management",
            "Human-in-the-loop escalation system"
        ],
        "scalability": [
            "Handling concurrent conversations",
            "LLM API rate limiting and cost optimization",
            "Context window management",
            "Horizontal scaling of agent instances"
        ]
    }'::jsonb,
    expected_components = '["LLM Service", "Intent Classifier", "Knowledge Base", "Tool Registry", "Conversation Manager", "Escalation Service"]'::jsonb,
    common_pitfalls = '{
        "context_management": "Not discussing context window limits and conversation history management",
        "tool_calling": "Missing discussion of tool/function calling for information retrieval",
        "cost_optimization": "Not addressing LLM API costs and optimization strategies",
        "escalation": "Not explaining when and how to escalate to humans",
        "hallucination": "Missing discussion of hallucination prevention"
    }'::jsonb,
    hints = '{
        "level_1": "How would the AI understand what the customer is asking? What techniques could help?",
        "level_2": "The AI needs to look up information from a database. How would it do that?",
        "level_3": "What if the AI doesn''t know the answer or the question is too complex? How would you handle that?"
    }'::jsonb,
    functional_requirements_template = 'Consider: Intent understanding, Multi-turn conversations, Tool/API calling, Human escalation, Knowledge retrieval',
    non_functional_requirements_template = 'Consider: Response latency (<2s), Cost optimization, Context management, Accuracy, Availability',
    evaluation_context = '{
        "domain_specific_notes": "AI agent systems require LLM integration, tool calling, context management, and human-in-the-loop workflows.",
        "scoring_tips": "Strong candidates will discuss prompt engineering, tool calling, context window management, and cost optimization."
    }'::jsonb
WHERE uuid = 'q6-agentic-ai-customer-support';

-- ============================================================================
-- Multi-Agent Collaboration (q7-agentic-ai-multi-agent)
-- ============================================================================

UPDATE system_design_question_bank
SET 
    guidance_prompts = '{
        "core_functionality": [
            "Agent-to-agent communication protocols",
            "Task delegation and coordination",
            "Shared memory and context management",
            "Conflict resolution and consensus mechanisms"
        ],
        "architecture": [
            "Agent registry and discovery",
            "Message bus or event system for communication",
            "Task queue and scheduling",
            "Shared knowledge base or workspace"
        ],
        "scalability": [
            "Supporting hundreds of concurrent agents",
            "Message routing and load balancing",
            "Distributed task execution",
            "Horizontal scaling of agent infrastructure"
        ]
    }'::jsonb,
    expected_components = '["Agent Registry", "Message Bus", "Task Queue", "Shared Memory", "Coordination Service", "Conflict Resolver"]'::jsonb,
    common_pitfalls = '{
        "communication_protocol": "Not discussing agent-to-agent communication protocols",
        "deadlock": "Missing discussion of deadlock detection and prevention",
        "consensus": "Not explaining consensus mechanisms for conflict resolution",
        "task_delegation": "Not addressing task delegation and coordination strategies",
        "shared_state": "Missing discussion of shared state management"
    }'::jsonb,
    hints = '{
        "level_1": "How would multiple AI agents communicate with each other? What communication pattern would work best?",
        "level_2": "What if two agents need to work on the same task? How would you coordinate them?",
        "level_3": "How would agents share information and maintain a shared understanding of the current state?"
    }'::jsonb,
    functional_requirements_template = 'Consider: Agent communication, Task delegation, Shared memory, Conflict resolution, Consensus',
    non_functional_requirements_template = 'Consider: Scalability (hundreds of agents), Message delivery guarantees, Deadlock prevention, Performance',
    evaluation_context = '{
        "domain_specific_notes": "Multi-agent systems require communication protocols, coordination mechanisms, and conflict resolution strategies.",
        "scoring_tips": "Strong candidates will discuss message buses, task queues, consensus algorithms, and deadlock prevention."
    }'::jsonb
WHERE uuid = 'q7-agentic-ai-multi-agent';

-- ============================================================================
-- AI Orchestration Platform (q8-agentic-ai-orchestration)
-- ============================================================================

UPDATE system_design_question_bank
SET 
    guidance_prompts = '{
        "core_functionality": [
            "Workflow definition and execution",
            "Agent scheduling and resource allocation",
            "State management across workflow steps",
            "Conditional branching and error handling"
        ],
        "architecture": [
            "Workflow engine and DAG execution",
            "Agent pool management and autoscaling",
            "LLM provider abstraction layer",
            "Monitoring and observability dashboard"
        ],
        "scalability": [
            "Handling thousands of concurrent workflows",
            "Dynamic agent provisioning",
            "Resource pooling and optimization",
            "Distributed workflow execution"
        ]
    }'::jsonb,
    expected_components = '["Workflow Engine", "Agent Pool", "Scheduler", "State Store", "LLM Provider Abstraction", "Monitoring Dashboard"]'::jsonb,
    common_pitfalls = '{
        "workflow_state": "Not discussing workflow state persistence and recovery",
        "error_handling": "Missing discussion of error handling and retry mechanisms",
        "resource_allocation": "Not addressing resource allocation and agent pool management",
        "dag_execution": "Not explaining DAG execution and parallel step execution",
        "cost_tracking": "Missing discussion of cost tracking and budget management"
    }'::jsonb,
    hints = '{
        "level_1": "How would you represent a workflow? What data structure would help model dependencies between steps?",
        "level_2": "What if a step in the workflow fails? How would you handle errors and retries?",
        "level_3": "How would you manage resources when thousands of workflows are running simultaneously?"
    }'::jsonb,
    functional_requirements_template = 'Consider: Workflow definition, Step execution, Conditional branching, Error handling, State management',
    non_functional_requirements_template = 'Consider: Scalability (thousands of workflows), Resource efficiency, Cost tracking, SLA management',
    evaluation_context = '{
        "domain_specific_notes": "Orchestration platforms require workflow engines, DAG execution, state management, and resource optimization.",
        "scoring_tips": "Strong candidates will discuss DAG execution, state persistence, retry mechanisms, and resource pooling."
    }'::jsonb
WHERE uuid = 'q8-agentic-ai-orchestration';

-- ============================================================================
-- AI Code Generation (q9-agentic-ai-code-generation)
-- ============================================================================

UPDATE system_design_question_bank
SET 
    guidance_prompts = '{
        "core_functionality": [
            "Code generation from natural language prompts",
            "Code review and quality analysis",
            "Integration with version control (Git)",
            "Test generation and execution"
        ],
        "architecture": [
            "LLM integration for code generation",
            "Code analysis and AST parsing",
            "CI/CD pipeline integration",
            "Security scanning and vulnerability detection"
        ],
        "scalability": [
            "Handling concurrent code generation requests",
            "LLM API rate limiting and caching",
            "Parallel code review processing",
            "Repository and branch management"
        ]
    }'::jsonb,
    expected_components = '["Code Generator", "Code Analyzer", "Git Integration", "Test Runner", "Security Scanner", "CI/CD Integration"]'::jsonb,
    common_pitfalls = '{
        "code_quality": "Not discussing code quality validation and testing",
        "git_integration": "Missing discussion of Git integration and branch management",
        "security": "Not addressing security scanning and vulnerability detection",
        "ast_parsing": "Not explaining AST parsing for code analysis",
        "test_generation": "Missing discussion of test generation and execution"
    }'::jsonb,
    hints = '{
        "level_1": "How would the AI generate code? What would the input and output look like?",
        "level_2": "How would you ensure the generated code is correct and follows best practices?",
        "level_3": "How would you integrate this with existing development workflows like Git and CI/CD?"
    }'::jsonb,
    functional_requirements_template = 'Consider: Code generation, Code review, Git integration, Test generation, Security scanning',
    non_functional_requirements_template = 'Consider: Code quality, Security, Integration with dev tools, Performance, Cost optimization',
    evaluation_context = '{
        "domain_specific_notes": "Code generation systems require LLM integration, AST parsing, Git integration, and security scanning.",
        "scoring_tips": "Strong candidates will discuss AST parsing, code quality validation, Git workflows, and security scanning."
    }'::jsonb
WHERE uuid = 'q9-agentic-ai-code-generation';

-- ============================================================================
-- Autonomous Task Execution (q10-agentic-ai-autonomous-tasks)
-- ============================================================================

UPDATE system_design_question_bank
SET 
    guidance_prompts = '{
        "core_functionality": [
            "Task planning and decomposition",
            "Tool selection and execution",
            "Progress monitoring and checkpointing",
            "Human-in-the-loop approval mechanisms"
        ],
        "architecture": [
            "Planning engine and task scheduler",
            "Tool registry and execution framework",
            "State management and checkpoint storage",
            "Notification and approval system"
        ],
        "scalability": [
            "Handling thousands of concurrent tasks",
            "Parallel task execution",
            "Resource allocation and optimization",
            "Distributed task processing"
        ]
    }'::jsonb,
    expected_components = '["Planning Engine", "Task Scheduler", "Tool Registry", "Checkpoint Store", "Approval Service", "Monitoring Service"]'::jsonb,
    common_pitfalls = '{
        "task_planning": "Not discussing task decomposition and planning strategies",
        "checkpointing": "Missing discussion of checkpointing and resume capabilities",
        "safety": "Not addressing safety checks and validation",
        "human_approval": "Not explaining when and how to request human approval",
        "tool_selection": "Missing discussion of tool selection and execution"
    }'::jsonb,
    hints = '{
        "level_1": "How would the AI break down a complex task into smaller steps? What planning approach would work?",
        "level_2": "What if a task fails halfway through? How would you recover and resume?",
        "level_3": "How would you ensure the AI doesn''t do something dangerous or irreversible? What safety mechanisms would you add?"
    }'::jsonb,
    functional_requirements_template = 'Consider: Task planning, Tool execution, Progress tracking, Checkpointing, Human approval',
    non_functional_requirements_template = 'Consider: Task reliability, Safety, Recovery mechanisms, Scalability, Performance',
    evaluation_context = '{
        "domain_specific_notes": "Autonomous task systems require planning engines, tool execution, checkpointing, and safety mechanisms.",
        "scoring_tips": "Strong candidates will discuss task decomposition, checkpointing, safety checks, and human-in-the-loop workflows."
    }'::jsonb
WHERE uuid = 'q10-agentic-ai-autonomous-tasks';

-- ============================================================================
-- Verification
-- ============================================================================

SELECT 
    uuid,
    domain,
    complexity,
    estimated_time_minutes,
    CASE WHEN guidance_prompts IS NOT NULL AND guidance_prompts != '{}'::jsonb THEN 'Yes' ELSE 'No' END as has_guidance,
    CASE WHEN expected_components IS NOT NULL AND expected_components != '[]'::jsonb THEN 'Yes' ELSE 'No' END as has_components,
    CASE WHEN common_pitfalls IS NOT NULL AND common_pitfalls != '{}'::jsonb THEN 'Yes' ELSE 'No' END as has_pitfalls,
    CASE WHEN hints IS NOT NULL AND hints != '{}'::jsonb THEN 'Yes' ELSE 'No' END as has_hints
FROM system_design_question_bank
ORDER BY uuid;

