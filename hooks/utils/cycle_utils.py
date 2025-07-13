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
    """Announce message via TTS with error handling"""
    try:
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
    """Filter hook events to capture valuable context (reduce logging ~50%, not 70%)"""
    tool_name = hook_data.get('tool_name', '')
    
    # Always log Stop hooks (cycle completion)
    if hook_name == 'Stop':
        return True
    
    # Always log SubagentStop hooks  
    if hook_name == 'SubagentStop':
        return True
    
    # For PreToolUse: Log TodoWrite and Task tools (user intent + subagent delegation)
    if hook_name == 'PreToolUse':
        return tool_name in ['TodoWrite', 'Task']
    
    # For PostToolUse: Log valuable tools + some context tools
    if hook_name == 'PostToolUse':
        # File modification tools (core value)
        if tool_name in ['Edit', 'Write', 'MultiEdit']:
            return True
        
        # User intent tracking (essential)
        if tool_name == 'TodoWrite':
            return True
        
        # Subagent delegation completion
        if tool_name == 'Task':
            return True
        
        # Significant Bash operations only
        if tool_name == 'Bash':
            command = hook_data.get('tool_input', {}).get('command', '').lower()
            # Only log important operations
            significant_operations = ['git', 'npm', 'pip', 'build', 'test', 'deploy', 'install', 'commit']
            return any(op in command for op in significant_operations)
        
        # Keep SOME read operations for context (but not all)
        # Filter out excessive noise while preserving some exploration context
        if tool_name in ['Read', 'Grep', 'Glob']:
            # Could add smarter filtering here if needed (e.g., only first few reads)
            return False  # For now, still filter these out
        
        # Log other tools by default (NotebookRead, WebFetch, etc. might be valuable)
        return True
    
    # Default: don't log other hook types
    return False


def dump_hook_data(hook_name, hook_data, session_id, transcript_path):
    """
    Dump only valuable hook data to reduce logging volume by ~70%.
    
    Args:
        hook_name: Name of the hook (e.g., "PreToolUse", "Stop")
        hook_data: Raw JSON data from the hook
        session_id: Session identifier
        transcript_path: Path to transcript
    """
    try:
        # Filter out noise - only log valuable context
        if not _is_valuable_context(hook_name, hook_data):
            return  # Skip logging noise
        
        # Calculate cycle ID
        cycle_id = get_current_cycle_id(session_id, transcript_path)
        
        # Announce via TTS only for valuable events
        tool_name = hook_data.get('tool_name', 'unknown')
        announce_tts(f"Logging {hook_name}:{tool_name} for cycle {cycle_id}")
        
        # Create output directory
        output_dir = Path("/Users/hanan/.claude/.claude/session_logs")
        output_dir.mkdir(exist_ok=True)
        
        # Prepare dump data
        dump_entry = {
            "timestamp": datetime.now().isoformat(),
            "hook_name": hook_name,
            "cycle_id": cycle_id,
            "session_id": session_id,
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