#!/usr/bin/env python3
"""
Shared utilities for cycle ID calculation and hook data management.
Used by all hooks to maintain consistent cycle tracking.
"""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime


def detect_project_root() -> Path:
    """
    Detect the current project root directory for smarter-claude.
    
    Returns:
        Path: Project root directory where .claude/smarter-claude/ should be created
    """
    current_dir = Path.cwd()
    
    # Special case: If we're in the hooks directory itself, don't treat it as a project
    # The hooks directory is the global installation, not a user project
    hooks_dir = Path(__file__).parent.parent  # Go up from utils/ to hooks/
    claude_global_dir = hooks_dir.parent      # Go up from hooks/ to .claude/
    
    if current_dir == claude_global_dir or current_dir.is_relative_to(claude_global_dir):
        # We're working from within the hooks directory - this is not a user project
        # Fall back to current directory as project root (user must create .claude manually)
        return current_dir
    
    # Strategy 1: Look for existing .claude directory (project boundary)
    search_dir = current_dir
    for _ in range(10):  # Limit search depth
        claude_dir = search_dir / ".claude"
        if claude_dir.exists():
            # Additional check: make sure this isn't the hooks installation directory
            if claude_dir != claude_global_dir:
                return search_dir
        
        parent = search_dir.parent
        if parent == search_dir:  # Reached filesystem root
            break
        search_dir = parent
    
    # Strategy 2: Look for git repository root
    search_dir = current_dir
    for _ in range(10):  # Limit search depth
        git_dir = search_dir / ".git"
        if git_dir.exists():
            return search_dir
        
        parent = search_dir.parent
        if parent == search_dir:  # Reached filesystem root
            break
        search_dir = parent
    
    # Strategy 3: Fallback to current working directory
    return current_dir


def get_project_smarter_claude_dir() -> Path:
    """
    Get the project-specific smarter-claude directory.
    
    Returns:
        Path: <project-root>/.claude/smarter-claude/
    """
    project_root = detect_project_root()
    return project_root / ".claude" / "smarter-claude"


def get_project_smarter_claude_logs_dir() -> Path:
    """
    Get the project-specific smarter-claude logs directory.
    
    Returns:
        Path: <project-root>/.claude/smarter-claude/logs/
    """
    return get_project_smarter_claude_dir() / "logs"


def get_tts_script_path():
    """
    Determine which TTS script to use based on user settings.
    Priority order: user preference > coqui > macos > pyttsx3
    """
    # Get current script directory and construct utils/tts path
    script_dir = Path(__file__).parent.parent
    tts_dir = script_dir / "utils" / "tts"
    
    # Get user's preferred TTS engine from settings
    try:
        from settings import get_setting
        preferred_engine = get_setting("tts_engine", "macos")
    except ImportError:
        # Fallback if settings not available
        preferred_engine = "macos"
    
    # Define available engines and their script paths
    engines = {
        "coqui-female": tts_dir / "coqui_tts.py",  # High-quality neural TTS
        "coqui-male": tts_dir / "coqui_male_tts.py",  # High-quality male neural TTS
        "macos-female": tts_dir / "macos_female_tts.py",
        "macos-male": tts_dir / "macos_male_tts.py", 
        "macos": tts_dir / "macos_native_tts.py",  # Legacy support
        "pyttsx3": tts_dir / "pyttsx3_tts.py"
    }
    
    # Try user's preferred engine first
    if preferred_engine in engines:
        preferred_script = engines[preferred_engine]
        if preferred_script.exists():
            return str(preferred_script)
    
    # Fallback chain: prioritize reliable engines (macos native > coqui > pyttsx3)
    fallback_order = ["macos-female", "macos-male", "macos", "coqui-female", "coqui-male", "pyttsx3"]
    for engine in fallback_order:
        if engine != preferred_engine:  # Skip already tried preference
            script_path = engines[engine]
            if script_path.exists():
                return str(script_path)
    
    return None


def announce_tts(message):
    """Announce infrastructure/debugging messages via TTS (controlled by speak_hook_logging)"""
    try:
        # Check settings for infrastructure TTS
        try:
            from settings import get_setting
            if not get_setting("logging_settings.speak_hook_logging", False):
                return  # Infrastructure TTS disabled
        except ImportError:
            # Settings not available, default to silent for infrastructure
            return
        
        tts_script = get_tts_script_path()
        if not tts_script:
            return  # No TTS scripts available
        
        # Call the TTS script with the message
        subprocess.run([
            "uv", "run", tts_script, message
        ], 
        capture_output=True,  # Suppress output
        timeout=10  # 10-second timeout
        )
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fail silently if TTS encounters issues
        pass
    except Exception:
        # Fail silently for any other errors
        pass


