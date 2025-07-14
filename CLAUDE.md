# Claude Contextual Memory System

This file documents Claude's enhanced contextual memory capabilities through the **smarter-claude** system.

## Overview

Claude now has access to a sophisticated contextual memory database that automatically tracks:
- User intents and requests
- File modifications with WHY context
- Task delegation and subagent usage  
- Execution summaries and workflow insights

## Database Schema

The contextual memory uses a 4-table SQLite schema designed for fast context retrieval:

### 1. `cycles` - Core Request Tracking
```sql
CREATE TABLE cycles (
    cycle_id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_intent TEXT,           -- The original user request
    phase_number INTEGER,       -- Project phase tracking  
    task_number INTEGER,        -- Task within phase
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    primary_activity TEXT       -- file_modification, testing, git-operation, etc.
);
```

**Purpose**: Tracks each request cycle with the original user intent as the primary driver.

### 2. `file_contexts` - File Changes with WHY Context
```sql
CREATE TABLE file_contexts (
    id INTEGER PRIMARY KEY,
    cycle_id INTEGER REFERENCES cycles(cycle_id),
    file_path TEXT NOT NULL,    -- What file was changed
    agent_type TEXT,            -- main_agent, subagent
    operation_type TEXT,        -- edit, write, multiedit
    change_reason TEXT,         -- WHY the change was made
    edit_count INTEGER,         -- Number of edits
    timestamp TIMESTAMP
);
```

**Purpose**: Captures not just WHAT files were changed, but WHY they were changed.

### 3. `llm_summaries` - Generated Insights
```sql
CREATE TABLE llm_summaries (
    id INTEGER PRIMARY KEY, 
    cycle_id INTEGER REFERENCES cycles(cycle_id),
    intent_sequence INTEGER,   -- For multi-intent cycles
    summary_text TEXT,         -- Generated summary content
    summary_type TEXT,         -- user_intent, execution_summary, workflow_insights
    confidence_level TEXT     -- high, medium, low
);
```

**Purpose**: Stores generated insights and summaries for complex request cycles.

### 4. `subagent_tasks` - Delegation Context
```sql
CREATE TABLE subagent_tasks (
    id INTEGER PRIMARY KEY,
    cycle_id INTEGER REFERENCES cycles(cycle_id), 
    task_description TEXT,     -- What was delegated
    files_modified TEXT,       -- JSON array of files
    status TEXT,              -- completed, failed, in_progress
    completion_time TIMESTAMP
);
```

**Purpose**: Tracks task delegation to specialized agents with their outcomes.

## Context Retrieval Patterns

### Recent Activity Queries
```sql
-- Get recent user requests with file changes
SELECT c.user_intent, c.primary_activity, 
       GROUP_CONCAT(fc.file_path) as files_changed
FROM cycles c 
LEFT JOIN file_contexts fc ON c.cycle_id = fc.cycle_id
WHERE c.start_time > datetime('now', '-1 day')
GROUP BY c.cycle_id
ORDER BY c.start_time DESC;
```

### File History Queries
```sql
-- Get context for specific file modifications
SELECT c.user_intent, fc.change_reason, fc.operation_type, fc.timestamp
FROM file_contexts fc
JOIN cycles c ON fc.cycle_id = c.cycle_id  
WHERE fc.file_path LIKE '%filename%'
ORDER BY fc.timestamp DESC;
```

### Task Complexity Analysis
```sql
-- Identify complex multi-agent tasks
SELECT c.user_intent, 
       COUNT(DISTINCT fc.file_path) as files_modified,
       COUNT(st.id) as subagents_used,
       c.primary_activity
FROM cycles c
LEFT JOIN file_contexts fc ON c.cycle_id = fc.cycle_id
LEFT JOIN subagent_tasks st ON c.cycle_id = st.cycle_id
GROUP BY c.cycle_id
HAVING files_modified > 2 OR subagents_used > 0
ORDER BY c.start_time DESC;
```

## Common Use Cases

### 1. Understanding Previous Work
When a user asks "what did we work on recently?", query the cycles table:

```sql
SELECT user_intent, primary_activity, start_time 
FROM cycles 
WHERE start_time > datetime('now', '-1 week')
ORDER BY start_time DESC;
```

### 2. File Change Context
When working with a file, understand why it was previously modified:

```sql
SELECT c.user_intent, fc.change_reason, fc.timestamp
FROM file_contexts fc
JOIN cycles c ON fc.cycle_id = c.cycle_id
WHERE fc.file_path = 'path/to/file.py'
ORDER BY fc.timestamp DESC
LIMIT 5;
```

### 3. Project Phase Tracking
For ongoing projects, track phase progression:

```sql
SELECT phase_number, task_number, user_intent, primary_activity
FROM cycles 
WHERE phase_number IS NOT NULL
ORDER BY phase_number, task_number;
```

### 4. Delegation Patterns
Understand when and why subagents were used:

```sql
SELECT c.user_intent, st.task_description, st.status
FROM subagent_tasks st
JOIN cycles c ON st.cycle_id = c.cycle_id
WHERE st.status = 'completed'
ORDER BY st.completion_time DESC;
```

## Database Location

The contextual database is project-specific and located at:
```
<project-root>/.claude/smarter-claude/smarter-claude.db
```

Each project maintains its own isolated context database, ensuring no cross-project data contamination.

## Automated Data Collection

The system automatically captures context through hooks:
- **PreToolUse**: Captures intent and tool parameters
- **PostToolUse**: Records results and file changes  
- **Stop**: Generates cycle summaries and cleans up
- **SubagentStop**: Tracks delegation completion

All data collection happens transparently - no user intervention required.

## Privacy and Cleanup

- **Retention Policy**: Configurable cleanup (default: 2 cycles retained)
- **Project Isolation**: Each project has separate database
- **No Personal Data**: Only captures technical context, file paths, and task descriptions
- **Local Storage**: All data stays on local machine

## Integration with TTS System

The contextual memory integrates with Claude's TTS announcement system:
- **Silent Mode**: No announcements, memory still captured
- **Quiet Mode**: Sound notifications only
- **Concise Mode**: Brief planning and completion announcements
- **Verbose Mode**: Detailed workflow narration with context awareness

## Settings Configuration

Contextual memory behavior is controlled through project settings at:
```json
{
  "interaction_level": "verbose",
  "cleanup_policy": {
    "retention_cycles": 2
  },
  "logging_settings": {
    "speak_hook_logging": false,
    "debug_logging": false
  }
}
```

## Usage Instructions for Claude

When users ask about previous work or context:

1. **Query the database** using the patterns above
2. **Provide specific details** from the user_intent and file_contexts
3. **Reference timestamps** to give temporal context
4. **Explain WHY changes were made** using change_reason data
5. **Mention delegation patterns** if subagents were involved

This contextual memory system enables Claude to maintain coherent, context-aware conversations across multiple sessions and provide meaningful continuity for ongoing projects.