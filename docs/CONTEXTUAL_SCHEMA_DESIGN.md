# Contextual Schema Design and Implementation Plan

## Executive Summary

Based on the research of Claude Code hooks documentation and the hooks mastery repository, this document outlines a comprehensive contextual schema design that captures user intent, tracks all work performed, and enables rich contextual queries. The key insight is that we need to capture data at the right moments in the lifecycle and enrich it with inferred context.

## Part 1: Data Collection Analysis

### Current State vs Ideal State

#### What We're Collecting Now:
1. **Notification Hook**: ✅ Correctly extracts user request from transcript
2. **PreToolUse Hook**: ⚠️ Only logging security events, missing tool intent capture
3. **PostToolUse Hook**: ❌ Not capturing actual results or file changes properly
4. **Stop Hook**: ⚠️ Only recording session end, missing summary generation
5. **SubagentStop Hook**: ❌ Not implemented

#### What We Should Be Collecting:

| Hook | Available Data | What to Extract | Purpose |
|------|---------------|-----------------|---------|
| **Notification** | session_id, transcript_path, message | First user message from transcript | Capture original intent |
| **PreToolUse** | tool_name, tool_input, session_id | Tool intent, target files, operation type | Track what's about to happen |
| **PostToolUse** | tool_name, tool_input, tool_output | Success/failure, actual changes, errors | Record what actually happened |
| **Stop** | session_id, transcript_path | Session summary, total changes, outcome | Summarize session results |
| **SubagentStop** | subagent_id, session_id | Subagent results, delegated work | Track hierarchical work |

### Key Discovery: User Intent Capture

The **transcript_path** is available in ALL hooks! This means we can:
1. Extract the original user request in the Notification hook
2. Parse the transcript for additional context in any hook
3. Track the conversation flow and decision-making process

## Part 2: Contextual Schema Design

### Core Design Principles

1. **Event-Driven Architecture**: Every action is an event in a stream
2. **Context Enrichment**: Each event carries rich contextual information
3. **Relationship Tracking**: Files, tasks, and sessions are interconnected
4. **Intent Preservation**: User's original request flows through all events
5. **Inferential Tagging**: Automatic categorization and pattern detection

### Database Schema

