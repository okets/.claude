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
    """Stop all TTS playback immediately when new user input arrives"""
    try:
        # Kill macOS 'say' processes
        subprocess.run(["pkill", "-f", "say"], capture_output=True, timeout=1)
        # Kill any afplay processes (audio playback)
        subprocess.run(["pkill", "-f", "afplay"], capture_output=True, timeout=1)
    except Exception:
        pass  # Fail silently

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional


def get_tts_script_path():
    """
    Determine which TTS script to use based on user settings.
    Priority order: user preference > coqui > macos > pyttsx3
    """
    # Get current script directory and construct utils/tts path
    script_dir = Path(__file__).parent
    tts_dir = script_dir / "utils" / "tts"
    
    # Get user's preferred TTS engine from settings
    try:
        sys.path.append(str(script_dir / 'utils'))
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


def announce_notification(user_request=None, input_data=None):
    """Announce that the agent needs user input (controlled by interaction_level)."""
    try:
        # Check interaction level settings
        try:
            sys.path.append(str(Path(__file__).parent / 'utils'))
            from settings import get_setting
            
            interaction_level = get_setting("interaction_level", "concise")
            
            # Silent mode: no announcements
            if interaction_level == "silent":
                return
            
            # Quiet mode: only notification sounds (beep/chime), no verbal announcements
            if interaction_level == "quiet":
                # Play subtle notification sound instead of TTS
                try:
                    sys.path.append(str(Path(__file__).parent / 'utils'))
                    from notification_sounds import play_notification_sound
                    play_notification_sound()
                except ImportError:
                    pass  # Fall back to no sound if utility not available
                return
            
            # Concise and verbose modes: verbal announcements
            # (concise and verbose both announce notifications)
            
        except ImportError:
            # Settings not available, default to announce
            pass
        
        tts_script = get_tts_script_path()
        if not tts_script:
            return  # No TTS scripts available
        
        # Get engineer name if available
        engineer_name = os.getenv('ENGINEER_NAME', '').strip()
        
        # Create notification message based on interaction level
        try:
            sys.path.append(str(Path(__file__).parent / 'utils'))
            from settings import get_setting
            from cycle_utils import create_concise_notification
            
            interaction_level = get_setting("interaction_level", "concise")
            
            if interaction_level == "concise":
                # Use enhanced concise, contextual notification with todo context
                try:
                    from cycle_utils import create_concise_notification
                    
                    # Get transcript path for todo context
                    transcript_path = input_data.get('transcript_path', '')
                    
                    notification_message = create_concise_notification(
                        user_request, 
                        input_data.get('message', ''), 
                        transcript_path
                    )
                        
                except Exception as e:
                    # Fallback to simple message
                    notification_message = "Ready to help"
                
                # Add engineer name occasionally for concise mode
                if engineer_name and random.random() < 0.2:
                    notification_message = f"{engineer_name}, {notification_message.lower()}"
                    
            else:
                # Verbose mode: use enhanced notifications with todo context first, then fallback
                try:
                    from cycle_utils import create_concise_notification, create_verbose_notification, get_recent_work_context, get_current_cycle_id
                    
                    # Get transcript path for todo context
                    transcript_path = input_data.get('transcript_path', '')
                    
                    # Try enhanced notification first (same as concise but with verbose context)
                    notification_message = create_concise_notification(
                        user_request, 
                        input_data.get('message', ''), 
                        transcript_path
                    )
                    
                    # If that didn't work, try the original verbose approach
                    if not notification_message or notification_message == "Ready to help":
                        # Get recent work context for enhanced verbose notifications
                        session_id = input_data.get('session_id', '')
                        current_cycle_id = get_current_cycle_id(session_id, transcript_path)
                        recent_work_context = get_recent_work_context(session_id, current_cycle_id, lookback_cycles=3)
                        
                        # Create verbose notification with full context
                        notification_message = create_verbose_notification(
                            user_request, 
                            input_data.get('message', ''),
                            recent_work_context
                        )
                    
                    # Add engineer name occasionally for verbose mode
                    if engineer_name and random.random() < 0.3:
                        notification_message = f"{engineer_name}, " + notification_message.lower()
                        
                except Exception as e:
                    # Fallback to simple verbose message
                    if user_request:
                        # Extract context using semantic truncation
                        from cycle_utils import truncate_for_speech
                        context = truncate_for_speech(user_request, 40)
                        if engineer_name and random.random() < 0.3:
                            notification_message = f"{engineer_name}, ready to help with: {context}"
                        else:
                            notification_message = f"Ready to help with: {context}"
                    else:
                        # Simple fallback messages for verbose mode
                        verbose_fallbacks = [
                            "Ready to help with your next task",
                            "Standing by for instructions", 
                            "I'm here and ready to assist",
                            "Awaiting your next request",
                            "At your service, captain!",
                            "Ready to rock and roll!"
                        ]
                        
                        base_message = random.choice(verbose_fallbacks)
                        
                        if engineer_name and random.random() < 0.3:
                            notification_message = f"{engineer_name}, {base_message.lower()}"
                        else:
                            notification_message = base_message
                        
        except ImportError:
            # Fallback if concise utilities not available - use varied messages
            fallback_messages = [
                "I need your input please",
                "Your input is needed",
                "Waiting for your guidance", 
                "Ready for your next instruction",
                "I'm here when you need me",
                "What would you like me to do next?",
                "Awaiting your command",
                "Ready to help with your next task",
                "I'm listening for your next request",
                "What can I assist you with?",
                "Standing by for instructions",
                "Ready when you are",
                "How can I help you today?",
                "Waiting for your next move",
                "At your service",
                "Ready to rumble!",
                "What's cooking?",
                "Let's do this thing!"
            ]
            
            base_message = random.choice(fallback_messages)
            
            if engineer_name and random.random() < 0.3:
                notification_message = f"{engineer_name}, {base_message.lower()}"
            else:
                notification_message = base_message
        
        # Debug: Log TTS attempt
        with open('/tmp/notification_debug.log', 'a') as f:
            f.write(f"TTS: Calling script {tts_script} with message: {notification_message}\n")
        
        # Call the TTS script with the notification message
        result = subprocess.run([
            "uv", "run", tts_script, notification_message
        ], 
        capture_output=True,  # Capture to log any errors
        timeout=10,  # 10-second timeout
        text=True
        )
        
        # Debug: Log result
        with open('/tmp/notification_debug.log', 'a') as f:
            f.write(f"TTS Result: exit_code={result.returncode}, stdout={result.stdout}, stderr={result.stderr}\n")
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fail silently if TTS encounters issues
        pass
    except Exception:
        # Fail silently for any other errors
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


def main():
    try:
        # Stop any playing TTS when new notification arrives (new user input)
        stop_all_tts()
        
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
            user_request = get_latest_user_message_from_transcript(transcript_path)
        
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