# Contextual Logging Implementation Plan

## ⚠️ CRITICAL: Self-Modifying System Warning

**WE ARE MODIFYING THE HOOKS THAT ARE CURRENTLY RUNNING ON THIS SESSION**

📖 **See also**: 
- [SELF_MODIFYING_HOOKS_WARNING.md](docs/SELF_MODIFYING_HOOKS_WARNING.md) for detailed scenarios and recovery procedures
- [TERMINOLOGY_REFERENCE.md](docs/TERMINOLOGY_REFERENCE.md) for Session vs Conversation definitions

This is the global `.claude` folder - every change we make affects:
- Our current session's logging
- How our own actions are being tracked
- The very system we're using to develop the system

### Critical Considerations
1. **Infinite Loop Risk**: Changes to hooks can cause recursive behaviors
2. **Live System**: Every edit takes effect immediately on our session
3. **Data Consistency**: Mid-session changes affect how data is logged
4. **Testing Strategy**: Often requires stopping and restarting sessions

### Safe Development Pattern
```
1. Make hook change
2. Test with simple command
3. If issues arise: "I've changed how a hook works, I am stopping execution, 
   send this prompt so I begin where I left off and test the change"
4. Start new session to test clean state
```

## Development Process

### Core Principle: Small Incremental Steps
- Start with JSON files to understand data structure
- Build schema from real data, not assumptions
- Each hook is its own phase
- Manual iteration to ensure correct context capture

### Development Guidelines
1. Each hook must have its own .py UV script
2. TTS messages announce hook execution and data location
3. Start with temporary JSON files before database
4. Test each incremental change with verifiable output
5. **BE AWARE**: Changes affect the current session immediately
6. **TEMP FILES**: Always write contextual files to project's `.claude/` directory
   - Example: `<project>/.claude/claude_contextual_data.json`
   - Debug files still go to system `/tmp/` with prefix `claude_debug_`
   - This keeps contextual data with the project while preventing git pollution

## Implementation Phases

### Phase 1: Stop Hook - Initial Data Collection
**Goal**: Understand what data is available in the Stop hook
**Why Start Here**: Stop hook is guaranteed to run at request cycle end

#### Task 1.1: Fetch Hook Initial Data ✅ COMPLETED
- Extract all available JSON data from Stop hook
- Store in `<project>/.claude/claude_contextual_data.json`
- If file exists from previous run, overwrite it
- **TTS**: "Conversation data captured at <project>/.claude/claude_contextual_data.json"
- Reference: docs/CLAUDE_CODE_HOOKS_REFERENCE.md for field meanings

#### Task 1.2: Manual Iteration - Building Context ✅ COMPLETED  
**Focus on CURRENT REQUEST CYCLE, not entire conversation**
- Stop hook captures request cycle completion data
- Store basic hook metadata for THIS request cycle
- Follow proper hook architecture per HOOKS_MASTERY_ANALYSIS.md
- **IMPORTANT**: Each Stop hook captures ONE request cycle's completion

### Phase 2: PostToolUse - Tool Execution Context
**Goal**: Capture tool usage and file modifications
**Challenge**: Runs before Stop hook, needs separate storage

#### Task 2.1: Create Per-Agent Tool Logs
- Main agent: `<project>/.claude/claude_main_tools.json`
- Subagents: `<project>/.claude/claude_subagent_[ID]_tools.json`
- Append mode for multiple tool executions per agent
- **TTS**: "PostToolUse: [tool_name] logged for [agent_type]"

#### Task 2.2: Extract File Modifications
- Focus on main agent only initially
- Identify which files were modified by which tools
- Build tool execution context
- This data will merge into contextual_data.json in Stop hook

### Phase 3: SubagentStop - Subagent Summaries
**Goal**: Create summaries of subagent work
**Input**: PostToolUse logs + SubagentStop hook data

#### Task 3.1: Combine Subagent Data
- Read subagent's tool log
- Combine with SubagentStop hook data
- Create summary: tasks completed, files modified
- Store in `<project>/.claude/claude_subagent_[ID]_summary.json`

