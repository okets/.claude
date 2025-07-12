# Long Agent Context System - Complete Data Flow

## Overview
This document explains how the Claude Code hooks system creates persistent, searchable context across multiple sessions. The system automatically tracks all tool usage, builds file relationships, generates conversation summaries, and enables natural language queries of historical work.

**Key Architecture Change**: As of January 2025, the system uses **per-project databases** instead of a machine-wide database. Each project gets its own `.claude/project-context.db` file, providing better isolation and portability.

## System Architecture Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER STARTS NEW CLAUDE SESSION                      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SESSION INITIALIZATION                               │
│  • Generate unique chat_session_id                                          │
│  • Detect project root (via .git)                                          │
│  • Create/connect to <project>/.claude/project-context.db                  │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER: "Fix the auth bug"                           │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TOOL EXECUTION LIFECYCLE                                 │
│                                                                             │
│  ┌──────────────┐     ┌─────────────┐     ┌──────────────┐               │
│  │ PRE-TOOL USE │ ──▶ │ TOOL EXECUTES│ ──▶ │ POST-TOOL USE│               │
│  └──────────────┘     └─────────────┘     └──────────────┘               │
│         │                     │                     │                       │
│         ▼                     ▼                     ▼                       │
│   Security Check        Actual Work          Log Execution                  │
│   • Block .env          • Read files         • Store intent                │
│   • Check paths         • Edit code          • Track files                 │
│   • Log attempt         • Run tests          • Build relationships         │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATABASE UPDATES                                     │
│                                                                             │
│  tool_executions                    file_relationships                      │
│  ┌─────────────────────┐           ┌──────────────────────┐               │
│  │ chat_session_id     │           │ file1: auth.js       │               │
│  │ tool: Edit          │           │ file2: login.js      │               │
│  │ intent: modify-file │           │ co_modification: +1  │               │
│  │ files: [auth.js]    │           │ last_session: xyz123 │               │
│  │ success: true       │           └──────────────────────┘               │
│  │ duration: 45ms      │                                                   │
│  └─────────────────────┘                                                   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SESSION END (stop.py)                                │
│                                                                             │
│  1. Analyze all tool_executions for this chat_session_id                   │
│  2. Extract: files touched, topics, intents, accomplishments               │
│  3. Link to active phases/tasks from database                              │
│  4. Generate human-readable summary                                         │
│  5. Store in conversation_summaries table                                  │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      NEW SESSION - CONTEXT RESTORATION                      │
│                                                                             │
│  User: /work_query "what auth work was done recently?"                     │
│         ↓                                                                   │
│  System queries: conversation_summaries + tool_executions                  │
│         ↓                                                                   │
│  Returns: "Last week you fixed auth bug in login.js, modified auth.js"     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Enhanced Database Schema

### Core Tables

#### 1. conversation_details (Enhanced conversation tracking)
```sql
CREATE TABLE conversation_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_session_id TEXT NOT NULL,
    project_id INTEGER NOT NULL,
    
    -- User request
    user_request_summary TEXT NOT NULL,   -- Initial user request summary
    user_request_raw TEXT,               -- Original user message
    
    -- Agent details  
    agent_model TEXT,                    -- e.g., 'claude-sonnet-4-20250514'
    agent_chain_of_thought TEXT,         -- JSON array of reasoning steps
    
    -- Tool usage
    tools_used TEXT,                     -- JSON array of {tool_name, count, purposes}
    
    -- Subagents
    subagents_used TEXT,                 -- JSON array of subagent invocations
    
    -- Outcomes
    agent_summary TEXT,                  -- Final conversation summary
    lessons_learned TEXT,                -- JSON array of insights
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds INTEGER,
    token_count INTEGER,
    
    FOREIGN KEY (chat_session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
```

#### 2. subagent_executions (Subagent delegation tracking)
```sql
CREATE TABLE subagent_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_chat_session_id TEXT NOT NULL,
    subagent_session_id TEXT NOT NULL,
    subagent_model TEXT NOT NULL,        -- e.g., 'claude-3-opus'
    subagent_task TEXT NOT NULL,         -- What the subagent was asked to do
    subagent_response_summary TEXT,      -- Brief summary of results
    duration_ms INTEGER,
    tool_count INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (parent_chat_session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
```