def announce_user_content(message, level="concise"):
    """Announce user-facing content about request cycles (controlled by interaction_level)"""
    try:
        # Check settings for user-facing TTS
        try:
            from settings import get_setting, is_tts_enabled
            if not is_tts_enabled():
                return  # User TTS disabled
            
            interaction_level = get_setting("interaction_level", "concise")
            
            # Only announce at appropriate levels
            if interaction_level == "silent":
                return
            elif interaction_level == "quiet":
                # Quiet mode: play completion sound instead of TTS
                try:
                    from notification_sounds import play_completion_sound
                    play_completion_sound()
                except ImportError:
                    pass  # Fall back to no sound if utility not available
                return
            elif interaction_level == "concise" and level in ["concise", "verbose"]:
                pass  # Announce concise and verbose content
            elif interaction_level == "verbose":
                pass  # Announce everything
            else:
                return  # Don't announce
                
        except ImportError:
            # Settings not available, use basic TTS check
            pass
        
        tts_script = get_tts_script_path()
        if not tts_script:
            return  # No TTS scripts available
        
        # Call the TTS script with the message
        subprocess.run([
            "uv", "run", tts_script, message
        ], 
        capture_output=True,  # Suppress output
        timeout=10  # 10-second timeout
        )
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fail silently if TTS encounters issues
        pass
    except Exception:
        # Fail silently for any other errors
        pass


def is_stop_hook_execution(entry):
    """Detect final Stop hook execution in transcript (not subagent stops)"""
    # Look for system messages indicating Stop hook execution
    if entry.get('type') == 'system':
        content = entry.get('content', '')
        # Look for Stop hook indicators, but exclude SubagentStop
        if ('Stop' in content and 'hook' in content.lower()) or ('stop.py' in content.lower()):
            # Exclude subagent stop hooks to only count final cycle completions
            if 'subagent' in content.lower():
                return False
            return True
    return False



def extract_user_intent_from_transcript(transcript_path, max_lines_back=50):
    """
    Extract the most recent user message from transcript.
    
    Args:
        transcript_path: Path to the conversation transcript
        max_lines_back: Maximum lines to read from end of file
        
    Returns:
        str: User message content or "Unknown task"
    """
    if not transcript_path or not Path(transcript_path).exists():
        return "Unknown task"
    
    try:
        # Read the last N lines from transcript to find recent user message
        with open(transcript_path, 'r') as f:
            lines = f.readlines()
        
        # Look backwards through recent lines for user messages
        recent_lines = lines[-max_lines_back:] if len(lines) > max_lines_back else lines
        
        for line in reversed(recent_lines):
            try:
                entry = json.loads(line.strip())
                
                # Look for user messages
                if (entry.get('type') == 'user' and 
                    entry.get('message', {}).get('role') == 'user'):
                    
                    content = entry.get('message', {}).get('content', '')
                    if content and isinstance(content, str) and len(content.strip()) > 0:
                        # Clean up the content - take first 200 chars to avoid huge intents
                        return content.strip()[:200]
                        
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
                
    except Exception:
        pass
    
    return "Unknown task"


