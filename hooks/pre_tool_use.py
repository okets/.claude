#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import json
import sys
import re
import subprocess
from pathlib import Path
import datetime


# Import our cycle utilities
sys.path.append(str(Path(__file__).parent / 'utils'))
try:
    from cycle_utils import dump_hook_data
except ImportError:
    # Fallback if utils not available
    def dump_hook_data(hook_name, hook_data, session_id, transcript_path):
        pass

def stop_all_tts():
    """Stop all TTS playback immediately when new cycle starts"""
    try:
        # Kill macOS 'say' processes
        subprocess.run(["pkill", "-f", "say"], capture_output=True, timeout=1)
        # Kill any afplay processes (audio playback)
        subprocess.run(["pkill", "-f", "afplay"], capture_output=True, timeout=1)
    except Exception:
        pass  # Fail silently


def get_project_root():
    """Find project root by looking for .git directory"""
    cwd = Path.cwd()
    current = cwd
    while current != current.parent:
        if (current / '.git').exists():
            return current
        current = current.parent
    return cwd  # Fallback to current directory

def is_outside_project(path_str):
    """Check if a path targets outside the current project"""
    try:
        project_root = get_project_root()
        target_path = Path(path_str).resolve()
        project_root = project_root.resolve()
        
        # Check if target is within project
        try:
            target_path.relative_to(project_root)
            return False  # Inside project
        except ValueError:
            return True   # Outside project
    except:
        # If we can't resolve paths, err on the side of caution
        return True

def is_dangerous_outside_project_command(command):
    """
    Check for operations targeting outside the current project.
    Allow all operations within project, block operations outside.
    """
    normalized = ' '.join(command.lower().split())
    
    # Extract potential paths from rm commands
    rm_patterns = [
        r'\brm\s+(?:-[a-z]*\s+)*([^\s]+)',  # rm [flags] path
        r'\brm\s+(?:--[a-z-]+\s+)*([^\s]+)',  # rm --flags path
    ]
    
    for pattern in rm_patterns:
        matches = re.findall(pattern, normalized)
        for match in matches:
            # Skip flags
            if match.startswith('-'):
                continue
            
            # Check specific dangerous patterns that should always be blocked
            dangerous_absolutes = [
                '/', '/usr', '/etc', '/var', '/home', '/root',
                '~', '~/', '$HOME'
            ]
            
            if match in dangerous_absolutes or match.startswith('/usr/') or match.startswith('/etc/'):
                return True
                
            # Check if targeting outside project
            if is_outside_project(match):
                return True
    
    return False

def needs_git_confirmation(command):
    """Check if git command needs user confirmation"""
    git_confirm_patterns = [
        r'\bgit\s+commit',
        r'\bgit\s+push', 
        r'\bgit\s+reset\s+--hard',
        r'\bgit\s+rebase',
        r'\bgit\s+merge\s+--no-ff',
        r'\bgit\s+force-push',
        r'\bgit\s+push\s+.*--force'
    ]
    
    command_lower = command.lower()
    return any(re.search(pattern, command_lower) for pattern in git_confirm_patterns)

def is_env_file_access(tool_name, tool_input):
    """
    Check if any tool is trying to access .env files containing sensitive data.
    """
    if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write', 'Bash']:
        # Check file paths for file-based tools
        if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write']:
            file_path = tool_input.get('file_path', '')
            if '.env' in file_path and not file_path.endswith('.env.sample'):
                return True
        
        # Check bash commands for .env file access
        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            # Pattern to detect .env file access (but allow .env.sample)
            env_patterns = [
                r'\b\.env\b(?!\.sample)',  # .env but not .env.sample
                r'cat\s+.*\.env\b(?!\.sample)',  # cat .env
                r'echo\s+.*>\s*\.env\b(?!\.sample)',  # echo > .env
                r'touch\s+.*\.env\b(?!\.sample)',  # touch .env
                r'cp\s+.*\.env\b(?!\.sample)',  # cp .env
                r'mv\s+.*\.env\b(?!\.sample)',  # mv .env
            ]
            
            for pattern in env_patterns:
                if re.search(pattern, command):
                    return True
    
    return False

