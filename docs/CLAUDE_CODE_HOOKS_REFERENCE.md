# Claude Code Hooks Reference

## Overview

Claude Code hooks are user-defined shell commands that execute at specific points in Claude Code's lifecycle. They provide deterministic control over Claude's behavior and execute with full user permissions. Hooks receive input via stdin as JSON and can return structured responses to control Claude's behavior.

## Hook System Architecture

- **Input Method**: JSON data passed via stdin
- **Output Method**: Exit codes and/or JSON responses
- **Execution Context**: Full user permissions
- **Timeout**: 60 seconds default
- **Configuration**: Via settings files using matchers

## Hook Types

### 1. PreToolUse Hook

**Purpose**: Runs after Claude creates tool parameters but before processing the tool call. Allows approval or blocking of tool usage.

**When Triggered**: Before any tool execution

**Common Matchers**: Task, Bash, Glob, Grep, Read, Edit, Write, WebFetch

**JSON Input Structure**:
```json
{
  "session_id": "abc123",
  "transcript_path": "path/to/transcript.jsonl",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.txt",
    "content": "file content"
  }
}
```

**Available Fields**:
- `session_id`: Unique identifier for the current Claude session
- `transcript_path`: Path to the conversation transcript file
- `hook_event_name`: Always "PreToolUse"
- `tool_name`: Name of the tool Claude wants to use
- `tool_input`: Complete parameters Claude will pass to the tool

**Return Values and Effects**:
- Exit code 0: Approve (default behavior)
- Exit code 1: Block the tool call
- JSON response with `decision` field:
  - `"approve"`: Allow tool execution
  - `"block"`: Prevent tool execution
  - `undefined`: Use exit code for decision

**Example JSON Response**:
```json
{
  "decision": "block",
  "reason": "File modification not allowed in this directory"
}
```

**Important Notes**:
- Hooks execute with full user permissions
- Must validate and sanitize all inputs
- Can prevent potentially harmful operations

### 2. PostToolUse Hook

**Purpose**: Runs immediately after a tool completes successfully. Allows retrospective feedback or blocking.

**When Triggered**: After successful tool execution

**Common Matchers**: Same as PreToolUse (Task, Bash, Glob, Grep, Read, Edit, Write, WebFetch)

**JSON Input Structure**:
```json
{
  "session_id": "abc123",
  "transcript_path": "path/to/transcript.jsonl",
  "hook_event_name": "PostToolUse",
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/path/to/file.txt",
    "old_string": "old content",
    "new_string": "new content"
  },
  "tool_output": "Edit completed successfully"
}
```

**Available Fields**:
- All fields from PreToolUse, plus:
- `tool_output`: The result/output from the completed tool execution

**Return Values and Effects**:
- Similar to PreToolUse
- Can provide feedback about completed operations
- Can block retrospectively if needed

### 3. Notification Hook

**Purpose**: Handles custom notifications when Claude needs permission or when there's extended idle time.

**When Triggered**:
- When Claude needs permission to use a tool
- When prompt input has been idle for 60+ seconds

**JSON Input Structure**:
```json
{
  "session_id": "abc123",
  "transcript_path": "path/to/transcript.jsonl",
  "hook_event_name": "Notification",
  "notification_type": "tool_permission_request",
  "details": {
    "tool_name": "Bash",
    "reason": "User approval required"
  }
}
```

**Available Fields**:
- `session_id`: Session identifier
- `transcript_path`: Path to transcript
- `hook_event_name`: Always "Notification"
- `notification_type`: Type of notification
- `details`: Context-specific information

**Return Values and Effects**:
- Allows custom notification handling
- Can integrate with external notification systems

### 4. Stop Hook

**Purpose**: Runs when the main agent finishes responding. Can prevent stopping with specific reasons.

**When Triggered**: When Claude completes its response

**JSON Input Structure**:
```json
{
  "session_id": "abc123",
  "transcript_path": "path/to/transcript.jsonl",
  "hook_event_name": "Stop",
  "stop_hook_active": false,
  "response_complete": true
}
```