## Data Flow and Tracking

### 1. Conversation Start (notification.py)
**Enhanced tracking captures**:
```python
db.create_conversation_details(
    chat_session_id=session_id,
    user_request_summary=user_message[:100],  # First 100 chars
    user_request_raw=user_message,            # Complete message
    agent_model='claude-sonnet-4-20250514'    # Current model
)
```

### 2. Tool Execution (post_tool_use.py)
**Builds chain of thought in real-time**:
```python
# Update conversation with reasoning steps
chain_step = {
    "step": step_number,
    "tool": tool_name,
    "intent": infer_intent(tool_name, tool_input),
    "thought": f"Using {tool_name} to {intent_description}",
    "files": extract_files_from_input(tool_input),
    "success": tool_success
}

db.update_conversation_chain_of_thought(session_id, chain_step)

# Track tool usage patterns
db.update_tools_used_summary(session_id, tool_name, intent)
```

**Chain of Thought Example**:
```json
{
  "agent_chain_of_thought": [
    {
      "step": 1,
      "tool": "Read",
      "intent": "reading-file",
      "thought": "Reading auth.js to understand the implementation",
      "files": ["src/auth.js"],
      "success": true
    },
    {
      "step": 2,
      "tool": "Edit", 
      "intent": "modifying-file",
      "thought": "Modifying auth.js to implement changes",
      "files": ["src/auth.js"],
      "success": true
    }
  ]
}
```

### 3. Subagent Delegation (subagent_stop.py)
**Tracks when main agents delegate work**:
```python
db.log_subagent_execution(
    parent_session_id=main_session_id,
    subagent_session_id=sub_session_id,
    subagent_model='claude-3-opus',
    subagent_task='Analyze authentication patterns',
    subagent_response_summary='Found 3 security issues',
    duration_ms=45000,
    tool_count=8
)
```

### 4. Session End (stop.py)
**Generates comprehensive analysis**:
```python
# Extract lessons learned from patterns
lessons = []
if test_failures > 2:
    lessons.append("Required multiple iterations to get tests passing")
if files_modified > 5:
    lessons.append("Complex change affecting multiple components")

db.finalize_conversation_details(
    session_id=session_id,
    agent_summary=generate_summary(tool_executions),
    lessons_learned=lessons,
    duration_seconds=total_duration,
    token_count=estimated_tokens
)
```

**Tools Used Summary Example**:
```json
{
  "tools_used": [
    {
      "tool_name": "Read",
      "count": 5,
      "purposes": ["reading-file"]
    },
    {
      "tool_name": "Edit",
      "count": 3, 
      "purposes": ["modifying-file"]
    }
  ]
}
```

**Lessons Learned Example**:
```json
{
  "lessons_learned": [
    "Token validation was failing due to timezone mismatch",
    "Required multiple iterations (4) to get auth.js working correctly", 
    "Successfully identified and resolved issues in the codebase"
  ]
}
```

## Enhanced Query Capabilities

### Model Attribution Queries
```bash
/work_query "show me all bugs fixed by opus model"
/work_query "what work was done by sonnet"
```

### Chain of Thought Analysis
```bash
/work_query "show chain of thought for fixing login bug"
/work_query "how did you solve the auth problem"
```

### Lessons Learned Mining
```bash
/work_query "what lessons were learned about authentication"
/work_query "insights from testing work"
```

### Subagent Usage Patterns
```bash
/work_query "which tasks used subagents"
/work_query "show delegated tasks"
```

## Data Storage Details (Legacy)

### 1. Pre-Tool Hook (`pre_tool_use.py`)

**Purpose**: Security checks and access control

**What Gets Stored**:
```python
db.log_security_event(
    chat_session_id=session_id,
    event_type='blocked|warned|allowed',
    tool_name='Bash',
    tool_input={'command': 'rm -rf /'},
    reason='Operation outside project directory blocked'
)
```

### 2. Post-Tool Hook (`post_tool_use.py`)

**Purpose**: Log successful operations and build intelligence

