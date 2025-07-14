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

## 📖 The Story

I saw [this demo](https://www.youtube.com/watch?v=J5B9UGTuNoM&t=1547s) of Claude Code with "long-term memory" and voice that had me thinking for days. Brilliant concept, and I really appreciate the innovation. But the more I thought about it, the less usable it seemed - burning tokens to re-process transcript data that Claude already saves in `~/.claude/` anyway.

So I dove deep: **What exactly does Claude Code give you?** Just hooks. Raw, cryptic lifecycle events. I analyzed massive JSON dumps, deployed sub-agents to reverse-engineer Claude's internals, built scaffolding to connect the dots. 

I started methodically piecing together how Claude thinks, how it processes, how it remembers. Claude and I spent 48 hours trying to make him remember useful information. Then it clicked! The context was there all along, hidden in the lifecycle. I just had to know how to catch it.

The result: A contextual system that uses **zero tokens** and honestly, should have been **BAKED INTO CLAUDE** to begin with.

## 🛠️ What I Built

**Real contextual memory that actually works:**

Here's my reasoning: If I tag all files and tasks with the context Claude generates when creating them, but do it in a relational database, I get a system ANY machine can run. Instead of running local agents to analyze my data or sending it to cloud LLMs, **I can utilize the fact that Claude is an intelligence** - give it a schema and it will fetch anything by creating creative SQL queries **that can run locally on any machine**.

So I capture all contextual data Claude generates and store it locally. Now Claude can query its own memory.

**Bottom line: It gives long context that works on any machine and doesn't consume tokens.**

## 🎯 Try This Right Now

Ask Claude after install:
```
"Show me all files modified in phase 8 and **why**?"
"What task involving index.js changed the header?"
"Why did task 8 change the interface of my rest server?"
"Can you check what was my last really complex task before the debugging session?"
```

**It knows. It actually knows.** 🤯

## ⚙️ How It Actually Works

1. **Hooks into Claude Code lifecycle** - Captures everything as it happens
2. **Stores contextual data** - Not just "what" but "why" and "how"
3. **SQLite database** - Searchable by semantic context, not keywords
4. **Claude's intelligence queries the data** - No need for another AI to analyze what Claude already understands
5. **Smart Text To Speech** - Zero extra tokens while giving Claude a meaningful voice

## ⚡ Need Help?

> [!TIP]
> Ask Claude: *"Help me troubleshoot smarter-claude"*

[![Getting Started](https://img.shields.io/badge/📖_Getting_Started-Complete_Setup_Guide-blue)](docs/GETTING_STARTED.md)
[![Troubleshooting](https://img.shields.io/badge/🔧_Troubleshooting-Fix_Issues_with_Claude-orange)](docs/TROUBLESHOOTING.md)
[![Database Schema](https://img.shields.io/badge/📊_Database_Schema-Query_Patterns_&_Examples-green)](docs/DATABASE_SCHEMA.md)

---

## 🚀 Stop losing your development context.

```bash
curl -sSL https://raw.githubusercontent.com/okets/.claude/main/install.sh | bash
```

*The Claude Code breakthrough you've been waiting for.* ⚡
