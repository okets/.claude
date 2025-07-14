#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import json
import os
import sys
from pathlib import Path
import re
from datetime import datetime
import time

# Import our cycle utilities
sys.path.append(str(Path(__file__).parent / 'utils'))
try:
    from cycle_utils import dump_hook_data
except ImportError:
    # Fallback if utils not available
    def dump_hook_data(hook_name, hook_data, session_id, transcript_path):
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

def extract_file_paths(tool_input, tool_response):
    """Extract file paths that were touched during tool execution"""
    files_touched = []
    
    # Extract from tool input
    if 'file_path' in tool_input:
        files_touched.append(tool_input['file_path'])
    if 'notebook_path' in tool_input:
        files_touched.append(tool_input['notebook_path'])
    
    # Extract from bash commands
    if tool_input.get('command'):
        command = tool_input['command']
        # Simple file extraction from common commands
        file_patterns = [
            r'>\s*([^\s]+)',  # > file
            r'cat\s+([^\s]+)',  # cat file
            r'touch\s+([^\s]+)',  # touch file
            r'cp\s+[^\s]+\s+([^\s]+)',  # cp src dest
            r'mv\s+[^\s]+\s+([^\s]+)',  # mv src dest
        ]
        for pattern in file_patterns:
            matches = re.findall(pattern, command)
            files_touched.extend(matches)
    
    # Clean and normalize paths
    cleaned_files = []
    for file_path in files_touched:
        try:
            # Convert to absolute path and resolve
            abs_path = Path(file_path).resolve()
            cleaned_files.append(str(abs_path))
        except:
            # Keep original if path resolution fails
            cleaned_files.append(file_path)
    
    return list(set(cleaned_files))  # Remove duplicates

def infer_intent(tool_name, tool_input, files_touched):
    """Infer the intent/purpose of the tool execution"""
    if tool_name == 'Read':
        return 'reading-file'
    elif tool_name in ['Write', 'Edit', 'MultiEdit']:
        return 'modifying-file'
    elif tool_name == 'Bash':
        command = tool_input.get('command', '').lower()
        if 'test' in command or 'pytest' in command:
            return 'running-tests'
        elif 'git' in command:
            return 'git-operation'
        elif 'npm' in command or 'yarn' in command:
            return 'package-management'
        elif 'build' in command or 'compile' in command:
            return 'building'
        else:
            return 'shell-command'
    elif tool_name == 'Grep':
        return 'searching-code'
    elif tool_name == 'Glob':
        return 'finding-files'
    else:
        return 'unknown'

def infer_success_from_tool_response(tool_name, tool_response):
    """Infer success from tool response structure"""
    if not tool_response:
        return False
    
    # For Bash tools - check if interrupted or has stderr
    if tool_name == 'Bash':
        if tool_response.get('interrupted', False):
            return False
        # Most commands succeed even with stderr
        return True
    
    # For file tools - presence of filePath usually indicates success
    if tool_name in ['Read', 'Write', 'Edit', 'MultiEdit']:
        return 'filePath' in tool_response or 'file' in tool_response
    
    # Default to success
    return True

def build_thought_from_tool(tool_name, tool_input, intent):
    """Build a human-readable thought based on tool execution"""
    if tool_name == 'Read':
        file_path = tool_input.get('file_path', 'unknown file')
        return f"Reading {Path(file_path).name} to understand the implementation"
    
    elif tool_name in ['Edit', 'MultiEdit']:
        file_path = tool_input.get('file_path', 'unknown file')
        return f"Modifying {Path(file_path).name} to implement changes"
    
    elif tool_name == 'Write':
        file_path = tool_input.get('file_path', 'unknown file')
        return f"Creating new file {Path(file_path).name}"
    
    elif tool_name == 'Bash':
        command = tool_input.get('command', '')
        if 'test' in command.lower():
            return "Running tests to verify changes"
        elif 'git' in command.lower():
            return f"Executing git operation: {command[:50]}..."
        elif 'npm' in command.lower() or 'yarn' in command.lower():
            return "Managing package dependencies"
        else:
            return f"Executing command: {command[:50]}..."
    
    elif tool_name == 'Grep':
        pattern = tool_input.get('pattern', '')
        return f"Searching for pattern: {pattern[:30]}..."
    
    elif tool_name == 'Glob':
        pattern = tool_input.get('pattern', '')
        return f"Finding files matching: {pattern}"
    
    elif tool_name == 'Task':
        desc = tool_input.get('description', '')
        return f"Launching subagent for: {desc}"
    
    else:
        return f"Using {tool_name} for {intent}"

