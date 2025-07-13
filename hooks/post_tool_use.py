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

# Import new database system only
sys.path.append(str(Path(__file__).parent / 'utils'))
from queryable_db import (
    add_event, track_file_change, add_session_tags, 
    get_current_user_request, get_session_modified_files,
    log_tool_execution, update_file_relationships, get_queryable_db
)

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
        
        # Add tool execution event to new database
        event_data = {
            'tool': tool_name,
            'target': files_touched[0] if files_touched else None,
            'intent': intent,
            'success': success,
            'duration_ms': duration_ms
        }
        add_event(session_id, 'tool_execution', event_data)
        
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
                
                # Get current user request for context
                user_request = get_current_user_request(session_id) or "No user request captured"
                
                # Build context
                context = {
                    'user_request': user_request,
                    'agent_reasoning': build_thought_from_tool(tool_name, tool_input, intent),
                    'related_files': get_session_modified_files(session_id),
                    'prompted_by': 'user_request'  # Could be enhanced to detect test_failure, etc.
                }
                
                # Track the file change
                track_file_change(
                    session_id=session_id,
                    file_path=file_path,
                    change_type=change_type,
                    change_summary=change_summary,
                    context=context
                )
                
                # Add file tags
                add_session_tags(session_id, [
                    ('file', file_path),
                    ('directory', str(Path(file_path).parent))
                ])
        
        # Also log to unified tool execution system for compatibility
        log_tool_execution(
            chat_session_id=session_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_response,
            success=success,
            intent=intent,
            files_touched=files_touched,
            duration_ms=duration_ms
        )
        
        # Update file relationships if multiple files were touched
        if len(files_touched) > 1:
            update_file_relationships(1, files_touched)  # project_id=1 for compatibility
        
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Exit cleanly on any other error
        sys.exit(0)

if __name__ == '__main__':
    main()