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

def stop_all_tts():
    """Stop all TTS playback immediately when new user input arrives (cross-platform)"""
    try:
        sys.path.append(str(Path(__file__).parent / 'utils'))
        from process_utils import stop_all_tts as _stop_tts
        _stop_tts()
    except ImportError:
        # Fallback to original macOS behavior if process_utils not available
        try:
            subprocess.run(["pkill", "-f", "say"], capture_output=True, timeout=1)
            subprocess.run(["pkill", "-f", "afplay"], capture_output=True, timeout=1)
        except Exception:
            pass
    except Exception:
        pass  # Fail silently

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

# Import centralized user-facing TTS function
sys.path.append(str(Path(__file__).parent / 'utils'))
try:
    from cycle_utils import announce_user_content
    from settings import get_setting
except ImportError:
    # Fallback if utils not available
    def announce_user_content(message, level="concise"):
        pass
    def get_setting(key, default):
        return default


def create_notification_message(user_request=None, input_data=None):
    """Create a contextual notification message for TTS."""
    try:
        # Import the rich notification functions from cycle_utils
        sys.path.append(str(Path(__file__).parent / 'utils'))
        from cycle_utils import create_concise_notification
        
        # Get transcript path for context
        transcript_path = input_data.get('transcript_path', '') if input_data else ''
        trigger_message = input_data.get('message', '') if input_data else ''
        
        # Try to create rich contextual notification
        rich_message = create_concise_notification(
            user_request, 
            trigger_message, 
            transcript_path
        )
        
        if rich_message and rich_message != "Ready to help":
            return rich_message
            
    except Exception:
        pass  # Fall back to simple messages
    
    # Fallback to varied simple messages
    
    # Get engineer name if available
    engineer_name = os.getenv('ENGINEER_NAME', '').strip()
    
    fallback_messages = [
        "Ready to help",
        "Awaiting your command", 
        "Standing by for instructions",
        "I'm here when you need me",
        "Ready for your next instruction",
        "What can I assist you with?",
        "How can I help you today?",
        "At your service"
    ]
    
    message = random.choice(fallback_messages)
    
    # Add engineer name occasionally
    if engineer_name and random.random() < 0.3:
        message = f"{engineer_name}, {message.lower()}"
    
    return message


def announce_notification(user_request=None, input_data=None):
    """Announce notification using centralized TTS system."""
    try:
        # Check interaction level settings
        interaction_level = get_setting("interaction_level", "concise")
        
        # Silent mode: no announcements
        if interaction_level == "silent":
            return
        
        # Quiet mode: only notification sounds (no TTS)
        if interaction_level == "quiet":
            try:
                from notification_sounds import play_notification_sound
                play_notification_sound()
            except ImportError:
                pass
            return
        
        # Concise and verbose modes: use centralized user-facing TTS
        message = create_notification_message(user_request, input_data)
        announce_user_content(message, level="concise")
        
    except Exception:
        # Fail silently for any errors
        pass






def get_latest_user_message_from_transcript(transcript_path):
    """Extract the most recent substantial user instruction from transcript."""
    try:
        if not os.path.exists(transcript_path):
            return None
        
        user_messages = []
        with open(transcript_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    # Look for user messages only (not tool results)
                    if (entry.get('type') == 'user' and 
                        entry.get('message', {}).get('role') == 'user' and
                        'content' in entry.get('message', {})):
                        content = entry['message']['content']
                        # Make sure it's a string, not a list
                        if isinstance(content, str):
                            user_messages.append(content)
                except json.JSONDecodeError:
                    continue
        
        # Look for the most recent substantial instruction (not just short responses)
        for msg in reversed(user_messages):
            msg_clean = msg.strip().lower()
            # Skip very short messages that are just responses
            if len(msg) > 10 and not msg_clean.startswith(('ok', 'yes', 'no', 'try again', 'good')):
                return msg
        
        # Fallback to latest message if no substantial one found
        return user_messages[-1] if user_messages else None
    except Exception:
        return None


def clean_stale_tts_locks():
    """Clean up stale TTS locks at start of new user session"""
    try:
        import os
        import time
        sys.path.append(str(Path(__file__).parent / 'utils'))
        from cycle_utils import get_tts_lock_path
        
        lock_file = get_tts_lock_path()
        
        if lock_file.exists():
            try:
                # If lock is older than 30 seconds, assume crash
                lock_age = time.time() - lock_file.stat().st_mtime
                if lock_age > 30:
                    lock_file.unlink()
            except:
                # If we can't read it, remove it
                try:
                    lock_file.unlink()
                except:
                    pass
    except Exception:
        # If cleanup fails, continue normally
        pass


def main():
    try:
        # Stop any playing TTS when new notification arrives (new user input)
        stop_all_tts()
        
        # Clean up any stale TTS locks from previous crashes
        clean_stale_tts_locks()
        
        # Parse command line arguments (for compatibility)
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
            user_request = get_latest_user_message_from_transcript(transcript_path)
        
        
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
        #     summary = truncate_user_intent(user_request, max_words=18) if user_request else user_request
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
        
        # Announce notification via centralized TTS system
        # Skip TTS for the generic "Claude is waiting for your input" message
        should_announce = input_data.get('message') != 'Claude is waiting for your input'
        
        if should_announce:
            announce_notification(user_request, input_data)
        
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)

if __name__ == '__main__':
    main()