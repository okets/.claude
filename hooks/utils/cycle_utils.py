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
                return  # Quiet means no verbal announcements
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