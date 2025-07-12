# Contextual Changelog Implementation Plan

## Overview

This plan outlines the implementation of a new event-driven, tag-based context system that creates a navigable changelog of all file modifications with rich contextual information. The system will replace the current scattered data storage with a unified, queryable database focused on understanding not just *what* changed, but *why* it changed.

## Core Design Principles

1. **Event Stream Architecture**: All hooks contribute to a single event stream
2. **Contextual File Changes**: Track only modifications (not reads) with full context
3. **Rich Tagging System**: Multi-dimensional tags for easy navigation and discovery
4. **Complete Traceability**: Every change traces back to user intent
5. **No Backward Compatibility**: Fresh start with `queryable-context.db`

## Database Schema

### 1. Core Event Stream

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

CREATE INDEX idx_session_events_session ON session_events(session_id);
CREATE INDEX idx_session_events_type ON session_events(event_type);
CREATE INDEX idx_session_events_parent ON session_events(parent_event_id);
```

### 2. File Changes (The Contextual Changelog)

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

CREATE INDEX idx_file_changes_path ON file_changes(file_path);
CREATE INDEX idx_file_changes_session ON file_changes(session_id);
CREATE INDEX idx_file_changes_timestamp ON file_changes(timestamp);
```

### 3. Change Context

```sql
CREATE TABLE change_context (
    change_id INTEGER PRIMARY KEY REFERENCES file_changes(id),
    user_request TEXT NOT NULL,
    agent_reasoning TEXT,
    task_context TEXT,
    phase_context TEXT,
    related_files JSON,
    test_results TEXT,
    iteration_count INTEGER DEFAULT 1,
    prompted_by TEXT CHECK (prompted_by IN ('user_request', 'test_failure', 'refactoring', 'bug_fix'))
);
```

### 4. Session Tags

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

CREATE INDEX idx_session_tags_type_value ON session_tags(tag_type, tag_value);
CREATE INDEX idx_session_tags_session ON session_tags(session_id);
```

### 5. Sessions Metadata

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    user_request_summary TEXT,
    final_outcome TEXT,
    total_tokens INTEGER,
    total_file_changes INTEGER,
    model TEXT
);
```

## Event Data Structures

### Session Start Event
```json
{
    "type": "session_start",
    "data": {
        "user_request": "Fix the authentication timeout issue",
        "model": "claude-opus-4",
        "project_path": "/Users/dev/myproject",
        "previous_context": "Last worked on auth system 2 days ago"
    }
}
```

### File Change Event
```json
{
    "type": "file_change",
    "data": {
        "file_path": "src/auth.js",
        "change_type": "modified",
        "change_summary": "Added configurable timeout to login function",
        "diff_stats": {
            "lines_added": 15,
            "lines_removed": 3,
            "functions_modified": ["login", "validateSession"]
        },
        "context": {
            "user_request": "Users are getting logged out too quickly",
            "reasoning": "Implementing configurable timeout to address logout complaints",
            "related_files": ["src/config.js", "tests/auth.test.js"],
            "iteration": 1
        }
    }
}
```

### Tool Execution Event
```json
{
    "type": "tool_execution",
    "data": {
        "tool": "Edit",
        "target": "src/auth.js",
        "intent": "implement-feature",
        "success": true,
        "duration_ms": 145
    }
}
```

## Hook Implementation Updates

### 1. notification.py
```python
def handle_notification(data):
    session_id = data['session_id']
    user_message = extract_user_message(data)
    
    # Create session and first event
    db.create_session(session_id, project_path, model)
    db.add_event(session_id, 'session_start', {
        'user_request': user_message,
        'model': model,
        'project_path': project_path
    })
    
    # Generate initial tags
    db.add_session_tags(session_id, [
        ('model', model),
        ('topic', extract_topic(user_message))
    ])
```

### 2. post_tool_use.py
```python
def handle_post_tool_use(data):
    if tool_name in ['Edit', 'Write', 'MultiEdit', 'NotebookEdit']:
        # Track file change with context
        event_id = db.add_event(session_id, 'file_change', {
            'file_path': file_path,
            'change_type': infer_change_type(),
            'change_summary': generate_change_summary(),
            'diff_stats': calculate_diff_stats()
        })
        
        # Add change context
        db.add_change_context(event_id, {
            'user_request': get_current_user_request(),
            'agent_reasoning': extract_reasoning(),
            'task_context': get_active_task(),
            'related_files': get_session_modified_files(),
            'test_results': 'pending'
        })
        
        # Update tags
        db.add_session_tags(session_id, [
            ('file', file_path),
            ('directory', os.path.dirname(file_path))
        ])
```

