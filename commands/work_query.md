# Work Query - Advanced Project Intelligence

Query your project work history, phases, tasks, and file relationships using natural language.

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

### Recent Activity
```
/work_query what did I work on today?
/work_query recent file changes
/work_query show me git operations from yesterday
```

### File Intelligence
```
/work_query files related to user authentication
/work_query what files are commonly modified together?
/work_query show file relationships for src/components/Login.tsx
```

### Task & Phase Tracking
```
/work_query active tasks
/work_query tasks in testing phase
/work_query completed assignments this week
/work_query what's blocking me?
```

### Pattern Analysis
```
/work_query common workflows in this project
/work_query how do I usually test components?
/work_query debugging patterns
```

### Security & Issues
```
/work_query blocked operations
/work_query security warnings
/work_query failed tool executions
```

## Examples

```bash
# Quick project overview
/work_query overview

# Find files you work on together
/work_query "files that change together with package.json"

# Track testing workflow
/work_query "show me testing related activities"

# Phase progress
/work_query "progress on authentication phase"

# Debug failed operations
/work_query "why did my last git push fail?"
```

## Smart Features

- **Intent Recognition**: Understands natural language queries
- **Context Aware**: Considers current project and recent work
- **Relationship Mapping**: Shows how files/tasks connect
- **Pattern Detection**: Identifies common workflows
- **Time Intelligence**: Handles relative time queries

## Database Requirements

Requires MySQL database with environment variables:
- `CLAUDE_DB_HOST` (default: localhost)
- `CLAUDE_DB_USER` (default: root) 
- `CLAUDE_DB_PASSWORD`
- `CLAUDE_DB_NAME` (default: claude_intelligence)

Falls back to JSON logs if database unavailable.