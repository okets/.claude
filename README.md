# Contextual Changelog System - Complete Data Flow

## Overview
This document explains how the Claude Code hooks system creates a **contextual changelog** that tracks not just what files changed, but **why they changed**. Every file modification is linked to the original user request, agent reasoning, test results, and related changes, creating a navigable history of your project's evolution.

**New Architecture**: The system now uses an **event-driven database** (`queryable-context.db`) with rich tagging for multi-dimensional navigation. File reads are ignored - only modifications are tracked to create a clean changelog.

## System Architecture Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER STARTS NEW CLAUDE SESSION                      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SESSION INITIALIZATION (notification.py)                 │
│  • Create session in queryable-context.db                                   │
│  • Capture user request as first event                                      │
│  • Generate initial tags (model, topic)                                     │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    USER: "Fix the authentication timeout issue"              │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EVENT STREAM LIFECYCLE                               │
│                                                                             │
│  ┌──────────────┐     ┌─────────────┐     ┌──────────────┐               │
│  │ TOOL EXECUTES│ ──▶ │ POST-TOOL USE│ ──▶ │ FILE CHANGE  │               │
│  └──────────────┘     └─────────────┘     └──────────────┘               │
│         │                     │                     │                       │
│         ▼                     ▼                     ▼                       │
│   Claude reads        Log as event         Track modification               │
│   and edits files     in event stream      with full context              │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONTEXTUAL CHANGELOG UPDATES                            │
│                                                                             │
│  file_changes                          change_context                       │
│  ┌────────────────────────┐           ┌────────────────────────┐          │
│  │ file_path: auth.js     │           │ user_request: "Fix..."  │          │
│  │ change_type: modified  │ ─────────▶│ reasoning: "Adding      │          │
│  │ summary: "Added        │           │  timeout to address..." │          │
│  │  timeout parameter"    │           │ related_files: [...]    │          │
│  └────────────────────────┘           └────────────────────────┘          │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SESSION END ANALYSIS (stop.py)                          │
│                                                                             │
│  1. Calculate session complexity (tokens, file changes)                     │
│  2. Add tags: complexity, outcome, patterns                                 │
│  3. Close session with final metadata                                       │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONTEXTUAL QUERIES                                   │
│                                                                             │
│  User: /work_query "why did auth.js change?"                               │
│         ↓                                                                   │
│  System queries: file_changes + change_context                             │
│         ↓                                                                   │
│  Returns: "Changed to fix timeout issue requested by user,                  │
│           added configurable timeout parameter, tests passed"               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## New Event-Driven Database Schema

### Database: `queryable-context.db`

The new schema focuses on creating a navigable changelog with rich context for every file modification.

### Core Tables

#### 1. session_events (Central event stream)
```sql
CREATE TABLE session_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'session_start', 'user_request', 'security_check', 
        'tool_execution', 'file_change', 'subagent_start', 
        'subagent_complete', 'session_end'
    )),
    event_data JSON NOT NULL,
    parent_event_id INTEGER REFERENCES session_events(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, event_sequence)
);
```

#### 2. file_changes (The contextual changelog)
```sql
CREATE TABLE file_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_id INTEGER NOT NULL REFERENCES session_events(id),
    file_path TEXT NOT NULL,
    change_type TEXT NOT NULL CHECK (change_type IN ('created', 'modified', 'deleted', 'renamed')),
    change_summary TEXT NOT NULL,
    diff_stats JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3. change_context (The "why" behind changes)
```sql
CREATE TABLE change_context (
    change_id INTEGER PRIMARY KEY REFERENCES file_changes(id),
    user_request TEXT NOT NULL,           -- Original user request
    agent_reasoning TEXT,                 -- Why the change was made
    task_context TEXT,                    -- Active task/phase
    phase_context TEXT,
    related_files JSON,                   -- Other files modified in session
    test_results TEXT,                    -- Did tests pass?
    iteration_count INTEGER DEFAULT 1,    -- How many tries?
    prompted_by TEXT                      -- user_request, test_failure, etc.
);
```

#### 4. session_tags (Multi-dimensional navigation)
```sql
CREATE TABLE session_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    tag_type TEXT NOT NULL CHECK (tag_type IN (
        'complexity', 'phase', 'task', 'file', 'directory',
        'topic', 'outcome', 'pattern', 'model', 'duration'
    )),
    tag_value TEXT NOT NULL,
    tag_metadata JSON,
    confidence REAL DEFAULT 1.0,
    UNIQUE(session_id, tag_type, tag_value)
);
```

## Data Flow Through Hooks

### 1. Session Start (notification.py)
```python
# Create session and capture user request
create_session(session_id, project_path, model)
add_event(session_id, 'session_start', {
    'user_request': message,
    'model': model,
    'project_path': project_path
})

