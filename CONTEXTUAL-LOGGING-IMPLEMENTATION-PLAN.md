# Contextual Logging Implementation Plan

## ⚠️ CRITICAL: Self-Modifying System Warning

**WE ARE MODIFYING THE HOOKS THAT ARE CURRENTLY RUNNING ON THIS CONVERSATION**

📖 **See also**: [SELF_MODIFYING_HOOKS_WARNING.md](docs/SELF_MODIFYING_HOOKS_WARNING.md) for detailed scenarios and recovery procedures

This is the global `.claude` folder - every change we make affects:
- Our current conversation's logging
- How our own actions are being tracked
- The very system we're using to develop the system

### Critical Considerations
1. **Infinite Loop Risk**: Changes to hooks can cause recursive behaviors
2. **Live System**: Every edit takes effect immediately on our session
3. **Data Consistency**: Mid-conversation changes affect how data is logged
4. **Testing Strategy**: Often requires stopping and restarting conversations

### Safe Development Pattern
```
1. Make hook change
2. Test with simple command
3. If issues arise: "I've changed how a hook works, I am stopping execution, 
   send this prompt so I begin where I left off and test the change"
4. Start new conversation to test clean state
```

## Development Process

### TTS-Based Development Feedback
- Each hook announces its name at start via TTS
- Add contextual information about current work being done
- One TTS announcement per hook execution
- Progressive refinement: detailed during development, minimal when stable
- Use as audible "console.log" for real-time development feedback

### Development Guidelines
1. Each hook must have its own .py UV script
2. TTS messages evolve with development needs
3. Clean messages back to hook name only after resolving issues
4. Test each incremental change with verifiable output
5. **BE AWARE**: Changes affect the current conversation immediately
6. **TEMP FILES**: Always write debug/temp files to `/tmp/` with prefix `claude_`
   - Example: `/tmp/claude_debug_notification.json`
   - Never write debug files to project directory
   - This prevents git pollution and project clutter

## Implementation Phases

### Phase 1: Hook Infrastructure & TTS Integration
**Goal**: Establish basic hook execution with TTS announcements
**⚠️ WARNING**: Adding TTS will immediately affect our current conversation

#### Task 1.1: Verify Hook Script Structure
- Ensure each hook has its own .py script
- Add TTS announcement at start of each hook
- Test: Run a tool and hear hook name announcements
- **SELF-MODIFY NOTE**: First TTS addition will announce on our next action

#### Task 1.2: Fix Hook Path Configuration
- Update settings.json to point to correct hook locations
- Ensure all 5 hooks are triggered properly
- Test: Execute various tools and verify all hooks announce
- **RESTART REQUIRED**: May need new conversation after settings change

#### Task 1.3: Standardize TTS Integration
- Create shared TTS announcement function
- Add to each hook's entry point
- Test: All hooks announce consistently with same voice/speed
- **WATCH FOR**: Recursive announcements if hooks trigger each other

### Phase 2: Database Connection & Schema
**Goal**: Establish database with proper schema

#### Task 2.1: Fix Database Path Resolution
- Ensure single project database at .claude/queryable-context.db
- Remove any duplicate databases
- Test: Verify single database file exists after hook execution

#### Task 2.2: Implement Core Schema Tables
- Create sessions table with user_request field
- Create session_events table for event stream
- Test: Query tables exist with correct columns

#### Task 2.3: Create File Change Tables
- Implement file_changes table
- Implement change_context table
- Test: Tables created with proper foreign keys

### Phase 3: User Intent Capture
**Goal**: Extract and store original user request
**⚠️ CRITICAL**: This captures our development conversation!

#### Task 3.1: Transcript Parser Implementation
- Create function to extract first user message from transcript
- Handle various transcript formats
- Test: Extract user request from sample transcript file
- **INCEPTION WARNING**: Will capture "implement user intent capture" as intent

#### Task 3.2: Notification Hook Enhancement
- Integrate transcript parser
- Store user request in sessions table
- Test: Query sessions table shows user_request populated
- **SELF-REFERENCE**: Our implementation prompts become test data

#### Task 3.3: Session Initialization
- Create session with full context
- Add session_start event
- Test: Query shows session and first event with user request
- **DATA POLLUTION**: Development commands mix with real usage data

### Phase 4: Tool Execution Tracking
**Goal**: Capture tool intentions and results

#### Task 4.1: PreToolUse Data Capture
- Extract tool name and parameters
- Infer tool intent from parameters
- Test: Query tool intentions in database after execution

#### Task 4.2: PostToolUse Result Recording
- Capture tool output and success status
- Extract modified files from results
- Test: Query shows tool executions with outcomes

