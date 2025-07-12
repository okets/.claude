---
allowed-tools: Read, Bash, Grep
description: Show common tool usage patterns for specific files
---

# File Patterns

Analyze tool usage patterns for specific files based on knowledge base history.

## Instructions
- Analyze .claude/logs/post_tool_use.json for file-specific patterns
- Show which tools are commonly used with specific files
- Identify file relationship clusters (files modified together)
- Suggest common workflows based on historical patterns

## Usage
- `--file=<filename>` - Analyze patterns for specific file
- `--extension=<ext>` - Analyze patterns for file type (e.g., .py, .js)
- `--cluster` - Show files commonly modified together

## Context Sources
- Tool execution history: @.claude/logs/post_tool_use.json
- File structure: !`find . -name "*" -type f | head -30`

## Output Format
1. **File Analysis**: Target file(s) and their context
2. **Common Tools**: Most frequently used tools with these files
3. **Related Files**: Files often modified in the same sessions
4. **Workflow Patterns**: Common sequences of operations
5. **Recommendations**: Suggested tools/actions based on patterns

## Example Queries
- "Show patterns for auth.py"
- "What files are usually modified with database models?"
- "Common workflow for test files"