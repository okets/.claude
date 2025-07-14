# Smarter-Claude

> **Give Claude Code long-term memory and context awareness**

<div align="center">

# 🚀 One-Line Install

```bash
curl -sSL https://raw.githubusercontent.com/okets/.claude/main/install.sh | bash
```

**That's it!** Claude Code now remembers everything.

</div>

## What It Does

- **Remembers every interaction** - "What was my last request?" gets a real answer
- **Tracks WHY files changed** - Not just what, but the intent behind every edit  
- **Smart notifications** - Customizable TTS announcements that actually help
- **Query your history** - Ask Claude about your past work and decisions

## How It Works

1. **Install once** - The script sets up everything automatically
2. **Use Claude Code normally** - Every interaction gets recorded with context
3. **Query when needed** - Ask Claude about your development history

```python
# Ask Claude: "What files did I change yesterday and why?"
# Or query directly:
from hooks.utils.contextual_db import ContextualDB
db = ContextualDB()
recent_files = db.get_file_context("", limit=10)
```

## Features

- **Contextual database** - 4-table SQLite schema tracks everything
- **TTS notifications** - Choose from silent, quiet, concise, or verbose modes
- **Intent tracking** - Every file change linked to your original request
- **Multi-agent support** - Tracks both main Claude and subagent work
- **Easy queries** - Ask Claude about your development history

## Configuration

```bash
# Change notification level
python ~/.claude/hooks/utils/manage_settings.py set interaction_level verbose

# Switch TTS voice  
python ~/.claude/hooks/utils/manage_settings.py set tts_engine coqui-female
```

**Or just ask Claude**: *"Make my notifications more verbose"* or *"Switch to the male voice"*

## Documentation

- **[Getting Started](docs/GETTING_STARTED.md)** - Complete setup guide
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Fix issues with Claude's help  
- **[Database Schema](docs/DATABASE_SCHEMA.md)** - Query patterns and examples

## Need Help?

**Just ask Claude**: *"Help me troubleshoot smarter-claude"* or *"Show me my recent file changes"*

---

**Transform your Claude Code experience from stateless interactions to intelligent, context-aware development sessions.**