def get_current_cycle_id(session_id, transcript_path):
    """
    Calculate current cycle ID by counting Stop hook executions in transcript.
    Works from any hook - Pre/Post/Notification/Stop/SubagentStop
    
    Args:
        session_id: Current session identifier
        transcript_path: Path to the conversation transcript
        
    Returns:
        int: Simple incremental cycle number (1, 2, 3, etc.)
    """
    stop_count = 0
    
    if transcript_path and Path(transcript_path).exists():
        try:
            with open(transcript_path, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if is_stop_hook_execution(entry):
                            stop_count += 1
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
        except Exception:
            # If we can't read transcript, default to cycle 1
            pass
    
    # Current cycle is next number (stop_count + 1)
    return stop_count + 1


def _is_valuable_context(hook_name, hook_data):
    """Log all tool events to capture full context for all task types"""
    
    # Always log Stop hooks (cycle completion)
    if hook_name == 'Stop':
        return True
    
    # Always log SubagentStop hooks  
    if hook_name == 'SubagentStop':
        return True
    
    # Log all PreToolUse events (captures user intent and all tool usage)
    if hook_name == 'PreToolUse':
        return True
    
    # Log all PostToolUse events (captures all tool results and context)
    if hook_name == 'PostToolUse':
        return True
    
    # Default: don't log other hook types (notifications, etc.)
    return False


def dump_hook_data(hook_name, hook_data, session_id, transcript_path):
    """
    Dump raw hook JSON data with cycle ID to log file.
    
    Args:
        hook_name: Name of the hook (e.g., "PreToolUse", "Stop")
        hook_data: Raw JSON data from the hook
        session_id: Session identifier
        transcript_path: Path to transcript
    """
    try:
        # Calculate cycle ID
        cycle_id = get_current_cycle_id(session_id, transcript_path)
        
        # Extract user intent from transcript
        user_intent = extract_user_intent_from_transcript(transcript_path)
        
        # Announce via TTS
        announce_tts(f"Hook {hook_name} fired for cycle {cycle_id}")
        
        # Create project-specific output directory
        output_dir = get_project_smarter_claude_logs_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare dump data with user intent
        dump_entry = {
            "timestamp": datetime.now().isoformat(),
            "hook_name": hook_name,
            "cycle_id": cycle_id,
            "session_id": session_id,
            "user_intent": user_intent,
            "raw_data": hook_data
        }
        
        # Create session-specific filename with cycle_id (JSONL only)
        session_short = session_id[:8] if session_id else "unknown"
        dumps_file = output_dir / f"session_{session_short}_cycle_{cycle_id}_hooks.jsonl"
        with open(dumps_file, 'a') as f:
            f.write(json.dumps(dump_entry) + "\n")
            
    except Exception as e:
        # Log errors but don't fail the hook
        try:
            with open('/tmp/cycle_utils_debug.log', 'a') as f:
                f.write(f"\n{datetime.now()}: Error in dump_hook_data: {str(e)}\n")
        except:
            pass


# Rule-based text processing utilities for Concise Mode
import re


def truncate_at_sentence_boundary(text, max_length=80):
    """Truncate text at sentence boundary, preferring periods over other punctuation."""
    if len(text) <= max_length:
        return text
    
    # Try to find last period within limit
    truncated = text[:max_length]
    last_period = truncated.rfind('.')
    
    if last_period > max_length * 0.6:  # If period is reasonably far in
        return truncated[:last_period + 1].strip()
    
    # Fall back to word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.5:
        return truncated[:last_space].strip() + "..."
    
    # Last resort: hard truncation
    return truncated.strip() + "..."


def extract_action_and_subject(user_request):
    """Extract main action and subject from user request using rule-based patterns."""
    if not user_request:
        return "help", "with your task"
    
    # If the request is short, use it more naturally to avoid awkward truncation
    if len(user_request.strip()) <= 50:
        return "help", f"with: {user_request.strip()}"
    
    # For longer requests, use a more natural truncation
    # Take first 80 chars and try to end at a word boundary
    truncated = user_request[:80]
    last_space = truncated.rfind(' ')
    if last_space > 20:  # If we found a reasonable word boundary
        subject = truncated[:last_space]
    else:
        subject = truncated
    
    # Add ellipsis if we truncated
    if len(user_request) > len(subject):
        subject += "..."
    
    # Simple action detection
    user_lower = user_request.lower()
    if any(word in user_lower for word in ['find', 'search', 'look']):
        action = "find"
    elif any(word in user_lower for word in ['fix', 'debug', 'resolve']):
        action = "fix"
    elif any(word in user_lower for word in ['test', 'check', 'verify']):
        action = "test"
    elif any(word in user_lower for word in ['implement', 'add', 'create', 'build']):
        action = "implement"
    elif any(word in user_lower for word in ['commit', 'git']):
        action = "handle git"
    else:
        action = "help"
    
    return action, subject


def get_varied_fallback_message():
    """Get a varied fallback message when user intent is unknown."""
    import random
    
    messages = [
        "I need your input please",
        "Your input is needed",
        "Waiting for your guidance",
        "Ready for your next instruction", 
        "What would you like me to do next?",
        "Awaiting your command",
        "I'm listening for your next request",
        "How can I help you today?"
    ]
    
    return random.choice(messages)


def get_varied_permission_prefix():
    """Get varied permission request prefix."""
    import random
    
    prefixes = [
        "Permission needed",
        "May I",
        "Can I proceed with",
        "Requesting permission to",
        "Need approval for",
        "Should I go ahead and",
        "Awaiting permission to",
        "Ready to proceed with"
    ]
    
    return random.choice(prefixes)


def get_varied_readiness_prefix():
    """Get varied readiness prefix."""
    import random
    
    prefixes = [
        "Ready to",
        "Set to",
        "Standing by to", 
        "Prepared to",
        "Let me",
        "I'll",
        "Time to",
        "About to"
    ]
    
    return random.choice(prefixes)


def extract_tool_from_permission_message(trigger_message):
    """Extract the tool name from permission message."""
    if not trigger_message:
        return None
    
    # Look for patterns like "Claude needs your permission to use [TOOL]"
    import re
    
    # Pattern: "Claude needs your permission to use TOOL"
    match = re.search(r'permission to use (\w+)', trigger_message, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern: "Claude needs permission for TOOL"  
    match = re.search(r'permission for (\w+)', trigger_message, re.IGNORECASE)
    if match:
        return match.group(1)
        
    return None




def create_tool_focused_notification(tool_name, user_request=None, input_data=None):
    """Create notification focused on the tool being requested."""
    if not tool_name:
        return get_varied_fallback_message()
    
    # Tool-specific messages
    tool_messages = {
        'Read': ['read files', 'access files', 'view files', 'check files'],
        'Write': ['write files', 'create files', 'save files'],
        'Edit': ['edit files', 'modify files', 'update files'],
        'Bash': ['run commands', 'execute commands', 'run bash'],
        'Task': ['create subtasks', 'spawn agents', 'delegate work'],
        'Glob': ['search files', 'find files', 'locate files'],
        'Grep': ['search content', 'find text', 'search files'],
        'WebFetch': ['fetch web content', 'access websites', 'get web data']
    }
    
    import random
    
    # Get tool-specific action
    actions = tool_messages.get(tool_name, [f'use {tool_name}'])
    action = random.choice(actions)
    
    # Get varied permission prefix
    prefix = get_varied_permission_prefix()
    
    if prefix in ["May I", "Should I go ahead and"]:
        return f"{prefix} {action}?"
    elif prefix in ["Can I proceed with", "Need approval for"]:
        return f"{prefix} {action}"
    elif prefix in ["Awaiting permission to", "Ready to proceed with"]:
        return f"{prefix} {action}"
    else:
        return f"{prefix}: {action}"


def create_concise_notification(user_request, trigger_message=""):
    """Create concise notification message based on user request and trigger type."""
    if not user_request or user_request.strip() == "":
        return get_varied_fallback_message()
    
    # Clean up user request - take first sentence if it's long
    clean_request = user_request.strip()
    if len(clean_request) > 80:
        # Find first sentence or truncate at word boundary
        first_sentence = clean_request.split('.')[0]
        if len(first_sentence) <= 80:
            clean_request = first_sentence
        else:
            last_space = clean_request[:80].rfind(' ')
            clean_request = clean_request[:last_space] if last_space > 40 else clean_request[:80]
    
    # Use the same clean format for all notifications
    return f"You instructed me to '{clean_request}'. I need your confirmation to proceed with a subtask related to that."


def get_varied_completion_suffix(primary_activity, files_modified=0):
    """Get varied completion suffix based on activity type."""
    import random
    
    if primary_activity == "file_modification" and files_modified > 0:
        file_word = "file" if files_modified == 1 else "files"
        variations = [
            f"{files_modified} {file_word} updated",
            f"{files_modified} {file_word} modified", 
            f"{files_modified} {file_word} changed",
            f"updated {files_modified} {file_word}",
            f"modified {files_modified} {file_word}",
            f"{files_modified} {file_word} edited"
        ]
        return random.choice(variations)
    
    elif primary_activity == "testing":
        variations = [
            "testing complete",
            "tests finished",
            "testing done", 
            "all tests run",
            "testing passed"
        ]
        return random.choice(variations)
    
    elif primary_activity == "git-operation":
        variations = [
            "git operations complete",
            "git commands finished",
            "git work done",
            "repository updated",
            "git tasks complete"
        ]
        return random.choice(variations)
    
    else:
        variations = [
            "complete",
            "done",
            "finished", 
            "all set",
            "task complete",
            "wrapped up"
        ]
        return random.choice(variations)


def get_varied_completion_connector():
    """Get varied connector for completion messages."""
    import random
    
    connectors = ["-", "—", "·", "•", "|"]
    return f" {random.choice(connectors)} "


def create_concise_completion(user_intent, files_modified=0, primary_activity="unknown"):
    """Create concise task completion message."""
    if not user_intent:
        fallback_completions = [
            "Task complete",
            "All done", 
            "Finished",
            "Work complete",
            "Task finished"
        ]
        import random
        return random.choice(fallback_completions)
    
    action, subject = extract_action_and_subject(user_intent)
    
    # Create base summary
    if subject == "task":
        summary = action
    else:
        summary = f"{action} {subject}"
    
    # Add contextual completion info with varied format
    suffix = get_varied_completion_suffix(primary_activity, files_modified)
    connector = get_varied_completion_connector()
    
    return f"{summary}{connector}{suffix}"


def extract_meaningful_context_from_summary(cycle_summary_data):
    """Extract meaningful context from cycle summary for enhanced notifications."""
    if not cycle_summary_data:
        return {}
    
    context = {}
    
    # Get user intent and file activities
    context['user_intent'] = cycle_summary_data.get('user_intent', '')
    context['files_modified'] = cycle_summary_data.get('execution_summary', {}).get('files_modified', 0)
    context['total_edits'] = cycle_summary_data.get('execution_summary', {}).get('total_edits', 0)
    context['primary_activity'] = cycle_summary_data.get('execution_summary', {}).get('primary_activity', 'unknown')
    context['subagents_used'] = cycle_summary_data.get('execution_summary', {}).get('subagents_used', 0)
    
    # Extract file names and operations
    file_activities = cycle_summary_data.get('file_activities', {})
    context['files_worked_on'] = []
    context['operation_types'] = set()
    
    for file_path, activities in file_activities.items():
        file_name = file_path.split('/')[-1]  # Get just filename
        context['files_worked_on'].append(file_name)
        
        # Get operations from main agent
        main_agent_data = activities.get('main_agent', {})
        operations = main_agent_data.get('operations', [])
        context['operation_types'].update(operations)
    
    # Get workflow insights
    workflow_insights = cycle_summary_data.get('workflow_insights', {})
    context['task_complexity'] = workflow_insights.get('task_complexity', {}).get('level', 'unknown')
    context['collaboration_type'] = workflow_insights.get('agent_collaboration', {}).get('collaboration_type', 'none')
    
    return context


def get_complexity_celebration(complexity_level, files_modified=0, subagents_used=0):
    """Get varied celebration messages based on task complexity."""
    import random
    
    celebrations = {
        "simple": [
            "That was a nice and easy one!",
            "Quick and smooth - just how I like it!",
            "Simple task, clean execution!",
            "That went really smoothly!",
            "Easy peasy!",
            "Straightforward and done!"
        ],
        "moderate": [
            "That was a solid piece of work!",
            "Good challenge, well executed!",
            "That required some thinking, but we got it!",
            "Nice work on that one!",
            "That was a decent challenge!",
            "A good workout for the brain!"
        ],
        "complex": [
            "Wow, that was a really challenging one!",
            "That was quite the complex task!",
            "Phew! That was a tough nut to crack!",
            "That was seriously challenging work!",
            "What a complex puzzle that was!",
            "That was no joke - really complex stuff!"
        ]
    }
    
    # Get base celebration
    base_celebrations = celebrations.get(complexity_level, celebrations["simple"])
    celebration = random.choice(base_celebrations)
    
    # Add context-specific enthusiasm
    if subagents_used > 2:
        team_additions = [
            " Great teamwork with all those agents!",
            " Love how the team came together on this!",
            " Excellent collaboration across the board!"
        ]
        celebration += random.choice(team_additions)
    elif files_modified > 5:
        file_additions = [
            " Lots of files touched - comprehensive work!",
            " Really thorough changes across the codebase!",
            " Great coverage across multiple files!"
        ]
        celebration += random.choice(file_additions)
    
    return celebration


def create_detailed_work_summary(context):
    """Create detailed summary of work performed."""
    work_parts = []
    
    # File work details
    if context['files_modified'] > 0:
        if len(context['files_worked_on']) == 1:
            filename = context['files_worked_on'][0]
            if context['total_edits'] > 1:
                work_parts.append(f"I updated {filename} with {context['total_edits']} careful edits")
            else:
                work_parts.append(f"I updated {filename}")
        elif len(context['files_worked_on']) <= 3:
            files_list = ", ".join(context['files_worked_on'])
            work_parts.append(f"I modified {files_list}")
        else:
            work_parts.append(f"I modified {context['files_modified']} files across the codebase")
    
    # Subagent collaboration
    if context['subagents_used'] > 0:
        if context['subagents_used'] == 1:
            work_parts.append("working with 1 specialized agent")
        else:
            work_parts.append(f"coordinating with {context['subagents_used']} specialized agents")
    
    # Operation types
    if context['operation_types']:
        ops = list(context['operation_types'])
        if len(ops) == 1:
            work_parts.append(f"focused on {ops[0]} operations")
        elif len(ops) == 2:
            work_parts.append(f"handling {ops[0]} and {ops[1]} operations")
        else:
            work_parts.append(f"performing {len(ops)} different types of operations")
    
    return work_parts


def create_rich_completion_message(user_intent, cycle_summary_data=None):
    """Create rich, celebratory completion message using cycle summary context."""
    if not cycle_summary_data:
        # Fallback to basic completion
        return create_concise_completion(user_intent, 0, "unknown")
    
    context = extract_meaningful_context_from_summary(cycle_summary_data)
    
    # Start with user intent reminder
    if user_intent and len(user_intent.strip()) > 10:
        # Clean up the user intent for speaking
        clean_intent = user_intent.strip()
        if len(clean_intent) > 80:
            clean_intent = clean_intent[:77] + "..."
        
        # Remove quotes if they wrap the entire intent
        if clean_intent.startswith('"') and clean_intent.endswith('"'):
            clean_intent = clean_intent[1:-1]
        
        intro = f"You asked: {clean_intent}. "
    else:
        intro = "Task completed! "
    
    # Get work summary details
    work_summary = create_detailed_work_summary(context)
    
    if work_summary:
        work_text = ", ".join(work_summary)
        middle = f"Done! {work_text}. "
    else:
        middle = "All finished! "
    
    # Get complexity celebration
    complexity = context.get('task_complexity', 'simple')
    celebration = get_complexity_celebration(
        complexity, 
        context['files_modified'], 
        context['subagents_used']
    )
    
    # Combine all parts
    full_message = intro + middle + celebration
    
    return full_message


def create_context_aware_notification(user_request, trigger_message="", recent_work_context=None):
    """Create notification with awareness of recent work patterns."""
    base_notification = create_concise_notification(user_request, trigger_message)
    
    # If we have context about recent work, enhance the notification
    if recent_work_context and user_request:
        action, subject = extract_action_and_subject(user_request)
        
        # If this request seems to continue previous work, mention it
        if recent_work_context.get('files_worked_on'):
            recent_files = recent_work_context['files_worked_on']
            
            # Check if request mentions similar files or concepts
            for filename in recent_files:
                file_base = filename.replace('.py', '').replace('.js', '').replace('.ts', '')
                if file_base.lower() in user_request.lower():
                    prefix = get_varied_readiness_prefix()
                    return f"{prefix} continue work on {filename}: {action.lower()} {subject}"
        
        # If this is a testing request after file modifications
        if (action.lower() == 'test' and 
            recent_work_context.get('primary_activity') == 'file_modification' and
            recent_work_context.get('files_modified', 0) > 0):
            prefix = get_varied_readiness_prefix()
            return f"{prefix} test the recent changes: {recent_work_context['files_modified']} files modified"
    
    return base_notification


def get_recent_work_context(session_id, current_cycle_id, lookback_cycles=2):
    """Get context from recent cycles to inform notifications."""
    try:
        import json
        
        logs_dir = get_project_smarter_claude_logs_dir()
        recent_context = {
            'files_worked_on': [],
            'primary_activity': 'unknown',
            'files_modified': 0,
            'operation_types': set()
        }
        
        # Look at the last few cycles
        for cycle_offset in range(1, lookback_cycles + 1):
            previous_cycle = current_cycle_id - cycle_offset
            if previous_cycle < 1:
                continue
                
            session_short = session_id[:8] if session_id else "unknown"
            summary_file = logs_dir / f"session_{session_short}_cycle_{previous_cycle}_summary.json"
            
            if summary_file.exists():
                try:
                    with open(summary_file, 'r') as f:
                        cycle_data = json.load(f)
                    
                    context = extract_meaningful_context_from_summary(cycle_data)
                    
                    # Accumulate information from recent cycles
                    recent_context['files_worked_on'].extend(context.get('files_worked_on', []))
                    recent_context['files_modified'] += context.get('files_modified', 0)
                    recent_context['operation_types'].update(context.get('operation_types', set()))
                    
                    # Use the most recent primary activity
                    if cycle_offset == 1:
                        recent_context['primary_activity'] = context.get('primary_activity', 'unknown')
                        
                except (json.JSONDecodeError, Exception):
                    continue
        
        # Remove duplicates from files list
        recent_context['files_worked_on'] = list(set(recent_context['files_worked_on']))
        recent_context['operation_types'] = list(recent_context['operation_types'])
        
        return recent_context
        
    except Exception:
        return None


def create_verbose_notification(user_request, trigger_message="", recent_work_context=None):
    """Create verbose notification using the same clean format."""
    if not user_request or user_request.strip() == "":
        return "Ready to help with your next task"
    
    # Clean up user request - take first sentence if it's long
    clean_request = user_request.strip()
    if len(clean_request) > 80:
        # Find first sentence or truncate at word boundary
        first_sentence = clean_request.split('.')[0]
        if len(first_sentence) <= 80:
            clean_request = first_sentence
        else:
            last_space = clean_request[:80].rfind(' ')
            clean_request = clean_request[:last_space] if last_space > 40 else clean_request[:80]
    
    # Use the same clean format as concise mode
    return f"You instructed me to '{clean_request}'. I need your confirmation to proceed with a subtask related to that."


def assess_task_complexity(cycle_summary_data, user_intent):
    """Assess task complexity based on multiple factors."""
    if not cycle_summary_data:
        # Simple heuristic based on user intent length
        if not user_intent or len(user_intent.strip()) < 20:
            return "simple"
        elif len(user_intent.strip()) < 100:
            return "moderate"
        else:
            return "complex"
    
    context = extract_meaningful_context_from_summary(cycle_summary_data)
    
    # Calculate complexity score
    score = 0
    
    # File-based complexity
    files_modified = context['files_modified']
    if files_modified >= 5:
        score += 3
    elif files_modified >= 2:
        score += 2
    elif files_modified == 1:
        score += 1
    
    # Edit-based complexity
    total_edits = context['total_edits']
    if total_edits >= 10:
        score += 3
    elif total_edits >= 4:
        score += 2
    elif total_edits >= 1:
        score += 1
    
    # Agent-based complexity
    subagents = context['subagents_used']
    if subagents >= 3:
        score += 3
    elif subagents >= 1:
        score += 2
    
    # Operation diversity
    op_types = len(context['operation_types'])
    if op_types >= 4:
        score += 2
    elif op_types >= 2:
        score += 1
    
    # Classify complexity
    if score <= 3:
        return "simple"
    elif score <= 7:
        return "moderate"
    else:
        return "complex"

def create_verbose_completion_message(user_intent, cycle_summary_data=None, timing_info=None):
    """Create dynamic completion message based on task complexity with varied reactions."""
    complexity = assess_task_complexity(cycle_summary_data, user_intent)
    
    if not cycle_summary_data:
        return create_fallback_verbose_message(user_intent, complexity)
    
    context = extract_meaningful_context_from_summary(cycle_summary_data)
    
    # Create message based on complexity
    if complexity == "simple":
        return create_simple_completion_message(user_intent, context, timing_info)
    elif complexity == "moderate":
        return create_moderate_completion_message(user_intent, context, timing_info)
    else:
        return create_complex_completion_message(user_intent, context, timing_info)

def create_fallback_verbose_message(user_intent, complexity):
    """Create fallback message when no summary data available."""
    import random
    
    if complexity == "simple":
        reactions = [
            "Done!", "Perfect!", "Complete!", "Finished!", "All set!"
        ]
        return f"{random.choice(reactions)} Quick and clean work."
    
    elif complexity == "moderate":
        if user_intent and len(user_intent.strip()) > 10:
            clean_intent = user_intent.strip()[:80] + ("..." if len(user_intent.strip()) > 80 else "")
            return f"Task completed! {clean_intent} - All handled with care."
        else:
            return "Solid work completed! Everything's been handled properly."
    
    else:  # complex
        reactions = [
            "Excellent work completed!",
            "Mission accomplished!",
            "Outstanding results achieved!",
            "Fantastic work finished!"
        ]
        if user_intent:
            clean_intent = user_intent.strip()[:100] + ("..." if len(user_intent.strip()) > 100 else "")
            return f"{random.choice(reactions)} {clean_intent} - Comprehensive solution delivered!"
        else:
            return f"{random.choice(reactions)} Complex task handled with precision and expertise!"

def create_simple_completion_message(user_intent, context, timing_info=None):
    """Create properly verbose completion for simple tasks."""
    import random
    
    # Build timing context if available
    timing_intro = ""
    if timing_info and timing_info.get('duration_seconds'):
        duration = timing_info['duration_seconds']
        if duration > 30:
            long_phrases = [
                "That was a long one! ", "Took longer than expected! ", "That required patience! ",
                "Bit of a slog, but ", "That was quite the journey! ", "Extended effort there! ",
                "That took some time! ", "Longer task completed! "
            ]
            timing_intro = random.choice(long_phrases)
        elif duration > 10:
            medium_phrases = [
                "Took a moment, but ", "Brief pause required, ", "Quick thinking time, ",
                "Short effort invested, ", "Moment of focus, ", "Brief work session, "
            ]
            timing_intro = random.choice(medium_phrases)
        elif duration < 3:
            quick_phrases = [
                "Quick work! ", "Lightning fast! ", "Speedy execution! ",
                "Rapid completion! ", "Swift work! ", "Instant results! "
            ]
            timing_intro = random.choice(quick_phrases)
    
    # Verbose but concise reactions for simple tasks
    base_reactions = [
        "Task completed successfully!",
        "Work finished perfectly!",
        "Everything handled cleanly!",
        "Simple task executed well!",
        "Straightforward work complete!",
        "Clean execution achieved!",
        "Boom! Nailed it!",
        "Easy peasy lemon squeezy!",
        "Like butter on toast!"
    ]
    
    # Add context details for verbosity
    details = []
    if context['files_modified'] > 0:
        if context['files_modified'] == 1:
            details.append(f"updated {context['files_modified']} file with precision")
        else:
            details.append(f"coordinated changes across {context['files_modified']} files")
    
    if context['total_edits'] > 0:
        details.append(f"made {context['total_edits']} careful edit{'s' if context['total_edits'] > 1 else ''}")
    
    # Combine timing + reaction + details
    base = f"{timing_intro}{random.choice(base_reactions)}"
    
    if details:
        detail_text = " and ".join(details[:2])  # Max 2 details for simple tasks
        return f"{base} I {detail_text}, ensuring everything integrates smoothly."
    else:
        return f"{base} Clean, efficient implementation with attention to detail."

def create_moderate_completion_message(user_intent, context, timing_info=None):
    """Create balanced completion for moderate tasks."""
    import random
    
    # Build timing context if available
    timing_intro = ""
    if timing_info and timing_info.get('duration_seconds'):
        duration = timing_info['duration_seconds']
        if duration > 45:
            substantial_phrases = [
                "That was a substantial one! ", "Significant effort invested! ", "That was quite involved! ",
                "Decent chunk of work there! ", "That required some dedication! ", "Solid effort completed! ",
                "That was no small task! ", "Good investment of time! "
            ]
            timing_intro = random.choice(substantial_phrases)
        elif duration > 20:
            moderate_phrases = [
                "Good effort required, but ", "Some focus needed, ", "Steady work invested, ",
                "Thoughtful approach taken, ", "Careful attention given, ", "Measured effort applied, "
            ]
            timing_intro = random.choice(moderate_phrases)
        elif duration < 5:
            efficient_phrases = [
                "Efficient work! ", "Smooth execution! ", "Well-paced effort! ",
                "Streamlined process! ", "Clean workflow! ", "Optimal timing! "
            ]
            timing_intro = random.choice(efficient_phrases)
    
    # Mix of reaction styles
    reactions = [
        "Solid work completed!",
        "Task handled successfully!",
        "Everything implemented nicely!",
        "Great results achieved!",
        "Work finished with care!",
        "Implementation complete!",
        "Smooth like jazz!",
        "Crushed it!",
        "Another one bites the dust!"
    ]
    
    base = f"{timing_intro}{random.choice(reactions)}"
    
    # Add context details (always for moderate tasks)
    details = []
    if context['files_modified'] > 1:
        details.append(f"coordinated {context['files_modified']} files seamlessly")
    if context['subagents_used'] > 0:
        details.append(f"managed agent collaboration effectively")
    if context['total_edits'] > 3:
        details.append(f"executed {context['total_edits']} precise edits")
    if len(context['operation_types']) > 1:
        details.append(f"handled {len(context['operation_types'])} operation types")
    
    if details:
        detail_text = random.choice(details)
        return f"{base} I {detail_text}, maintaining quality throughout the process."
    else:
        return f"{base} Methodical approach with attention to detail and integration."

def create_complex_completion_message(user_intent, context, timing_info=None):
    """Create celebratory completion for complex tasks with high variation."""
    import random
    
    # Build timing context for complex tasks
    timing_intro = ""
    if timing_info and timing_info.get('duration_seconds'):
        duration = timing_info['duration_seconds']
        if duration > 120:
            marathon_phrases = [
                "That was a marathon! ", "Epic journey completed! ", "That was quite the odyssey! ",
                "Major undertaking finished! ", "That was a serious expedition! ", "Long haul completed! ",
                "That was quite the adventure! ", "Extended mission accomplished! ", "What a ride that was! "
            ]
            timing_intro = random.choice(marathon_phrases)
        elif duration > 60:
            serious_phrases = [
                "That took some serious work! ", "Heavy lifting completed! ", "That was substantial! ",
                "Significant effort invested! ", "That required real focus! ", "Deep work session! ",
                "That was quite involved! ", "Intensive work completed! "
            ]
            timing_intro = random.choice(serious_phrases)
        elif duration > 30:
            good_effort_phrases = [
                "Good effort invested! ", "Solid work session! ", "That took some doing! ",
                "Decent effort required! ", "That needed focus! ", "Good chunk of work! ",
                "That was engaging! ", "Quality time invested! "
            ]
            timing_intro = random.choice(good_effort_phrases)
        elif duration < 10:
            efficient_phrases = [
                "Remarkably efficient! ", "Lightning fast execution! ", "Incredibly smooth! ",
                "Blazing fast work! ", "Exceptionally quick! ", "Amazingly swift! ",
                "Impressively rapid! ", "Surprisingly fast! "
            ]
            timing_intro = random.choice(efficient_phrases)
    
    # Highly varied celebration styles
    celebration_styles = [
        "short_celebration",
        "detailed_technical", 
        "enthusiastic_brief",
        "comprehensive_summary",
        "achievement_focused"
    ]
    
    style = random.choice(celebration_styles)
    
    if style == "short_celebration":
        celebrations = [
            "Boom! Complex task conquered!",
            "Nailed it! Sophisticated work complete!",
            "Outstanding! Intricate task mastered!",
            "Exceptional work finished!",
            "Brilliant execution complete!",
            "Mic drop moment!",
            "Like a boss!",
            "Chef's kiss perfection!"
        ]
        return f"{timing_intro}{random.choice(celebrations)}"
    
    elif style == "enthusiastic_brief":
        enthusiastic = [
            f"Fantastic! Coordinated {context['files_modified']} files flawlessly!",
            f"Amazing work! {context['total_edits']} edits executed with precision!",
            f"Superb! Complex orchestration handled beautifully!",
            f"Incredible! Multi-faceted task completed expertly!"
        ]
        return random.choice(enthusiastic)
    
    elif style == "achievement_focused":
        achievements = [
            f"Mission accomplished! Successfully managed {len(context['operation_types'])} operation types.",
            f"Victory! Complex coordination across {context['files_modified']} files achieved.",
            f"Success! Sophisticated task requiring {context['subagents_used']} agents completed.",
            f"Excellence! Multi-layered implementation finished flawlessly."
        ]
        return random.choice(achievements)
    
    elif style == "detailed_technical":
        # Longer technical celebration
        details = []
        if context['files_modified'] > 2:
            details.append(f"orchestrated changes across {context['files_modified']} files")
        if context['subagents_used'] > 1:
            details.append(f"coordinated {context['subagents_used']} specialized agents")
        if len(context['operation_types']) > 2:
            details.append(f"executed {len(context['operation_types'])} operation types")
        
        if details:
            work_desc = ", ".join(details[:2])  # Limit to 2 details
            return f"Complex task mastered! I {work_desc} with expert precision. Everything integrated beautifully!"
        else:
            return "Sophisticated work completed! Complex requirements handled with technical excellence!"
    
    else:  # comprehensive_summary
        # Full celebration with context
        if user_intent:
            intent_snippet = user_intent.strip()[:60] + ("..." if len(user_intent.strip()) > 60 else "")
            return (f"Outstanding achievement! Your request: {intent_snippet} - "
                   f"Successfully delivered through {context['files_modified']} file modifications, "
                   f"{context['total_edits']} edits, demonstrating complex technical coordination. Exceptional results!")
        else:
            return (f"Magnificent work completed! This complex task involved {context['files_modified']} files, "
                   f"{context['total_edits']} modifications, and sophisticated coordination. "
                   f"Every aspect handled with expertise and precision!")
