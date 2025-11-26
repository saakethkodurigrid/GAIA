# System Design API Documentation

All endpoints are prefixed with `/api/v1/system-design`

**Authentication:** All endpoints require Bearer token in Authorization header
```
Authorization: Bearer <google_oauth_token>
```

---

## 1. GET `/questions`

**Description:** Get all questions, optionally filtered by tag.

**Query Parameters:**
- `tag` (optional, string): Filter questions by tag (e.g., 'normal_hld', 'agentic_ai_hld')

**Request from Frontend:**
```typescript
GET /api/v1/system-design/questions?tag=normal_hld
Headers: {
  Authorization: "Bearer <token>"
}
```

**Response to Frontend:**
```typescript
{
  questions: [
    {
      uuid: string,              // Question UUID
      question_id: string,        // Question ID
      question: string,           // Question text
      evaluation_criteria: string, // Evaluation criteria
      tags?: {                    // Optional tags object
        [key: string]: any
      }
    }
  ]
}
```

---

## 2. GET `/questions/{uuid}`

**Description:** Get a specific question by UUID.

**Path Parameters:**
- `uuid` (required, string): UUID of the question

**Request from Frontend:**
```typescript
GET /api/v1/system-design/questions/{uuid}
Headers: {
  Authorization: "Bearer <token>"
}
```

**Response to Frontend:**
```typescript
{
  uuid: string,
  question_id: string,
  question: string,
  evaluation_criteria: string,
  tags?: {
    [key: string]: any
  }
}
```

**Error Responses:**
- `404`: Question not found
- `500`: Internal server error

---

## 3. GET `/questions/random`

**Description:** Get a random question, optionally filtered by tag.

**Query Parameters:**
- `tag` (optional, string): Filter questions by tag

**Request from Frontend:**
```typescript
GET /api/v1/system-design/questions/random?tag=agentic_ai_hld
Headers: {
  Authorization: "Bearer <token>"
}
```

**Response to Frontend:**
```typescript
{
  uuid: string,
  question_id: string,
  question: string,
  evaluation_criteria: string,
  tags?: {
    [key: string]: any
  }
}
```

**Error Responses:**
- `404`: No questions found
- `500`: Internal server error

---

## 4. POST `/sessions`

**Description:** Create a new interview session.

**Request from Frontend:**
```typescript
POST /api/v1/system-design/sessions
Headers: {
  Authorization: "Bearer <token>",
  Content-Type: "application/json"
}
Body: {
  question_id?: string,        // Optional (legacy)
  question_text?: string,     // Optional (if custom question)
  question_uuid?: string,      // Optional (UUID from question bank)
  tag?: string,               // Optional (for random selection, e.g., 'normal_hld', 'agentic_ai_hld')
  candidate_id?: string       // Optional (auto-filled from auth token)
}
```

**Response to Frontend:**
```typescript
{
  session_id: string,         // Created session ID
  question_text: string,      // Question text for the session
  question_uuid?: string       // Optional question UUID
}
```

**Error Responses:**
- `403`: Candidate ID mismatch
- `404`: Question not found
- `500`: Internal server error

**Note:** `candidate_id` is automatically filled from the authenticated user's token if not provided.

---

## 5. POST `/canvas/update`

**Description:** Handle canvas updates (save, submit, or update).

**Request from Frontend:**
```typescript
POST /api/v1/system-design/canvas/update
Headers: {
  Authorization: "Bearer <token>",
  Content-Type: "application/json"
}
Body: {
  session_id: string,         // Session ID
  canvas_data: {
    elements: Array<{         // Excalidraw elements
      [key: string]: any
    }>,
    appState?: {              // Optional app state
      [key: string]: any
    },
    files?: {                 // Optional files
      [key: string]: any
    }
  },
  action: string,             // 'save', 'submit', or 'update'
  change_hash?: string        // Optional hash for optimization
}
```

**Response to Frontend:**
```typescript
{
  status: string,             // Status of the operation
  version?: number,           // Optional version number
  evaluation?: {              // Optional evaluation (if submitted)
    [key: string]: any
  },
  evaluation_message?: string // Optional evaluation message
}
```