### Phase 4: Combine and Store
**Goal**: Merge all JSONs into database
**Challenge**: Handle concurrent agents, clean up properly

#### Task 4.1: Merge All Data
- In Stop hook, combine:
  - claude_contextual_data.json (main context)
  - claude_main_tools.json (main agent tools)
  - claude_subagent_*_summary.json (all subagent summaries)
- Create single comprehensive JSON
- Handle concurrent agents - only clean files for THIS session

#### Task 4.2: Design Database Schema
- Derive schema from actual JSON structure
- Create relational tables based on real data
- No assumptions - schema comes from data



### Phase 5: Context-Oriented Summary System ✅ COMPLETED
**Goal**: Transform from analytics to context retrieval for fast agent access
**Vision**: Enable Claude.md to provide relevant context when agents need file history, task info, or phase modifications

#### Task 5.1: Design Context-First Data Structure ✅ COMPLETED
- ✅ Created 4-table SQLite schema optimized for context queries
- ✅ Structure around **user intent as primary driver**
- ✅ Handle multiple intents per cycle with hybrid extraction approach
- ✅ Core data: cycles, file_contexts, llm_summaries, subagent_tasks

#### Task 5.2: Multi-Intent Context Extractor ✅ COMPLETED
**Implemented Context Extraction**:
- ✅ **User intent progression** - TodoWrite progression + transcript parsing
- ✅ **LLM-generated summaries** - Rich cycle summaries with workflow insights
- ✅ **File changes with intent context** - WHY each change happened linked to user request
- ✅ **Phase/task metadata** - Project context extraction from conversations
- ✅ **Intent-to-outcome mapping** - Complete workflow capture with agent collaboration

**Successfully Filters**: Now captures ALL tool events (removed over-filtering that broke read-only tasks)

#### Task 5.3: Intent-Aware Database Schema ✅ COMPLETED
**Implemented 4-table schema** optimized for context queries:
- ✅ `cycles`: cycle_id → user_intent, primary_activity, timing, project_context
- ✅ `file_contexts`: file_path + cycle_id → change_reason, operations, agent_type, edit_count
- ✅ `llm_summaries`: cycle_id → execution_summary, workflow_insights, task_complexity
- ✅ `subagent_tasks`: cycle_id → task_description, delegation_info, completion_status

#### Task 5.4: Claude.md Integration for Intent-Based Retrieval ✅ FOUNDATION COMPLETE
**Database queries now working**:
- ✅ "What was my last request?" - answered from database with actual user intent
- ✅ "What files were edited and why?" - complete change_reason context
- ✅ "Show all changes to hooks/stop.py" - queryable file modification history

**Successfully demonstrates**: 
```python
# Query what files were edited and why
db.execute("SELECT file_path, change_reason FROM file_contexts WHERE cycle_id = ?")

# Find user intents for a specific phase  
db.execute("SELECT user_intent FROM cycles WHERE primary_activity = 'file_modification'")

# Track subagent work patterns
db.execute("SELECT task_description, status FROM subagent_tasks WHERE cycle_id = ?")
```

**Key Principle ACHIEVED**: Every stored piece maps back to **"What did the user want and how did we achieve it?"**

#### Task 5.5: Store and Clean ✅ COMPLETED
- ✅ **Automatic database ingestion** - every cycle immediately stored in database
- ✅ **Complete data pipeline** - JSONL → Timeline Analysis → Summary Generation → Database Storage
- ✅ **Hybrid intent extraction** - TodoWrite progression (priority) + transcript parsing (fallback)
- ✅ **Multi-agent tracking** - SubagentStop hooks capture delegation completion

### Phase 6: Cleanup and Low Signature 🧹 ✅ COMPLETED
**Goal**: Clean up logs and JSON files after database ingestion
**Vision**: Keep minimal footprint - database contains everything, temporary files cleaned up

