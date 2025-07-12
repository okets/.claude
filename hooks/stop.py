#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import argparse
import json
import os
import sys
import random
import subprocess
from pathlib import Path
from datetime import datetime
import re
from typing import List, Dict, Set

# Import database utility
sys.path.append(str(Path(__file__).parent / 'utils'))
from db import get_db

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

def get_completion_messages():
    """Return list of friendly completion messages."""
    return [
        "Work complete!",
        "All done!",
        "Task finished!",
        "Job complete!",
        "Ready for next task!"
    ]

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

def get_llm_completion_message():
    """
    Generate completion message using available LLM services.
    Priority order: OpenAI > Anthropic > fallback to random message
    
    Returns:
        str: Generated or fallback completion message
    """
    # Get current script directory and construct utils/llm path
    script_dir = Path(__file__).parent
    llm_dir = script_dir / "utils" / "llm"
    
    # Try OpenAI first (highest priority)
    if os.getenv('OPENAI_API_KEY'):
        oai_script = llm_dir / "oai.py"
        if oai_script.exists():
            try:
                result = subprocess.run([
                    "uv", "run", str(oai_script), "--completion"
                ], 
                capture_output=True,
                text=True,
                timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass
    
    # Try Anthropic second
    if os.getenv('ANTHROPIC_API_KEY'):
        anth_script = llm_dir / "anth.py"
        if anth_script.exists():
            try:
                result = subprocess.run([
                    "uv", "run", str(anth_script), "--completion"
                ], 
                capture_output=True,
                text=True,
                timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass
    
    # Fallback to random predefined message
    messages = get_completion_messages()
    return random.choice(messages)

def announce_completion():
    """Announce completion using the best available TTS service."""
    try:
        tts_script = get_tts_script_path()
        if not tts_script:
            return  # No TTS scripts available
        
        # Get completion message (LLM-generated or fallback)
        completion_message = get_llm_completion_message()
        
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

def get_project_claude_dir():
    """Find or create .claude directory in current project"""
    cwd = Path.cwd()
    
    # Look for git root to determine project boundary
    current = cwd
    git_root = None
    while current != current.parent:
        if (current / '.git').exists():
            git_root = current
            break
        current = current.parent
    
    # Use git root or current directory
    project_root = git_root if git_root else cwd
    project_claude = project_root / '.claude'
    project_claude.mkdir(exist_ok=True)
    return project_claude

def extract_lessons_learned(tool_executions: List[Dict], accomplishments: str, files_mentioned: List[str]) -> List[str]:
    """Extract lessons learned from the session"""
    lessons = []
    
    # Check for test failures and fixes
    test_failures = sum(1 for exec in tool_executions if exec['intent'] == 'running-tests' and not exec.get('success', True))
    test_successes = sum(1 for exec in tool_executions if exec['intent'] == 'running-tests' and exec.get('success', True))
    
    if test_failures > 0 and test_successes > test_failures:
        lessons.append("Fixed failing tests through iterative debugging")
    
    # Check for multiple modifications to same file
    file_edit_counts = {}
    for exec in tool_executions:
        if exec['intent'] == 'modifying-file' and exec['files_touched']:
            try:
                files = json.loads(exec['files_touched']) if isinstance(exec['files_touched'], str) else exec['files_touched']
                for file in files:
                    file_name = Path(file).name
                    file_edit_counts[file_name] = file_edit_counts.get(file_name, 0) + 1
            except:
                pass
    
    for file, count in file_edit_counts.items():
        if count > 3:
            lessons.append(f"Required multiple iterations ({count}) to get {file} working correctly")
    
    # Check for git operations
    git_ops = [exec for exec in tool_executions if exec['intent'] == 'git-operation']
    if git_ops:
        lessons.append(f"Used {len(git_ops)} git operations to manage version control")
    
    # Check for search patterns
    search_count = sum(1 for exec in tool_executions if exec['intent'] in ['searching-code', 'finding-files'])
    if search_count > 5:
        lessons.append(f"Required extensive searching ({search_count} searches) to understand codebase")
    
    # Generic accomplishment-based lessons
    if accomplishments:
        if 'bug' in accomplishments.lower() or 'fix' in accomplishments.lower():
            lessons.append("Successfully identified and resolved issues in the codebase")
        if 'refactor' in accomplishments.lower():
            lessons.append("Improved code structure through refactoring")
        if 'implement' in accomplishments.lower() or 'add' in accomplishments.lower():
            lessons.append("Added new functionality to the system")
    
    return lessons

def analyze_session_for_summary(chat_session_id: str, project_id: int, db) -> Dict:
    """Analyze the session's tool executions to generate intelligent summary"""
    if not db.connection:
        return {}
    
    try:
        cursor = db.connection.cursor()
        
        # Get all tool executions for this session
        cursor.execute("""
            SELECT tool_name, intent, files_touched, tool_input, success, executed_at
            FROM tool_executions
            WHERE chat_session_id = ?
            ORDER BY executed_at
        """, (chat_session_id,))
        
        executions = [dict(row) for row in cursor.fetchall()]
        
        if not executions:
            return {}
        
        # Extract insights
        files_mentioned = set()
        intents = []
        accomplishments = []
        topics = set()
        
        for exec in executions:
            # Collect files
            if exec['files_touched']:
                try:
                    files = json.loads(exec['files_touched'])
                    files_mentioned.update([Path(f).name for f in files])
                except:
                    pass
            
            # Collect intents
            if exec['intent']:
                intents.append(exec['intent'])
            
            # Extract topics from tool inputs
            if exec['tool_input']:
                try:
                    tool_input = json.loads(exec['tool_input']) if isinstance(exec['tool_input'], str) else exec['tool_input']
                    
                    # Extract from commands
                    if 'command' in tool_input:
                        cmd = tool_input['command']
                        if 'git' in cmd:
                            topics.add('version-control')
                        if any(word in cmd for word in ['test', 'pytest', 'npm test']):
                            topics.add('testing')
                        if any(word in cmd for word in ['build', 'compile', 'webpack']):
                            topics.add('build-process')
                        if 'npm' in cmd or 'yarn' in cmd:
                            topics.add('package-management')
                    
                    # Extract from file operations
                    if 'file_path' in tool_input:
                        file_path = tool_input['file_path']
                        if any(ext in file_path for ext in ['.js', '.ts', '.jsx', '.tsx']):
                            topics.add('javascript-development')
                        if any(ext in file_path for ext in ['.py']):
                            topics.add('python-development')
                        if any(name in file_path for name in ['auth', 'login', 'user']):
                            topics.add('authentication')
                        if any(name in file_path for name in ['api', 'endpoint', 'route']):
                            topics.add('api-development')
                        if any(name in file_path for name in ['component', 'ui', 'view']):
                            topics.add('ui-development')
                    
                except:
                    pass
        
        # Generate accomplishments based on successful operations
        intent_counts = {}
        for intent in intents:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        if intent_counts.get('modifying-file', 0) > 0:
            accomplishments.append(f"Modified {intent_counts['modifying-file']} files")
        if intent_counts.get('git-operation', 0) > 0:
            accomplishments.append(f"Performed {intent_counts['git-operation']} git operations")
        if intent_counts.get('running-tests', 0) > 0:
            accomplishments.append(f"Ran tests {intent_counts['running-tests']} times")
        
        # Extract phase/task context from current database
        phase_tags = set()
        task_tags = set()
        
        # Get active phases and tasks for context
        cursor.execute("""
            SELECT ph.name as phase_name, t.name as task_name
            FROM tasks t
            JOIN phases ph ON t.phase_id = ph.id
            WHERE ph.project_id = ? AND t.status IN ('in_progress', 'todo')
        """, (project_id,))
        
        active_work = cursor.fetchall()
        for work in active_work:
            if work['phase_name']:
                phase_tags.add(work['phase_name'])
            if work['task_name']:
                task_tags.add(work['task_name'])
        
        return {
            'files_mentioned': list(files_mentioned),
            'key_topics': list(topics),
            'phase_tags': list(phase_tags),
            'task_tags': list(task_tags),
            'accomplishments': ', '.join(accomplishments) if accomplishments else None,
            'intent_summary': intent_counts,
            'executions': executions  # Return raw executions for lessons learned extraction
        }
        
    except Exception as e:
        print(f"Error analyzing session: {e}", file=sys.stderr)
        return {}

def generate_summary_from_analysis(analysis: Dict) -> str:
    """Generate a human-readable summary from the analysis"""
    parts = []
    
    if analysis.get('accomplishments'):
        parts.append(f"Accomplished: {analysis['accomplishments']}")
    
    if analysis.get('files_mentioned'):
        files = analysis['files_mentioned'][:5]  # Top 5 files
        parts.append(f"Worked with files: {', '.join(files)}")
    
    if analysis.get('key_topics'):
        topics = list(analysis['key_topics'])[:3]  # Top 3 topics
        parts.append(f"Focus areas: {', '.join(topics)}")
    
    if analysis.get('phase_tags'):
        phases = list(analysis['phase_tags'])[:2]  # Max 2 phases
        parts.append(f"Related to phases: {', '.join(phases)}")
    
    return '. '.join(parts) if parts else "Session completed with tool executions"

def main():
    try:
        # Debug logging to understand the issue
        with open('/tmp/stop_hook_debug.log', 'a') as f:
            f.write(f"\n{datetime.now()}: stop.py called with args: {sys.argv}\n")
            f.write(f"Working directory: {os.getcwd()}\n")
        
        # Parse command line arguments
        parser = argparse.ArgumentParser()
        # Add --chat argument to prevent error (but ignore it)
        parser.add_argument('--chat', action='store_true', help='Deprecated flag - ignored')
        args = parser.parse_args()
        
        if args.chat:
            print("Warning: --chat flag is deprecated and will be ignored", file=sys.stderr)
        
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)
        
        # Debug: Log input data to understand structure
        debug_log = Path(__file__).parent.parent / 'debug_stop.json'
        with open(debug_log, 'w') as f:
            json.dump(input_data, f, indent=2)

        # Extract required fields
        session_id = input_data.get("session_id", "")
        stop_hook_active = input_data.get("stop_hook_active", False)
        
        # Try to get model info from input
        model_info = input_data.get("model", input_data.get("agent_model", "unknown"))

        # Get database connection and project info
        db = get_db()
        project_claude = get_project_claude_dir()
        project_root = str(project_claude.parent)
        project_name = Path(project_root).name
        
        # Ensure project exists in database
        project_id = db.ensure_project(project_root, project_name)
        
        if db.connection and project_id and session_id:
            # Analyze the session for intelligent summary
            analysis = analyze_session_for_summary(session_id, project_id, db)
            
            if analysis:
                # Generate summary
                summary = generate_summary_from_analysis(analysis)
                
                # Extract lessons learned
                lessons_learned = extract_lessons_learned(
                    analysis.get('executions', []),
                    analysis.get('accomplishments', ''),
                    analysis.get('files_mentioned', [])
                )
                
                # Save conversation summary (existing table)
                success = db.save_conversation_summary(
                    chat_session_id=session_id,
                    project_id=project_id,
                    summary=summary,
                    key_topics=analysis.get('key_topics'),
                    files_mentioned=analysis.get('files_mentioned'),
                    phase_tags=analysis.get('phase_tags'),
                    task_tags=analysis.get('task_tags'),
                    assignment_tags=None,  # Could be enhanced later
                    accomplishments=analysis.get('accomplishments'),
                    next_steps=None  # Could be inferred from incomplete tasks
                )
                
                if success:
                    print(f"📝 Session summary saved: {summary}", file=sys.stderr)
                
                # Update conversation details with final summary and lessons
                existing_details = db.get_conversation_details(session_id)
                if existing_details:
                    # Calculate session duration
                    start_time = existing_details.get('created_at')
                    duration_seconds = None
                    if start_time:
                        try:
                            from datetime import datetime
                            start_dt = datetime.fromisoformat(start_time.replace(' ', 'T'))
                            duration_seconds = int((datetime.now() - start_dt).total_seconds())
                        except:
                            pass
                    
                    # Update with final summary and lessons learned
                    cursor = db.connection.cursor()
                    cursor.execute("""
                        UPDATE conversation_details 
                        SET agent_summary = ?, lessons_learned = ?, duration_seconds = ?, agent_model = ?
                        WHERE chat_session_id = ?
                    """, (
                        summary,
                        json.dumps(lessons_learned) if lessons_learned else None,
                        duration_seconds,
                        model_info,
                        session_id
                    ))
                    db.connection.commit()
                    
                    if lessons_learned:
                        print(f"💡 Lessons learned: {', '.join(lessons_learned[:2])}", file=sys.stderr)

        # Session data is now stored in the database via conversation_summaries
        # The old JSON logging is obsolete

        # Announce completion via TTS
        announce_completion()

        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)

if __name__ == "__main__":
    main()