**Error Responses:**
- `400`: Bad request (validation error)
- `403`: Access denied (session doesn't belong to candidate)
- `500`: Internal server error

---

## 6. POST `/chat/message`

**Description:** Send a chat message. Can optionally include current canvas state for better AI context.

**Request from Frontend:**
```typescript
POST /api/v1/system-design/chat/message
Headers: {
  Authorization: "Bearer <token>",
  Content-Type: "application/json"
}
Body: {
  message: string,            // Chat message content (min length: 1)
  session_id: string,         // Session ID
  canvas_data?: {             // Optional: Current canvas state from Excalidraw
    elements: Array<{         // Excalidraw elements
      [key: string]: any
    }>,
    appState?: {              // Optional app state
      [key: string]: any
    },
    files?: {                 // Optional files
      [key: string]: any
    }
  }
}
```

**Note:** If `canvas_data` is provided, it will update the session's current canvas state, ensuring the AI always has the latest drawing context when responding.

**Response to Frontend:**
```typescript
{
  user_message: {            // User's message
    [key: string]: any
  },
  ai_response?: string,       // Optional AI response
  evaluation?: {              // Optional evaluation
    [key: string]: any
  }
}
```

**Error Responses:**
- `403`: Access denied (session doesn't belong to candidate)
- `500`: Internal server error

---

## 7. GET `/sessions/{session_id}/check-prompts`

**Description:** Check if any proactive prompts should be triggered. Frontend should poll this endpoint periodically (every 5-10 seconds).

**Path Parameters:**
- `session_id` (required, string): Session ID

**Request from Frontend:**
```typescript
GET /api/v1/system-design/sessions/{session_id}/check-prompts
Headers: {
  Authorization: "Bearer <token>"
}
```

**Response to Frontend:**
```typescript
{
  has_prompt: boolean,        // Whether a prompt is available
  prompt?: string             // Optional prompt text
}
```

**Error Responses:**
- `403`: Access denied (session doesn't belong to candidate)
- `500`: Internal server error

**Note:** Consider using `/prompts-stream` endpoint for better performance instead of polling.

---

## 8. GET `/sessions/{session_id}/chat-history`

**Description:** Get full chat history for a session.

**Path Parameters:**
- `session_id` (required, string): Session ID

**Request from Frontend:**
```typescript
GET /api/v1/system-design/sessions/{session_id}/chat-history
Headers: {
  Authorization: "Bearer <token>"
}
```

**Response to Frontend:**
```typescript
{
  messages: [                 // Array of chat messages
    {
      [key: string]: any
    }
  ]
}
```

**Error Responses:**
- `403`: Access denied (session doesn't belong to candidate)
- `500`: Internal server error

---

## 9. POST `/sessions/{session_id}/end`

**Description:** End session and generate final report.

**Path Parameters:**
- `session_id` (required, string): Session ID

**Request from Frontend:**
```typescript
POST /api/v1/system-design/sessions/{session_id}/end
Headers: {
  Authorization: "Bearer <token>"
}
```

**Response to Frontend:**
```typescript
{
  session_id: string,
  question: string,            // Question text
  average_scores: {           // Average scores by category
    [category: string]: number
  },
  timeline: [                 // Timeline of events
    {
      [key: string]: any
    }
  ],
  total_versions: number,     // Total canvas versions
  total_messages: number,     // Total chat messages
  lowest_area?: string,       // Optional area with lowest score
  suggested_learning: string[] // Suggested learning topics
}
```

**Error Responses:**
- `403`: Access denied (session doesn't belong to candidate)
- `500`: Internal server error

---

## 10. GET `/sessions/{session_id}/report`

**Description:** Get final evaluation report.

**Path Parameters:**
- `session_id` (required, string): Session ID

**Request from Frontend:**
```typescript
GET /api/v1/system-design/sessions/{session_id}/report
Headers: {
  Authorization: "Bearer <token>"
}
```

**Response to Frontend:**
```typescript
{
  session_id: string,
  question: string,
  average_scores: {
    [category: string]: number
  },
  timeline: [
    {
      [key: string]: any
    }
  ],
  total_versions: number,
  total_messages: number,
  lowest_area?: string,
  suggested_learning: string[]
}
```

**Error Responses:**
- `403`: Access denied (session doesn't belong to candidate)
- `500`: Internal server error

---

## 11. GET `/sessions/{session_id}/prompts-stream`

**Description:** Server-Sent Events (SSE) stream for proactive prompts. Frontend connects once and receives prompts as they're generated. More efficient than polling `/check-prompts` repeatedly.

**Path Parameters:**
- `session_id` (required, string): Session ID

**Request from Frontend:**
```typescript
GET /api/v1/system-design/sessions/{session_id}/prompts-stream
Headers: {
  Authorization: "Bearer <token>"
}
```

**Response to Frontend:**
Server-Sent Events stream with the following event format:

```
data: {"has_prompt": true, "prompt": "Your prompt text here"}\n\n
data: {"has_prompt": false}\n\n  // Heartbeat to keep connection alive
data: {"has_prompt": false, "closed": true}\n\n  // Connection closed (no activity for 5 minutes)
data: {"error": "Error message"}\n\n  // Error occurred
```

**Event Types:**
- `has_prompt: true` - New prompt available
- `has_prompt: false` - No prompt (heartbeat)
- `closed: true` - Stream closed (no activity for 5 minutes)
- `error` - Error occurred

**Error Responses:**
- `403`: Access denied (session doesn't belong to candidate)

**Note:** 
- Stream checks for prompts every 2-3 seconds
- Stream automatically closes after 5 minutes of inactivity
- Frontend should handle connection drops and reconnect if needed

---

## Summary Table

| Method | Endpoint | Purpose | Auth Required |
|--------|----------|---------|---------------|
| GET | `/questions` | List all questions | Yes |
| GET | `/questions/{uuid}` | Get specific question | Yes |
| GET | `/questions/random` | Get random question | Yes |
| POST | `/sessions` | Create interview session | Yes |
| POST | `/canvas/update` | Update/save/submit canvas | Yes |
| POST | `/chat/message` | Send chat message | Yes |
| GET | `/sessions/{session_id}/check-prompts` | Check for prompts (polling) | Yes |
| GET | `/sessions/{session_id}/chat-history` | Get chat history | Yes |
| POST | `/sessions/{session_id}/end` | End session & get report | Yes |
| GET | `/sessions/{session_id}/report` | Get evaluation report | Yes |
| GET | `/sessions/{session_id}/prompts-stream` | Stream prompts (SSE) | Yes |

---

## Common Error Codes

- `400`: Bad Request - Invalid input data
- `403`: Forbidden - Access denied (session doesn't belong to candidate)
- `404`: Not Found - Resource not found
- `500`: Internal Server Error - Server error

---

## Notes

1. All endpoints require authentication via Bearer token
2. `candidate_id` is automatically extracted from the auth token, so it's optional in requests
3. Session ownership is verified on all session-related endpoints
4. For proactive prompts, prefer SSE streaming (`/prompts-stream`) over polling (`/check-prompts`)
5. Canvas data follows Excalidraw format
6. All timestamps are in ISO format

