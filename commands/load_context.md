---
allowed-tools: Read, Bash
description: Load project context from knowledge base logs
---

# Load Context

Load relevant context from the project's knowledge base based on recent work patterns.

## Instructions
- Read the project's .claude/logs/post_tool_use.json to understand recent tool usage
- Analyze file modification patterns and work clusters
- Identify recent intents and file relationships
- Provide a summary of recent work context for better continuity

## Context Sources
- Project logs: @.claude/logs/post_tool_use.json
- Security logs: @.claude/logs/pre_tool_use.json  
- Project structure: !`find . -type f -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.md" | head -20`
- Recent git activity: !`git log --oneline -10`

## Output Format
Provide a concise summary including:
1. **Recent Work Patterns**: What files have been modified together
2. **Active Intents**: What types of work are happening (testing, refactoring, etc.)
3. **File Clusters**: Related files that form logical units
4. **Suggested Next Steps**: Based on incomplete work patterns