#### Task 4.3: File Change Detection
- Identify files modified by tools
- Determine change type (create/modify/delete)
- Test: Query file_changes shows accurate modifications

### Phase 5: Context Enrichment
**Goal**: Link changes to user intent

#### Task 5.1: Change Context Association
- Link file changes to user requests
- Add tool execution context
- Test: Query shows why each file was changed

#### Task 5.2: Related Files Tracking
- Identify files changed together
- Build file relationship map
- Test: Query co-changed files for any given file

#### Task 5.3: Session Tagging
- Extract topics from user request
- Calculate complexity scores
- Test: Query sessions by topic or complexity

### Phase 6: Pattern Detection
**Goal**: Identify recurring patterns

#### Task 6.1: Co-change Pattern Detection
- Analyze files that change together
- Calculate relationship strength
- Test: Query shows file pairs with high co-change frequency

#### Task 6.2: Error Pattern Recognition
- Track tool failures and fixes
- Identify common error types
- Test: Query common errors and their solutions

#### Task 6.3: Refactoring Pattern Analysis
- Detect repeated code transformations
- Track architectural changes
- Test: Query shows refactoring patterns

### Phase 7: Query Interface
**Goal**: Natural language queries over context

#### Task 7.1: Basic Query Functions
- Implement "why did X change" queries
- Add file history queries
- Test: Run queries and get contextual results

#### Task 7.2: Complex Query Support
- Session filtering by tags
- Multi-dimensional searches
- Test: Complex queries return accurate results

#### Task 7.3: Query Optimization
- Add appropriate indexes
- Implement query caching
- Test: Query response time < 100ms

### Phase 8: Stop Hook Intelligence
**Goal**: Session summarization and insights

#### Task 8.1: Session Summary Generation
- Analyze session outcomes
- Generate completion summary
- Test: Query shows meaningful session summaries

#### Task 8.2: Insight Generation
- Detect session patterns
- Generate actionable insights
- Test: Query returns relevant insights

#### Task 8.3: Metrics Calculation
- Token usage tracking
- Complexity scoring
- Test: Query shows session metrics

## Verification Tests

### Phase 1 Tests
```bash
# Test hook announcements
echo "test" > test.txt
# Should hear: "notification hook", "pre tool use hook", "post tool use hook"
```

### Phase 2 Tests
```bash
# Test database creation
sqlite3 .claude/queryable-context.db ".tables"
# Should show: sessions, session_events, file_changes, etc.
```

### Phase 3 Tests
```bash
# Test user intent capture
sqlite3 .claude/queryable-context.db "SELECT user_request FROM sessions;"
# Should show: captured user requests
```

### Phase 4 Tests
```bash
# Test tool tracking
sqlite3 .claude/queryable-context.db "SELECT tool_name, tool_intent FROM tool_executions;"
# Should show: tool executions with intents
```

### Phase 5 Tests
```bash
# Test context queries
/work_query "why did test.txt change?"
# Should show: user request, tool used, reason for change
```

### Phase 6 Tests
```bash
# Test pattern detection
/work_query "what files change together?"
# Should show: co-change patterns with frequencies
```

### Phase 7 Tests
```bash
# Test complex queries
/work_query "show me complex authentication work"
# Should show: filtered results by topic and complexity
```

### Phase 8 Tests
```bash
# Test session insights
/work_query "show session summary"
# Should show: comprehensive session analysis
```

## Success Criteria

1. **TTS Feedback**: Clear audio indication of hook execution
2. **Data Capture**: >95% of user intents captured
3. **Context Linking**: Every file change linked to user request
4. **Query Performance**: <100ms response time
5. **Pattern Detection**: Meaningful patterns identified
6. **Zero Data Loss**: All events properly recorded

## Self-Modifying System Guidelines

### DO's:
- Test changes with simple, harmless commands first
- Be ready to restart conversation if hooks misbehave
- Keep backup of working hook versions
- Add safety checks to prevent infinite loops
- Use TTS to understand what's happening in real-time
- Write all debug output to `/tmp/claude_*` files

### DON'T's:
- Don't add hooks that call the same tools they monitor
- Don't create circular dependencies between hooks
- Don't forget that changes are LIVE immediately
- Don't test destructive operations on the hooks folder itself

### Recovery Procedures:
1. **Hook Infinite Loop**: Kill Claude Code process, fix hook, restart
2. **Database Corruption**: Move .db file, let it recreate
3. **TTS Spam**: Comment out TTS temporarily, fix logic
4. **Lost Context**: Note current task, restart conversation with context

## Notes

- Start with verbose TTS messages, reduce as features stabilize
- Each phase builds on previous phases
- Run verification test after each task
- Document any deviations or issues encountered
- Keep implementation incremental and testable
- **REMEMBER**: We're performing surgery on a living system!