# Contextual Logging Terminology Reference

## Core Concepts

### Conversation vs RequestCycle
Understanding the difference between these terms is critical for correct implementation.

#### Conversation
- **Definition**: The entire Claude Code conversation from startup until Stop hook fires
- **Duration**: From first user interaction to conversation end
- **Scope**: Contains multiple RequestCycles (user prompts and responses)
- **Hook Coverage**: One conversation = one set of hook events across all request cycles
- **Example**: Opening Claude Code, asking 5 different questions, then closing

#### RequestCycle  
- **Definition**: Everything that happened between the previous "Stop" hook to the next "Stop" hook
- **Duration**: From user message to Claude finishing response (including all tools) + Stop hook
- **Scope**: One user intent → one complete Claude response → Stop hook
- **Hook Coverage**: Multiple PreToolUse/PostToolUse pairs within one RequestCycle
- **Example**: "fix this bug" → Claude reads files, edits code, runs tests, responds → Stop hook

### Current Conversation Analysis

Based on transcript analysis, our current conversation contains these request cycles:

1. **RequestCycle 1**: "I am trying to find a commit that was in a working condition..."
   - Intent: Find working git commit
   - Tools: git log, git reflog, git checkout

2. **RequestCycle 2**: "remember, we are working on hooks system..."
   - Intent: Warn about self-modifying system
   - Tools: Documentation updates, warning creation

3. **RequestCycle 3**: "I don't hear ANY TTS messages from any hook..."
   - Intent: Debug TTS integration
   - Tools: Code analysis, file reading

4. **RequestCycle 4**: "commit first"
   - Intent: Save current work
   - Tools: git add, git commit

5. **RequestCycle 5**: "this is the json... bring the relevant transcript..."
   - Intent: Enhance Stop hook with transcript parsing
   - Tools: Code modification, hook enhancement

6. **Current RequestCycle**: "well, we have a mismatch between what we call a conversation..."
   - Intent: Fix terminology mismatch in our implementation
   - Tools: Documentation updates, terminology corrections

## Data Structure Implications

### Conversation-Level Data
```json
{
  "conversation_id": "uuid",
  "conversation_first_request": "I am trying to find a commit...",
  "conversation_duration": "2 hours",
  "total_request_cycles": 6,
  "overall_theme": "Contextual logging implementation"
}
```

### RequestCycle-Level Data  
```json
{
  "request_cycle_number": 5,
  "user_request": "this is the json... enhance it with transcript",
  "tools_used": ["Edit", "Write", "Read"],
  "files_modified": ["stop.py"],
  "request_cycle_outcome": "Enhanced Stop hook with transcript parsing"
}
```

## Hook Implementation Guidelines

### What Each Hook Should Track

#### Notification Hook
- **Conversation Context**: First user request of conversation
- **RequestCycle Context**: Current user request being processed

#### PreToolUse/PostToolUse Hooks
- **Conversation Context**: Which conversation this tool belongs to
- **RequestCycle Context**: Which request cycle this tool serves
- **Tool Context**: What this specific tool accomplishes

#### Stop Hook
- **Conversation Context**: Complete conversation summary
- **RequestCycle Context**: Final request cycle that ended the conversation
- **Overall Context**: Conversation-wide patterns and outcomes

## Terminology Usage in Code

### Correct Usage
```python
# Good - Clear distinction
conversation_first_request = "I am trying to find a commit..."
current_request_cycle_request = "this prompt about terminology..."
conversation_tool_count = 47
request_cycle_tool_count = 3
```

### Incorrect Usage
```python
# Bad - Ambiguous
request_cycle_id = conversation_id  # Wrong! These are different
user_intent = first_message  # Wrong! First != Current
```

## Documentation Standards

When writing documentation:
- **Conversation** = Complete Claude Code conversation (multiple request cycles)
- **RequestCycle** = Single user prompt + complete Claude response + Stop hook
- **User Intent** = What the user wants in current request cycle
- **Conversation Theme** = Overall purpose of the entire conversation

This prevents confusion and ensures accurate context tracking.