**What Gets Stored**:
```python
# Main execution log
db.log_tool_execution(
    chat_session_id=session_id,
    tool_name='Edit',
    tool_input={'file_path': 'src/auth.js', 'old_string': '...', 'new_string': '...'},
    tool_output={'success': True},
    intent='modifying-file',  # Inferred from tool type
    files_touched=['src/auth.js'],
    duration_ms=125
)

# File relationships (if multiple files touched)
db.update_file_relationships(project_id, ['src/auth.js', 'src/login.js'])
```

**Intent Inference Logic**:
```python
def infer_intent(tool_name, tool_input, files_touched):
    if tool_name == 'Read':
        return 'reading-file'
    elif tool_name in ['Write', 'Edit', 'MultiEdit']:
        return 'modifying-file'
    elif tool_name == 'Bash':
        command = tool_input.get('command', '').lower()
        if 'test' in command or 'pytest' in command:
            return 'running-tests'
        elif 'git' in command:
            return 'git-operation'
        elif 'npm' in command:
            return 'package-management'
        elif 'build' in command:
            return 'building'
    elif tool_name == 'Grep':
        return 'searching-code'
```

### 3. Stop Hook (`stop.py`)

**Purpose**: Generate session summary with intelligent tagging

**Analysis Process**:
```python
def analyze_session_for_summary(chat_session_id, project_id, db):
    # 1. Get all tool executions for this session
    executions = db.query("SELECT * FROM tool_executions WHERE chat_session_id = ?")
    
    # 2. Extract patterns
    files_mentioned = set()  # Unique files touched
    topics = set()           # Inferred from file names and commands
    accomplishments = []     # Built from intent counts
    
    # 3. Topic extraction from tool inputs
    for exec in executions:
        if 'auth' in file_path or 'login' in file_path:
            topics.add('authentication')
        if '.js' in file_path or '.ts' in file_path:
            topics.add('javascript-development')
        if 'test' in command:
            topics.add('testing')
    
    # 4. Link to active work context
    active_phases = db.query("SELECT name FROM phases WHERE status = 'active'")
    active_tasks = db.query("SELECT name FROM tasks WHERE status IN ('in_progress', 'todo')")
    
    return {
        'files_mentioned': ['auth.js', 'login.js', 'auth.test.js'],
        'key_topics': ['authentication', 'testing', 'javascript-development'],
        'phase_tags': ['authentication-phase'],
        'task_tags': ['fix-auth-bug'],
        'accomplishments': 'Modified 3 files, Ran tests 2 times'
    }
```

**Generated Summary Example**:
```sql
INSERT INTO conversation_summaries (
    chat_session_id,
    summary,
    key_topics,
    files_mentioned,
    phase_tags,
    task_tags,
    accomplishments,
    tools_used_count,
    session_duration_minutes
) VALUES (
    'abc123-xyz',
    'Accomplished: Modified 3 files, Ran tests 2 times. Worked with files: auth.js, login.js, auth.test.js. Focus areas: authentication, testing.',
    '["authentication", "testing", "javascript-development"]',
    '["auth.js", "login.js", "auth.test.js"]',
    '["authentication-phase"]',
    '["fix-auth-bug"]',
    'Modified 3 files, Ran tests 2 times',
    15,
    45
);
```

## Tagging System

### Automatic Topic Detection

Topics are inferred from multiple sources:

1. **File Names**:
   - `auth.js`, `login.js` → `authentication`
   - `api/routes.js` → `api-development`
   - `Button.jsx` → `ui-development`

2. **Tool Commands**:
   - `npm test` → `testing`
   - `git commit` → `version-control`
   - `webpack build` → `build-process`

3. **File Extensions**:
   - `.js`, `.ts`, `.jsx` → `javascript-development`
   - `.py` → `python-development`
   - `.css`, `.scss` → `styling`

### File Relationship Building

Every time multiple files are touched in the same tool execution:

```sql
-- If Edit modifies auth.js after reading login.js
INSERT INTO file_relationships (
    project_id, file1_path, file2_path, co_modification_count
) VALUES (1, 'auth.js', 'login.js', 1)
ON CONFLICT UPDATE SET 
    co_modification_count = co_modification_count + 1,
    last_chat_session_id = 'current-session-id';
```

## Context Restoration Flow

### 1. Natural Language Query
```bash
/work_query "last 5 tasks involving auth.js"
```

