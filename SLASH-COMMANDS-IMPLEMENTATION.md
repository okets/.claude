# Slash Commands Implementation Plan

## Overview

This plan outlines the complete implementation of functional slash commands that integrate seamlessly with the `queryable-context.db` database, providing natural language interfaces to our contextual changelog system.

## Current Status

### ✅ **What Works**
- Claude Code slash command framework (Markdown files in `.claude/commands/`)
- Contextual changelog database (`queryable-context.db`) with rich schema
- Python backend scripts (`work_intelligence.py`, `work_manager.py`) with CLI interfaces
- Hook system capturing all file modifications with context

### ❌ **What's Broken**
- Database schema mismatch (Python scripts use old `db.py`, need `queryable_db.py`)
- Command files are documentation-only (no actual script execution)
- SQLite cursor compatibility issues
- No end-to-end integration testing

### 🗑️ **Removed Commands (Not Data-Related)**
- `/git_status` - Standard git operations, no contextual data integration
- `/session_summary` - Outdated, expects old log files
- `/load_context` - Outdated, expects old log files  
- `/file_patterns` - Outdated, expects old log files

## Implementation Strategy

### Phase 1: Database Integration ⚠️ **Critical**

#### Update Python Scripts to Use New Schema

**File:** `hooks/utils/work_intelligence.py`
**Changes:**
```python
# Replace this import:
from db import get_db

# With this:
from queryable_db import get_queryable_db

# Update class initialization:
def __init__(self, project_path: str = None):
    self.db = get_queryable_db()
    # Remove project_id logic (not needed in new schema)
```

**File:** `hooks/utils/work_manager.py`
**Same changes as above**

#### Fix SQL Compatibility Issues

**Problem:** `'sqlite3.Cursor' object does not support the context manager protocol`
**Solution:** Replace cursor context managers with try/finally blocks:

```python
# Replace this pattern:
with self.db.connection.cursor() as cursor:
    cursor.execute(...)

# With this pattern:
cursor = self.db.connection.cursor()
try:
    cursor.execute(...)
    self.db.connection.commit()
finally:
    cursor.close()
```

#### Update SQL Queries for New Schema

**Current schema tables:**
- `session_events` (central event stream)
- `file_changes` (contextual changelog)
- `change_context` (reasoning and context)
- `session_tags` (multi-dimensional navigation)
- `sessions` (session metadata)

**Example query updates:**
```python
# Old query (broken):
SELECT * FROM tool_executions WHERE project_id = ?

# New query (working):
SELECT event_data FROM session_events 
WHERE event_type = 'tool_execution' AND session_id = ?
```

### Phase 2: Command File Implementation 🔧 **High Priority**

#### Convert Documentation to Executable Commands

**File:** `commands/work_query.md`
**Current:** Documentation only
**Target:** Executable command with bash integration

```markdown
---
allowed-tools: Bash(python3:*)
description: Query contextual changelog with natural language
---

# Work Query - Contextual Changelog Analysis

Execute intelligent queries against your project's contextual changelog:

!`python3 hooks/utils/work_intelligence.py $ARGUMENTS`

## Examples
- `/work_query "why did auth.js change?"`
- `/work_query "show me complex authentication tasks"`
- `/work_query "what files change together?"`
```

**File:** `commands/manage_work.md`
**Target:**
```markdown
---
allowed-tools: Bash(python3:*)
description: Manage project phases, tasks, and assignments
---

# Project Work Management

Manage your development workflow with structured phase and task tracking:

!`python3 hooks/utils/work_manager.py $ARGUMENTS`

## Quick Commands
- `/manage_work overview` - Current work status
- `/manage_work create-phase "New Feature"` - Start new phase
- `/manage_work current` - Active tasks
```

#### Enhanced Command Integration


### Phase 3: Advanced Query Patterns 🎯 **Medium Priority**

#### Natural Language Processing Enhancement

**Expand query patterns in `work_intelligence.py`:**

```python
# Add these query patterns:
'file_evolution': [
    r'evolution.*of', r'history.*of', r'changes.*to.*over.*time',
    r'how.*has.*changed', r'timeline.*of'
],
'developer_insights': [
    r'what.*did.*i.*work.*on', r'my.*recent.*work', r'my.*contributions',
    r'what.*have.*i.*been.*doing'
],
'impact_analysis': [
    r'what.*else.*changed.*when', r'impact.*of.*changes',
    r'related.*changes', r'cascade.*effects'
],
'quality_metrics': [
    r'test.*results', r'success.*rate', r'failure.*patterns',
    r'quality.*trends', r'bug.*patterns'
]
```

#### Advanced SQL Query Templates