**Available Fields**:
- `session_id`: Session identifier
- `transcript_path`: Path to transcript
- `hook_event_name`: Always "Stop"
- `stop_hook_active`: Boolean to prevent infinite loops
- `response_complete`: Whether the response is complete

**Return Values and Effects**:
- Can prevent Claude from stopping
- Must be careful to avoid infinite loops

### 5. SubagentStop Hook

**Purpose**: Runs when a subagent finishes responding.

**When Triggered**: When a subagent completes its task

**JSON Input Structure**:
```json
{
  "session_id": "abc123",
  "transcript_path": "path/to/transcript.jsonl",
  "hook_event_name": "SubagentStop",
  "subagent_id": "subagent_xyz",
  "stop_hook_active": false
}
```

**Available Fields**:
- Similar to Stop hook, plus:
- `subagent_id`: Identifier for the specific subagent

### 6. PreCompact Hook

**Purpose**: Runs before compact operations that reduce conversation history.

**When Triggered**: Before compacting the conversation

**Matchers**:
- `"manual"`: Triggered by `/compact` command
- `"auto"`: Triggered when context window is full

**JSON Input Structure**:
```json
{
  "session_id": "abc123",
  "transcript_path": "path/to/transcript.jsonl",
  "hook_event_name": "PreCompact",
  "compact_type": "manual"
}
```

**Available Fields**:
- `session_id`: Session identifier
- `transcript_path`: Path to transcript
- `hook_event_name`: Always "PreCompact"
- `compact_type`: "manual" or "auto"

## Data Flow Between Hooks

1. **PreToolUse** → Tool Execution → **PostToolUse**
2. **Notification** hooks can trigger independently
3. **Stop/SubagentStop** hooks execute at conversation endpoints
4. **PreCompact** hooks execute before history reduction

## Data NOT Available

Based on the documentation, the following data is typically NOT available in hooks:

- **Tool execution details during PreToolUse**: The tool hasn't run yet
- **Real-time tool progress**: Only pre/post execution data
- **User input history**: Only current tool parameters
- **Claude's internal reasoning**: Only the final tool parameters
- **Other concurrent sessions**: Each hook only sees its own session
- **Future tool calls**: Only current tool information

## Best Practices

### Security
- **Validate and sanitize all inputs** from hook JSON
- **Use absolute paths** to prevent directory traversal
- **Quote shell variables** to prevent injection
- **Block path traversal attempts** (../, etc.)
- **Avoid modifying sensitive files** without explicit approval

### Performance
- **Keep hooks lightweight** (60-second timeout)
- **Cache expensive operations** when possible
- **Use appropriate exit codes** for simple decisions

### Reliability
- **Handle JSON parsing errors** gracefully
- **Provide meaningful error messages** in responses
- **Test hooks thoroughly** before deployment
- **Use `stop_hook_active`** to prevent infinite loops

### Configuration
- **Use specific matchers** rather than catching all tools
- **Organize hooks by purpose** (security, logging, etc.)
- **Document hook behavior** for team members

## Example Hook Implementation

```bash
#!/bin/bash
# Example PreToolUse hook for file operations

# Read JSON input from stdin
INPUT=$(cat)

# Parse tool name and file path
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Block writes to sensitive directories
if [[ "$TOOL_NAME" == "Write" || "$TOOL_NAME" == "Edit" ]]; then
    if [[ "$FILE_PATH" == /etc/* || "$FILE_PATH" == /usr/* ]]; then
        echo '{"decision": "block", "reason": "Cannot modify system files"}'
        exit 0
    fi
fi

# Approve by default
echo '{"decision": "approve"}'
exit 0
```

## Configuration Example

```json
{
  "hooks": {
    "pre_tool_use": [
      {
        "matcher": "Write",
        "command": "/path/to/write-guard.sh"
      },
      {
        "matcher": "Bash",
        "command": "/path/to/bash-monitor.sh"
      }
    ],
    "notification": [
      {
        "matcher": "*",
        "command": "/path/to/notify.sh"
      }
    ]
  }
}
```

This reference provides the complete data structures and capabilities available through Claude Code hooks, enabling precise control over Claude's behavior and comprehensive monitoring of its operations.