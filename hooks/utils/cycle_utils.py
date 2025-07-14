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
    
    # Strategy 1: Look for existing .claude directory (project boundary)
    search_dir = current_dir
    for _ in range(10):  # Limit search depth
        claude_dir = search_dir / ".claude"
        if claude_dir.exists():
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
    Determine which TTS script to use based on available API keys.
    Priority order: ElevenLabs > OpenAI > pyttsx3
    """
    # Get current script directory and construct utils/tts path
    script_dir = Path(__file__).parent.parent
    tts_dir = script_dir / "utils" / "tts"
    
    # Check for ElevenLabs API key (highest priority)
    if os.getenv('ELEVENLABS_API_KEY'):
        elevenlabs_script = tts_dir / "elevenlabs_tts.py"
        if elevenlabs_script.exists():
            return str(elevenlabs_script)
    
    # Check for OpenAI API key (second priority)
    if os.getenv('OPENAI_API_KEY'):
        openai_script = tts_dir / "openai_tts.py"
        if openai_script.exists():
            return str(openai_script)
    
    # Fall back to pyttsx3 (no API key required)
    pyttsx3_script = tts_dir / "pyttsx3_tts.py"
    if pyttsx3_script.exists():
        return str(pyttsx3_script)
    
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


def truncate_at_sentence_boundary(text, max_length=40):
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
        return "help", "with task"
    
    # Clean up common prefixes
    clean_request = re.sub(
        r'^(i am|help me|can you|please|could you|i want to|i need to)\s+', 
        '', 
        user_request.lower(), 
        flags=re.IGNORECASE
    ).strip()
    
    # Action patterns with their clean versions (order matters - more specific first)
    action_patterns = {
        r'run.*test|test.*run|testing|check.*test|verify.*test': 'Test',
        r'trying to find|looking for|find|search for': 'Find',
        r'fix|debug|resolve|solve': 'Fix',
        r'refactor|clean up|optimize|improve': 'Refactor',
        r'implement|add|create|build|make': 'Implement', 
        r'test|check|verify|validate': 'Test',
        r'commit|git': 'Git operation'
    }
    
    # Find matching action
    action = "Help"
    for pattern, clean_action in action_patterns.items():
        if re.search(pattern, clean_request, re.IGNORECASE):
            action = clean_action
            break
    
    # Extract subject (simplified - take next significant words)
    # Remove the action part and get the subject
    matched_pattern = None
    for pattern in action_patterns.keys():
        if re.search(pattern, clean_request, re.IGNORECASE):
            matched_pattern = pattern
            break
    
    if matched_pattern:
        clean_request = re.sub(matched_pattern, '', clean_request, flags=re.IGNORECASE).strip()
    
    # Clean up connecting words
    clean_request = re.sub(r'^(the|a|an|with|for|in|on)\s+', '', clean_request).strip()
    
    # Get first few significant words as subject
    words = clean_request.split()
    subject_words = [w for w in words[:4] if len(w) > 2]  # Skip short words
    subject = " ".join(subject_words) if subject_words else "task"
    
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
    
    # Detect trigger type
    if "permission" in trigger_message.lower():
        # For permission requests, focus on the tool being requested
        tool_name = extract_tool_from_permission_message(trigger_message)
        if tool_name:
            return create_tool_focused_notification(tool_name, user_request, trigger_message)
        
        # Fallback to user intent if no tool detected
        action, subject = extract_action_and_subject(user_request)
        prefix = get_varied_permission_prefix()
        if prefix in ["May I", "Should I go ahead and"]:
            return f"{prefix} {action.lower()} {subject}?"
        elif prefix in ["Can I proceed with", "Need approval for", "Awaiting permission to", "Ready to proceed with"]:
            return f"{prefix} {action.lower()}ing {subject}"
        else:
            return f"{prefix}: {action} {subject}"
    
    # Regular readiness notification - focus on user intent
    action, subject = extract_action_and_subject(user_request)
    prefix = get_varied_readiness_prefix()
    
    if subject == "task":
        if prefix in ["Let me", "I'll"]:
            return f"{prefix} {action.lower()}"
        else:
            return f"{prefix} {action.lower()}"
    else:
        if prefix in ["Let me", "I'll"]:
            return f"{prefix} {action.lower()} {subject}"
        else:
            return f"{prefix} {action.lower()}: {subject}"


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
    """Create verbose but concise notification - more speaking, not more text."""
    if not user_request or user_request.strip() == "":
        # Simple fallback for verbose mode
        verbose_fallbacks = [
            "Ready to help with your next task",
            "Standing by for instructions",
            "I'm here and ready to assist",
            "Awaiting your next request"
        ]
        import random
        return random.choice(verbose_fallbacks)
    
    # Extract meaningful action and subject from user request
    action, subject = extract_action_and_subject(user_request)
    
    # Add tool-specific context if this is a permission request (brief)
    if "permission" in trigger_message.lower():
        tool_name = extract_tool_from_permission_message(trigger_message)
        if tool_name:
            tool_contexts = {
                'Read': "Need to read files",
                'Write': "Need to write files", 
                'Edit': "Need to edit files",
                'Bash': "Need to run commands",
                'Task': "Need to use agents",
                'Glob': "Need to search files",
                'Grep': "Need to search content",
                'WebFetch': "Need to fetch web data"
            }
            
            context = tool_contexts.get(tool_name, f"Need to use {tool_name}")
            return f"{context} for: {action.lower()} {subject}"
    
    # Regular readiness notification - focus on user intent briefly
    if subject == "task":
        return f"Ready to {action.lower()}"
    else:
        return f"Ready to {action.lower()}: {subject}"


def create_verbose_completion_message(user_intent, cycle_summary_data=None):
    """Create comprehensive, verbose completion message with full context and details."""
    if not cycle_summary_data:
        # Fallback to basic but verbose completion
        if user_intent and len(user_intent.strip()) > 10:
            clean_intent = user_intent.strip()
            if len(clean_intent) > 100:
                clean_intent = clean_intent[:97] + "..."
            
            if clean_intent.startswith('"') and clean_intent.endswith('"'):
                clean_intent = clean_intent[1:-1]
            
            return (f"Task completed successfully! You had asked me to: {clean_intent}. "
                   "I've finished all the necessary work and everything is ready for your review. "
                   "All changes have been implemented according to your specifications and the project is in a good state.")
        else:
            return ("All work has been completed successfully! I've handled all aspects of your request comprehensively. "
                   "The project files have been updated appropriately and everything is ready for your continued development work.")
    
    context = extract_meaningful_context_from_summary(cycle_summary_data)
    
    # Build comprehensive message parts
    parts = []
    
    # Start with user intent reminder - more detailed for verbose mode
    if user_intent and len(user_intent.strip()) > 10:
        clean_intent = user_intent.strip()
        if len(clean_intent) > 120:
            clean_intent = clean_intent[:117] + "..."
        
        if clean_intent.startswith('"') and clean_intent.endswith('"'):
            clean_intent = clean_intent[1:-1]
        
        parts.append(f"Perfect! You had asked me to: {clean_intent}")
    else:
        parts.append("Excellent! Task completed successfully")
    
    # Detailed work summary - much more comprehensive for verbose mode
    work_details = []
    
    # File work details with full context
    if context['files_modified'] > 0:
        if len(context['files_worked_on']) == 1:
            filename = context['files_worked_on'][0]
            if context['total_edits'] > 1:
                work_details.append(f"I carefully updated {filename} with {context['total_edits']} precise edits, ensuring all changes integrate seamlessly with existing code")
            else:
                work_details.append(f"I made targeted modifications to {filename}, preserving the existing structure while implementing your requested changes")
        elif len(context['files_worked_on']) <= 4:
            files_list = ", ".join(context['files_worked_on'])
            work_details.append(f"I successfully modified {files_list}, coordinating changes across all files to maintain consistency and functionality")
        else:
            work_details.append(f"I comprehensively updated {context['files_modified']} files across your codebase, ensuring all modifications work together harmoniously and follow your project's conventions")
    
    # Subagent collaboration details
    if context['subagents_used'] > 0:
        if context['subagents_used'] == 1:
            work_details.append("I coordinated with 1 specialized agent to ensure optimal task execution and comprehensive coverage of all requirements")
        else:
            work_details.append(f"I orchestrated the work of {context['subagents_used']} specialized agents, managing parallel execution and ensuring seamless integration of all their contributions")
    
    # Operation types and technical details
    if context['operation_types']:
        ops = list(context['operation_types'])
        if len(ops) == 1:
            work_details.append(f"All work focused on {ops[0]} operations, executed with precision and attention to detail")
        elif len(ops) == 2:
            work_details.append(f"I handled both {ops[0]} and {ops[1]} operations, maintaining high quality standards throughout")
        else:
            work_details.append(f"I performed {len(ops)} different types of operations ({', '.join(ops[:3])}{'...' if len(ops) > 3 else ''}), demonstrating the comprehensive nature of this task")
    
    # Add detailed work summary
    if work_details:
        work_text = ". ".join(work_details)
        parts.append(f"Here's what I accomplished: {work_text}.")
    
    # Project state and quality assurance
    quality_messages = [
        "All changes have been thoroughly implemented and tested for compatibility",
        "The codebase is in excellent condition with all modifications properly integrated",
        "Every file has been updated according to best practices and your project's coding standards",
        "All work has been completed with careful attention to code quality and maintainability"
    ]
    
    import random
    parts.append(random.choice(quality_messages) + ".")
    
    # Complexity celebration with detailed context
    complexity = context.get('task_complexity', 'moderate')
    files_modified = context['files_modified']
    subagents_used = context['subagents_used']
    
    detailed_celebrations = {
        "simple": [
            "This was a beautifully straightforward task that I was able to execute cleanly and efficiently!",
            "What a pleasure to work on such a well-defined, clear request - executed perfectly!",
            "I love these kinds of focused tasks - simple to understand, satisfying to complete!",
            "This was exactly the kind of clean, efficient work that makes development a joy!"
        ],
        "moderate": [
            "This was a really solid piece of development work that required careful analysis and thoughtful implementation!",
            "What a satisfying challenge! This task demanded good technical judgment and I'm pleased with how it turned out!",
            "This was excellent development work - complex enough to be interesting but manageable enough to execute cleanly!",
            "I thoroughly enjoyed working through this well-scoped task with its clear requirements and meaningful outcomes!"
        ],
        "complex": [
            "Wow, this was genuinely challenging and comprehensive work! I'm really proud of how we tackled this complex task together!",
            "What an impressive undertaking! This required careful orchestration of multiple components and I'm thrilled with the results!",
            "This was seriously sophisticated work that pushed multiple systems and required deep technical coordination - excellent outcome!",
            "What a fantastic complex challenge! The scope and depth of this task made it incredibly rewarding to complete successfully!"
        ]
    }
    
    celebration = random.choice(detailed_celebrations.get(complexity, detailed_celebrations["moderate"]))
    
    # Add context-specific enhancements to celebration
    if subagents_used > 3:
        team_enhancements = [
            f" The coordination of {subagents_used} specialized agents was particularly impressive - true collaborative engineering at its finest!",
            f" Managing {subagents_used} different agents working in parallel was like conducting a technical orchestra - beautiful teamwork!",
            f" The way {subagents_used} agents came together to solve this shows the power of distributed, specialized problem-solving!"
        ]
        celebration += random.choice(team_enhancements)
    elif files_modified > 8:
        file_enhancements = [
            f" The scope of changes across {files_modified} files required careful coordination and attention to detail - expertly handled!",
            f" Working across {files_modified} different files while maintaining consistency and quality was a real technical achievement!",
            f" The comprehensive nature of updates to {files_modified} files demonstrates the thorough and systematic approach this task required!"
        ]
        celebration += random.choice(file_enhancements)
    elif context['total_edits'] > 10:
        edit_enhancements = [
            f" With {context['total_edits']} total edits, this required sustained focus and precision - every change was deliberate and valuable!",
            f" The {context['total_edits']} individual edits show the granular attention to detail that makes for truly professional development work!",
            f" Each of the {context['total_edits']} edits was carefully considered and implemented - this is craftsmanship-level programming!"
        ]
        celebration += random.choice(edit_enhancements)
    
    parts.append(celebration)
    
    # Future readiness and availability
    readiness_messages = [
        "I'm ready and excited for whatever challenge comes next!",
        "Standing by for your next request - I'm fully equipped and eager to tackle new problems!",
        "All systems are running smoothly and I'm prepared for continued development work!",
        "I'm energized and ready to dive into the next phase of your project whenever you need me!"
    ]
    
    parts.append(random.choice(readiness_messages))
    
    # Join all parts with appropriate spacing
    return " ".join(parts)