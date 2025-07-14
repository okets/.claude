# 📊 Database Schema Reference

> **4-table SQLite schema optimized for lightning-fast context retrieval**

[![SQLite](https://img.shields.io/badge/📊_SQLite-Database-blue)](https://sqlite.org)
[![Zero Tokens](https://img.shields.io/badge/💰_Zero-Tokens-orange)](../README.md)
[![Local Storage](https://img.shields.io/badge/🏠_Local-Storage-green)](../README.md)
[![Fast Queries](https://img.shields.io/badge/⚡_Fast-Queries-purple)](../README.md)

## 🎯 Key Questions Answered

- **🎯 What was the user's intent?** - Every action linked to original request
- **📝 Why were files changed?** - Context behind every modification
- **🔗 How do tasks relate to outcomes?** - Complete workflow tracking
- **📈 What patterns emerge?** - Development insights across sessions

## Core Tables

### 1. cycles
**Purpose**: Track user intent and development cycles

```sql
CREATE TABLE cycles (
    cycle_id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_intent TEXT,           -- Primary driver: what the user wanted
    phase_number INTEGER,       -- Project phase (if applicable)
    task_number INTEGER,        -- Task within phase (if applicable)
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    primary_activity TEXT       -- file_modification, testing, research, etc.
);
```

**Key Indexes**:
- `idx_cycles_session`: Fast session lookups
- `idx_cycles_phase_task`: Phase/task-based queries

**Example Data**:
```json
{
  "cycle_id": 42,
  "session_id": "session_abc123",
  "user_intent": "Add TTS notification format fix to reduce word salad",
  "phase_number": 8,
  "task_number": 4,
  "primary_activity": "file_modification"
}
```

### 2. file_contexts
**Purpose**: Track file changes with WHY context

```sql
CREATE TABLE file_contexts (
    id INTEGER PRIMARY KEY,
    cycle_id INTEGER REFERENCES cycles(cycle_id),
    file_path TEXT NOT NULL,    -- Primary driver: which file
    agent_type TEXT,            -- main_agent, subagent
    operation_type TEXT,        -- edit, write, multiedit
    change_reason TEXT,         -- WHY context from tool input
    edit_count INTEGER,
    timestamp TIMESTAMP
);
```

**Key Indexes**:
- `idx_file_contexts_path`: File-based lookups
- `idx_file_contexts_cycle`: Cycle-based queries

**Example Data**:
```json
{
  "file_path": "/hooks/utils/cycle_utils.py",
  "cycle_id": 42,
  "agent_type": "main_agent",
  "operation_type": "edit",
  "change_reason": "Update notification functions to use clean user instruction format",
  "edit_count": 3
}
```

### 3. llm_summaries
**Purpose**: Generated insights and workflow analysis

```sql
CREATE TABLE llm_summaries (
    id INTEGER PRIMARY KEY, 
    cycle_id INTEGER REFERENCES cycles(cycle_id),
    intent_sequence INTEGER,   -- For multi-intent cycles
    summary_text TEXT,
    summary_type TEXT,         -- user_intent, execution_summary, etc.
    confidence_level TEXT     -- high, medium, low
);
```

**Key Indexes**:
- `idx_llm_summaries_cycle`: Cycle-based lookups
- `idx_llm_summaries_type`: Summary type filtering

**Example Data**:
```json
{
  "cycle_id": 42,
  "summary_type": "execution_summary",
  "summary_text": "Successfully implemented user-requested TTS format change across both concise and verbose notification systems",
  "confidence_level": "high"
}
```

### 4. subagent_tasks
**Purpose**: Track delegation and subagent work

```sql
CREATE TABLE subagent_tasks (
    id INTEGER PRIMARY KEY,
    cycle_id INTEGER REFERENCES cycles(cycle_id), 
    task_description TEXT,
    files_modified TEXT,        -- JSON array as text
    status TEXT,               -- completed, failed, in_progress
    completion_time TIMESTAMP
);
```

**Key Indexes**:
- `idx_subagent_tasks_cycle`: Cycle-based lookups

**Example Data**:
```json
{
  "cycle_id": 42,
  "task_description": "Review public documentation for open source readiness",
  "files_modified": "[\"README.md\", \"docs/HOOKS_REFERENCE.md\"]",
  "status": "completed"
}
```

## Common Query Patterns

### Recent Activity Queries

#### What was I working on recently?
```sql
SELECT user_intent, primary_activity, start_time 
FROM cycles 
ORDER BY cycle_id DESC 
LIMIT 10;
```

#### What files were changed in the last 5 cycles?
```sql
SELECT DISTINCT fc.file_path, fc.change_reason, c.user_intent
FROM file_contexts fc
JOIN cycles c ON fc.cycle_id = c.cycle_id
WHERE c.cycle_id >= (SELECT MAX(cycle_id) - 5 FROM cycles)
ORDER BY fc.timestamp DESC;
```

### File History Queries

#### Complete history for a specific file
```sql
SELECT c.user_intent, fc.change_reason, fc.operation_type, 
       fc.edit_count, fc.timestamp
FROM file_contexts fc
JOIN cycles c ON fc.cycle_id = c.cycle_id
WHERE fc.file_path LIKE '%notification.py%'
ORDER BY fc.timestamp DESC;
```

#### Files modified by subagents
```sql
SELECT fc.file_path, fc.change_reason, st.task_description
FROM file_contexts fc
JOIN subagent_tasks st ON fc.cycle_id = st.cycle_id
WHERE fc.agent_type = 'subagent'
ORDER BY fc.timestamp DESC;
```

### Intent and Workflow Queries

#### Find all work related to TTS
```sql
SELECT c.user_intent, c.primary_activity, 
       GROUP_CONCAT(fc.file_path) as files_modified
FROM cycles c
LEFT JOIN file_contexts fc ON c.cycle_id = fc.cycle_id
WHERE c.user_intent LIKE '%TTS%' OR c.user_intent LIKE '%notification%'
GROUP BY c.cycle_id
ORDER BY c.start_time DESC;
```

#### Most edited files
```sql
SELECT fc.file_path, 
       COUNT(*) as edit_frequency,
       SUM(fc.edit_count) as total_edits,
       MAX(fc.timestamp) as last_modified
FROM file_contexts fc
GROUP BY fc.file_path
ORDER BY edit_frequency DESC
LIMIT 20;
```

### Project and Phase Analysis

#### Work by development phase
```sql
SELECT phase_number, task_number, 
       COUNT(*) as cycles_count,
       GROUP_CONCAT(DISTINCT user_intent, '; ') as intents
FROM cycles 
WHERE phase_number IS NOT NULL
GROUP BY phase_number, task_number
ORDER BY phase_number, task_number;
```

#### Task complexity assessment
```sql
SELECT c.user_intent,
       COUNT(fc.id) as files_touched,
       SUM(fc.edit_count) as total_edits,
       COUNT(st.id) as subagent_tasks,
       ls.summary_text
FROM cycles c
LEFT JOIN file_contexts fc ON c.cycle_id = fc.cycle_id
LEFT JOIN subagent_tasks st ON c.cycle_id = st.cycle_id
LEFT JOIN llm_summaries ls ON c.cycle_id = ls.cycle_id 
    AND ls.summary_type = 'execution_summary'
GROUP BY c.cycle_id
ORDER BY files_touched DESC, total_edits DESC;
```

## Advanced Analysis Patterns

### Workflow Pattern Recognition
```sql
-- Find similar problem-solving patterns
SELECT c1.user_intent as original_intent,
       c2.user_intent as similar_intent,
       c1.primary_activity
FROM cycles c1
JOIN cycles c2 ON c1.primary_activity = c2.primary_activity
WHERE c1.cycle_id != c2.cycle_id
  AND c1.user_intent LIKE '%fix%'
  AND c2.user_intent LIKE '%fix%'
ORDER BY c1.start_time DESC;
```

### Productivity Metrics
```sql
-- Development velocity by session
SELECT session_id,
       COUNT(DISTINCT cycle_id) as cycles_completed,
       COUNT(DISTINCT fc.file_path) as unique_files_modified,
       SUM(fc.edit_count) as total_edits
FROM cycles c
LEFT JOIN file_contexts fc ON c.cycle_id = fc.cycle_id
GROUP BY session_id
ORDER BY cycles_completed DESC;
```

### Context Retrieval for Claude
```sql
-- What Claude might query for context awareness
SELECT c.user_intent, fc.file_path, fc.change_reason,
       ls.summary_text
FROM cycles c
JOIN file_contexts fc ON c.cycle_id = fc.cycle_id
LEFT JOIN llm_summaries ls ON c.cycle_id = ls.cycle_id
WHERE fc.file_path = ? -- Current file being worked on
ORDER BY c.start_time DESC
LIMIT 5;
```

## Database Maintenance

### Cleanup Queries
```sql
-- Remove old cycles (keep last 100)
DELETE FROM cycles 
WHERE cycle_id NOT IN (
    SELECT cycle_id FROM cycles 
    ORDER BY cycle_id DESC 
    LIMIT 100
);

-- Vacuum to reclaim space
VACUUM;
```

### Performance Optimization
```sql
-- Analyze table statistics
ANALYZE;

-- Check index usage
EXPLAIN QUERY PLAN 
SELECT * FROM file_contexts 
WHERE file_path LIKE '%hooks%';
```

## Integration with Python

### Basic Database Access
```python
from hooks.utils.contextual_db import ContextualDB

db = ContextualDB()

# Query recent user intents
recent_intents = db.connection.execute("""
    SELECT user_intent, start_time 
    FROM cycles 
    ORDER BY cycle_id DESC 
    LIMIT 5
""").fetchall()

for intent, time in recent_intents:
    print(f"{time}: {intent}")
```

### Using Helper Methods
```python
# Get file modification history
file_history = db.get_file_context("notification.py", limit=10)

# Get phase/task context
phase_context = db.get_phase_task_context(phase_number=8)
```

## 📚 Navigation

[![Getting Started](https://img.shields.io/badge/📖_Getting-Started-blue)](GETTING_STARTED.md)
[![Troubleshooting](https://img.shields.io/badge/🔧_Troubleshooting-orange)](TROUBLESHOOTING.md)
[![Back to README](https://img.shields.io/badge/🏠_Back_to-README-green)](../README.md)

---

**This schema enables powerful context-aware development workflows while maintaining fast query performance and clear data relationships.**