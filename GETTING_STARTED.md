# 🚀 Getting Started with Smarter-Claude

> **Transform Claude Code from stateless to context-aware in 30 seconds**

[![Memory](https://img.shields.io/badge/🧠_Long_Term-Memory-purple)](README.md)
[![Intent Tracking](https://img.shields.io/badge/🎯_Intent-Tracking-green)](README.md)
[![Smart TTS](https://img.shields.io/badge/🔊_Smart-Notifications-blue)](README.md)
[![Zero Tokens](https://img.shields.io/badge/💰_Zero-Tokens-orange)](README.md)

## What Smarter-Claude Does

- **🧠 Remembers everything** - SQLite database stores every interaction with context
- **🎯 Tracks intent** - Know WHY files changed, not just what changed
- **🔊 Smart notifications** - Customizable TTS that actually helps
- **💰 Zero tokens** - All processing happens locally

## 🚀 Installation

### Ask Claude Code (Recommended)

Simply tell Claude Code:

```
"Install https://github.com/okets/.claude"
```

Claude will read the repository, understand the project, and handle the entire installation process automatically.

**OR**

### One-Line Install

```bash
curl -sSL https://raw.githubusercontent.com/okets/.claude/main/install.sh | bash 
```

**OR**

### Manual Install

```bash
git clone https://github.com/okets/.claude.git
cd .claude && cp -r * ~/.claude/
bash ~/.claude/setup.sh
```

**Both methods will:**
- ✅ Check if Claude Code is installed
- ✅ Download and install smarter-claude
- ✅ **Auto-install all TTS voices** (Kokoro, macOS voices)
- ✅ **Configure optimal voice** for your platform
- ✅ Configure sensible defaults
- ✅ Test the installation

### 🔧 Installation Issues?

If anything goes wrong during installation, just ask Claude Code to fix it:

```
"Help me troubleshoot my smarter-claude installation"
"Fix my smarter-claude setup - the installation failed"
"Debug my Claude hooks and TTS configuration"
```

Claude will analyze your setup, check logs, and guide you through fixes!

## ✅ Verify It's Working

Launch Claude Code from any project folder:

```bash
claude
```

That's it! Smarter-claude is now active, listening to lifecycle events, and storing context to a local database.

After your first interaction, you should see:
```bash
ls .claude/smarter-claude/
# → smarter-claude.db
```

## 💬 Slash Commands

| Command | Description |
|---------|-------------|
| `/smarter-claude_voice <voice>` | Set TTS voice using friendly names (alloy, nicole, emma, daniel, default-male, default-female) |
| `/smarter-claude_interaction_level <level>` | Set feedback level (0=silent, 1=quiet, 2=concise, 3=verbose) |
| `/smarter-claude_update` | Update smarter-claude to latest version |

**Example usage:**
```bash
/smarter-claude_voice alloy
/smarter-claude_interaction_level 2
```

## 🧪 Try This

Ask Claude after you've written or refactored some code:

```
"What did I change in phase 3, and why?"
"Which task modified the header in index.js?"
"What was my last non-trivial commit before debugging?"
```

If smarter-claude is installed, Claude will remember everything with full context.

## 🔊 TTS Voice Configuration

**Watch: How to Change Your Voice** 🎥  
[![Voice Configuration Guide](https://img.youtube.com/vi/linS2EZ14bc/hqdefault.jpg)](https://youtu.be/linS2EZ14bc)

**Automatic voice installation and management:**

```bash
# Set your preferred voice (auto-installs if needed)
/smarter-claude_voice alloy

# Available voices:
/smarter-claude_voice nicole         # Kokoro Nicole (whispering)
/smarter-claude_voice alloy          # Kokoro Alloy (neutral female)
/smarter-claude_voice emma           # Kokoro Emma (British female)
/smarter-claude_voice daniel         # Kokoro Daniel (British male)
/smarter-claude_voice default-female # macOS Samantha voice  
/smarter-claude_voice default-male   # macOS Alex voice

# Check voice installation status
/smarter-claude_voice
```

**Voice features:**
- **🚀 Auto-installation** - Missing dependencies installed automatically
- **🔍 Smart detection** - Best voice recommended for your platform
- **✅ Validation** - Voices tested before activation
- **📊 Status display** - See which voices are available

## 🔊 Interaction Levels

**Choose your feedback level:**

```bash
# Set interaction level
/smarter-claude_interaction_level 0   # Silent
/smarter-claude_interaction_level 1   # Quiet  
/smarter-claude_interaction_level 2   # Concise (Default)
/smarter-claude_interaction_level 3   # Verbose
```

- **🔇 Silent (0)** - Database logging only, perfect for shared environments
- **🔉 Quiet (1)** - Subtle notification sounds, no verbal announcements  
- **🔊 Concise (2)** - Brief TTS announcements and task summaries *(Default)*
- **📢 Verbose (3)** - Detailed narration of all actions and workflow commentary

## 📁 Project Context (Optional)

Add a `CLAUDE.md` file to your project root with:

- Project summary and goals
- Common scripts and commands
- Style guide and conventions
- Key design decisions

Claude will read it automatically to enrich context for your project.

## 🧪 Query Your Development History

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

## 🛠 Troubleshooting
My advice? Utilize Claude code to solve them for you.

**Most issues can be solved by Claude itself. Try asking:**

```
"Help me troubleshoot smarter-claude"
```

### Common Issues & Claude-Powered Fixes

#### Installation Problems
```
The smarter-claude installation script failed. Can you help me troubleshoot what went wrong? Please check if Claude Code is installed, if I have the right permissions, and guide me through a manual installation if needed.
```

#### TTS Not Working
```
My smarter-claude TTS isn't working properly - it's not using the Coqui voice I configured. Can you check if Coqui TTS is installed correctly and test the TTS system?
```

#### Database Issues
```
My smarter-claude database isn't being created in this project. Can you check the project detection logic and ensure the database directory is set up correctly?
```

#### No Notifications
```
I'm not getting any TTS notifications from smarter-claude during our conversation. Can you check the notification hook system and my interaction level settings?
```

### Manual Troubleshooting

<details>
<summary>Click for manual troubleshooting commands</summary>

#### Check Installation
```bash
# Verify hooks are installed and executable
ls -la ~/.claude/hooks/
chmod +x ~/.claude/hooks/*.py

# Test Python imports
python3 -c "from hooks.utils.contextual_db import ContextualDB; print('Success')"
```

#### Debug TTS
```bash
# Check TTS settings
/smarter-claude_voice  # Shows current voice and status

# Test system audio
afplay /System/Library/Sounds/Ping.aiff  # macOS

# Check interaction level (silent mode disables audio)
python ~/.claude/hooks/utils/manage_settings.py get interaction_level
```

#### Database Issues
```bash
# Check if database exists
ls .claude/smarter-claude/

# Verify permissions
chmod 755 .claude/smarter-claude/
chmod 644 .claude/smarter-claude/smarter-claude.db  # if exists

# Test database integrity
sqlite3 .claude/smarter-claude/smarter-claude.db "PRAGMA integrity_check;"
```

#### Reset Everything
```bash
# Remove project data (keeps global settings)
rm -rf .claude/smarter-claude/

# Nuclear option: remove all settings
rm ~/.claude/hooks/utils/smarter-claude-global.json

# Restart Claude Code for fresh installation
claude
```

</details>

## 📚 Quick Reminders

- **🎯 Project-specific** - Each project gets its own database and context
- **💰 Zero tokens** - All memory and processing happens locally
- **🔇 Silent operation** - Works invisibly in the background with any Claude Code session
- **🧠 Semantic memory** - Query by intent and context, not just keywords

## 🔗 More Resources

[![Back to README](https://img.shields.io/badge/🏠_Back_to-README-blue)](README.md)
[![Database Schema](https://img.shields.io/badge/📊_Database_Schema-Query_Patterns-green)](developer-docs/DATABASE_SCHEMA.md)
[![Advanced Docs](https://img.shields.io/badge/🛠️_Developer-Documentation-orange)](developer-docs/)

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

---

**Welcome to intelligent, context-aware Claude Code development!** 🤖✨