#### Task 6.1: Automatic Log Cleanup ✅ COMPLETED
- ✅ Delete JSONL and JSON summary files after successful database ingestion
- ✅ Keep only the database file for long-term storage
- ✅ Implement cleanup in stop.py after auto-ingestion completes
- ✅ Add error handling to preserve files if database ingestion fails
- ✅ Fixed critical import bug: `from settings import get_setting` → `from utils.settings import get_setting`
- ✅ Added cross-session cleanup for files older than 24 hours

#### Task 6.2: File Retention Strategy ✅ COMPLETED
- ✅ Retain current cycle files until next cycle completes
- ✅ Clean up previous cycle files only after confirming new cycle data is safely in database
- ✅ Configurable retention_cycles: 2 setting properly implemented
- ✅ Cross-session cleanup prevents accumulation from old sessions

### Phase 6.5: Fix Project Isolation 🚨 ✅ COMPLETED
**Goal**: Fix critical bug where all projects share global smarter-claude folder
**Issue**: Working in `/Projects/demo-project` but saving to global `~/.claude/.claude/smarter-claude/`

#### Task 6.5.1: Project Directory Detection ✅ COMPLETED
- ✅ Added `detect_project_root()` function to detect current project root directory
- ✅ Look for `.claude` directory or git root as project boundary
- ✅ Fallback to current working directory if no project markers found

#### Task 6.5.2: Dynamic Path Resolution ✅ COMPLETED
- ✅ Replaced all hardcoded `/Users/hanan/.claude/.claude/smarter-claude/` paths
- ✅ Use `<project-root>/.claude/smarter-claude/` for project-specific data
- ✅ Maintain global location only for global hooks configuration

#### Task 6.5.3: Update All Hook Utilities ✅ COMPLETED
- ✅ cycle_utils.py: Dynamic output directory with `get_project_smarter_claude_dir()`
- ✅ contextual_db.py: Project-specific database path
- ✅ hook_parser.py: Project-specific logs directory
- ✅ data_collector.py: Project-specific session logs
- ✅ stop.py: Project-specific cleanup paths

#### Task 6.5.4: Ensure Project Isolation ✅ COMPLETED
- ✅ Each project gets own: `<project>/.claude/smarter-claude/smarter-claude.db`
- ✅ Each project gets own: `<project>/.claude/smarter-claude/logs/`
- ✅ Test: Working in different projects creates separate databases
- ✅ Verify: No cross-project data contamination

### Phase 7: Rebrand as "smarter-claude" 🎯 ✅ COMPLETED
**Goal**: Professional branding and organized file structure
**Vision**: Clean, branded system with intuitive folder organization

#### Task 7.1: Folder Structure Redesign ✅ COMPLETED
- ✅ Renamed `session_logs` → `smarter-claude`
- ✅ Move database to `smarter-claude/smarter-claude.db`
- ✅ Create `smarter-claude/logs/` for temporary JSON/JSONL files
- ✅ Update all paths in hook utilities

#### Task 7.2: Per-Project Settings System ✅ COMPLETED
- ✅ Created `settings.py` module with hierarchical settings system
- ✅ Implemented settings hierarchy: project > global > defaults
- ✅ Created project settings file: `<project>/.claude/smarter-claude/smarter-claude.json`
- ✅ Created global settings file: `~/.claude/hooks/utils/smarter-claude-global.json`
- ✅ Settings include: interaction_level, cleanup_policy, database_settings, logging_settings
- ✅ Built management CLI: `manage_settings.py` with commands: info, get, set, init, levels
- ✅ Integrated settings into TTS announcements and retention cleanup
- ✅ Supports dot notation for nested settings (e.g., "cleanup_policy.retention_cycles")

### Phase 8: Interaction Levels 🔊 ✅ COMPLETED
**Goal**: Four levels of user interaction with TTS and notifications
**Vision**: Customizable experience from silent to verbose

