---
allowed-tools: Read, Bash
description: Summarize recent work session from knowledge base
---

# Session Summary

Generate a summary of recent work based on the project's knowledge base logs.

## Instructions
- Read recent entries from .claude/logs/post_tool_use.json
- Group tool executions by intent and time clusters
- Identify completed vs incomplete work patterns
- Summarize meaningful accomplishments and next steps

## Time Filters
- `--last=1h` - Last 1 hour of work
- `--last=2h` - Last 2 hours of work  
- `--last=1d` - Last day of work
- `--since=<timestamp>` - Since specific timestamp

## Context Sources
- Tool execution logs: @.claude/logs/post_tool_use.json
- Security events: @.claude/logs/pre_tool_use.json
- Current project state: !`git status --porcelain`

## Output Format
Provide a structured summary:
1. **Time Range**: Period covered by the summary
2. **Work Sessions**: Logical groupings of related work
3. **Files Modified**: What files were changed and why
4. **Accomplishments**: What was completed successfully
5. **Incomplete Work**: What was started but not finished
6. **Suggested Next Steps**: Logical continuation points