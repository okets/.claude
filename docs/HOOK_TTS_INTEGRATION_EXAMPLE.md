# Hook TTS Integration Example

## How to Add TTS Announcements to Hooks

### 1. Import the TTS Announcer

Add this import at the top of your hook file:

```python
from utils.tts_announcer import announce_hook
```

### 2. Basic Hook Announcement

At the start of your main() function, add:

```python
def main():
    # Announce hook start
    announce_hook("pre tool use")
    
    # Rest of your hook logic...
```

### 3. Development Phase - Detailed Announcements

When working on specific features, add context:

```python
def main():
    # During development of user intent extraction
    announce_hook("notification", "extracting user request")
    
    # ... code to extract user request ...
    
    # Or when debugging database writes
    announce_hook("post tool use", f"recording {tool_name} execution")
```

### 4. Examples for Each Hook

#### Notification Hook
```python
# Basic
announce_hook("notification")

# During transcript parsing development
announce_hook("notification", "parsing transcript for user request")

# During session creation development
announce_hook("notification", f"creating session {session_id[:8]}")
```

#### Pre Tool Use Hook
```python
# Basic
announce_hook("pre tool use")

# During security check development
announce_hook("pre tool use", f"checking {tool_name} security")

# During intent inference development
announce_hook("pre tool use", f"inferring intent for {tool_name}")
```

#### Post Tool Use Hook
```python
# Basic
announce_hook("post tool use")

# During file change tracking development
announce_hook("post tool use", f"tracking {len(files_modified)} file changes")

# During context enrichment development
announce_hook("post tool use", "enriching change context")
```

#### Stop Hook
```python
# Basic
announce_hook("stop")

# During summary generation development
announce_hook("stop", "generating session summary")

# During pattern detection development
announce_hook("stop", f"detected {len(patterns)} patterns")
```

#### Subagent Stop Hook
```python
# Basic
announce_hook("subagent stop")

# During hierarchy tracking development
announce_hook("subagent stop", f"linking to parent {parent_id[:8]}")
```

### 5. Clean Up After Feature is Stable

Once a feature is working correctly, reduce the announcement back to just the hook name:

```python
def main():
    # Feature is stable, just announce the hook
    announce_hook("pre tool use")
    
    # All the working code remains unchanged
    # ...
```

## Best Practices

1. **One announcement per hook execution** - Don't spam multiple TTS messages
2. **Keep messages short** - TTS should be quick feedback, not verbose logs
3. **Include relevant data** - Tool names, counts, or short identifiers
4. **Clean up when done** - Remove detailed messages after features work
5. **Use for active development** - Add context when debugging specific issues

## Example Integration Pattern

```python
def main():
    try:
        # Announce at the very start
        announce_hook("notification", "extracting user request")  # DEV MODE
        # announce_hook("notification")  # PRODUCTION MODE
        
        # Read input
        input_data = json.load(sys.stdin)
        
        # Your hook logic here...
        
    except Exception as e:
        # Even errors are silent for TTS
        sys.exit(0)
```