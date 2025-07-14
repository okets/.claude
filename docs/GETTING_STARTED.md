# Getting Started with Smarter-Claude

## What is Smarter-Claude?

Smarter-Claude transforms Claude Code from a stateless assistant into a context-aware development partner by providing:

- **Long-term memory**: Every interaction is stored in a SQLite database
- **Intent tracking**: Why each file was changed, not just what changed
- **Context-aware assistance**: Query your development history
- **Smart notifications**: Customizable TTS announcements

## 🚀 One-Line Installation

**The easiest way to install smarter-claude:**

```bash
# When repo is public:
curl -sSL https://raw.githubusercontent.com/okets/.claude/main/install.sh | bash

# For now, download and run locally:
git clone https://github.com/okets/.claude
cd .claude && ./install.sh
```

That's it! The script will:
- ✅ Check if Claude Code is installed
- ✅ Download and install smarter-claude
- ✅ Install optional TTS engines (Coqui)
- ✅ Configure sensible defaults
- ✅ Test the installation

### Manual Installation (if preferred)

<details>
<summary>Click to expand manual steps</summary>

#### 1. Install Prerequisites

```bash
# Ensure Claude Code is installed
claude --version

# Install optional high-quality TTS (recommended)
uv tool install coqui-tts

# On macOS, install ffmpeg for enhanced male voice
brew install ffmpeg
```

#### 2. Clone and Configure

```bash
# Clone to your global Claude directory
cd ~/.claude
git clone https://github.com/okets/smarter-claude .

# Configure your preferred interaction level
python hooks/utils/manage_settings.py set interaction_level concise

# Set your preferred TTS voice
python hooks/utils/manage_settings.py set tts_engine coqui-female
```

#### 3. Verify Installation

```bash
# Start Claude Code in any project
cd /path/to/your/project
claude

# After your first interaction, check the database was created
ls .claude/smarter-claude/
# Should see: smarter-claude.db
```

</details>

## ✅ Verify It's Working

```bash
# Start Claude Code in any project
cd /path/to/your/project
claude

# After your first interaction, you should see:
ls .claude/smarter-claude/
# → smarter-claude.db
```

**Having issues?** Ask Claude directly:
```
I just installed smarter-claude but it's not working. Can you check my installation and fix any issues?
```

## Understanding Interaction Levels

### Silent Mode
- No audio feedback
- Database logging only
- Perfect for shared environments

### Quiet Mode  
- Subtle notification sounds
- No verbal announcements
- Minimal but present feedback

### Concise Mode (Default)
- Brief TTS announcements for key actions
- Task completion summaries
- Balanced feedback level

### Verbose Mode
- Detailed narration of all actions
- Pre-tool and post-tool announcements
- Full workflow commentary

## Your First Query

After using Claude Code for a few interactions, you can query your development history:

```python
# In a Python script or interactive session
from hooks.utils.contextual_db import ContextualDB

db = ContextualDB()

# What was I working on recently?
recent_cycles = db.get_phase_task_context(phase_number=None)
for cycle in recent_cycles[:5]:
    print(f"Intent: {cycle['user_intent']}")
    print(f"Activity: {cycle['primary_activity']}")
    print("---")

# What files have I been editing?
recent_files = db.get_file_context("", limit=10)
for file_ctx in recent_files:
    print(f"{file_ctx['file_path']}: {file_ctx['change_reason']}")
```

## Next Steps

- Read the [Database Schema Guide](DATABASE_SCHEMA.md) to understand query patterns
- Explore [Advanced Usage](ADVANCED_USAGE.md) for complex workflows
- Check the [Troubleshooting Guide](TROUBLESHOOTING.md) if you encounter issues

## Common Use Cases

### Development Workflow Memory
- "What was I working on last session?"
- "Why did I change this file?"
- "How did I solve similar problems?"

### Code Review Assistance
- Intent-driven diffs showing WHY changes were made
- Complete workflow context for file modifications
- Team collaboration history

### Project Knowledge Base
- Pattern recognition across development sessions
- Context-aware assistance for future interactions
- Knowledge transfer between team members

Welcome to intelligent, context-aware Claude Code development!