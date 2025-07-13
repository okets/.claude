# Claude Code Global Hooks with Contextual Memory System

A comprehensive hook system for Claude Code that provides **long-term contextual memory** and **intent-driven logging** for AI development workflows.

## 🧠 What This Gives You

**Transform Claude Code from a stateless assistant into a context-aware development partner:**

- **Remember every interaction**: "What was my last request?" answered from database, not memory
- **Track user intent**: Why each file was changed, not just what changed
- **Query development history**: "Show me all changes to hooks/stop.py and the user intents behind them"
- **Context-aware assistance**: Future integration with Claude.md for intelligent context retrieval
- **Full workflow capture**: File modifications, subagent delegations, and task progressions

## 🚀 Key Features

### Contextual Memory Database
- **4-table SQLite schema** optimized for fast context queries
- **Automatic database ingestion** - every cycle immediately available
- **Intent-driven organization** - every change linked to user goals
- **Multi-agent tracking** - main agent and subagent work fully captured

### Intelligent Hook System
- **Universal logging** - Pre/Post tool use, Stop hooks, Subagent completions
- **Smart intent extraction** - TodoWrite progression for structured tasks, transcript parsing for read-only tasks
- **Rich timeline data** - Complete audit trail of every development session
- **TTS announcements** - Real-time feedback on hook execution

### Query Interface
```python
# Query what files were edited and why
db.execute("SELECT file_path, change_reason FROM file_contexts WHERE cycle_id = ?")

# Find user intents for a specific phase
db.execute("SELECT user_intent FROM cycles WHERE primary_activity = 'file_modification'")

# Track subagent work patterns
db.execute("SELECT task_description, status FROM subagent_tasks WHERE cycle_id = ?")
```

## 📊 Database Schema

### Core Tables
- **`cycles`** - User intent, timing, primary activity per development cycle
- **`file_contexts`** - File changes with WHY context, not just WHAT changed  
- **`llm_summaries`** - Generated insights and workflow analysis
- **`subagent_tasks`** - Delegation context and completion tracking

### Sample Data
```json
{
  "user_intent": "Add transcript parsing to extract user intent in all hooks",
  "file_activities": {
    "/hooks/utils/cycle_utils.py": {
      "change_reason": "Added extract_user_intent_from_transcript() function",
      "operations": ["edit"],
      "edit_count": 3
    }
  },
  "primary_activity": "file_modification"
}
```

## 🛠 Installation

### Prerequisites
- Claude Code CLI installed and configured
- Python 3.8+ with standard libraries
- SQLite3 (included with Python)

### Setup
1. **Clone to your global Claude directory:**
   ```bash
   cd ~/.claude
   git clone <this-repo> .
   ```

2. **Hooks are automatically active** - Claude Code will start using them immediately

3. **Verify installation:**
   ```bash
   # Check if hooks are working
   ls ~/.claude/.claude/session_logs/
   
   # Should see: session_*_cycle_*_hooks.jsonl and *_summary.json files
   ```

## 🔧 Usage

### Basic Queries
```python
from contextual_db import ContextualDB

db = ContextualDB()
db.connect()

# What was my last request?
cursor = db.conn.execute("SELECT user_intent FROM cycles ORDER BY cycle_id DESC LIMIT 1")
print(cursor.fetchone()[0])

# What files were edited recently?
cursor = db.conn.execute("""
    SELECT file_path, change_reason 
    FROM file_contexts 
    WHERE cycle_id >= (SELECT MAX(cycle_id) - 5 FROM cycles)
""")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")
```

### Advanced Analysis
```python
# Find all contextual logging implementations
cursor = db.conn.execute("""
    SELECT c.user_intent, f.file_path, f.change_reason
    FROM cycles c 
    JOIN file_contexts f ON c.cycle_id = f.cycle_id
    WHERE c.user_intent LIKE '%contextual%'
""")
```

## 🎯 Use Cases

