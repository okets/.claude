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
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

# Import our cycle utilities
sys.path.append(str(Path(__file__).parent / 'utils'))
try:
    from cycle_utils import dump_hook_data
except ImportError:
    # Fallback if utils not available
    def dump_hook_data(hook_name, hook_data, session_id, transcript_path):
        pass


def get_tts_script_path():
    """
    Determine which TTS script to use based on user settings.
    Priority order: user preference > macos > pyttsx3
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
    
    # Fallback chain: coqui-female > macos-female > macos-male > macos > pyttsx3
    fallback_order = ["coqui-female", "macos-female", "macos-male", "macos", "pyttsx3"]
    for engine in fallback_order:
        if engine != preferred_engine:  # Skip already tried preference
            script_path = engines[engine]
            if script_path.exists():
                return str(script_path)
    
    return None


def create_manager_style_message(subagent_task, subagent_summary, interaction_level):
    """Create varied manager-style messages about subagent work."""
    import random
    
    # Extract key info from task/summary
    task_snippet = (subagent_task[:50] + "...") if len(subagent_task) > 50 else subagent_task
    
    if interaction_level == "concise":
        concise_messages = [
            f"My agent handled {task_snippet}",
            f"Subagent completed {task_snippet}",
            f"Agent finished the work",
            f"Delegation successful",
            f"My helper got it done",
            f"Agent reported back",
            # Funny options (15%)
            f"My unpaid intern delivered",
            f"Bot completed slave labor"
        ]
        return random.choice(concise_messages)
    
    elif interaction_level == "verbose":
        verbose_messages = [
            f"I sent a subagent to handle {task_snippet} and they delivered excellent results",
            f"My subagent did some digging on {task_snippet} and came back with solid findings",
            f"Dispatched a specialist agent for {task_snippet} - mission accomplished",
            f"My agent team completed {task_snippet} with great success",
            f"Delegated {task_snippet} to a subagent who executed it perfectly",
            f"My helper agent wrapped up {task_snippet} beautifully",
            f"Sent out an agent for {task_snippet} and they knocked it out of the park",
            f"My specialist completed {task_snippet} with impressive efficiency",
            f"Agent deployment successful - {task_snippet} handled with expertise",
            f"My subagent tackled {task_snippet} and delivered outstanding work",
            f"Coordination complete - agent finished {task_snippet} flawlessly",
            f"My field agent completed {task_snippet} and filed their report",
            # Funny options (15%)
            f"Sent my digital minion to do {task_snippet} - they work for free and never complain",
            f"My robot employee finished {task_snippet} without asking for benefits or vacation time",
            f"Deployed a bot to handle {task_snippet} - no HR complaints, perfect attendance record"
        ]
        return random.choice(verbose_messages)
    
    else:  # Default fallback
        return "Subagent work complete"

def announce_subagent_completion(subagent_task="work", subagent_summary=""):
    """Announce subagent completion using the best available TTS service (controlled by interaction_level)."""
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
                # Play subtle completion sound instead of TTS
                try:
                    sys.path.append(str(Path(__file__).parent / 'utils'))
                    from notification_sounds import play_subagent_completion_sound
                    play_subagent_completion_sound()
                except ImportError:
                    pass  # Fall back to no sound if utility not available
                return
            
        except ImportError:
            # Settings not available, default to announce
            interaction_level = "concise"
        
        tts_script = get_tts_script_path()
        if not tts_script:
            return  # No TTS scripts available
        
        # Create manager-style message
        completion_message = create_manager_style_message(subagent_task, subagent_summary, interaction_level)
        
        # Call the TTS script with the completion message
        subprocess.run([
            "uv", "run", tts_script, completion_message
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


def generate_subagent_contextual_data(session_id, transcript_path, input_data):
    """Generate contextual data file for subagent session using logic from stop.py"""
    try:
        # Call the stop.py script to generate contextual data
        # We'll pass the same input data to stop.py and let it handle subagent detection
        stop_script = Path(__file__).parent / "stop.py"
        
        if stop_script.exists():
            # Run stop.py with the same input data
            result = subprocess.run([
                "uv", "run", str(stop_script)
            ], 
            input=json.dumps(input_data),
            text=True,
            capture_output=True,
            timeout=30
            )
            
            # Log the result for debugging
            with open('/tmp/subagent_contextual_debug.log', 'a') as f:
                f.write(f"\n{datetime.now()}: Subagent contextual data generation completed\n")
                f.write(f"Return code: {result.returncode}\n")
                if result.stderr:
                    f.write(f"Stderr: {result.stderr}\n")
                    
    except Exception as e:
        # Log errors but don't fail
        with open('/tmp/subagent_contextual_debug.log', 'a') as f:
            f.write(f"\n{datetime.now()}: Error generating subagent contextual data: {str(e)}\n")


def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser()
        args = parser.parse_args()
        
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)
        
        # Dump raw hook data for analysis
        session_id = input_data.get('session_id', '')
        transcript_path = input_data.get('transcript_path', '')
        dump_hook_data('SubagentStop', input_data, session_id, transcript_path)
        
        # First, generate contextual data for subagent session by calling stop.py logic
        try:
            # Import the contextual analysis logic from stop.py
            sys.path.append(str(Path(__file__).parent))
            
            # We'll run a simplified version of the stop.py analysis here
            # since we need to capture subagent work before DB operations
            session_id = input_data.get("session_id", "")
            transcript_path = input_data.get("transcript_path", "")
            
            if session_id and transcript_path:
                # Generate subagent contextual data file
                generate_subagent_contextual_data(session_id, transcript_path, input_data)
                
        except Exception as e:
            # Don't let contextual logging failures break the main hook
            with open('/tmp/subagent_stop_debug.log', 'a') as f:
                f.write(f"\n{datetime.now()}: Contextual logging error: {str(e)}\n")

        # Extract required fields
        session_id = input_data.get("session_id", "")
        stop_hook_active = input_data.get("stop_hook_active", False)
        
        # Import database utility
        sys.path.append(str(Path(__file__).parent / 'utils'))
        from db import get_db
        
        # Get database connection
        db = get_db()
        
        # Get project information
        project_root = Path.cwd()
        while project_root != project_root.parent:
            if (project_root / '.git').exists():
                break
            project_root = project_root.parent
        
        project_id = db.ensure_project(str(project_root), project_root.name)
        
        if project_id and db.connection and session_id:
            # Get the parent conversation details
            parent_details = db.get_conversation_details(session_id)
            
            if parent_details:
                # Extract subagent information from input_data
                subagent_model = input_data.get('model', 'unknown')
                subagent_task = input_data.get('task', 'Unknown task')
                subagent_summary = input_data.get('summary', '')
                duration_ms = input_data.get('duration_ms', 0)
                tool_count = input_data.get('tool_count', 0)
                
                # Save subagent execution
                db.save_subagent_execution(
                    chat_session_id=session_id,
                    parent_conversation_id=parent_details.get('id'),
                    subagent_model=subagent_model,
                    subagent_task=subagent_task,
                    subagent_response_summary=subagent_summary,
                    duration_ms=duration_ms,
                    success=True,
                    tool_count=tool_count
                )
                
                # Update parent conversation's subagents_used field
                subagents_used = parent_details.get('subagents_used', [])
                subagents_used.append({
                    'model': subagent_model,
                    'task': subagent_task,
                    'response_summary': subagent_summary,
                    'duration_ms': duration_ms
                })
                
                cursor = db.connection.cursor()
                cursor.execute("""
                    UPDATE conversation_details 
                    SET subagents_used = ?
                    WHERE chat_session_id = ?
                """, (
                    json.dumps(subagents_used),
                    session_id
                ))
                db.connection.commit()

        # Announce subagent completion via TTS with actual task data
        subagent_task = input_data.get('task', 'work')
        subagent_summary = input_data.get('summary', '')
        announce_subagent_completion(subagent_task, subagent_summary)

        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)


if __name__ == "__main__":
    main()