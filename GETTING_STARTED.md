# 🚀 Getting Started with Smarter-Claude

> **Transform Claude Code from stateless to context-aware in 30 seconds**

[![Memory](https://img.shields.io/badge/🧠_Long_Term-Memory-purple)](../README.md)
[![Intent Tracking](https://img.shields.io/badge/🎯_Intent-Tracking-green)](../README.md)
[![Smart TTS](https://img.shields.io/badge/🔊_Smart-Notifications-blue)](../README.md)
[![Zero Tokens](https://img.shields.io/badge/💰_Zero-Tokens-orange)](../README.md)

## What Smarter-Claude Does

- **🧠 Remembers everything** - SQLite database stores every interaction with context
- **🎯 Tracks intent** - Know WHY files changed, not just what changed
- **🔊 Smart notifications** - Customizable TTS that actually helps
- **💰 Zero tokens** - All processing happens locally

## 🚀 One-Line Installation

**The easiest way to install smarter-claude:**

```bash
curl -sSL https://raw.githubusercontent.com/okets/.claude/main/install.sh | bash
```

That's it! The script will:
- ✅ Check if Claude Code is installed
- ✅ Download and install smarter-claude
- ✅ **Auto-install all TTS voices** (Coqui, ffmpeg, pyttsx3)
- ✅ **Configure optimal voice** for your platform
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

## 🔊 TTS Voice Configuration

**Automatic voice installation and management:**

```bash
# Set your preferred voice (auto-installs if needed)
/smarter-claude_voice coqui-female

# Available voices:
/smarter-claude_voice coqui-male     # High-quality male neural voice
/smarter-claude_voice macos-female   # macOS Samantha voice  
/smarter-claude_voice macos-male     # macOS Alex voice
/smarter-claude_voice pyttsx3        # Cross-platform fallback

# Check voice installation status
/smarter-claude_voice
```

**Voice features:**
- **🚀 Auto-installation** - Missing dependencies installed automatically
- **🔍 Smart detection** - Best voice recommended for your platform
- **✅ Validation** - Voices tested before activation
- **📊 Status display** - See which voices are available

## 🔊 Interaction Levels

[![Silent](https://img.shields.io/badge/🔇_Silent-Database_Only-gray)](../README.md)
[![Quiet](https://img.shields.io/badge/🔉_Quiet-Subtle_Sounds-blue)](../README.md)
[![Concise](https://img.shields.io/badge/🔊_Concise-Brief_TTS-green)](../README.md)
[![Verbose](https://img.shields.io/badge/📢_Verbose-Full_Narration-orange)](../README.md)

**Choose your feedback level:**

```bash
# Set interaction level
/smarter-claude_interaction_level 0   # Silent
/smarter-claude_interaction_level 1   # Quiet  
/smarter-claude_interaction_level 2   # Concise (Default)
/smarter-claude_interaction_level 3   # Verbose
```

- **🔇 Silent** - Database logging only, perfect for shared environments
- **🔉 Quiet** - Subtle notification sounds, no verbal announcements  
- **🔊 Concise (Default)** - Brief TTS announcements and task summaries
- **📢 Verbose** - Detailed narration of all actions and workflow commentary

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

## 📚 Next Steps

[![Database Schema](https://img.shields.io/badge/📊_Database_Schema-Query_Patterns-green)](DATABASE_SCHEMA.md)
[![Troubleshooting](https://img.shields.io/badge/🔧_Troubleshooting-Fix_Issues-orange)](TROUBLESHOOTING.md)
[![Back to README](https://img.shields.io/badge/🏠_Back_to-README-blue)](../README.md)

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