```sql
-- 1. Sessions Table (Enhanced)
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    user_request TEXT NOT NULL,  -- Original user request
    user_request_summary TEXT,   -- AI-generated summary
    final_outcome TEXT,          -- Success/failure/partial
    total_tokens INTEGER,
    total_file_changes INTEGER,
    total_tool_executions INTEGER,
    model TEXT,
    complexity_score REAL,       -- Calculated complexity (0-1)
    FOREIGN KEY (project_path) REFERENCES projects(path)
);

-- 2. Session Events (Core Event Stream)
CREATE TABLE session_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'session_start', 'user_request', 'security_check', 
        'tool_intent', 'tool_execution', 'tool_result',
        'file_change', 'error', 'subagent_start', 
        'subagent_complete', 'session_summary', 'session_end'
    )),
    event_data JSON NOT NULL,
    parent_event_id INTEGER REFERENCES session_events(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, event_sequence),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- 3. Tool Executions (Detailed Tool Tracking)
CREATE TABLE tool_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_id INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    tool_intent TEXT,           -- What we think the tool will do
    tool_input JSON NOT NULL,
    tool_output JSON,
    success BOOLEAN,
    error_message TEXT,
    files_read TEXT[],          -- Array of files read
    files_modified TEXT[],      -- Array of files modified
    execution_time_ms INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (event_id) REFERENCES session_events(id)
);

-- 4. File Changes (The Contextual Changelog)
CREATE TABLE file_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    tool_execution_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    change_type TEXT NOT NULL CHECK (change_type IN (
        'created', 'modified', 'deleted', 'renamed', 'read'
    )),
    change_summary TEXT NOT NULL,
    lines_added INTEGER,
    lines_removed INTEGER,
    diff_preview TEXT,          -- First 500 chars of diff
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (tool_execution_id) REFERENCES tool_executions(id)
);

-- 5. Change Context (The "Why" Behind Changes)
CREATE TABLE change_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_change_id INTEGER NOT NULL,
    user_request TEXT NOT NULL,      -- Original user request
    agent_reasoning TEXT,            -- Why Claude made this change
    related_changes TEXT[],          -- Other files changed in same context
    prompted_by TEXT CHECK (prompted_by IN (
        'user_request', 'test_failure', 'error_fix', 
        'refactoring', 'dependency_update', 'feature_addition'
    )),
    task_id INTEGER,                 -- Link to task management
    phase_id INTEGER,                -- Link to project phase
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_change_id) REFERENCES file_changes(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (phase_id) REFERENCES phases(id)
);

-- 6. Session Tags (Multi-dimensional Navigation)
CREATE TABLE session_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    tag_type TEXT NOT NULL CHECK (tag_type IN (
        'complexity', 'topic', 'file', 'directory', 
        'error_type', 'model', 'outcome', 'pattern'
    )),
    tag_value TEXT NOT NULL,
    tag_metadata JSON,          -- Additional context for the tag
    confidence REAL DEFAULT 1.0,
    UNIQUE(session_id, tag_type, tag_value),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- 7. File Relationships (Track Co-changes)
CREATE TABLE file_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_a TEXT NOT NULL,
    file_b TEXT NOT NULL,
    relationship_type TEXT CHECK (relationship_type IN (
        'imports', 'tests', 'implements', 'extends', 
        'config_for', 'commonly_changed_with'
    )),
    strength REAL DEFAULT 1.0,  -- How strong the relationship is
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (file_a < file_b)     -- Prevent duplicates
);

-- 8. Inferred Insights (Pattern Detection)
CREATE TABLE inferred_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_type TEXT NOT NULL CHECK (insight_type IN (
        'common_error', 'refactoring_pattern', 'test_coverage_gap',
        'complexity_hotspot', 'frequent_change_area', 'architectural_pattern'
    )),
    insight_data JSON NOT NULL,
    confidence REAL DEFAULT 0.5,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    occurrence_count INTEGER DEFAULT 1
);

-- Indexes for Performance
CREATE INDEX idx_events_session ON session_events(session_id);
CREATE INDEX idx_events_type ON session_events(event_type);
CREATE INDEX idx_tool_exec_session ON tool_executions(session_id);
CREATE INDEX idx_file_changes_path ON file_changes(file_path);
CREATE INDEX idx_file_changes_session ON file_changes(session_id);
CREATE INDEX idx_change_context_prompted ON change_context(prompted_by);
CREATE INDEX idx_tags_type_value ON session_tags(tag_type, tag_value);
CREATE INDEX idx_file_rel_files ON file_relationships(file_a, file_b);
```

## Part 3: Data Flow and Collection Strategy

### 1. Notification Hook - Session Initialization
```python
def notification_hook(input_data):
    # Extract user request from transcript
    user_request = extract_first_user_message(transcript_path)
    
    # Create session with full context
    create_session(session_id, project_path, model, user_request)
    
    # Add initial event
    add_event(session_id, 'session_start', {
        'user_request': user_request,
        'model': model,
        'project_context': analyze_project_context()
    })
    
    # Generate initial tags
    tags = infer_tags_from_request(user_request)
    add_session_tags(session_id, tags)
```

### 2. PreToolUse Hook - Intent Capture
```python
def pre_tool_use_hook(input_data):
    tool_name = input_data['tool_name']
    tool_input = input_data['tool_input']
    
    # Infer intent from tool and parameters
    intent = infer_tool_intent(tool_name, tool_input)
    
    # Add tool intent event
    add_event(session_id, 'tool_intent', {
        'tool': tool_name,
        'intent': intent,
        'target_files': extract_file_paths(tool_input),
        'operation_type': classify_operation(tool_name, tool_input)
    })
    
    # Security checks
    if is_dangerous_operation(tool_name, tool_input):
        add_event(session_id, 'security_check', {
            'result': 'blocked',
            'reason': get_block_reason()
        })
        return block_operation()
```

