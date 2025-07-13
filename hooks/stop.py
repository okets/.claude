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

# Import our cycle utilities
sys.path.append(str(Path(__file__).parent / 'utils'))
try:
    from cycle_utils import dump_hook_data, get_current_cycle_id, announce_tts
    from hook_parser import generate_contextual_summary
except ImportError:
    # Fallback if utils not available
    def dump_hook_data(hook_name, hook_data, session_id, transcript_path):
        pass
    def get_current_cycle_id(session_id, transcript_path):
        return 1
    def generate_contextual_summary(session_id, cycle_id, output_dir=None):
        return {"error": "Hook parser not available"}
    def announce_tts(message):
        pass

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
        
        # Dump raw hook data for analysis
        session_id = input_data.get('session_id', '')
        transcript_path = input_data.get('transcript_path', '')
        dump_hook_data('Stop', input_data, session_id, transcript_path)
        
        # Smart detection: Is this a subagent completion or final cycle completion?
        def should_generate_final_summary(hook_data):
            """Determine if this Stop hook should generate final contextual summary"""
            hook_event_name = hook_data.get("hook_event_name", "")
            
            # If this Stop hook has event_name "SubagentStop", it's a subagent completion
            if hook_event_name == "SubagentStop":
                announce_tts("Stop detected from a subagent")
                with open('/tmp/stop_hook_debug.log', 'a') as f:
                    f.write(f"\n{datetime.now()}: Stop hook triggered by SubagentStop - skipping final summary\n")
                return False
            
            # If this Stop hook has event_name "Stop", it's the final cycle completion
            if hook_event_name == "Stop":
                announce_tts("Stop detected from Main Agent")
                with open('/tmp/stop_hook_debug.log', 'a') as f:
                    f.write(f"\n{datetime.now()}: Stop hook triggered by cycle completion - generating final summary\n")
                return True
            
            # Fallback: if event name is unclear, default to generating summary
            announce_tts("Stop detected with unclear source")
            with open('/tmp/stop_hook_debug.log', 'a') as f:
                f.write(f"\n{datetime.now()}: Stop hook with unclear event '{hook_event_name}' - defaulting to summary generation\n")
            return True
        
        # Check if we should generate the final summary
        if not should_generate_final_summary(input_data):
            # This is just a subagent completion, exit early
            sys.exit(0)
        
        # Debug: Log input data to understand structure
        debug_log = Path('/tmp') / 'claude_debug_stop.json'
        with open(debug_log, 'w') as f:
            json.dump(input_data, f, indent=2)
        
        # Phase 1: Capture current RequestCycle data by parsing transcript
        def analyze_request_cycle(user_request, tools_used, responses):
            """Analyze RequestCycle data to create organized summary for DB schema"""
            
            # Extract contextual information from responses
            def extract_context_for_tools(tools_used, responses):
                """Extract WHY context for each tool from surrounding assistant responses"""
                tool_contexts = {}
                
                for tool in tools_used:
                    tool_line = tool.get('line', 0)
                    tool_name = tool.get('tool_name', '')
                    
                    # Progressive context window: try 3 lines first, then 5, then 7
                    # This prevents bleeding into unrelated context while ensuring we find meaningful context
                    preceding_context = []
                    for window_size in [3, 5, 7]:
                        preceding_context = []
                        for response in responses:
                            response_line = response.get('line', 0)
                            if response_line < tool_line and (tool_line - response_line) <= window_size:
                                # Handle different content structures
                                content_list = response.get('content', [])
                                if isinstance(content_list, list):
                                    for content in content_list:
                                        if isinstance(content, dict):
                                            # Regular text content
                                            if content.get('type') == 'text':
                                                text = content.get('text', '').strip()
                                                if text and len(text) > 15:  # Only meaningful text
                                                    preceding_context.append(text)
                                            # Thinking content (also valuable context)
                                            elif content.get('type') == 'thinking':
                                                thinking = content.get('thinking', '').strip()
                                                if thinking and len(thinking) > 50:  # Longer threshold for thinking
                                                    # Extract first meaningful sentence from thinking
                                                    first_sentence = thinking.split('.')[0].strip()
                                                    if len(first_sentence) > 20:
                                                        preceding_context.append(first_sentence)
                        
                        # If we found meaningful context, stop expanding
                        if preceding_context:
                            break
                    
                    # Store context for this tool
                    if preceding_context:
                        # Use the most meaningful context (longest non-empty one)
                        best_context = max(preceding_context, key=len)
                        tool_contexts[f"{tool_name}_{tool_line}"] = {
                            'context': best_context,
                            'all_context': preceding_context,
                            'window_used': window_size  # Track which window size worked
                        }
                
                return tool_contexts
            
            # Get contextual explanations
            tool_contexts = extract_context_for_tools(tools_used, responses)
            
            # Extract file activities with enhanced context tracking
            file_activities = {}
            subagent_tasks = {}
            total_edits_in_cycle = 0
            
            # First pass: collect all file operations by agent
            for tool in tools_used:
                tool_line = tool.get('line', 0)
                tool_key = f"{tool['tool_name']}_{tool_line}"
                context_info = tool_contexts.get(tool_key, {})
                
                if tool['tool_name'] in ['Edit', 'Write', 'MultiEdit']:
                    file_path = tool['input'].get('file_path', '')
                    if file_path:
                        # Determine agent type
                        agent_type = 'subagent' if any(t['tool_name'] == 'Task' and t['line'] < tool_line for t in tools_used) else 'main_agent'
                        
                        # Initialize file structure
                        if file_path not in file_activities:
                            file_activities[file_path] = {}
                        
                        if agent_type not in file_activities[file_path]:
                            file_activities[file_path][agent_type] = {
                                'operations': [],
                                'edit_count': 0,
                                'contexts': [],
                                'timestamps': []
                            }
                        
                        # Track operation details
                        operation_type = tool['tool_name'].lower()
                        file_activities[file_path][agent_type]['operations'].append(operation_type)
                        file_activities[file_path][agent_type]['edit_count'] += 1
                        file_activities[file_path][agent_type]['contexts'].append(context_info.get('context', 'No context available'))
                        file_activities[file_path][agent_type]['timestamps'].append(tool['timestamp'])
                        
                        total_edits_in_cycle += 1
                
                elif tool['tool_name'] == 'Task':
                    subagent_tasks[tool_line] = {
                        'delegation_info': {
                            'description': tool['input'].get('description', ''),
                            'prompt': tool['input'].get('prompt', ''),
                            'context': context_info.get('context', 'Subagent delegation'),
                            'timestamp': tool['timestamp']
                        },
                        'work_summary': {
                            'files_modified': [],
                            'edit_count': 0,
                            'accomplishments': '',
                            'completion_status': 'pending'
                        }
                    }
            
            # Second pass: generate summaries for each file+agent combination
            final_file_activities = {}
            for file_path, agents in file_activities.items():
                final_file_activities[file_path] = {}
                for agent_type, data in agents.items():
                    # Generate reason summary from contexts
                    contexts = [ctx for ctx in data['contexts'] if ctx != 'No context available']
                    if contexts:
                        # Use the most meaningful context (longest non-empty one)
                        reason = max(contexts, key=len)
                    else:
                        reason = f"File modifications via {agent_type}"
                    
                    # Clean up operations list
                    unique_operations = list(set(data['operations']))
                    
                    final_file_activities[file_path][agent_type] = {
                        'reason': reason,
                        'edit_count': data['edit_count'],
                        'operations': unique_operations,
                        'first_edit_timestamp': min(data['timestamps']) if data['timestamps'] else None,
                        'last_edit_timestamp': max(data['timestamps']) if data['timestamps'] else None
                    }
            
            # Third pass: populate subagent work summaries by analyzing what each subagent accomplished
            def populate_subagent_work_summaries(subagent_tasks, tools_used, file_activities):
                """Extract and summarize what each subagent actually accomplished"""
                
                # Create mapping of subagent delegation line -> tools used by that subagent
                for task_line, task_data in subagent_tasks.items():
                    subagent_start_line = task_line
                    
                    # Find the next subagent delegation or end of conversation to determine subagent scope
                    next_task_line = min([line for line in subagent_tasks.keys() if line > task_line], 
                                       default=float('inf'))
                    
                    # Find all tools used by this subagent (between this Task and next Task)
                    subagent_tools = [
                        tool for tool in tools_used 
                        if subagent_start_line < tool.get('line', 0) < next_task_line
                        and tool['tool_name'] in ['Edit', 'Write', 'MultiEdit', 'Read', 'Glob', 'Grep']
                    ]
                    
                    # Extract files modified by this subagent
                    files_modified = []
                    edit_count = 0
                    accomplishments = []
                    
                    for tool in subagent_tools:
                        if tool['tool_name'] in ['Edit', 'Write', 'MultiEdit']:
                            file_path = tool['input'].get('file_path', '')
                            if file_path and file_path not in files_modified:
                                files_modified.append(file_path)
                            edit_count += 1
                        
                        # Extract accomplishments from tool contexts
                        tool_key = f"{tool['tool_name']}_{tool.get('line', 0)}"
                        if tool_key in tool_contexts:
                            context = tool_contexts[tool_key]['context']
                            if context and len(context) > 20:
                                accomplishments.append(context)
                    
                    # Generate accomplishments summary
                    if accomplishments:
                        # Use the most comprehensive accomplishment description
                        main_accomplishment = max(accomplishments, key=len)
                    else:
                        main_accomplishment = task_data['delegation_info']['description']
                    
                    # Determine completion status based on tools used
                    if subagent_tools:
                        completion_status = 'completed' if edit_count > 0 else 'researched'
                    else:
                        completion_status = 'no_activity'
                    
                    # Update work summary
                    task_data['work_summary'] = {
                        'files_modified': files_modified,
                        'edit_count': edit_count,
                        'accomplishments': main_accomplishment,
                        'completion_status': completion_status,
                        'tools_used_count': len(subagent_tools)
                    }
                
                return subagent_tasks
            
            # Populate subagent work summaries
            subagent_tasks = populate_subagent_work_summaries(subagent_tasks, tools_used, final_file_activities)
            
            # Detect agent types
            subagent_involved = any(tool['tool_name'] == 'Task' for tool in tools_used)
            
            # Extract purpose/intent from user request
            user_content = user_request.get('content', '')
            
            # Categorize tools by function
            tool_categories = {
                'file_operations': [t for t in tools_used if t['tool_name'] in ['Edit', 'Write', 'Read']],
                'search_operations': [t for t in tools_used if t['tool_name'] in ['Glob', 'Grep']],
                'subagent_delegation': [t for t in tools_used if t['tool_name'] == 'Task'],
                'other_operations': [t for t in tools_used if t['tool_name'] not in ['Edit', 'Write', 'Read', 'Glob', 'Grep', 'Task']]
            }
            
            return {
                "user_intent": user_content,
                "total_edits_in_cycle": total_edits_in_cycle,
                "file_activities": final_file_activities,
                "subagent_tasks": subagent_tasks,
                "agents_involved": {
                    "main_agent": True,
                    "subagents": subagent_involved,
                    "subagent_count": len(tool_categories['subagent_delegation'])
                },
                "tool_categories": tool_categories,
                "summary": {
                    "files_modified": list(final_file_activities.keys()),
                    "total_file_changes": total_edits_in_cycle,
                    "involved_subagents": subagent_involved,
                    "primary_activity": determine_primary_activity(tool_categories, user_content)
                },
                "contextual_insights": {
                    "file_change_reasons": extract_file_change_reasons_v2(final_file_activities),
                    "subagent_purposes": [
                        {
                            "delegation": task['delegation_info']['description'],
                            "accomplishments": task['work_summary']['accomplishments'],
                            "files_modified": task['work_summary']['files_modified'],
                            "edit_count": task['work_summary']['edit_count'],
                            "completion_status": task['work_summary']['completion_status']
                        } for task in subagent_tasks.values()
                    ],
                    "overall_workflow": generate_workflow_summary_v2(user_content, final_file_activities, subagent_tasks)
                }
            }
        
        def extract_file_change_reasons_v2(file_activities):
            """Extract reasons for each file change using new structure"""
            reasons = {}
            for file_path, agents in file_activities.items():
                file_reasons = []
                for agent_type, activity in agents.items():
                    file_reasons.append({
                        'agent': agent_type,
                        'reason': activity['reason'],
                        'edit_count': activity['edit_count'],
                        'operations': activity['operations']
                    })
                reasons[file_path] = file_reasons
            return reasons
        
        def generate_workflow_summary_v2(user_intent, file_activities, subagent_tasks):
            """Generate a high-level workflow summary using new structure"""
            workflow_steps = []
            
            # User initiated the request
            workflow_steps.append(f"User requested: {user_intent[:100]}...")
            
            # Subagent tasks with work summaries
            for task in subagent_tasks.values():
                delegation = task['delegation_info']['description']
                work_summary = task['work_summary']
                
                if work_summary['completion_status'] == 'completed':
                    workflow_steps.append(f"Delegated to subagent: {delegation} → Completed {work_summary['edit_count']} edits to {len(work_summary['files_modified'])} files")
                elif work_summary['completion_status'] == 'researched':
                    workflow_steps.append(f"Delegated to subagent: {delegation} → Researched with {work_summary['tools_used_count']} tools")
                else:
                    workflow_steps.append(f"Delegated to subagent: {delegation} → {work_summary['completion_status']}")
            
            # File activities summary
            for file_path, agents in file_activities.items():
                file_name = file_path.split('/')[-1]
                agent_summaries = []
                for agent_type, activity in agents.items():
                    agent_summaries.append(f"{agent_type} ({activity['edit_count']} edits)")
                workflow_steps.append(f"Modified {file_name} via {', '.join(agent_summaries)}")
            
            return workflow_steps
        
        def determine_primary_activity(tool_categories, user_content):
            """Determine the main purpose of this RequestCycle"""
            if 'test' in user_content.lower():
                return 'testing'
            elif len(tool_categories['file_operations']) > len(tool_categories['search_operations']):
                return 'file_modification'
            elif len(tool_categories['search_operations']) > 0:
                return 'code_analysis'
            elif len(tool_categories['subagent_delegation']) > 0:
                return 'delegated_work'
            else:
                return 'general_assistance'
        
        def parse_current_request_cycle(transcript_path):
            """Parse transcript to extract current RequestCycle (last user message to now)"""
            try:
                if not Path(transcript_path).exists():
                    error_msg = f"Transcript file not found: {transcript_path}"
                    announce_hook("stop", f"ERROR: {error_msg}")
                    return {"error": error_msg, "path": transcript_path}
                
                user_messages = []
                assistant_messages = []
                tool_calls = []
                is_subagent_session = False  # Track if this is a subagent session
                
                with open(transcript_path, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        try:
                            entry = json.loads(line.strip())
                            
                            # Validate expected JSON structure
                            if not isinstance(entry, dict):
                                error_msg = f"Unexpected JSON format at line {line_num}: expected dict, got {type(entry)}"
                                announce_hook("stop", f"ERROR: {error_msg}")
                                continue
                            
                            # Detect subagent session by checking isSidechain flag
                            if entry.get('isSidechain') is True:
                                is_subagent_session = True
                            
                            # Extract user messages (actual text, not tool results)
                            if entry.get('type') == 'user' and 'message' in entry:
                                # Validate message structure
                                if not isinstance(entry.get('message'), dict):
                                    error_msg = f"Unexpected message format at line {line_num}: expected dict message"
                                    announce_hook("stop", f"ERROR: {error_msg}")
                                    continue
                                    
                                message_content = entry['message'].get('content', '')
                                if isinstance(message_content, str) and message_content.strip():
                                    # Detect subagent prompts (they start with "You are a subagent")
                                    is_subagent_prompt = message_content.startswith("You are a subagent")
                                    
                                    user_messages.append({
                                        'line': line_num,
                                        'content': message_content,
                                        'timestamp': entry.get('timestamp'),
                                        'is_subagent_prompt': is_subagent_prompt
                                    })
                            
                            # Extract assistant messages and embedded tool calls
                            elif entry.get('type') == 'assistant' and 'message' in entry:
                                # Validate assistant message structure
                                if not isinstance(entry.get('message'), dict):
                                    error_msg = f"Unexpected assistant message format at line {line_num}"
                                    announce_hook("stop", f"ERROR: {error_msg}")
                                    continue
                                    
                                assistant_messages.append({
                                    'line': line_num,
                                    'content': entry['message'].get('content', ''),
                                    'timestamp': entry.get('timestamp')
                                })
                                
                                # Check for tool calls embedded in assistant messages
                                message_content = entry['message'].get('content', [])
                                if isinstance(message_content, list):
                                    for content_item in message_content:
                                        if isinstance(content_item, dict) and content_item.get('type') == 'tool_use':
                                            # Validate tool call structure
                                            if not content_item.get('name'):
                                                error_msg = f"Tool call missing 'name' field at line {line_num}"
                                                announce_hook("stop", f"WARNING: {error_msg}")
                                                continue
                                                
                                            tool_calls.append({
                                                'line': line_num,
                                                'tool_name': content_item.get('name'),
                                                'input': content_item.get('input'),
                                                'timestamp': entry.get('timestamp')
                                            })
                            
                            # Extract standalone tool calls (rare)
                            elif entry.get('type') == 'tool_use':
                                tool_calls.append({
                                    'line': line_num,
                                    'tool_name': entry.get('name'),
                                    'input': entry.get('input'),
                                    'timestamp': entry.get('timestamp')
                                })
                                
                        except json.JSONDecodeError as e:
                            error_msg = f"JSON parse error at line {line_num}: {str(e)}"
                            announce_hook("stop", f"ERROR: {error_msg}")
                            continue
                        except Exception as e:
                            error_msg = f"Unexpected error parsing line {line_num}: {str(e)}"
                            announce_hook("stop", f"ERROR: {error_msg}")
                            continue
                
                # Get the LAST REAL user message (not subagent prompt)
                if not user_messages:
                    error_msg = "No user messages found in transcript - possible format change"
                    announce_hook("stop", f"ERROR: {error_msg}")
                    return {"error": error_msg}
                
                # Find the last non-subagent user message
                real_user_messages = [msg for msg in user_messages if not msg.get('is_subagent_prompt', False)]
                if not real_user_messages:
                    error_msg = "No real user messages found - only subagent prompts detected"
                    announce_hook("stop", f"WARNING: {error_msg}")
                    return {"error": error_msg}
                
                current_request = real_user_messages[-1]
                request_cycle_start_line = current_request['line']
                
                # Get everything that happened AFTER the last user message
                request_cycle_tools = [
                    tool for tool in tool_calls 
                    if tool['line'] > request_cycle_start_line
                ]
                
                request_cycle_responses = [
                    msg for msg in assistant_messages 
                    if msg['line'] > request_cycle_start_line
                ]
                
                # Analyze and organize the data for better DB structure
                analysis = analyze_request_cycle(current_request, request_cycle_tools, request_cycle_responses)
                
                # Handle subagent sessions differently
                if is_subagent_session:
                    # Mark subagent work in file_activities for proper attribution
                    for file_path, agents in analysis.get('file_activities', {}).items():
                        if 'main_agent' in agents:
                            # Transfer main_agent work to subagent
                            agents['subagent'] = agents.pop('main_agent')
                            # Update reason to reflect subagent work
                            agents['subagent']['reason'] = f"Subagent work: {agents['subagent']['reason']}"
                    
                    # Update agents_involved to reflect subagent activity
                    analysis['agents_involved'] = {
                        'main_agent': False,
                        'subagents': True,
                        'subagent_count': 1
                    }
                    
                    # Add subagent session metadata
                    analysis['session_type'] = 'subagent'
                    analysis['parent_session_note'] = 'Task delegation details in parent session'
                else:
                    analysis['session_type'] = 'main'
                
                return {
                    "request_cycle_summary": analysis,
                    "raw_data": {
                        "user_request": current_request,
                        "tools_used": request_cycle_tools,
                        "assistant_responses": request_cycle_responses,
                        "tool_count": len(request_cycle_tools),
                        "response_count": len(request_cycle_responses)
                    },
                    "conversation_context": {
                        "total_request_cycles": len(user_messages),
                        "conversation_first_request": user_messages[0] if user_messages else None,
                        "is_subagent_session": is_subagent_session
                    }
                }
                
            except FileNotFoundError as e:
                error_msg = f"Transcript file not accessible: {str(e)}"
                announce_hook("stop", f"ERROR: {error_msg}")
                return {"error": error_msg}
            except PermissionError as e:
                error_msg = f"Permission denied reading transcript: {str(e)}"
                announce_hook("stop", f"ERROR: {error_msg}")
                return {"error": error_msg}
            except Exception as e:
                error_msg = f"Failed to parse transcript - possible format change: {str(e)}"
                announce_hook("stop", f"CRITICAL ERROR: {error_msg}")
                return {"error": error_msg}
        
        # Phase 1: Try hook-based parsing (new approach)
        cycle_id = get_current_cycle_id(session_id, input_data.get('transcript_path', ''))
        
        try:
            # Use new hook-based parsing
            hook_summary = generate_contextual_summary(session_id, cycle_id)
            
            if "error" not in hook_summary:
                # Hook parsing successful - use it as primary data
                request_cycle_data = {
                    "request_cycle_summary": hook_summary,
                    "raw_data": {
                        "data_source": "hook_timeline",
                        "cycle_id": cycle_id,
                        "session_id": session_id
                    },
                    "conversation_context": {
                        "is_hook_based": True,
                        "cycle_id": cycle_id
                    }
                }
                
                with open('/tmp/stop_hook_debug.log', 'a') as f:
                    f.write(f"\n{datetime.now()}: Successfully used hook-based parsing for cycle {cycle_id}\n")
                    
            else:
                # Hook parsing failed - fall back to transcript parsing
                with open('/tmp/stop_hook_debug.log', 'a') as f:
                    f.write(f"\n{datetime.now()}: Hook parsing failed ({hook_summary.get('error')}), falling back to transcript parsing\n")
                    
                transcript_path = input_data.get('transcript_path', '')
                if not transcript_path:
                    error_msg = "No transcript path provided and hook parsing failed"
                    request_cycle_data = {"error": error_msg}
                else:
                    request_cycle_data = parse_current_request_cycle(transcript_path)
                    
        except Exception as e:
            # Hook parsing error - fall back to transcript parsing
            with open('/tmp/stop_hook_debug.log', 'a') as f:
                f.write(f"\n{datetime.now()}: Hook parsing exception ({str(e)}), falling back to transcript parsing\n")
                
            transcript_path = input_data.get('transcript_path', '')
            if not transcript_path:
                error_msg = "No transcript path provided and hook parsing failed with exception"
                request_cycle_data = {"error": error_msg}
            else:
                request_cycle_data = parse_current_request_cycle(transcript_path)
        
        # Create conversation completion data with organized structure
        # Extract request_cycle_summary for top-level placement
        request_cycle_summary = request_cycle_data.get("request_cycle_summary", {})
        
        conversation_completion = {
            **input_data,  # Original hook data
            "request_cycle_summary": request_cycle_summary,  # Curated schema-ready data at top level
            "conversation_data": {
                "raw_data": request_cycle_data.get("raw_data", {}),
                "conversation_context": request_cycle_data.get("conversation_context", {})
            },
            "conversation_end_context": {
                "session_id": input_data.get("session_id", ""),
                "stop_hook_active": input_data.get("stop_hook_active", False),
                "transcript_available": bool(transcript_path),
                "conversation_completed": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        project_claude_dir = get_project_claude_dir()
        contextual_data_path = project_claude_dir / 'claude_contextual_data.json'
        
        # Handle session-wide data aggregation to prevent loss during context compacting
        def aggregate_session_data(current_conversation, existing_data=None):
            """Combine current conversation with existing session data to prevent data loss"""
            # Detect if this is a post-compacting conversation
            current_user_intent = current_conversation.get('request_cycle_summary', {}).get('user_intent', '')
            is_post_compacting = 'context' in current_user_intent.lower() and 'compacting' in current_user_intent.lower()
            
            if is_post_compacting:
                # Extract pre-compacting data from user intent summary since the pre-compacting 
                # activities never got a Stop hook to save their data
                def extract_precompacting_data_from_summary(user_intent):
                    """Parse user intent summary to extract pre-compacting file activities"""
                    import re
                    
                    precompacting_files = {}
                    precompacting_edit_count = 0
                    
                    # Look for mentions of files that were modified
                    # Pattern: mentions of file paths and edit counts
                    file_mentions = re.findall(r'`([^`]+\.py)`', user_intent)
                    
                    # Look for total edit count from previous cycle
                    edit_count_match = re.search(r'total_edits_in_cycle[:\s]*(\d+)', user_intent)
                    if edit_count_match:
                        precompacting_edit_count = int(edit_count_match.group(1))
                    
                    # Look for specific file activities mentioned in summary
                    for file_path in file_mentions:
                        if 'stop.py' in file_path:  # Our main working file
                            # Extract context about what was done to this file
                            file_context_pattern = rf'{re.escape(file_path)}[^*]*?- ([^-\n]+)'
                            context_matches = re.findall(file_context_pattern, user_intent, re.MULTILINE)
                            
                            if context_matches:
                                reason = '; '.join(context_matches[:3])  # Take first 3 context items
                            else:
                                reason = "Pre-compacting file modifications (extracted from summary)"
                            
                            precompacting_files[file_path] = {
                                'main_agent': {
                                    'reason': reason,
                                    'edit_count': precompacting_edit_count,  # All edits attributed to main file
                                    'operations': ['edit'],
                                    'first_edit_timestamp': '2025-07-13T14:00:00.000Z',  # Synthetic timestamp
                                    'last_edit_timestamp': '2025-07-13T14:20:00.000Z'   # Before current cycle
                                }
                            }
                    
                    return precompacting_files, precompacting_edit_count
                
                # Get existing data or extract from summary
                if existing_data:
                    existing_summary = existing_data.get('request_cycle_summary', {})
                    existing_files = existing_summary.get('file_activities', {})
                    existing_subagents = existing_summary.get('subagent_tasks', {})
                    pre_edit_count = existing_summary.get('total_edits_in_cycle', 0)
                else:
                    # Extract from user intent summary - this is the key fix!
                    existing_files, pre_edit_count = extract_precompacting_data_from_summary(current_user_intent)
                    existing_subagents = {}
                
                current_summary = current_conversation.get('request_cycle_summary', {})
                current_files = current_summary.get('file_activities', {})
                current_subagents = current_summary.get('subagent_tasks', {})
                current_edit_count = current_summary.get('total_edits_in_cycle', 0)
                
                # Merge file activities
                merged_files = {**existing_files}
                for file_path, current_agents in current_files.items():
                    if file_path in merged_files:
                        # Merge agents for same file
                        merged_files[file_path] = {**merged_files[file_path], **current_agents}
                    else:
                        merged_files[file_path] = current_agents
                
                # Merge subagent tasks
                merged_subagents = {**existing_subagents, **current_subagents}
                
                # Calculate total edits across both cycles
                total_edits = pre_edit_count + current_edit_count
                
                # Update current conversation with merged data
                if 'request_cycle_summary' not in current_conversation:
                    current_conversation['request_cycle_summary'] = {}
                
                current_conversation['request_cycle_summary']['file_activities'] = merged_files
                current_conversation['request_cycle_summary']['subagent_tasks'] = merged_subagents
                current_conversation['request_cycle_summary']['total_edits_in_cycle'] = total_edits
                
                # Update summary with merged counts
                current_summary_section = current_conversation['request_cycle_summary'].get('summary', {})
                current_summary_section['files_modified'] = list(merged_files.keys())
                current_summary_section['total_file_changes'] = total_edits
                current_summary_section['involved_subagents'] = bool(merged_subagents)
                
                # Add session continuity metadata
                current_conversation['session_continuity'] = {
                    'is_post_compacting': True,
                    'pre_compacting_file_count': len(existing_files),
                    'pre_compacting_subagent_count': len(existing_subagents),
                    'pre_compacting_edit_count': pre_edit_count,
                    'current_cycle_edit_count': current_edit_count,
                    'total_merged_edits': total_edits,
                    'merged_data_preserved': True,
                    'data_source': 'existing_file' if existing_data else 'extracted_from_summary'
                }
            
            return current_conversation
        
        # Load existing data if available
        existing_data = None
        if contextual_data_path.exists():
            try:
                with open(contextual_data_path, 'r') as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = None
        
        # Aggregate with existing data
        final_conversation_data = aggregate_session_data(conversation_completion, existing_data)
        
        # Write aggregated data
        with open(contextual_data_path, 'w') as f:
            json.dump(final_conversation_data, f, indent=2)
        
        # Add TTS announcement
        sys.path.append(str(Path(__file__).parent / 'utils'))
        from tts_announcer import announce_hook
        
        # Get summary data for announcement
        summary = final_conversation_data.get('request_cycle_summary', {}).get('summary', {})
        primary_activity = summary.get('primary_activity', 'unknown')
        files_modified_count = len(summary.get('files_modified', []))
        
        announce_hook("stop", f"Conversation completed: {primary_activity}, {files_modified_count} files modified")

        # Extract required fields
        session_id = input_data.get("session_id", "")
        stop_hook_active = input_data.get("stop_hook_active", False)
        
        # Try to get model info from input
        model_info = input_data.get("model", input_data.get("agent_model", "unknown"))

        # Use new database system only
        
        # Add session end event to new database
        add_event(session_id, 'session_end', {
            'model': model_info,
            'stop_hook_active': stop_hook_active
        })
        

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