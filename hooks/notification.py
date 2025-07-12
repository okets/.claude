#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import argparse
import json
import os
import sys
import subprocess
import random
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional


def get_tts_script_path():
    """
    Determine which TTS script to use based on available API keys.
    Priority order: ElevenLabs > OpenAI > pyttsx3
    """
    # Get current script directory and construct utils/tts path
    script_dir = Path(__file__).parent
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


def announce_notification():
    """Announce that the agent needs user input."""
    try:
        tts_script = get_tts_script_path()
        if not tts_script:
            return  # No TTS scripts available
        
        # Get engineer name if available
        engineer_name = os.getenv('ENGINEER_NAME', '').strip()
        
        # Create notification message with 30% chance to include name
        if engineer_name and random.random() < 0.3:
            notification_message = f"{engineer_name}, I need your input please"
        else:
            notification_message = "I need your input please"
        
        # Call the TTS script with the notification message
        subprocess.run([
            "uv", "run", tts_script, notification_message
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


def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--notify', action='store_true', help='Enable TTS notifications')
        args = parser.parse_args()
        
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        # Debug: Log input data to understand structure
        debug_log = Path(__file__).parent.parent / 'debug_notification.json'
        with open(debug_log, 'w') as f:
            json.dump(input_data, f, indent=2)
        
        # Import database utility
        sys.path.append(str(Path(__file__).parent / 'utils'))
        from db import get_db
        
        # Get database connection
        db = get_db()
        
        # Check if this is a user message (first message in conversation)
        message = input_data.get('message', '')
        session_id = input_data.get('session_id', '')
        
        # Store first user message as the conversation request
        if message and session_id and message != 'Claude is waiting for your input':
            # Get project information
            project_root = Path.cwd()
            while project_root != project_root.parent:
                if (project_root / '.git').exists():
                    break
                project_root = project_root.parent
            
            project_id = db.ensure_project(str(project_root), project_root.name)
            
            if project_id and db.connection:
                # Check if this session already has a conversation detail entry
                existing = db.get_conversation_details(session_id)
                
                if not existing:
                    # This is the first user message - capture it
                    # Generate a summary (in real implementation, could use LLM)
                    summary = message[:100] if len(message) > 100 else message
                    
                    # Save initial conversation details
                    db.save_conversation_details(
                        chat_session_id=session_id,
                        project_id=project_id,
                        user_request_summary=summary,
                        user_request_raw=message,
                        agent_model=input_data.get('model', 'unknown')
                    )
        
        # Announce notification via TTS only if --notify flag is set
        # Skip TTS for the generic "Claude is waiting for your input" message
        if args.notify and input_data.get('message') != 'Claude is waiting for your input':
            announce_notification()
        
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)

if __name__ == '__main__':
    main()