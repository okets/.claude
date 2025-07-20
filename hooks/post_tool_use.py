#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import json
import os
import sys
from pathlib import Path
import re
import datetime

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
                
        
        # Announce tool description if available
        try:
            sys.path.append(str(Path(__file__).parent / 'utils'))
            from settings import get_setting
            from cycle_utils import announce_user_content
            
            interaction_level = get_setting("interaction_level", "concise")
            
            # Skip announcements for TodoWrite - too frequent and annoying
            if tool_name != 'TodoWrite':
                # Get tool description from input (the white bullet point text)
                tool_description = tool_input.get('description', '').strip()
                
                if tool_description:
                    # Deduplication: Check if we've already announced this description recently
                    cache_file = Path('/tmp') / 'last_tool_description.txt'
                    should_announce = True
                    
                    if cache_file.exists():
                        try:
                            with open(cache_file, 'r') as f:
                                last_description = f.read().strip()
                            # Don't repeat if it's the same description
                            if last_description == tool_description:
                                should_announce = False
                        except:
                            pass  # If cache read fails, proceed with announcement
                    
                    if should_announce:
                        # Cache this description to avoid immediate repetition
                        try:
                            with open(cache_file, 'w') as f:
                                f.write(tool_description)
                        except:
                            pass  # Cache write failure shouldn't break the hook
                        
                        # Announce the description with completion indicator
                        completion_suffixes = [
                            "- done",
                            "- complete", 
                            "- finished",
                            "- success",
                            "- ready"
                        ]
                        
                        import random
                        suffix = random.choice(completion_suffixes)
                        announcement = f"{tool_description} {suffix}"
                        
                        # Use appropriate level based on interaction setting
                        if interaction_level in ["concise", "verbose"]:
                            announce_user_content(announcement)
                
                # Fallback to original verbose announcements if no description available
                elif interaction_level == "verbose":
                    if success:
                        import random
                        
                        completion_announcements = {
                            'Read': [
                                'Read completed', 'File processed', 'Content analyzed', 'Read operation finished',
                                'File contents retrieved', 'Reading successful', 'Content loaded', 'File examined',
                                'Read task complete', 'File analysis done', 'Content processed', 'Reading finished'
                            ],
                            'Write': [
                                'Write completed', 'File created', 'Content written', 'Write operation finished',
                                'File saved successfully', 'Writing complete', 'Content generated', 'File built',
                                'Write task done', 'File creation complete', 'Content saved', 'Writing finished'
                            ], 
                            'Edit': [
                                'Edit completed', 'Changes applied', 'File modified', 'Edit operation finished',
                                'Updates saved', 'Modifications complete', 'File updated', 'Changes processed',
                                'Edit task done', 'File changes saved', 'Updates applied', 'Editing finished'
                            ],
                            'Bash': [
                                'Command executed', 'Script completed', 'Execution finished', 'Command processed',
                                'Script run successfully', 'Execution complete', 'Command finished', 'Process completed',
                                'Shell command done', 'Script execution finished', 'Command successful', 'Execution done'
                            ],
                            'Task': [
                                'Task completed', 'Agent finished', 'Delegation successful', 'Task execution done',
                                'Agent task complete', 'Collaboration finished', 'Task processed', 'Agent work done',
                                'Delegation complete', 'Task agent finished', 'Agent execution done', 'Task successful'
                            ],
                            'Glob': [
                                'File search completed', 'Files located', 'Search finished', 'Pattern matching done',
                                'File discovery complete', 'Search successful', 'Files found', 'Pattern search finished',
                                'File matching complete', 'Search operation done', 'File lookup finished', 'Search complete'
                            ],
                            'Grep': [
                                'Text search completed', 'Pattern found', 'Search finished', 'Text matching done',
                                'Pattern search complete', 'Text scan finished', 'Search successful', 'Pattern matching finished',
                                'Text analysis complete', 'Search operation done', 'Pattern lookup finished', 'Grep complete'
                            ],
                            'WebFetch': [
                                'Web fetch completed', 'Data retrieved', 'Download finished', 'Web request done',
                                'Content downloaded', 'Fetch successful', 'Web data obtained', 'Download complete',
                                'Web operation finished', 'Data fetch done', 'Web content retrieved', 'Fetch complete'
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