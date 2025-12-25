# Claude Contextual Memory System

This file documents Claude's enhanced contextual memory capabilities through the **smarter-claude** system.

## Project Context Check

Before starting any task, run:
`ls -la .claude/smarter-claude/smarter-claude.db`

If this file exists, you have access to rich contextual memory.

## CRITICAL: Database-First Policy

BEFORE using git log, git show, or any historical analysis:
1. ALWAYS check if `.claude/smarter-claude/smarter-claude.db` exists
2. If it exists, query it FIRST for file changes and context
3. Only use git as a fallback or for verification

**Trigger phrases that MUST use database first:**
- "what files were changed"
- "what did we work on"
- "recent changes"
- "which files were modified"
- "what was the last thing we did"
- "what did we work on recently"
- "recent activity"
- "previous work"
- "file history"
- "changes made"

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

## Convenience Views for Simplified Queries

To make database queries more accessible, create these views:

```sql
-- Recent file changes (last 7 days) with WHY context
CREATE VIEW recent_file_changes AS
SELECT c.user_intent, fc.file_path, fc.change_reason, 
       fc.operation_type, fc.timestamp, c.cycle_id,
       c.primary_activity
FROM cycles c 
JOIN file_contexts fc ON c.cycle_id = fc.cycle_id
WHERE c.start_time > datetime('now', '-7 days')
ORDER BY fc.timestamp DESC;

-- Recent activity summary with change reasoning
CREATE VIEW recent_activity AS
SELECT c.user_intent, c.primary_activity, c.start_time,
       GROUP_CONCAT(fc.file_path || ' (' || fc.change_reason || ')') as files_and_reasons
FROM cycles c 
LEFT JOIN file_contexts fc ON c.cycle_id = fc.cycle_id
WHERE c.start_time > datetime('now', '-7 days')
GROUP BY c.cycle_id
ORDER BY c.start_time DESC;

-- File modification history with full context
CREATE VIEW file_history AS
SELECT fc.file_path, c.user_intent, fc.change_reason,
       fc.operation_type, fc.timestamp, c.primary_activity,
       CASE 
         WHEN fc.change_reason IS NOT NULL THEN fc.change_reason
         ELSE 'No specific reason recorded'
       END as why_changed
FROM file_contexts fc
JOIN cycles c ON fc.cycle_id = c.cycle_id
ORDER BY fc.file_path, fc.timestamp DESC;

-- WHY analysis view - focuses on reasoning patterns
CREATE VIEW change_reasoning AS
SELECT fc.file_path, fc.change_reason as why,
       c.user_intent as original_request,
       fc.operation_type, fc.timestamp,
       COUNT(*) OVER (PARTITION BY fc.file_path) as total_changes
FROM file_contexts fc
JOIN cycles c ON fc.cycle_id = c.cycle_id
WHERE fc.change_reason IS NOT NULL
ORDER BY fc.timestamp DESC;
```

## Common Database Queries

### Quick Pattern Lookups

**Files changed in recent task with WHY context:**
```sql
SELECT file_path, change_reason, user_intent, timestamp 
FROM recent_file_changes 
LIMIT 10;
```

**What did we work on recently with reasoning:**
```sql
SELECT user_intent, files_and_reasons, start_time 
FROM recent_activity 
LIMIT 5;
```

**History for specific file with WHY context:**
```sql
SELECT user_intent, why_changed, operation_type, timestamp
FROM file_history
WHERE file_path LIKE '%filename%'
LIMIT 5;
```

**WHY was this file changed so much:**
```sql
SELECT why, original_request, timestamp, total_changes
FROM change_reasoning
WHERE file_path LIKE '%filename%'
LIMIT 10;
```

**What types of changes are we making:**
```sql
SELECT change_reason, COUNT(*) as frequency,
       GROUP_CONCAT(DISTINCT file_path) as affected_files
FROM recent_file_changes
WHERE change_reason IS NOT NULL
GROUP BY change_reason
ORDER BY frequency DESC;
```

### Time Boundary Guidelines