def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)
        
        # Dump raw hook data for analysis
        session_id = input_data.get('session_id', '')
        transcript_path = input_data.get('transcript_path', '')
        dump_hook_data('PreToolUse', input_data, session_id, transcript_path)
        
        # Optional debug logging - uncomment for debugging
        # debug_log = Path('/tmp') / 'claude_debug_pre_tool_use.json'
        # with open(debug_log, 'w') as f:
        #     json.dump(input_data, f, indent=2)
        
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        
        # Check for .env file access (blocks access to sensitive environment files)
        if is_env_file_access(tool_name, tool_input):
            print("BLOCKED: Access to .env files containing sensitive data is prohibited", file=sys.stderr)
            print("Use .env.sample for template files instead", file=sys.stderr)
            
            
            sys.exit(2)  # Exit code 2 blocks tool call and shows error to Claude
        
        # Enhanced security for bash commands
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            
            # Block operations outside project directory
            if is_dangerous_outside_project_command(command):
                print("BLOCKED: Operation targeting outside project directory", file=sys.stderr)
                print("Only operations within the current project are allowed", file=sys.stderr)
                
                
                sys.exit(2)
            
            # Git confirmation - show warning but allow
            if needs_git_confirmation(command):
                print(f"⚠️  Claude is running git command: {command}", file=sys.stderr)
                print("📋 This will affect your git history.", file=sys.stderr)
                
                try:
                    # Show current git status for context
                    import subprocess
                    result = subprocess.run(['git', 'status', '--porcelain'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        print("📁 Current changes:", file=sys.stderr)
                        for line in result.stdout.strip().split('\n')[:5]:  # Show first 5 changes
                            print(f"   {line}", file=sys.stderr)
                except:
                    pass  # Don't fail on git status error
                
                print("✅ Git command proceeding...", file=sys.stderr)
        
        # Stop any playing TTS before new cycle starts
        stop_all_tts()
        
        # Announce tool usage in verbose mode
        try:
            sys.path.append(str(Path(__file__).parent / 'utils'))
            from settings import get_setting
            from cycle_utils import announce_user_content
            
            interaction_level = get_setting("interaction_level", "concise")
            
            # Announce TodoWrite with actual todo content instead of generic messages
            if tool_name == 'TodoWrite' and interaction_level in ["concise", "verbose"]:
                try:
                    # Get the actual todo data from the tool input
                    todos = tool_input.get('todos', [])
                    
                    if todos:
                        # Find current working item (in_progress or next pending)
                        current_todo = None
                        next_todo = None
                        
                        # Look for in_progress items first
                        for todo in todos:
                            if todo.get('status') == 'in_progress':
                                current_todo = todo.get('content', '').strip()
                                break
                        
                        # If no in_progress, find first pending
                        if not current_todo:
                            for todo in todos:
                                if todo.get('status') == 'pending':
                                    next_todo = todo.get('content', '').strip()
                                    break
                        
                        # Create contextual announcement
                        if current_todo:
                            announcement = f"Working on: {current_todo}"
                        elif next_todo:
                            announcement = f"Next task: {next_todo}"
                        else:
                            # Fallback if no clear current item
                            completed_count = len([t for t in todos if t.get('status') == 'completed'])
                            total_count = len(todos)
                            announcement = f"Planning tasks - {completed_count} of {total_count} completed"
                    else:
                        # No todos in input, use generic planning message
                        announcement = "Planning this task"
                    
                    announce_user_content(announcement, level="concise")
                    
                except Exception:
                    # Fallback to simple message if todo parsing fails
                    announce_user_content("Planning tasks", level="concise")
            
            # Special announcement for smarter-claude database access (all interaction levels)
            if tool_name == 'Bash':
                command = tool_input.get('command', '')
                if command.startswith('sqlite3 .claude/smarter-claude/smarter-claude.db'):
                    announce_user_content("accessing my long context memory", level=interaction_level)
                elif interaction_level == "verbose":
                    # Only announce regular bash commands in verbose mode if not database access
                    import random
                    
                    # Extract command name for more informative announcements
                    command_parts = command.strip().split()
                    if command_parts:
                        command_name = command_parts[0]
                        
                        # Special handling for git commands - include subcommand
                        if command_name.lower() == 'git' and len(command_parts) > 1:
                            full_command = f"git {command_parts[1]}"
                        else:
                            full_command = command_name
                        
                        bash_announcements = [
                            f'I\'m running {full_command} now', f'I need to execute {full_command}', f'I\'m launching {full_command}',
                            f'I\'m starting {full_command}', f'I need to run {full_command}', f'I\'m executing {full_command} now',
                            f'I\'m processing {full_command}', f'Running {full_command}', f'Executing {full_command}'
                        ]
                        announcement = random.choice(bash_announcements)
                    else:
                        # Fallback for edge cases
                        announcement = "I'm running this command now"
                    
                    announce_user_content(announcement, level="verbose")
            
            elif interaction_level == "verbose":
                
                # Announce tool usage with varied messages
                import random
                
                tool_announcements = {
                    'Read': [
                        'I need to read this now', 'I\'m checking this file', 'I\'m looking at this', 'I need to see this',
                        'I\'m reading through this now', 'I\'m examining this', 'I\'m reviewing this file', 'I need to check this',
                        'I\'m going through this', 'I\'m analyzing this now', 'I need to understand this'
                    ],
                    'Write': [
                        'I\'m writing this now', 'I\'m creating this file', 'I need to write this', 'I\'m building this',
                        'I\'m making this file', 'I need to create this now', 'I\'m putting this together', 'I\'m generating this',
                        'I\'m composing this', 'I need to save this', 'I\'m constructing this now'
                    ], 
                    'Edit': [
                        'I\'m updating this now', 'I need to modify this', 'I\'m changing this', 'I\'m fixing this',
                        'I need to edit this', 'I\'m adjusting this now', 'I\'m improving this', 'I\'m correcting this',
                        'I need to update this', 'I\'m revising this', 'I\'m refining this now'
                    ],
                    'Task': [
                        'I\'m creating a specialized agent', 'I\'m delegating this task', 'I\'m launching a subagent',
                        'I\'m spinning up an expert agent', 'I\'m creating a focused agent', 'I\'m deploying specialized help',
                        'I\'m starting a dedicated agent', 'I\'m creating targeted assistance', 'I\'m launching expert support'
                    ],
                    'Glob': [
                        'I\'m finding files now', 'I need to locate files', 'I\'m searching for files', 'I need to find matches',
                        'I\'m looking for files', 'I need to track down files now', 'I\'m hunting for files', 'I\'m seeking files',
                        'I need to discover files', 'I\'m locating files now', 'I\'m identifying files'
                    ],
                    'Grep': [
                        'I\'m searching for this now', 'I need to find this pattern', 'I\'m looking for matches', 'I\'m scanning for this',
                        'I need to locate this text', 'I\'m hunting for this now', 'I\'m searching through code', 'I need to find this',
                        'I\'m looking through text', 'I\'m analyzing patterns now', 'I\'m examining content'
                    ],
                    'WebFetch': [
                        'I\'m getting web data now', 'I need to fetch this', 'I\'m downloading this', 'I need web information',
                        'I\'m retrieving this data', 'I need to access this online now', 'I\'m gathering web data', 'I\'m fetching online content',
                        'I need to download this', 'I\'m accessing web resources now', 'I\'m collecting web data'
                    ],
                    'WebSearch': [
                        'I\'m searching online now', 'I need to search the web', 'I\'m looking this up online', 'I need web search results',
                        'I\'m searching the internet', 'I need to find this online', 'I\'m doing a web search', 'I\'m looking online for this',
                        'I need to search for information', 'I\'m browsing for answers', 'I\'m researching online'
                    ],
                    'exit_plan_mode': [
                        'I\'ve created a plan for you to review', 'Here\'s my implementation plan', 'I\'ve prepared a detailed plan',
                        'Let me present my plan', 'I\'ve outlined an approach', 'Here\'s my proposed solution plan',
                        'I\'ve drafted an implementation strategy', 'Let me share my analysis and plan', 'I\'ve prepared a roadmap',
                        'Here\'s my recommended approach', 'I\'ve created a step-by-step plan'
                    ]
                }
                
                # TodoWrite and Bash already handled above, skip them here
                if tool_name not in ['TodoWrite', 'Bash']:
                    # Helper function to make filenames more TTS-friendly
                    def make_filename_speakable(filename):
                        """Replace dots and underscores for better TTS pronunciation"""
                        return filename.replace('.', ' dot ').replace('_', ' ')
                    
                    # Special handling for file-related tools to include filename
                    if tool_name == 'Read':
                        file_path = tool_input.get('file_path', '')
                        if file_path:
                            filename = file_path.split('/')[-1]  # Get just the filename
                            speakable_filename = make_filename_speakable(filename)
                            read_announcements = [
                                f'I need to read {speakable_filename}', f'I\'m checking {speakable_filename}', f'I\'m looking at {speakable_filename}',
                                f'I\'m reading {speakable_filename} now', f'I\'m examining {speakable_filename}', f'I\'m reviewing {speakable_filename}',
                                f'I need to check {speakable_filename}', f'I\'m going through {speakable_filename}', f'I\'m analyzing {speakable_filename}'
                            ]
                            announcement = random.choice(read_announcements)
                        else:
                            # Fallback if no file path
                            announcements = tool_announcements.get(tool_name, [f'Using {tool_name}'])
                            announcement = random.choice(announcements)
                    elif tool_name in ['Write', 'Edit', 'MultiEdit']:
                        file_path = tool_input.get('file_path', '')
                        if file_path:
                            filename = file_path.split('/')[-1]  # Get just the filename
                            speakable_filename = make_filename_speakable(filename)
                            if tool_name == 'Write':
                                write_announcements = [
                                    f'I\'m writing {speakable_filename}', f'I\'m creating {speakable_filename}', f'I need to write {speakable_filename}',
                                    f'I\'m building {speakable_filename}', f'I\'m making {speakable_filename}', f'I\'m generating {speakable_filename}',
                                    f'I\'m composing {speakable_filename}', f'I\'m constructing {speakable_filename}'
                                ]
                                announcement = random.choice(write_announcements)
                            elif tool_name in ['Edit', 'MultiEdit']:
                                edit_announcements = [
                                    f'I\'m updating {speakable_filename}', f'I need to modify {speakable_filename}', f'I\'m changing {speakable_filename}',
                                    f'I\'m fixing {speakable_filename}', f'I need to edit {speakable_filename}', f'I\'m adjusting {speakable_filename}',
                                    f'I\'m improving {speakable_filename}', f'I\'m revising {speakable_filename}'
                                ]
                                announcement = random.choice(edit_announcements)
                        else:
                            # Fallback if no file path
                            announcements = tool_announcements.get(tool_name, [f'Using {tool_name}'])
                            announcement = random.choice(announcements)
                    elif tool_name == 'WebSearch':
                        # Special handling for WebSearch to include the search query
                        search_query = tool_input.get('query', '')
                        if search_query:
                            # Truncate query for speech if it's too long
                            from cycle_utils import truncate_for_speech
                            speakable_query = truncate_for_speech(search_query, max_words=20)
                            web_search_announcements = [
                                f'I\'m searching online for: {speakable_query}',
                                f'Looking up: {speakable_query}',
                                f'Searching the web for: {speakable_query}',
                                f'Finding information about: {speakable_query}',
                                f'Researching: {speakable_query}'
                            ]
                            announcement = random.choice(web_search_announcements)
                        else:
                            # Fallback if no query
                            announcements = tool_announcements.get(tool_name, [f'Using {tool_name}'])
                            announcement = random.choice(announcements)
                    elif tool_name == 'WebFetch':
                        # Special handling for WebFetch to include URL or prompt context
                        url = tool_input.get('url', '')
                        prompt = tool_input.get('prompt', '')
                        if url and prompt:
                            # Truncate prompt for speech if it's too long
                            from cycle_utils import truncate_for_speech
                            speakable_prompt = truncate_for_speech(prompt, max_words=20)
                            web_fetch_announcements = [
                                f'Fetching web content about: {speakable_prompt}',
                                f'Getting online data for: {speakable_prompt}',
                                f'Retrieving web information about: {speakable_prompt}',
                                f'Accessing online content for: {speakable_prompt}'
                            ]
                            announcement = random.choice(web_fetch_announcements)
                        elif url:
                            # Just have URL, use generic fetch message
                            announcements = tool_announcements.get(tool_name, [f'Using {tool_name}'])
                            announcement = random.choice(announcements)
                        else:
                            # Fallback if no URL
                            announcements = tool_announcements.get(tool_name, [f'Using {tool_name}'])
                            announcement = random.choice(announcements)
                    else:
                        # Default handling for other tools
                        announcements = tool_announcements.get(tool_name, [f'Using {tool_name}'])
                        announcement = random.choice(announcements)
                    
                    announce_user_content(announcement, level="verbose")
                
        except ImportError:
            pass  # Settings not available
        
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Gracefully handle JSON decode errors
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)

if __name__ == '__main__':
    main()