#### Task 8.1: Settings Infrastructure ✅ COMPLETED
- ✅ Implement settings loader with project/global hierarchy
- ✅ Default interaction level: "concise"
- ✅ Settings schema: interaction_level, tts_enabled, notification_sounds

#### Task 8.2: Interaction Levels Implementation ✅ COMPLETED
**Silent Mode** ✅ COMPLETED:
- ✅ No TTS announcements
- ✅ No notification sounds  
- ✅ Database logging only

**Quiet Mode** ✅ COMPLETED:
- ✅ Subtle notification.mp3 for notification hook
- ✅ Subtle decide.mp3 for cycle completion and subagent completion
- ✅ No verbal announcements
- ✅ Sound files copied to hooks/utils/resources/sounds/
- ✅ Uses afplay on macOS for minimal audio feedback

**Concise Mode (Default)** ✅ COMPLETED:
- ✅ TTS for notification hooks with short attention description
- ✅ Brief cycle summary: task type, file changes, subagent usage
- ✅ Completion chime with summary
- ✅ Integrated Coqui TTS as default high-quality voice engine

**Verbose Mode** ✅ COMPLETED:
- ✅ Everything in concise mode
- ✅ SubagentStop TTS notifications with task summary
- ✅ PreToolUse/PostToolUse announcements with details
- ✅ Detailed workflow narration with "I" statements
- ✅ Use of "now" for immediacy in pre-tool announcements

#### Task 8.3: TTS Engine Diversification ✅ COMPLETED
**High-Quality Local TTS Implementation**:
- ✅ Installed Coqui TTS via `uv tool install coqui-tts`
- ✅ Created `coqui_tts.py` for high-quality female voice using VITS model
- ✅ Created `coqui_male_tts.py` for masculine voice with audio processing
- ✅ Implemented ffmpeg-based pitch shifting (4 semitones lower) for natural male voice
- ✅ Performance: Real-time factor ~0.156, extremely fast processing
- ✅ Updated settings to include "coqui-female" and "coqui-male" as TTS engines
- ✅ Enhanced TTS engine selection logic with proper fallback chains

#### Task 8.4: TTS Human-like Improvements ✅ COMPLETED
**Announcement Quality Enhancement**:
- ✅ Removed superlatives and "jokey" content from TTS messages
- ✅ Implemented "I" statements for pre-tool announcements ("I need to read this now")
- ✅ Added "now" for immediacy in pre-tool announcements
- ✅ Made post-tool announcements factual without "I" statements
- ✅ TodoWrite announcements silenced to reduce spam while maintaining todo feedback
- ✅ Short interaction responses read actual content instead of meta-commentary

### Phase 9: Update Claude.md Integration 📝 ✅ COMPLETED
**Goal**: Inform Claude about the new contextual memory system
**Vision**: Claude understands its own memory capabilities and schema

#### Task 9.1: Claude.md Schema Documentation ✅ COMPLETED
- ✅ Document 4-table database schema in Claude.md
- ✅ Explain query patterns for context retrieval
- ✅ Provide example queries for common use cases
- ✅ Complete database schema documentation with SQL examples
- ✅ Context retrieval patterns for recent activity, file history, task complexity

#### Task 9.2: Context System Instructions ✅ COMPLETED
- ✅ Inform Claude about automatic memory capture
- ✅ Explain user intent tracking and file change context
- ✅ Document how to query its own contextual memory
- ✅ Usage instructions for Claude to provide context-aware responses
- ✅ Integration documentation with TTS system and settings

### Phase 10: Cleanup Unused Components 🗑️ ✅ COMPLETED
**Goal**: Remove obsolete files and unused features
**Vision**: Clean, focused codebase with only essential components

#### Task 10.1: Remove Unused Slash Commands ✅ COMPLETED
- ✅ Audit and remove obsolete slash command implementations
- ✅ Removed /commands/ directory (manage_work.md, work_query.md)
- ✅ Removed SLASH-COMMANDS-IMPLEMENTATION.md (outdated schema)
- ✅ Removed work_intelligence.py and work_manager.py (used old db.py)
- ✅ Removed obsolete database files (queryable-context.db, db.py, queryable_db.py)
- ✅ Keep only actively used and maintained commands
- ✅ Update documentation to reflect available commands

