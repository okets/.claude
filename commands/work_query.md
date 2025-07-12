# Work Query - Contextual Changelog & Project Intelligence

Query your project's contextual changelog, understanding not just what changed but why it changed. Every file modification is tracked with full context including user requests, reasoning, and related changes.

## Usage

```
/work_query [options] <query>
```

## Options

- `--project <name>` - Query specific project (default: current)
- `--days <n>` - Limit to last N days (default: 7)
- `--format <json|table|summary>` - Output format (default: summary)
- `--limit <n>` - Limit results (default: 20)

## Query Types

### Contextual File Changelog
```
/work_query why did auth.js change?
/work_query show me the evolution of Login.tsx
/work_query what prompted changes to the config file?
/work_query history of authentication implementation
```

### Recent Sessions with Full Context
```
/work_query what did I work on today?
/work_query show me complex tasks from this week
/work_query sessions where tests failed multiple times
/work_query what did opus model accomplish?
```

### File Relationships & Co-changes
```
/work_query what files change together with auth.js?
/work_query files commonly modified during authentication work
/work_query show related changes when I modify package.json
```

### Complexity & Pattern Analysis
```
/work_query show me massive tasks
/work_query simple bug fixes from last week
/work_query what makes tasks complex in this project?
/work_query common refactoring patterns
```

### Tagged Navigation
```
/work_query authentication work
/work_query all testing sessions
/work_query bug-fix conversations
/work_query feature development by sonnet
```

## Examples

```bash
# Understand why a file changed
/work_query "why did src/auth.js change?"
→ Shows: user request, reasoning, test results, related files

# Track file evolution
/work_query "show me all changes to Login.tsx with context"
→ Timeline of modifications with reasons and outcomes

# Find complex work
/work_query "show me complex authentication tasks"
→ Sessions tagged as complex + authentication topic

# Analyze patterns
/work_query "what files usually change together?"
→ Co-modification frequency analysis

# Model-specific queries
/work_query "what bugs did opus fix?"
→ Sessions by opus model with bug-fix tags
```

## Database Schema

The system uses a new `queryable-context.db` with an event-driven architecture:

### Core Tables

1. **session_events** - Single event stream for all activities
   - Event types: session_start, tool_execution, file_change, session_end
   - Parent-child relationships for nested operations

2. **file_changes** - Contextual changelog
   - Tracks only modifications (not reads)
   - Links each change to user request and reasoning

3. **change_context** - The "why" behind each change
   - User request that prompted the change
   - Agent reasoning and thought process
   - Test results and iteration count

4. **session_tags** - Multi-dimensional navigation
   - Tag types: complexity, topic, file, directory, model, outcome
   - Enables fast lookups by any dimension

### Key Features

- **Complete Traceability**: Every file change traces back to the original user request
- **Rich Context**: Understand not just what changed, but why and what else was affected
- **Smart Tagging**: Automatic categorization by complexity, topics, and patterns
- **Fast Navigation**: Indexed tags enable sub-second queries even with millions of events

## Query Implementation

Queries are processed through natural language understanding that maps to optimized SQL:

```sql
-- Example: "why did auth.js change?"
SELECT 
    fc.timestamp,
    fc.change_summary,
    cc.user_request,
    cc.agent_reasoning,
    cc.test_results
FROM file_changes fc
JOIN change_context cc ON fc.id = cc.change_id
WHERE fc.file_path LIKE '%auth.js%'
ORDER BY fc.timestamp DESC
```

## Database Location

- Primary: `<project-root>/.claude/queryable-context.db`