**Default time ranges for queries:**
- **Recent work**: Last 7 days (`datetime('now', '-7 days')`)
- **Current session**: Last 24 hours (`datetime('now', '-1 day')`)
- **Extended history**: Last 30 days (`datetime('now', '-30 days')`)
- **All history**: No time filter (use with LIMIT)

### Pattern Matching Best Practices

**File path matching:**
```sql
-- Exact match (fastest)
WHERE fc.file_path = 'src/components/Header.tsx'

-- Filename only
WHERE fc.file_path LIKE '%Header.tsx'

-- Directory pattern
WHERE fc.file_path LIKE 'src/components/%'

-- Multiple patterns
WHERE fc.file_path LIKE '%Header%' OR fc.file_path LIKE '%Nav%'
```

**Intent matching:**
```sql
-- Bug-related work
WHERE c.user_intent LIKE '%bug%' OR c.user_intent LIKE '%fix%'

-- Feature development
WHERE c.user_intent LIKE '%feature%' OR c.user_intent LIKE '%add%'

-- Refactoring
WHERE c.user_intent LIKE '%refactor%' OR c.user_intent LIKE '%cleanup%'
```

### WHY Context Best Practices

**Good change_reason examples:**
- "Fix TypeScript error in component props"
- "Add validation to prevent null user data"
- "Optimize query performance for large datasets"
- "Update API endpoint to match new backend schema"
- "Remove deprecated function calls"

**Poor change_reason examples:**
- "Updated file"
- "Made changes"
- "Fixed it"
- "Code cleanup"

**WHY-focused queries for better context:**
```sql
-- Understanding decision patterns
SELECT change_reason, COUNT(*) as times_used,
       AVG(julianday('now') - julianday(timestamp)) as avg_days_ago
FROM file_contexts
WHERE change_reason IS NOT NULL
GROUP BY change_reason
ORDER BY times_used DESC;

-- Files that keep getting changed for same reason
SELECT file_path, change_reason, COUNT(*) as repeat_changes
FROM file_contexts
WHERE change_reason IS NOT NULL
GROUP BY file_path, change_reason
HAVING repeat_changes > 1
ORDER BY repeat_changes DESC;

-- Tracing problem resolution
SELECT c.user_intent, fc.file_path, fc.change_reason, fc.timestamp
FROM cycles c
JOIN file_contexts fc ON c.cycle_id = fc.cycle_id
WHERE c.user_intent LIKE '%error%' OR c.user_intent LIKE '%bug%'
   OR fc.change_reason LIKE '%fix%' OR fc.change_reason LIKE '%error%'
ORDER BY fc.timestamp DESC;
```

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

**Example triggers**: "what did we work on recently?", "what was the last thing we did?", "recent activity"

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

**Example triggers**: "what files were changed?", "which files were modified?", "file history"

### 3. Recent File Changes Across All Files
For broad change tracking:

```sql
SELECT fc.file_path, fc.change_reason, fc.operation_type, c.user_intent, fc.timestamp
FROM file_contexts fc
JOIN cycles c ON fc.cycle_id = c.cycle_id
WHERE fc.timestamp > datetime('now', '-3 days')
ORDER BY fc.timestamp DESC
LIMIT 20;
```

**Example triggers**: "what files were changed?", "recent changes", "changes made"

### 4. Project Phase Tracking
For ongoing projects, track phase progression:

```sql
SELECT phase_number, task_number, user_intent, primary_activity
FROM cycles 
WHERE phase_number IS NOT NULL
ORDER BY phase_number, task_number;
```

### 5. Delegation Patterns
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

## When to Query the Database

Claude should query the contextual memory database in these scenarios:

- **User asks about previous work**: "what did we work on recently?", "what was the last thing we did?"
- **File modification history unclear**: Working on files without clear context of why they were previously changed
- **User references earlier conversations**: "like we discussed before", "the bug we fixed yesterday"
- **Complex multi-step tasks**: Need to understand project progression and dependencies
- **Cross-session continuity**: When user resumes work after time gap
- **Error context**: Understanding why certain approaches were tried/abandoned

## Fallback Behavior

If the contextual database is unavailable or corrupted:
- Continue normal operation without context queries
- Capture what information is possible for future sessions
- Inform user that historical context is limited
- Rely on immediate conversation context and file inspection

