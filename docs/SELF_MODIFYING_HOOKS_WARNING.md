# ⚠️ CRITICAL WARNING: Self-Modifying Hooks System

## You Are Modifying The System That Is Currently Running

This is not a typical development environment. The hooks in the global `.claude` folder are:
- **LIVE** - Running on your current Claude Code session
- **IMMEDIATE** - Changes take effect instantly
- **RECURSIVE** - Hooks monitor the very actions that modify them

## The Inception Problem

When you edit a hook file:
1. The `pre_tool_use` hook sees you're about to edit
2. The `post_tool_use` hook logs that you edited
3. The edited hook now behaves differently
4. Your current conversation is affected by the change

## Real Scenarios You Will Face

### Scenario 1: Adding TTS to notification.py
```
You: "Add TTS announcement to notification hook"
Claude: *edits notification.py*
Next prompt: *YOU HEAR THE TTS ANNOUNCEMENT*
```

### Scenario 2: Logging Tool Executions
```
You: "Make post_tool_use log all file edits"
Claude: *edits post_tool_use.py*
The edit itself: *IS LOGGED BY THE NEWLY MODIFIED HOOK*
```

### Scenario 3: Database Schema Changes
```
You: "Add new column to sessions table"
Claude: *modifies schema*
Current session: *MIGHT FAIL TO LOG PROPERLY*
```

## Development Strategies

### 1. The Restart Pattern
```
"I've modified the notification hook to extract user intents.
I'm stopping here. Please restart the conversation with this prompt:
'Test that user intent extraction is working correctly'"
```

### 2. The Safe Test Pattern
```python
# In your hook
if "TEST_HOOK_CHANGE" in os.environ:
    # New behavior
else:
    # Old behavior
```

### 3. The Gradual Rollout
```python
# Phase 1: Just log
print(f"Would do: {new_feature}", file=sys.stderr)

# Phase 2: Actually do it
do_new_feature()
```

## Common Pitfalls

### 1. Infinite Loops
```python
# DON'T: Hook that triggers itself
def post_tool_use_hook():
    # This writes a file...
    with open("log.txt", "a") as f:
        f.write("Tool used")  # ...which triggers post_tool_use again!
```

### 2. Cascade Failures
```python
# If notification hook fails, ALL subsequent hooks might not run
def notification_hook():
    result = database.query()  # If DB is down, everything stops
```

### 3. Data Inconsistency
```
Session starts with Schema v1
Mid-session: Upgrade to Schema v2
Result: Half the session in v1, half in v2
```

## Safety Rules

1. **Test First**: Create a test file, edit it, delete it
2. **Backup Working Versions**: `cp working_hook.py hook.py.backup`
3. **Use TTS for Debugging**: Hear what's happening in real-time
4. **Small Changes**: One feature at a time
5. **Document State**: "Currently testing X, if it fails do Y"

## Recovery Commands

```bash
# When hooks are misbehaving
mv ~/.claude/hooks ~/.claude/hooks.broken
mkdir ~/.claude/hooks
# Copy back one by one

# When database is corrupted
mv ~/.claude/.claude/queryable-context.db ~/.claude/.claude/queryable-context.db.old

# When in doubt
echo "I need to restart Claude Code due to hook issues" > recovery.txt
```

## The Golden Rule

**Every change you make affects the conversation you're having right now.**

Think of it like performing brain surgery on yourself while awake. Possible? Yes. Requires extreme care? Absolutely.

## Remember

- You're not just writing code, you're modifying a running system
- Your development actions become the test data
- The system observing you is the system you're changing
- When in doubt, restart with a clean conversation

Stay safe, test carefully, and remember: with great power comes great opportunity to accidentally create infinite loops.