### Development Workflow Memory
- **"Why did I change this file?"** - Query change reasons for any file
- **"What was I working on last session?"** - Review recent user intents
- **"How did I solve similar problems?"** - Search historical patterns

### Code Review Assistance  
- **Intent-driven diffs** - See WHY changes were made, not just WHAT
- **Workflow context** - Understand the full story behind file modifications
- **Collaboration history** - Track main agent vs subagent contributions

### Project Knowledge Base
- **Context-aware assistance** - Future Claude.md integration will provide relevant context automatically
- **Pattern recognition** - Identify recurring development workflows
- **Knowledge transfer** - Share development context with team members

## 📁 File Structure

```
~/.claude/
├── hooks/
│   ├── pre_tool_use.py       # Captures tool execution intent
│   ├── post_tool_use.py      # Logs tool results and file changes  
│   ├── stop.py               # Generates cycle summaries and database ingestion
│   └── utils/
│       ├── cycle_utils.py    # Core hook utilities and transcript parsing
│       ├── hook_parser.py    # Timeline analysis and intent extraction
│       ├── contextual_db.py  # Database schema and operations
│       └── data_collector.py # JSONL to database pipeline
├── session_logs/
│   ├── session_*_cycle_*_hooks.jsonl     # Raw hook timeline data
│   ├── session_*_cycle_*_summary.json    # Rich contextual summaries
│   └── contextual_context.db             # SQLite database
└── README.md
```

## 🔍 How It Works

### Hook Execution Flow
```
User Request
    ↓
PreToolUse Hook → Extract user intent from transcript
    ↓
Tool Execution (Edit, Read, Bash, etc.)
    ↓  
PostToolUse Hook → Log file changes with context
    ↓
Stop Hook → Generate cycle summary → Auto-ingest to database
```

### Intent Extraction Strategy
1. **TodoWrite progression** (structured tasks) - Highest priority
2. **Transcript parsing** (read-only tasks) - Fallback for unstructured queries  
3. **Tool pattern analysis** - Command descriptions and usage patterns

### Data Processing Pipeline
```
Raw Hook Events → Timeline Analysis → Intent Extraction → Summary Generation → Database Storage
```

## 🎉 Success Stories

### Before: Limited Context
```json
{
  "user_intent": "Unknown task",
  "file_activities": {},
  "primary_activity": "general_assistance"
}
```

### After: Rich Context Memory
```json
{
  "user_intent": "Add transcript parsing to extract user intent in all hooks",
  "file_activities": {
    "cycle_utils.py": {
      "change_reason": "Added extract_user_intent_from_transcript() for read-only task context",
      "edit_count": 3
    }
  },
  "primary_activity": "file_modification",
  "timeline_metadata": {
    "total_hook_events": 12,
    "duration": "2 minutes 15 seconds"
  }
}
```

## 🛣 Roadmap

### Phase 5 Complete ✅
- [x] 4-table database schema
- [x] Automatic database ingestion
- [x] Transcript parsing for read-only tasks
- [x] Intent-driven logging system

### Future Enhancements
- [ ] Claude.md integration for context-aware assistance
- [ ] Web interface for browsing development history
- [ ] Advanced analytics and pattern recognition
- [ ] Export capabilities for documentation generation
- [ ] Cross-session project memory
- [ ] Integration with git for commit message generation

## 🤝 Contributing

This system captures the complete development workflow - including how it was built! Check the database for the full implementation story:

```python
# See how this system was developed
cursor = db.conn.execute("""
    SELECT user_intent, file_path, change_reason 
    FROM cycles c JOIN file_contexts f ON c.cycle_id = f.cycle_id 
    WHERE f.file_path LIKE '%contextual%' 
    ORDER BY c.cycle_id
""")
```

## 📄 License

MIT License - Build upon this, share improvements, and help make AI development workflows more intelligent.

## 🙏 Acknowledgments

Built with Claude Code CLI - this system is a testament to the power of AI-assisted development with proper contextual memory.

---

**Transform your Claude Code experience from stateless interactions to intelligent, context-aware development sessions.**