## Query Performance Guidelines

For optimal performance on large projects:
- **Limit results**: Use `LIMIT 50` for cycles queries to avoid overwhelming context
- **Time boundaries**: Default to last 7 days unless user specifies otherwise
- **File path matching**: Use exact paths when possible; `LIKE` patterns only when necessary
- **Indexed fields**: Prefer queries on `timestamp`, `file_path`, and `cycle_id` for faster results

## Data Validation

Valid database entries should have:
- **Non-empty user_intent**: Essential for understanding request context
- **Valid file_paths**: Must exist or have existed in the project
- **Meaningful change_reason**: Explains WHY not just WHAT was changed
- **Consistent timestamps**: All times in UTC format
- **Valid status values**: Only predefined statuses (completed, failed, in_progress)

## Cross-Session Behavior

The contextual memory system maintains continuity across multiple Claude sessions:
- **Session isolation**: Each conversation gets unique session_id
- **Persistent context**: Previous sessions remain queryable
- **Progressive understanding**: Context builds over time across sessions
- **Intent linking**: Related requests across sessions can be identified

## Real-World Examples

### Example 1: User asks "What was that bug we fixed yesterday?"
```sql
SELECT c.user_intent, fc.change_reason, fc.file_path, c.start_time
FROM cycles c
JOIN file_contexts fc ON c.cycle_id = fc.cycle_id
WHERE c.start_time > datetime('now', '-2 days') 
  AND (c.user_intent LIKE '%bug%' OR fc.change_reason LIKE '%fix%')
ORDER BY c.start_time DESC;
```

**Expected result**: Shows specific bug description, which files were changed, and why they were modified.

### Example 2: User resumes work on feature after weekend
```sql
SELECT c.user_intent, c.primary_activity, fc.file_path, c.start_time
FROM cycles c
LEFT JOIN file_contexts fc ON c.cycle_id = fc.cycle_id
WHERE c.start_time > datetime('now', '-7 days')
  AND c.user_intent LIKE '%feature%'
ORDER BY c.start_time DESC
LIMIT 10;
```

**Expected result**: Recent work on features with context about what was accomplished.

## Usage Instructions for Claude

When users ask about previous work or context:

1. **Query the database** using the patterns above
2. **Provide specific details** from the user_intent and file_contexts
3. **Reference timestamps** to give temporal context
4. **Explain WHY changes were made** using change_reason data
5. **Mention delegation patterns** if subagents were involved
6. **Handle missing data gracefully** - explain what context is available vs. missing

### Capturing Better WHY Context

**When recording file changes, always include:**
- **Root cause**: Why was this change necessary?
- **Problem solved**: What specific issue did this address?
- **Impact**: How does this change affect the system?
- **Decision rationale**: Why this approach vs alternatives?

**Examples of good WHY context recording:**
```sql
-- Instead of: "Updated component"
INSERT INTO file_contexts (change_reason) VALUES 
('Fix prop drilling by implementing Redux state management');

-- Instead of: "Fixed bug"
INSERT INTO file_contexts (change_reason) VALUES 
('Resolve infinite loop in useEffect by adding dependency array');

-- Instead of: "Added feature"
INSERT INTO file_contexts (change_reason) VALUES 
('Implement user authentication to secure dashboard routes');
```

**When querying for WHY context, prioritize:**
1. **change_reason** field for specific technical reasoning
2. **user_intent** for the original business/user need
3. **Timestamps** to understand sequence of related changes
4. **Repeat patterns** to identify recurring issues

**WHY-focused response format:**
```
File: src/components/Header.tsx
When: 2024-01-15 14:30:00
Why: Fix TypeScript error in component props
Original need: User reported navigation not working
Impact: Resolves type safety issues in navigation component
```

This contextual memory system enables Claude to maintain coherent, context-aware conversations across multiple sessions and provide meaningful continuity for ongoing projects.
- add these requirements as our coding stnadards.
  - Single Responsibility - Each method has one clear purpose
  - DRY (Don't Repeat Yourself) - Validation logic is centralized
  - Clean Code - Methods are small, focused, and well-named