#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import os
import subprocess
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_tts_script_path() -> Optional[str]:
    """
    Determine which TTS script to use based on available API keys.
    Priority order: ElevenLabs > OpenAI > pyttsx3
    """
    script_dir = Path(__file__).parent
    tts_dir = script_dir / "tts"
    
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


def announce_hook(hook_name: str, message: Optional[str] = None):
    """
    Announce hook execution with optional context message.
    
    Args:
        hook_name: Name of the hook being executed
        message: Optional context about what the hook is doing
    """
    try:
        tts_script = get_tts_script_path()
        if not tts_script:
            return  # No TTS scripts available
        
        # Build announcement
        if message:
            announcement = f"{hook_name} hook: {message}"
        else:
            announcement = f"{hook_name} hook"
        
        # Call the TTS script with the announcement
        subprocess.run([
            "uv", "run", tts_script, announcement
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


# Example usage for development phases:
# Phase 1: Basic announcement
# announce_hook("notification")
#
# Phase 2: With context during development
# announce_hook("notification", "extracting user request from transcript")
#
# Phase 3: Back to simple after feature is stable
# announce_hook("notification")