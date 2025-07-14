```
███████╗███╗   ███╗ █████╗ ██████╗ ████████╗███████╗██████╗ 
██╔════╝████╗ ████║██╔══██╗██╔══██╗╚══██╔══╝██╔════╝██╔══██╗
███████╗██╔████╔██║███████║██████╔╝   ██║   █████╗  ██████╔╝
╚════██║██║╚██╔╝██║██╔══██║██╔══██╗   ██║   ██╔══╝  ██╔══██╗
███████║██║ ╚═╝ ██║██║  ██║██║  ██║   ██║   ███████╗██║  ██║
╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
                     C L A U D E
```

## **100% local. Zero tokens. Cloud-level context. And yes, it speaks.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://python.org)
[![Local](https://img.shields.io/badge/100%25-Local-green?logo=home)](https://github.com/okets/.claude)
[![Zero Tokens](https://img.shields.io/badge/Zero-Tokens-orange?logo=coin)](https://github.com/okets/.claude)
[![macOS](https://img.shields.io/badge/macOS-Compatible-black?logo=apple)](https://github.com/okets/.claude)
[![Linux](https://img.shields.io/badge/Linux-Compatible-yellow?logo=linux)](https://github.com/okets/.claude)
[![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## 🚀 One-Line Install

```bash
curl -sSL https://raw.githubusercontent.com/okets/.claude/main/install.sh | bash
```

> [!NOTE]
> This will run over your global .claude directory. But trust me, it's worth it.

## 🔍 The Problem You Face Daily

Every time you restart Claude Code, you lose everything. Your entire development context, the reasoning behind your changes, the problems you solved - gone. You're constantly re-explaining your project, re-establishing context, starting from scratch.

**What if Claude remembered?**

**It actually knows.** Your entire development journey, queryable by context, stored locally, **zero tokens** wasted.

This is Claude Code with memory. This is what you've been missing.

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

## 🎯 Try This Right Now

Ask Claude after you've written or refactored some code:

```
"Show me all files modified in phase 8 and why?"
"What task involving index.js changed the header?"
"Why did task 8 change the interface of my rest server?"
"Can you check what was my last really complex task before the debugging session?"
```

**It knows. It actually knows.** 🤯

## 💬 Slash Commands

| Command | Description |
|---------|-------------|
| `/smarter-claude_voice <voice>` | Set TTS voice (coqui-female, coqui-male, macos-female, macos-male, pyttsx3) |
| `/smarter-claude_interaction_level <level>` | Set feedback level (0=silent, 1=quiet, 2=concise, 3=verbose) |
| `/smarter-claude_update` | Update smarter-claude to latest version |

**Example usage:**
```bash
/smarter-claude_voice coqui-female
/smarter-claude_interaction_level 2
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

## 📖 The Story

I came across [![Original Project](https://img.shields.io/badge/📂_Original-Project-blue)](https://github.com/disler/claude-code-hooks-mastery) by the brilliant [![@indyDevDan](https://img.shields.io/badge/👨‍💻_@indyDevDan-YouTube-red)](https://www.youtube.com/@indyDevDan), featured in this [![Demo Video](https://img.shields.io/badge/🎥_Demo-Video-red)](https://www.youtube.com/watch?v=J5B9UGTuNoM).

He introduced a fascinating idea: using Claude Code's hooks to create "long-term storage" — a concept that stuck with me for days. I borrowed that idea and deeply appreciate the innovation behind it.

The concept of auto-generating data with hooks and retrieving it via slash commands seemed promising at first. But in practice, the process proved to be heavily human-centric—more like quick shortcuts to manually bring bits of context into the conversation.

What I really wanted was a memory.
A contextual memory.

So I dove deep: **What exactly does Claude Code give you?** Just hooks. Raw, cryptic lifecycle events. I analyzed massive JSON dumps, deployed sub-agents to reverse-engineer Claude's internals, built scaffolding to connect the dots. 

I started methodically piecing together how Claude thinks, how it processes, how it remembers. Claude and I spent 48 hours trying to make him remember useful information. Then it clicked! The context was there all along, hidden in the lifecycle. I just had to know how to catch it.

The result: A contextual system that uses **zero tokens** and honestly, should have been **BAKED INTO CLAUDE** to begin with.

## 🛠️ What I Built

**Real contextual memory that actually works:**

Here's my reasoning: If I tag all files and tasks with the context Claude generates when creating them, but do it in a relational database, I get a system ANY machine can run. Instead of running local agents to analyze my data or sending it to cloud LLMs, **I can utilize the fact that Claude is an intelligence** - give it a schema and it will fetch anything by creating creative SQL queries **that can run locally on any machine**.

So I capture all contextual data Claude generates and store it locally. Now Claude can query its own memory.

**Bottom line: It gives long context that works on any machine and doesn't consume tokens.**

[![Contextual Memory](https://img.shields.io/badge/🧠_Contextual-Memory-purple)](developer-docs/DATABASE_SCHEMA.md)
[![Smart TTS](https://img.shields.io/badge/🔊_Smart-TTS-blue)](#tts-voice-configuration)
[![Intent Tracking](https://img.shields.io/badge/🎯_Intent-Tracking-green)](developer-docs/DATABASE_SCHEMA.md)
[![Multi-Agent](https://img.shields.io/badge/🤖_Multi-Agent_Support-orange)](developer-docs/DATABASE_SCHEMA.md)

## ⚙️ How It Actually Works

1. **Hooks into Claude Code lifecycle** - Captures everything as it happens
2. **Stores contextual data** - Not just "what" but "why" and "how"
3. **SQLite database** - Searchable by semantic context, not keywords
4. **Claude's intelligence queries the data** - No need for another AI to analyze what Claude already understands
5. **Smart Text To Speech** - Zero extra tokens while giving Claude a meaningful voice

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

## ⚡ Need Help?

> [!TIP]
> Ask Claude: *"Help me troubleshoot smarter-claude"*

[![Database Schema](https://img.shields.io/badge/📊_Database_Schema-Query_Patterns_&_Examples-green)](developer-docs/DATABASE_SCHEMA.md)
[![Advanced Docs](https://img.shields.io/badge/🛠️_Developer-Documentation-orange)](developer-docs/)

---

## 🚀 Stop losing your development context.

```bash
curl -sSL https://raw.githubusercontent.com/okets/.claude/main/install.sh | bash
```

*The Claude Code breakthrough you've been waiting for.* ⚡

---

## 📄 License

MIT License - Build upon this, share improvements, and help make AI development workflows more intelligent.

See [![License Details](https://img.shields.io/badge/📄_License-Details-green)](LICENSE) for full details.