### 3. PostToolUse Hook - Result Recording
```python
def post_tool_use_hook(input_data):
    tool_output = input_data['tool_output']
    
    # Record execution
    execution_id = log_tool_execution(
        session_id, tool_name, tool_input, tool_output,
        success=infer_success(tool_output),
        files_modified=extract_modified_files(tool_name, tool_input, tool_output)
    )
    
    # Track file changes with context
    if tool_modifies_files(tool_name):
        for file_path in get_modified_files(tool_input, tool_output):
            change_id = track_file_change(
                session_id, execution_id, file_path,
                change_type=infer_change_type(tool_name, file_path),
                change_summary=generate_change_summary(tool_input)
            )
            
            # Add contextual information
            add_change_context(
                change_id,
                user_request=get_current_user_request(session_id),
                agent_reasoning=infer_reasoning_from_transcript(session_id),
                related_changes=get_session_modified_files(session_id),
                prompted_by=infer_prompt_reason(session_id)
            )
```

### 4. Stop Hook - Session Summary
```python
def stop_hook(input_data):
    # Generate session summary
    summary = generate_session_summary(session_id, transcript_path)
    
    # Update session with results
    update_session(session_id, {
        'final_outcome': infer_outcome(session_id),
        'total_file_changes': count_file_changes(session_id),
        'total_tool_executions': count_tool_executions(session_id),
        'complexity_score': calculate_complexity(session_id)
    })
    
    # Add final event
    add_event(session_id, 'session_end', {
        'summary': summary,
        'outcome': get_session_outcome(session_id),
        'insights': generate_insights(session_id)
    })
    
    # Update file relationships
    update_file_relationships_from_session(session_id)
    
    # Generate pattern insights
    detect_and_store_patterns(session_id)
```

## Part 4: Inferential Capabilities

### 1. Intent Inference Pipeline
```python
def infer_complete_context(session_id):
    # Layer 1: User Request
    user_request = get_user_request(session_id)
    
    # Layer 2: Tool Sequence Analysis
    tool_sequence = analyze_tool_sequence(session_id)
    
    # Layer 3: File Change Patterns
    change_patterns = analyze_change_patterns(session_id)
    
    # Layer 4: Error Recovery Analysis
    error_context = analyze_error_recovery(session_id)
    
    # Combine all layers
    return {
        'primary_intent': extract_primary_intent(user_request),
        'implementation_strategy': tool_sequence,
        'affected_components': change_patterns,
        'challenges_faced': error_context
    }
```

### 2. Automatic Tagging System
```python
TOPIC_PATTERNS = {
    'authentication': ['auth', 'login', 'jwt', 'token', 'session'],
    'testing': ['test', 'spec', 'jest', 'pytest', 'unit'],
    'database': ['sql', 'query', 'migration', 'schema', 'model'],
    'api': ['endpoint', 'route', 'rest', 'graphql', 'request'],
    'frontend': ['component', 'react', 'vue', 'css', 'ui'],
    'performance': ['optimize', 'cache', 'speed', 'memory', 'profile'],
    'security': ['vulnerability', 'xss', 'csrf', 'encrypt', 'sanitize']
}

def auto_tag_session(session_id, user_request, file_changes):
    tags = []
    
    # Topic tags from request
    for topic, keywords in TOPIC_PATTERNS.items():
        if any(keyword in user_request.lower() for keyword in keywords):
            tags.append(('topic', topic))
    
    # Complexity tags
    complexity = calculate_complexity(session_id)
    if complexity > 0.7:
        tags.append(('complexity', 'complex'))
    elif complexity < 0.3:
        tags.append(('complexity', 'simple'))
    else:
        tags.append(('complexity', 'moderate'))
    
    # File and directory tags
    for file_change in file_changes:
        tags.append(('file', file_change.file_path))
        tags.append(('directory', os.path.dirname(file_change.file_path)))
    
    return tags
```

### 3. Pattern Detection
```python
def detect_patterns(project_id):
    patterns = []
    
    # Co-change patterns
    co_changes = detect_file_co_changes(project_id)
    for pattern in co_changes:
        if pattern.confidence > 0.7:
            patterns.append({
                'type': 'co_change',
                'files': pattern.files,
                'frequency': pattern.frequency,
                'insight': f"Files {pattern.files} often change together"
            })
    
    # Error patterns
    error_patterns = detect_common_errors(project_id)
    for pattern in error_patterns:
        patterns.append({
            'type': 'common_error',
            'error_type': pattern.type,
            'solution_pattern': pattern.common_solution,
            'insight': f"Error '{pattern.type}' often fixed by {pattern.common_solution}"
        })
    
    # Refactoring patterns
    refactor_patterns = detect_refactoring_patterns(project_id)
    
    return patterns
```