# Generate initial tags
add_session_tags(session_id, [
    ('model', 'claude-opus-4'),
    ('topic', 'authentication')  # Extracted from message
])
```

### 2. File Modification Tracking (post_tool_use.py)
```python
# Only tracks modifications, not reads
if tool_name in ['Edit', 'Write', 'MultiEdit', 'NotebookEdit']:
    # Track file change with full context
    track_file_change(
        session_id=session_id,
        file_path='src/auth.js',
        change_type='modified',
        change_summary='Added timeout parameter to login function',
        context={
            'user_request': 'Fix authentication timeout issue',
            'agent_reasoning': 'Adding configurable timeout to address user complaints',
            'related_files': ['src/config.js', 'tests/auth.test.js'],
            'test_results': 'pending',
            'prompted_by': 'user_request'
        }
    )
    
    # Add navigation tags
    add_session_tags(session_id, [
        ('file', 'src/auth.js'),
        ('directory', 'src/')
    ])
```

### 3. Session Analysis (stop.py)
```python
# Analyze session complexity
if total_tokens < 1000 and file_changes < 2:
    complexity = 'simple'
elif total_tokens < 5000 and file_changes < 5:
    complexity = 'moderate'
elif total_tokens < 15000 and file_changes < 10:
    complexity = 'complex'
else:
    complexity = 'massive'

# Add final tags
add_session_tags(session_id, [
    ('complexity', complexity, {
        'tokens': total_tokens,
        'file_changes': file_change_count,
        'reason': 'Multi-step implementation'
    }),
    ('outcome', 'completed')
])

# Close session
close_session(session_id, final_outcome, total_tokens, file_changes)
```

## Query Examples

### Contextual File History
```sql
-- "Why did auth.js change?"
SELECT 
    fc.timestamp,
    fc.change_summary,
    cc.user_request,
    cc.agent_reasoning,
    cc.test_results,
    s.model
FROM file_changes fc
JOIN change_context cc ON fc.id = cc.change_id
JOIN sessions s ON fc.session_id = s.id
WHERE fc.file_path = 'src/auth.js'
ORDER BY fc.timestamp DESC;
```

### Complex Task Discovery
```sql
-- "Show me complex authentication work"
SELECT 
    s.id,
    s.user_request_summary,
    st_complex.tag_metadata
FROM sessions s
JOIN session_tags st_complex ON s.id = st_complex.session_id 
    AND st_complex.tag_type = 'complexity' 
    AND st_complex.tag_value IN ('complex', 'massive')
JOIN session_tags st_topic ON s.id = st_topic.session_id 
    AND st_topic.tag_type = 'topic' 
    AND st_topic.tag_value = 'authentication'
```

### File Co-modification Patterns
```sql
-- "What files change together?"
SELECT 
    fc1.file_path as file1,
    fc2.file_path as file2,
    COUNT(DISTINCT fc1.session_id) as times_changed_together
FROM file_changes fc1
JOIN file_changes fc2 ON fc1.session_id = fc2.session_id 
    AND fc1.id < fc2.id
GROUP BY file1, file2
HAVING times_changed_together > 3
ORDER BY times_changed_together DESC;
```

## Key Benefits

1. **Contextual Understanding**: Every file change includes the full context - user request, reasoning, test results
2. **Navigable History**: Multi-dimensional tags enable finding work by complexity, topic, model, or outcome
3. **Pattern Discovery**: Automatically identifies which files change together and common workflows
4. **No Data Gaps**: Event stream architecture ensures complete traceability
5. **Fast Queries**: Indexed tags and focused schema enable sub-second lookups

## Implementation Status

### Completed
- ✅ New `queryable-context.db` with event-driven schema
- ✅ Hooks updated to use new database:
  - `notification.py` - Creates sessions and captures user requests
  - `post_tool_use.py` - Tracks file modifications with context
  - `stop.py` - Adds complexity tags and session analysis
- ✅ Rich tagging system for multi-dimensional navigation
- ✅ Contextual changelog tracking (only modifications, not reads)
- ✅ `/work_query` command documentation updated

### Database Locations
- **Primary**: `<project-root>/.claude/queryable-context.db` (new)

### Usage
Simply use Claude Code as normal. The system automatically:
1. Creates the database on first tool use
2. Captures user requests and links them to changes
3. Tags sessions by complexity, topics, and outcomes
4. Enables rich queries through `/work_query`

## Example Workflow

1. **User Request**: "Fix the authentication timeout issue"
2. **Claude Actions**:
   - Reads `auth.js` (not tracked - read only)
   - Edits `auth.js` (tracked with full context)
   - Edits `config.js` (tracked as related change)
   - Runs tests (tracked as tool execution)
3. **Queryable Later**:
   - `/work_query "why did auth.js change?"` → Shows user request, reasoning, test results
   - `/work_query "what files change with auth.js?"` → Shows config.js co-modifications
   - `/work_query "complex authentication tasks"` → Finds this session if tagged as complex

The result is a **navigable changelog** where every file modification tells a complete story.