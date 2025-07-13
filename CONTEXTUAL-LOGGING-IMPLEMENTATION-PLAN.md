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

#### Task 4.3: Store and Clean
- Store combined data in database
- Delete only this session's temp files
- **Note**: Check if subagents trigger Stop or just SubagentStop

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

## Success Criteria

1. **Complete Context Capture**: Every tool use and file change tracked
2. **User Intent Preserved**: Original request linked to all actions
3. **Subagent Hierarchy**: Full delegation tree captured
4. **Clean Temp Files**: No leftover JSONs after storage
5. **TTS Feedback**: Clear indication of what's happening

## Notes

- Start with Stop hook - it's guaranteed to run
- Build incrementally - JSON first, database later
- Let data drive schema design
- Manual iteration ensures we understand the data
- Small steps prevent breaking the live system
- **REMEMBER**: We're performing surgery on a living system!