def main():
    start_time = time.time()
    
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)
        
        # Dump raw hook data for analysis
        session_id = input_data.get('session_id', '')
        transcript_path = input_data.get('transcript_path', '')
        dump_hook_data('PostToolUse', input_data, session_id, transcript_path)
        
        # Optional debug logging - uncomment for debugging
        # debug_log = Path('/tmp') / 'claude_debug_post_tool_use.json'
        # with open(debug_log, 'w') as f:
        #     json.dump(input_data, f, indent=2)
        
        # Get session ID
        session_id = input_data.get('session_id', '')
        
        # Extract tool information
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        tool_response = input_data.get('tool_response', {})
        
        # Extract context information
        files_touched = extract_file_paths(tool_input, tool_response)
        intent = infer_intent(tool_name, tool_input, files_touched)
        success = infer_success_from_tool_response(tool_name, tool_response)
        duration_ms = int((time.time() - start_time) * 1000)
        
        
        # Track file changes for modification tools only
        if tool_name in ['Edit', 'Write', 'MultiEdit', 'NotebookEdit'] and files_touched:
            for file_path in files_touched:
                # Determine change type
                if tool_name == 'Write':
                    # Check if file exists to determine if created or modified
                    change_type = 'created' if not Path(file_path).exists() else 'modified'
                else:
                    change_type = 'modified'
                
                # Generate change summary
                if tool_name == 'Edit':
                    change_summary = "Modified file content"
                elif tool_name == 'MultiEdit':
                    edits = tool_input.get('edits', [])
                    change_summary = f"Applied {len(edits)} edits"
                elif tool_name == 'Write':
                    change_summary = f"{'Created' if change_type == 'created' else 'Updated'} file"
                else:
                    change_summary = "Modified notebook"
                
        
        # Announce tool completion in verbose mode
        try:
            sys.path.append(str(Path(__file__).parent / 'utils'))
            from settings import get_setting
            from cycle_utils import announce_user_content
            
            interaction_level = get_setting("interaction_level", "concise")
            
            if interaction_level == "verbose":
                # Announce tool completion with varied messages
                if success:
                    import random
                    
                    completion_announcements = {
                        'Read': [
                            'Got it', 'All read', 'Done reading', 'Checked it out',
                            'Had a look', 'Read through', 'All good', 'Seen enough',
                            'Got the info', 'Read it all', 'Looks good', 'All checked',
                            'Snooping complete', 'Mystery solved', 'Knowledge acquired'
                        ],
                        'Write': [
                            'All written', 'Got it down', 'File created', 'Done writing',
                            'All saved', 'Written up', 'File ready', 'All set',
                            'Created that', 'All done', 'Saved it', 'Built that',
                            'Magic happened', 'Masterpiece created', 'Pure genius unleashed'
                        ], 
                        'Edit': [
                            'Changes made', 'All updated', 'Fixed up', 'Tweaked it',
                            'All changed', 'Updated that', 'Polished up', 'All better',
                            'Modified it', 'Changes done', 'All improved', 'Edited that',
                            'Surgery successful', 'Patient survived', 'Tweakage complete'
                        ],
                        'Bash': [
                            'Command done', 'All executed', 'Ran successfully', 'That worked',
                            'Command finished', 'All good', 'Executed fine', 'Done running',
                            'Script complete', 'All ran', 'Command success', 'Finished that',
                            'Matrix exited', 'Terminal tamed', 'Shell conquered'
                        ],
                        'Task': [
                            'Helper done', 'Agent finished', 'Got the help', 'Team work done',
                            'All delegated', 'Support complete', 'Helper succeeded', 'Backup done',
                            'Collaboration done', 'Agent complete', 'Help finished', 'Team success',
                            'Cavalry arrived', 'Minions delivered', 'Squad assembled'
                        ],
                        'Glob': [
                            'Found them', 'Search done', 'Got the files', 'Hunt complete',
                            'Files found', 'Search success', 'Located them', 'Found matches',
                            'Hunt successful', 'All found', 'Search finished', 'Detective work done',
                            'Treasure located', 'Safari successful', 'Sherlock strikes again'
                        ],
                        'Grep': [
                            'Found it', 'Search done', 'Got matches', 'Pattern found',
                            'Text located', 'Search complete', 'Found patterns', 'Hunt success',
                            'Needle found', 'Search finished', 'Got results', 'Pattern hunt done',
                            'Hide and seek won', 'Archaeology complete', 'Elementary Watson'
                        ],
                        'WebFetch': [
                            'Got web data', 'Downloaded it', 'Web search done', 'Found online',
                            'Retrieved info', 'Web hunt done', 'Got the data', 'Downloaded that',
                            'Web success', 'Online data got', 'Fetched it', 'Web search complete',
                            'Surfboard stowed', 'Adventure complete', 'Cave explored'
                        ]
                    }
                    
                    announcements = completion_announcements.get(tool_name, [f'{tool_name} completed'])
                    announcement = random.choice(announcements)
                    announce_user_content(announcement, level="verbose")
                
        except ImportError:
            pass  # Settings not available
        
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Exit cleanly on any other error
        sys.exit(0)

if __name__ == '__main__':
    main()