### 3. stop.py
```python
def handle_stop(data):
    # Analyze session and generate final tags
    session_stats = analyze_session(session_id)
    
    # Add complexity tags based on tokens and operations
    if session_stats['total_tokens'] < 1000:
        complexity = 'simple'
    elif session_stats['total_tokens'] < 5000:
        complexity = 'moderate'
    elif session_stats['total_tokens'] < 15000:
        complexity = 'complex'
    else:
        complexity = 'massive'
    
    db.add_session_tags(session_id, [
        ('complexity', complexity, {
            'tokens': session_stats['total_tokens'],
            'file_changes': session_stats['file_change_count'],
            'duration_minutes': session_stats['duration']
        }),
        ('outcome', session_stats['outcome']),
        ('pattern', detect_workflow_pattern(session_events))
    ])
    
    # Close session
    db.close_session(session_id, final_outcome)
```

## Query Patterns for work_query.md

### 1. Recent Work with Context
```sql
-- "What did I work on recently?"
SELECT 
    s.id,
    s.user_request_summary,
    s.started_at,
    GROUP_CONCAT(DISTINCT fc.file_path) as modified_files,
    GROUP_CONCAT(DISTINCT st.tag_value) as topics
FROM sessions s
LEFT JOIN file_changes fc ON s.id = fc.session_id
LEFT JOIN session_tags st ON s.id = st.session_id AND st.tag_type = 'topic'
WHERE s.started_at > datetime('now', '-7 days')
GROUP BY s.id
ORDER BY s.started_at DESC;
```

### 2. File Change History
```sql
-- "Show me why auth.js changed"
SELECT 
    fc.timestamp,
    fc.change_summary,
    cc.user_request,
    cc.agent_reasoning,
    cc.task_context,
    cc.test_results
FROM file_changes fc
JOIN change_context cc ON fc.id = cc.change_id
WHERE fc.file_path = 'src/auth.js'
ORDER BY fc.timestamp DESC;
```

### 3. Complex Task Analysis
```sql
-- "Show me complex authentication work"
SELECT 
    s.id,
    s.user_request_summary,
    st_complex.tag_metadata,
    GROUP_CONCAT(fc.file_path) as files_modified
FROM sessions s
JOIN session_tags st_complex ON s.id = st_complex.session_id 
    AND st_complex.tag_type = 'complexity' 
    AND st_complex.tag_value IN ('complex', 'massive')
JOIN session_tags st_topic ON s.id = st_topic.session_id 
    AND st_topic.tag_type = 'topic' 
    AND st_topic.tag_value LIKE '%auth%'
LEFT JOIN file_changes fc ON s.id = fc.session_id
GROUP BY s.id;
```

### 4. Pattern Discovery
```sql
-- "What files usually change together?"
SELECT 
    fc1.file_path as file1,
    fc2.file_path as file2,
    COUNT(DISTINCT fc1.session_id) as co_change_count
FROM file_changes fc1
JOIN file_changes fc2 ON fc1.session_id = fc2.session_id 
    AND fc1.id < fc2.id
GROUP BY file1, file2
HAVING co_change_count > 3
ORDER BY co_change_count DESC;
```

## Implementation Steps

1. **Create new database schema** in `queryable-context.db`
2. **Update db.py** with new schema and helper functions
3. **Update each hook** to use event stream approach
4. **Implement tag generation** logic
5. **Update work_intelligence.py** with new query patterns
6. **Update work_query.md** with schema documentation
7. **Test with real workflow** and refine
8. **Update README.md** with complete documentation

## Benefits of This Design

1. **Complete Context**: Every file change has full context - user request, reasoning, outcomes
2. **Rich Navigation**: Tags enable multi-dimensional search and discovery
3. **Pattern Learning**: Automatically discover common workflows and file relationships
4. **Efficient Queries**: Indexed tags and events enable fast lookups
5. **Developer Intelligence**: Understand not just what changed, but why and what else was affected

## Success Metrics

- Can trace any file change back to original user request
- Can find similar past work in < 100ms
- Can generate meaningful insights from patterns
- Can predict related changes when modifying a file
- Can understand the full context of any development decision