### 2. Query Parsing (`work_intelligence.py`)
```python
def parse_query(query):
    # Pattern matching to determine intent
    if 'last' in query and 'tasks' in query:
        intent = 'conversations_by_file'
    
    # Entity extraction
    entities = {
        'files': ['auth.js'],  # Extracted via regex
        'limit': 5             # Extracted number
    }
    
    return {
        'intent': 'conversations_by_file',
        'entities': entities
    }
```

### 3. Database Query Execution
```sql
SELECT summary, accomplishments, created_at, phase_tags, task_tags
FROM conversation_summaries
WHERE project_id = ? 
  AND files_mentioned LIKE '%auth.js%'
ORDER BY created_at DESC
LIMIT 5;
```

### 4. Formatted Response
```
📋 Conversations involving auth.js:

1. 2025-01-12 15:30 
   Summary: Fixed authentication bug in login flow
   Accomplishments: Modified 3 files, Ran tests 2 times
   Related phases: authentication-phase
   Related tasks: fix-auth-bug

2. 2025-01-10 10:15
   Summary: Refactored auth middleware for better error handling
   Accomplishments: Modified 5 files, Added 3 new test cases
   Related phases: authentication-phase
   Related tasks: improve-error-handling
```

## Complete Workflow Example

### Scenario: Developer fixes an authentication bug across multiple sessions

#### Session 1: Initial Investigation
```
User: "Let me see the auth code"
Claude: [Reads auth.js]

Database state:
- tool_executions: +1 record (Read auth.js)
- conversation_summaries: (added on session end)
```

#### Session 2: Making Changes (Next Day)
```
User: /work_query "what was I working on with auth?"
System: "Yesterday you were reading auth.js in the authentication-phase"

User: "Fix the token validation bug"
Claude: [Edits auth.js, login.js, adds tests]

Database state:
- tool_executions: +5 records (multiple edits and test runs)
- file_relationships: auth.js ↔ login.js (count: 3)
- conversation_summaries: +1 (links to previous work)
```

#### Session 3: Verification (Week Later)
```
User: /work_query "show me recent auth changes"
System: Returns both sessions with summaries, files changed, test results

User: "Did we test the edge cases?"
Claude: [Has context from summaries showing test additions]
```

## Key Implementation Insights

### 1. Chat Session ID as Context Key
- Every tool execution is tagged with `chat_session_id`
- Enables grouping all actions within a conversation
- Allows reconstruction of work sequences

### 2. Intent-Based Intelligence
- Tools aren't just logged; their purpose is inferred
- Creates semantic understanding of work patterns
- Enables queries like "show me all testing work"

### 3. Automatic Relationship Discovery
- No manual tagging required
- Files edited together build relationship strength
- Surfaces hidden dependencies in codebase

### 4. Zero Configuration Design
- Database auto-creates on first use
- Projects auto-register on first tool execution
- No setup or initialization needed

## Per-Project Database Architecture

### Database Location
Each project now has its own database at:
```
<project-root>/.claude/project-context.db
```

### Benefits of Per-Project Approach
1. **Better Isolation**: Each project's data is completely separate
2. **Portability**: Can share project WITH its context history
3. **Privacy**: Client projects don't mix data
4. **Git Integration**: Can optionally track database in git for team sharing
5. **Cleaner Uninstall**: Delete project = delete all its context

### Project Detection
The system finds the project root by:
1. Looking for `.git` directory walking up from current directory
2. If no git found, uses current working directory
3. Creates `.claude/` directory in project root if needed

## Limitations and Considerations

1. **No Cross-Project Intelligence**: Can't query across projects anymore
2. **No User Differentiation**: All work attributed to single user
3. **Growing Database**: No automatic cleanup/archival
4. **No Cross-Machine Sync**: Each machine has separate project database
5. **No Versioning**: Can't track how code evolved over time

## Future Enhancement Possibilities

1. **Export/Import**: Share project context with team
2. **Analytics Dashboard**: Visualize work patterns
3. **Smart Suggestions**: "You usually test after editing auth.js"
4. **Project Templates**: Learn common patterns, suggest workflows
5. **Integration Points**: Connect to ticket systems, git commits