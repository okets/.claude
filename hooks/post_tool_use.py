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

# Import database utility
sys.path.append(str(Path(__file__).parent / 'utils'))
from db import get_db

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
        
        # Get database connection
        db = get_db()
        
        # Get project information
        project_claude = get_project_claude_dir()
        project_root = str(project_claude.parent)
        project_name = Path(project_root).name
        
        # Ensure project and session exist in database
        project_id = db.ensure_project(project_root, project_name)
        session_id = input_data.get('session_id', '')
        
        if project_id:
            db.ensure_session(session_id, project_id)
        
        # Extract tool information
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        tool_response = input_data.get('tool_response', {})
        
        # Extract context information
        files_touched = extract_file_paths(tool_input, tool_response)
        intent = infer_intent(tool_name, tool_input, files_touched)
        success = tool_response.get('success', True)
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log to database
        if db.connection and project_id:
            db.log_tool_execution(
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
                db.update_file_relationships(project_id, files_touched)
            
            # Update conversation details with chain of thought
            existing_details = db.get_conversation_details(session_id)
            if existing_details:
                # Build chain of thought step
                chain_step = {
                    "step": len(existing_details.get('agent_chain_of_thought', [])) + 1,
                    "tool": tool_name,
                    "intent": intent,
                    "thought": build_thought_from_tool(tool_name, tool_input, intent),
                    "files": files_touched,
                    "success": success
                }
                
                # Update chain of thought
                chain_of_thought = existing_details.get('agent_chain_of_thought', [])
                chain_of_thought.append(chain_step)
                
                # Update tools used tracking
                tools_used = existing_details.get('tools_used', [])
                tool_entry = next((t for t in tools_used if t['tool_name'] == tool_name), None)
                if tool_entry:
                    tool_entry['count'] += 1
                    if intent not in tool_entry['purposes']:
                        tool_entry['purposes'].append(intent)
                else:
                    tools_used.append({
                        'tool_name': tool_name,
                        'count': 1,
                        'purposes': [intent]
                    })
                
                # Update the conversation details (we need to add an update method)
                cursor = db.connection.cursor()
                cursor.execute("""
                    UPDATE conversation_details 
                    SET agent_chain_of_thought = ?, tools_used = ?
                    WHERE chat_session_id = ?
                """, (
                    json.dumps(chain_of_thought),
                    json.dumps(tools_used),
                    session_id
                ))
                db.connection.commit()
        
        # Database is the primary storage - no JSON fallback needed
        # If database is unavailable, we'll lose this execution data, but that's better
        # than maintaining duplicate storage systems
        
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Exit cleanly on any other error
        sys.exit(0)

if __name__ == '__main__':
    main()