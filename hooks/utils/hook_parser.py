#!/usr/bin/env python3
"""
Hook Parser Module for Contextual Logging

This module provides clean, structured parsing of hook data files to generate
contextual summaries for Claude Code sessions. It replaces complex transcript
parsing with simple, reliable hook timeline analysis.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any


def load_hook_timeline(session_id: str, cycle_id: int, output_dir: Optional[str] = None) -> List[Dict]:
    """Load complete hook timeline for a specific session and cycle"""
    if output_dir is None:
        output_dir = "/Users/hanan/.claude/.claude"
    
    # Construct hook file path
    session_short = session_id[:8] if session_id else "unknown"
    hook_file = Path(output_dir) / f"session_{session_short}_cycle_{cycle_id}_hooks.jsonl"
    
    if not hook_file.exists():
        return []
    
    timeline = []
    try:
        with open(hook_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    timeline.append(entry)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading hook timeline: {e}")
        return []
    
    # Sort by timestamp to ensure chronological order
    timeline.sort(key=lambda x: x.get('timestamp', ''))
    return timeline


def identify_agent_boundaries(timeline: List[Dict]) -> Dict[str, List[Dict]]:
    """Identify agent boundaries and categorize hook events by agent"""
    main_agent_events = []
    subagent_events = []
    current_agent = "main"
    
    for event in timeline:
        hook_name = event.get('hook_name', '')
        tool_name = event.get('raw_data', {}).get('tool_name', '')
        
        # Task tool indicates subagent delegation
        if tool_name == 'Task' and hook_name == 'PreToolUse':
            current_agent = "subagent"  # Switch to subagent context after Task delegation
            main_agent_events.append(event)  # Delegation itself is main agent action
        elif tool_name == 'Task' and hook_name == 'PostToolUse':
            # Task completion - this is when subagent finishes and returns to main
            current_agent = "main"
            main_agent_events.append(event)
        elif hook_name == 'SubagentStop':
            # Subagent completion
            subagent_events.append(event)
            # Don't change current_agent yet - wait for Task PostToolUse
        elif hook_name == 'Stop':
            # Could be subagent stop or final stop
            event_name = event.get('raw_data', {}).get('hook_event_name', '')
            if event_name == 'SubagentStop':
                subagent_events.append(event)
            else:
                main_agent_events.append(event)
        else:
            # Regular tool events - assign based on current context
            if current_agent == "main":
                main_agent_events.append(event)
            elif current_agent == "subagent":
                # Between Task delegation and Task completion = subagent work
                subagent_events.append(event)
            else:
                # Default to main agent for unclear cases
                main_agent_events.append(event)
    
    return {
        'main_agent': main_agent_events,
        'subagent': subagent_events
    }


def extract_file_activities(timeline: List[Dict]) -> Dict[str, Dict]:
    """Extract file modification activities with rich context"""
    file_activities = {}
    agent_boundaries = identify_agent_boundaries(timeline)
    
    for agent_type, events in agent_boundaries.items():
        for event in events:
            if event.get('hook_name') not in ['PreToolUse', 'PostToolUse']:
                continue
                
            raw_data = event.get('raw_data', {})
            tool_name = raw_data.get('tool_name', '')
            
            # Focus on file modification tools
            if tool_name not in ['Write', 'Edit', 'MultiEdit']:
                continue
            
            tool_input = raw_data.get('tool_input', {})
            tool_response = raw_data.get('tool_response', {})
            file_path = tool_input.get('file_path', '')
            
            if not file_path:
                continue
            
            # Initialize file activity structure
            if file_path not in file_activities:
                file_activities[file_path] = {}
            
            if agent_type not in file_activities[file_path]:
                file_activities[file_path][agent_type] = {
                    'operations': [],
                    'edit_count': 0,
                    'reasons': [],
                    'patches': [],
                    'timestamps': []
                }
            
            activity = file_activities[file_path][agent_type]
            
            # Extract operation details
            if event.get('hook_name') == 'PostToolUse':
                activity['operations'].append(tool_name.lower())
                activity['edit_count'] += 1
                activity['timestamps'].append(event.get('timestamp', ''))
                
                # Extract patch data for actual changes
                if 'structuredPatch' in tool_response:
                    patches = tool_response['structuredPatch']
                    if patches:
                        activity['patches'].extend(patches)
                
                # Extract reason from tool context
                if tool_name == 'Write':
                    reason = "File creation"
                elif tool_name == 'Edit':
                    old_string = tool_input.get('old_string', '')
                    new_string = tool_input.get('new_string', '')
                    if len(old_string) > len(new_string):
                        reason = f"Removed content: {old_string[:50]}..."
                    elif len(new_string) > len(old_string):
                        reason = f"Added content: {new_string[:50]}..."
                    else:
                        reason = f"Modified content"
                elif tool_name == 'MultiEdit':
                    edits = tool_input.get('edits', [])
                    reason = f"Applied {len(edits)} edits"
                else:
                    reason = f"{tool_name} operation"
                
                activity['reasons'].append(reason)
    
    return file_activities


def extract_subagent_tasks(timeline: List[Dict]) -> Dict[str, Dict]:
    """Extract subagent delegation and work summary"""
    subagent_tasks = {}
    task_counter = 0
    
    for event in timeline:
        if event.get('hook_name') != 'PreToolUse':
            continue
            
        raw_data = event.get('raw_data', {})
        tool_name = raw_data.get('tool_name', '')
        
        if tool_name != 'Task':
            continue
        
        task_counter += 1
        tool_input = raw_data.get('tool_input', {})
        
        task_id = f"task_{task_counter}"
        subagent_tasks[task_id] = {
            'delegation_info': {
                'description': tool_input.get('description', ''),
                'prompt': tool_input.get('prompt', ''),
                'timestamp': event.get('timestamp', '')
            },
            'work_summary': {
                'status': 'delegated',
                'completion_time': None,
                'tools_used': 0,
                'files_modified': []
            }
        }
    
    # Find corresponding subagent work and completion
    agent_boundaries = identify_agent_boundaries(timeline)
    subagent_events = agent_boundaries.get('subagent', [])
    
    # Extract subagent work summary
    files_modified = set()
    tools_used = 0
    completion_time = None
    
    for event in subagent_events:
        if event.get('hook_name') == 'PostToolUse':
            tools_used += 1
            raw_data = event.get('raw_data', {})
            tool_input = raw_data.get('tool_input', {})
            file_path = tool_input.get('file_path', '')
            if file_path:
                files_modified.add(file_path)
        elif event.get('hook_name') == 'SubagentStop':
            completion_time = event.get('timestamp', '')
    
    # Update first task with summary (assuming single subagent per cycle for now)
    if subagent_tasks:
        first_task = list(subagent_tasks.values())[0]
        first_task['work_summary'].update({
            'status': 'completed' if completion_time else 'in_progress',
            'completion_time': completion_time,
            'tools_used': tools_used,
            'files_modified': list(files_modified)
        })
    
    return subagent_tasks


def extract_user_intent(timeline: List[Dict]) -> str:
    """Extract user intent from TodoWrite progression or other indicators"""
    todo_progression = []
    
    for event in timeline:
        if event.get('hook_name') != 'PostToolUse':
            continue
            
        raw_data = event.get('raw_data', {})
        tool_name = raw_data.get('tool_name', '')
        
        if tool_name != 'TodoWrite':
            continue
        
        tool_response = raw_data.get('tool_response', {})
        new_todos = tool_response.get('newTodos', [])
        
        # Extract task descriptions
        task_descriptions = [todo.get('content', '') for todo in new_todos]
        todo_progression.extend(task_descriptions)
    
    # Generate intent from todo progression
    if todo_progression:
        # Take unique tasks and create a summary
        unique_tasks = list(dict.fromkeys(todo_progression))  # Preserve order, remove duplicates
        if len(unique_tasks) <= 3:
            return "; ".join(unique_tasks)
        else:
            return f"Multi-step task: {unique_tasks[0]}... (and {len(unique_tasks)-1} more steps)"
    
    return "Unknown task"


def generate_contextual_summary(session_id: str, cycle_id: int, output_dir: Optional[str] = None) -> Dict:
    """Generate complete contextual summary from hook timeline"""
    timeline = load_hook_timeline(session_id, cycle_id, output_dir)
    
    if not timeline:
        return {"error": "No hook timeline found"}
    
    # Extract all components
    file_activities = extract_file_activities(timeline)
    subagent_tasks = extract_subagent_tasks(timeline)
    user_intent = extract_user_intent(timeline)
    agent_boundaries = identify_agent_boundaries(timeline)
    
    # Calculate metrics
    total_edits = sum(
        sum(agent['edit_count'] for agent in file_data.values())
        for file_data in file_activities.values()
    )
    
    # Generate final summary structure (compatible with existing format)
    return {
        "user_intent": user_intent,
        "total_edits_in_cycle": total_edits,
        "file_activities": file_activities,
        "subagent_tasks": subagent_tasks,
        "agents_involved": {
            "main_agent": len(agent_boundaries.get('main_agent', [])) > 0,
            "subagents": len(agent_boundaries.get('subagent', [])) > 0,
            "subagent_count": len(subagent_tasks)
        },
        "summary": {
            "files_modified": list(file_activities.keys()),
            "total_file_changes": total_edits,
            "involved_subagents": len(subagent_tasks) > 0,
            "primary_activity": determine_primary_activity(timeline, user_intent)
        },
        "timeline_metadata": {
            "total_hook_events": len(timeline),
            "start_time": timeline[0].get('timestamp') if timeline else None,
            "end_time": timeline[-1].get('timestamp') if timeline else None,
            "data_source": "hook_timeline"
        }
    }


def determine_primary_activity(timeline: List[Dict], user_intent: str) -> str:
    """Determine the main purpose of this request cycle"""
    if 'test' in user_intent.lower():
        return 'testing'
    
    # Count tool types
    tool_counts = {}
    for event in timeline:
        if event.get('hook_name') != 'PostToolUse':
            continue
        tool_name = event.get('raw_data', {}).get('tool_name', '')
        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
    
    # Determine primary activity based on tool usage
    if tool_counts.get('Edit', 0) + tool_counts.get('Write', 0) + tool_counts.get('MultiEdit', 0) > 0:
        return 'file_modification'
    elif tool_counts.get('Read', 0) + tool_counts.get('Grep', 0) + tool_counts.get('Glob', 0) > 0:
        return 'code_analysis'
    elif tool_counts.get('Task', 0) > 0:
        return 'delegated_work'
    else:
        return 'general_assistance'