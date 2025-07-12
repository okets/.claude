# Manage Work - Project Phase, Task & Assignment Management

Manage your project phases, tasks, and assignments for better work organization and tracking.

## Usage

```
/manage_work <command> [options]
```

## Commands

### Phase Management
```bash
# Create a new phase
/manage_work create-phase "Authentication System" --status planning

# List all phases
/manage_work list-phases

# Update phase status
/manage_work update-phase "Authentication System" --status active

# Complete a phase
/manage_work complete-phase "Authentication System"
```

### Task Management
```bash
# Create a task within a phase
/manage_work create-task "Authentication System" "Implement JWT tokens" --priority high

# List tasks in a phase
/manage_work list-tasks "Authentication System"

# Update task status
/manage_work update-task "Implement JWT tokens" --status in_progress

# Complete a task
/manage_work complete-task "Implement JWT tokens"
```

### Assignment Management
```bash
# Create assignment within a task
/manage_work create-assignment "Implement JWT tokens" "Create token validation middleware" --files "src/middleware/*.ts"

# List assignments for a task
/manage_work list-assignments "Implement JWT tokens"

# Complete an assignment
/manage_work complete-assignment "Create token validation middleware"
```

### Quick Operations
```bash
# Show current work overview
/manage_work overview

# Show what's currently in progress
/manage_work current

# Show next tasks to work on
/manage_work next

# Mark current file work as completing an assignment
/manage_work auto-complete --file src/middleware/auth.ts
```

## Options

- `--status <status>` - Set status (planning/active/completed for phases; todo/in_progress/completed for tasks)
- `--priority <priority>` - Set priority (low/medium/high/urgent for tasks)
- `--files <pattern>` - File pattern for assignments (e.g., "src/auth/*.ts")
- `--description <text>` - Add description

## Integration with Tool Tracking

When you work on files, the system can automatically:
- Link tool executions to relevant assignments
- Track progress on file-based work
- Suggest which assignments are being worked on

## Examples

```bash
# Set up a new feature
/manage_work create-phase "User Dashboard"
/manage_work create-task "User Dashboard" "Build dashboard components" --priority high
/manage_work create-assignment "Build dashboard components" "Create main Dashboard.tsx" --files "src/components/Dashboard.tsx"

# Check what's active
/manage_work current

# When you finish working on dashboard files
/manage_work auto-complete --file src/components/Dashboard.tsx
```

## Smart Features

- **Auto-linking**: File operations automatically link to relevant assignments
- **Progress tracking**: Visual progress indicators for phases and tasks  
- **Priority management**: Focus on high-priority work first
- **Pattern matching**: Assignments can track file patterns, not just specific files
- **Context awareness**: Understands your current work context

## Database Storage

All work data is stored in MySQL tables:
- `phases` - High-level project phases
- `tasks` - Specific work items within phases
- `assignments` - File-level work within tasks
- `tool_executions` - Links to actual work done

Falls back to JSON if database unavailable.