#### Task 10.2: Clean Test Files and Docs ✅ COMPLETED
- ✅ Remove irrelevant test files and temporary debugging code
- ✅ Removed 6 TTS test files (test_*.py, pyttsx3_voice_tester.py)
- ✅ Consolidate scattered documentation
- ✅ Removed 5 outdated docs (CONTEXTUAL_SCHEMA_DESIGN.md, HOOKS_MASTERY_ANALYSIS.md, etc.)
- ✅ Remove outdated implementation notes
- ✅ Cleaned up Python cache files
- ✅ Result: Clean codebase with 5,294 lines removed, ready for open source

### Phase 11: Documentation Consolidation 📚 READY
**Goal**: Professional, comprehensive documentation
**Vision**: Single source of truth with clear getting started guide

#### Task 11.1: Update README.md
- Reflect "smarter-claude" branding
- Update installation instructions for new folder structure
- Include interaction levels documentation

#### Task 11.2: Consolidate /docs Folder
- Move all documentation to organized /docs structure
- Create getting started guide
- API reference for database schema
- Advanced usage patterns and examples

### Phase 12: Public Release 🌍 READY
**Goal**: Share smarter-claude with the community
**Vision**: Open source the most advanced Claude Code memory system

#### Task 12.1: Repository Preparation
- Final code review and cleanup
- Comprehensive testing across interaction levels
- Version tagging and release notes

#### Task 12.2: Community Sharing
- GitHub repository with proper documentation
- Social media announcement
- Developer community engagement
- Usage examples and tutorials
## Hook Execution Order Reference

### Typical Flow:
```
Session Start (no hook!)
→ PreToolUse → [Tool] → PostToolUse
→ PreToolUse → [Tool] → PostToolUse
→ Stop
```

### With Subagents:
```
Session Start (no hook!)
→ PreToolUse → [Task] → PostToolUse
    ↓
    [Subagent starts]
    → PreToolUse → [Tool] → PostToolUse
    → SubagentStop
    ↓
→ Stop
```

## Verification Tests

### Phase 1 Test:
```bash
# After implementing Stop hook logging
cat <project>/.claude/claude_contextual_data.json | jq .
# Should see: session_id, transcript_path, stop_hook_active, etc.
```

### Phase 2 Test:
```bash
# After implementing PostToolUse logging
cat <project>/.claude/claude_main_tools.json | jq .
# Should see: tool executions with file modifications
```

### Phase 3 Test:
```bash
# After implementing SubagentStop summaries
cat <project>/.claude/claude_subagent_*_summary.json | jq .
# Should see: subagent task summaries
```

### Phase 4 Test:
```bash
# After database storage
sqlite3 [database_path] "SELECT * FROM [table];"
# Should see: all contextual data properly stored
```

## Success Criteria ✅ ALL ACHIEVED

1. **Complete Context Capture**: ✅ Every tool use and file change tracked
2. **User Intent Preserved**: ✅ Original request linked to all actions
3. **Subagent Hierarchy**: ✅ Full delegation tree captured
4. **Clean Temp Files**: ✅ No leftover JSONs after storage (retention_cycles: 2)
5. **TTS Feedback**: ✅ Clear indication of what's happening with high-quality Coqui voices
6. **Project Isolation**: ✅ Each project maintains separate databases and logs
7. **Human-like Announcements**: ✅ Natural "I" statements, removed superlatives
8. **Advanced TTS Options**: ✅ Both male and female Coqui voices with audio processing
9. **Branch Management**: ✅ Working version successfully made new main branch

## Notes

- Start with Stop hook - it's guaranteed to run
- Build incrementally - JSON first, database later
- Let data drive schema design
- Manual iteration ensures we understand the data
- Small steps prevent breaking the live system
- **REMEMBER**: We're performing surgery on a living system!