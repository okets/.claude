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


def get_first_user_message_from_transcript(transcript_path):
    """Extract the first user message from the transcript file."""
    try:
        if not os.path.exists(transcript_path):
            return None
            
        with open(transcript_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    # Look for first user message (parentUuid is null)
                    if (entry.get('type') == 'user' and 
                        entry.get('parentUuid') is None and
                        'message' in entry and
                        'content' in entry['message']):
                        return entry['message']['content']
                except json.JSONDecodeError:
                    continue
        return None
    except Exception:
        return None


def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('--notify', action='store_true', help='Enable TTS notifications')
        args = parser.parse_args()
        
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        # Get session info
        session_id = input_data.get('session_id', '')
        transcript_path = input_data.get('transcript_path', '')
        
        # Extract actual user request from transcript
        user_request = None
        if transcript_path:
            user_request = get_first_user_message_from_transcript(transcript_path)
        
        # Debug: Log input data and extracted user request
        debug_log = Path('/tmp') / 'claude_debug_notification.json'
        debug_data = {
            'input_data': input_data,
            'extracted_user_request': user_request,
            'transcript_path': transcript_path
        }
        with open(debug_log, 'w') as f:
            json.dump(debug_data, f, indent=2)
        
        # # Import new queryable database utility
        # sys.path.append(str(Path(__file__).parent / 'utils'))
        # from queryable_db import create_session, add_event, add_session_tags, update_session_summary
        
        # # Store first user message as the conversation request
        # if user_request and session_id:
        #     # Get project information
        #     project_root = Path.cwd()
        #     project_path = str(project_root)
        #     
        #     # Extract model from input or use default
        #     model = input_data.get('model', 'claude-unknown')
        #     
        #     # Create session and first event
        #     create_session(session_id, project_path, model)
        #     
        #     # Add session start event with user request
        #     event_id = add_event(session_id, 'session_start', {
        #         'user_request': user_request,
        #         'model': model,
        #         'project_path': project_path
        #     })
        #     
        #     # Update session with user request summary
        #     summary = user_request[:100] + '...' if len(user_request) > 100 else user_request
        #     update_session_summary(session_id, summary)
        #     
        #     # Generate initial tags
        #     tags = [
        #         ('model', model),
        #     ]
        #     
        #     # Extract topics from message (simple keyword matching for now)
        #     message_lower = user_request.lower()
        #     topic_keywords = {
        #         'auth': 'authentication',
        #         'login': 'authentication', 
        #         'test': 'testing',
        #         'bug': 'bug-fix',
        #         'fix': 'bug-fix',
        #         'feature': 'feature-development',
        #         'implement': 'feature-development',
        #         'refactor': 'refactoring',
        #         'clean': 'refactoring',
        #         'doc': 'documentation',
        #         'readme': 'documentation'
        #     }
        #     
        #     for keyword, topic in topic_keywords.items():
        #         if keyword in message_lower:
        #             tags.append(('topic', topic))
        #             break
        #     
        #     add_session_tags(session_id, tags)
        
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