## Part 5: Query Capabilities

### Natural Language Query Examples

1. **"Why did auth.js change?"**
```sql
SELECT 
    fc.timestamp,
    fc.change_summary,
    cc.user_request,
    cc.agent_reasoning,
    cc.prompted_by
FROM file_changes fc
JOIN change_context cc ON fc.id = cc.file_change_id
WHERE fc.file_path LIKE '%auth.js%'
ORDER BY fc.timestamp DESC;
```

2. **"Show me complex authentication tasks"**
```sql
SELECT 
    s.id,
    s.user_request,
    s.complexity_score,
    COUNT(DISTINCT fc.file_path) as files_changed,
    COUNT(te.id) as tool_executions
FROM sessions s
JOIN session_tags st ON s.id = st.session_id
JOIN file_changes fc ON s.id = fc.session_id
JOIN tool_executions te ON s.id = te.session_id
WHERE st.tag_type = 'topic' AND st.tag_value = 'authentication'
  AND s.complexity_score > 0.7
GROUP BY s.id
ORDER BY s.started_at DESC;
```

3. **"What files commonly change together?"**
```sql
SELECT 
    fr.file_a,
    fr.file_b,
    fr.relationship_type,
    fr.strength,
    COUNT(*) as co_change_count
FROM file_relationships fr
WHERE fr.relationship_type = 'commonly_changed_with'
  AND fr.strength > 0.5
GROUP BY fr.file_a, fr.file_b
ORDER BY co_change_count DESC;
```

## Part 6: Implementation Plan

### Phase 1: Foundation (Week 1)
1. **Fix hook configuration** to ensure all hooks are called
2. **Implement proper data extraction** in each hook
3. **Create database schema** with all tables
4. **Build core data collection functions**

### Phase 2: Context Enrichment (Week 2)
1. **Implement transcript parsing** for context extraction
2. **Build intent inference system**
3. **Create automatic tagging system**
4. **Develop change context tracking**

### Phase 3: Intelligence Layer (Week 3)
1. **Implement pattern detection algorithms**
2. **Build file relationship tracking**
3. **Create insight generation system**
4. **Develop complexity scoring**

### Phase 4: Query Interface (Week 4)
1. **Build natural language query parser**
2. **Create query optimization layer**
3. **Implement result formatting**
4. **Develop command-line interface**

### Phase 5: Integration (Week 5)
1. **Integrate with existing task management**
2. **Connect to project phases**
3. **Build cross-session analytics**
4. **Create export capabilities**

## Key Implementation Considerations

### 1. Data Collection Timing
- **Notification**: Capture user intent immediately
- **PreToolUse**: Record what we expect to happen
- **PostToolUse**: Record what actually happened
- **Stop**: Summarize and analyze the session

### 2. Context Preservation
- Always link back to original user request
- Maintain parent-child relationships for events
- Track temporal sequences for pattern detection
- Preserve hierarchical context for subagents

### 3. Performance Optimization
- Use database indexes strategically
- Implement caching for frequent queries
- Batch insert operations
- Async processing for heavy analysis

### 4. Privacy and Security
- Never log sensitive data (passwords, keys)
- Implement data retention policies
- Provide data export/deletion capabilities
- Ensure hook security best practices

## Success Metrics

1. **Context Capture Rate**: >95% of file changes linked to user intent
2. **Query Response Time**: <100ms for most queries
3. **Pattern Detection Accuracy**: >80% relevant patterns
4. **User Intent Match**: >90% accurate intent inference
5. **System Overhead**: <5% impact on Claude Code performance

## Conclusion

This contextual schema design provides a comprehensive solution for tracking not just what changes in a codebase, but why it changes. By capturing data at the right moments, enriching it with inferred context, and providing powerful query capabilities, we create a system that enables developers to understand the complete story behind their code evolution.

The key innovation is the multi-layered context capture that preserves user intent throughout the entire execution lifecycle, combined with intelligent inference systems that can extract meaning from the raw event data. This creates a navigable, contextual changelog that serves as a powerful tool for understanding and managing complex software projects.