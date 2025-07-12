# Enhanced Conversation Tracking System

## Overview

The enhanced conversation tracking system provides deep insights into AI agent conversations, including:
- User request tracking
- Chain of thought analysis
- Tool usage patterns
- Subagent delegation
- Lessons learned extraction
- Model attribution

## New Database Schema

### conversation_details Table
Stores comprehensive conversation metadata:
- `user_request_summary`: Concise summary of what the user asked
- `user_request_raw`: Original user message
- `agent_model`: Which AI model handled the conversation
- `agent_chain_of_thought`: JSON array of reasoning steps
- `tools_used`: JSON array of tools with counts and purposes
- `subagents_used`: JSON array of subagent invocations
- `agent_summary`: Final summary of what was accomplished
- `lessons_learned`: JSON array of insights gained

### subagent_executions Table
Tracks when main agents delegate to subagents:
- `subagent_model`: Model used (e.g., claude-3-opus)
- `subagent_task`: What the subagent was asked to do
- `subagent_response_summary`: Brief summary of results
- `duration_ms`: How long the subagent took
- `tool_count`: Number of tools the subagent used

## Data Flow

### 1. Conversation Start (notification.py)
- Captures first user message
- Creates initial conversation_details entry
- Stores user request and model info

### 2. Tool Execution (post_tool_use.py)
- Builds chain of thought from tool sequence
- Tracks tool usage with purposes
- Updates conversation details in real-time

### 3. Subagent Completion (subagent_stop.py)
- Records subagent execution details
- Links to parent conversation
- Tracks delegation patterns

### 4. Session End (stop.py)
- Generates final summary
- Extracts lessons learned
- Calculates session duration

## New Query Patterns

### Query by Model
```bash
/work_query "show me all bugs fixed by opus model"
/work_query "what work was done by sonnet"
```

### Lessons Learned
```bash
/work_query "what lessons were learned about authentication"
/work_query "insights from testing work"
```

### Chain of Thought
```bash
/work_query "show chain of thought for fixing login bug"
/work_query "how did you solve the auth problem"
```

### Subagent Usage
```bash
/work_query "which tasks used subagents"
/work_query "show delegated tasks"
```

## Example Data Structure

### Chain of Thought
```json
{
  "agent_chain_of_thought": [
    {
      "step": 1,
      "tool": "Read",
      "intent": "reading-file",
      "thought": "Reading auth.js to understand the implementation",
      "files": ["src/auth.js"],
      "success": true
    },
    {
      "step": 2,
      "tool": "Edit",
      "intent": "modifying-file",
      "thought": "Modifying auth.js to implement changes",
      "files": ["src/auth.js"],
      "success": true
    }
  ]
}
```

### Tools Used
```json
{
  "tools_used": [
    {
      "tool_name": "Read",
      "count": 5,
      "purposes": ["reading-file"]
    },
    {
      "tool_name": "Edit",
      "count": 3,
      "purposes": ["modifying-file"]
    }
  ]
}
```

### Lessons Learned
```json
{
  "lessons_learned": [
    "Token validation was failing due to timezone mismatch",
    "Required multiple iterations (4) to get auth.js working correctly",
    "Successfully identified and resolved issues in the codebase"
  ]
}
```

## Benefits

1. **AI-Explorable**: All data stored as structured JSON for semantic search
2. **Model Attribution**: Track which AI model solved what problems
3. **Learning Repository**: Accumulate lessons learned over time
4. **Subagent Insights**: Understand when and why delegation happens
5. **Chain of Thought**: See the reasoning process for complex tasks

## Usage Tips

- The system automatically tracks all conversations
- No manual tagging required
- Query results improve as more data accumulates
- Lessons learned help avoid repeating mistakes
- Chain of thought helps understand complex solutions