```python
def get_file_evolution(self, file_path: str, days: int = 30) -> List[Dict]:
    """Get complete evolution of a file with context"""
    return self.db.connection.execute("""
        SELECT 
            fc.timestamp,
            fc.change_type,
            fc.change_summary,
            cc.user_request,
            cc.agent_reasoning,
            cc.test_results,
            s.model
        FROM file_changes fc
        JOIN change_context cc ON fc.id = cc.change_id  
        JOIN sessions s ON fc.session_id = s.id
        WHERE fc.file_path LIKE ? 
        AND fc.timestamp > datetime('now', '-{} days')
        ORDER BY fc.timestamp DESC
    """.format(days), (f'%{file_path}%',)).fetchall()

def get_impact_analysis(self, session_id: str) -> Dict:
    """Analyze the impact and relationships of changes in a session"""
    return {
        'files_changed': self.db.get_session_modified_files(session_id),
        'related_sessions': self._find_related_sessions(session_id),
        'common_patterns': self._identify_patterns(session_id)
    }
```

### Phase 4: Testing & Validation ✅ **Critical**

#### End-to-End Testing Suite

**File:** `test_slash_commands.py`
```python
#!/usr/bin/env python3

import subprocess
import json
from pathlib import Path

def test_work_query_basic():
    """Test basic work_query functionality"""
    result = subprocess.run([
        'python3', 'hooks/utils/work_intelligence.py', 
        'recent work', '--format', 'json'
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"work_query failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert 'results' in data, "Missing results in output"

def test_manage_work_basic():
    """Test basic manage_work functionality"""
    result = subprocess.run([
        'python3', 'hooks/utils/work_manager.py', 
        'overview'
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"manage_work failed: {result.stderr}"

def test_database_connectivity():
    """Test database connection and schema"""
    from hooks.utils.queryable_db import get_queryable_db
    
    db = get_queryable_db()
    assert db.connection is not None, "Database connection failed"
    
    # Test basic query
    cursor = db.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM sessions")
    count = cursor.fetchone()[0]
    assert count >= 0, "Basic query failed"

if __name__ == '__main__':
    test_database_connectivity()
    test_work_query_basic() 
    test_manage_work_basic()
    print("✅ All tests passed!")
```

#### Integration Testing with Claude Code

**Test scenarios:**
1. Type `/work_query "recent work"` in Claude Code
2. Verify bash command execution
3. Confirm proper output formatting
4. Test error handling for invalid queries
5. Validate database query performance

### Phase 5: Performance & Polish 🚀 **Low Priority**

#### Query Optimization

```python
# Add database indexes for common queries
CREATE INDEX IF NOT EXISTS idx_file_changes_path_time ON file_changes(file_path, timestamp);
CREATE INDEX IF NOT EXISTS idx_session_tags_lookup ON session_tags(tag_type, tag_value, session_id);
CREATE INDEX IF NOT EXISTS idx_change_context_user_request ON change_context(user_request);
```

#### Caching Layer

```python
class QueryCache:
    """Simple in-memory cache for frequently accessed data"""
    def __init__(self, ttl_seconds=300):  # 5-minute TTL
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get_or_compute(self, key: str, compute_fn):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
        
        result = compute_fn()
        self.cache[key] = (result, time.time())
        return result
```

## Implementation Timeline

### Week 1: Foundation
- [ ] Fix database schema integration
- [ ] Resolve SQLite compatibility issues  
- [ ] Update Python scripts to use `queryable_db.py`
- [ ] Basic end-to-end testing

### Week 2: Integration
- [ ] Convert command files to executable format
- [ ] Implement bash command integration
- [ ] Test slash commands in Claude Code
- [ ] Fix integration issues

### Week 3: Enhancement  
- [ ] Add advanced query patterns
- [ ] Implement complex analysis functions
- [ ] Performance optimization
- [ ] Documentation updates

### Week 4: Polish
- [ ] Comprehensive testing suite
- [ ] Error handling and edge cases
- [ ] User experience improvements
- [ ] Final validation

## Success Metrics

### Functional Requirements
- [ ] Both core slash commands execute without errors (`/work_query`, `/manage_work`)
- [ ] Natural language queries return relevant results
- [ ] Database queries complete in <1 second for typical queries
- [ ] Integration works seamlessly in Claude Code

### Quality Requirements  
- [ ] 95%+ query success rate
- [ ] Comprehensive error messages for failures
- [ ] Consistent output formatting across commands
- [ ] Full test coverage for core functionality

### User Experience
- [ ] Commands feel natural and intuitive
- [ ] Results provide actionable insights
- [ ] Faster than writing equivalent SQL queries
- [ ] Valuable for daily development workflow

## Risk Mitigation

### Database Schema Evolution
**Risk:** Future schema changes break slash commands
**Mitigation:** Abstract database layer, comprehensive tests

### Performance Degradation
**Risk:** Slow queries impact user experience  
**Mitigation:** Query optimization, caching layer, timeout limits

### Maintenance Overhead
**Risk:** Complex codebase becomes hard to maintain
**Mitigation:** Simple, focused implementations, good documentation

## Conclusion

This implementation plan provides a clear path from the current broken state to fully functional slash commands that enhance the developer experience. The phased approach ensures we build a solid foundation before adding advanced features, while the testing strategy validates functionality at each step.

The end result will be a powerful natural language interface to our contextual changelog system that makes complex project analysis as simple as typing a slash command.