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
        output_dir = "/Users/hanan/.claude/.claude/session_logs"
    
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
                
                # Extract reason from tool context - PRESERVE FULL CONTEXT
                if tool_name == 'Write':
                    reason = "File creation"
                elif tool_name == 'Edit':
                    old_string = tool_input.get('old_string', '')
                    new_string = tool_input.get('new_string', '')
                    if len(old_string) > len(new_string):
                        reason = f"Removed content: {old_string}"
                    elif len(new_string) > len(old_string):
                        reason = f"Added content: {new_string}"
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
    """Extract user intent from hook timeline - prioritize TodoWrite for structured tasks"""
    
    # FIRST PRIORITY: Extract from TodoWrite progression (structured tasks - MOST VALUABLE)
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
    
    # Generate intent from todo progression - PRESERVE FULL CONTEXT
    if todo_progression:
        # Take unique tasks and create a summary
        unique_tasks = list(dict.fromkeys(todo_progression))  # Preserve order, remove duplicates
        # Always return full context - don't truncate valuable information
        return "; ".join(unique_tasks)
    
    # SECOND PRIORITY: Fallback to transcript parsing (for read-only tasks)
    for event in timeline:
        user_intent = event.get('user_intent', '')
        if user_intent and user_intent != "Unknown task":
            return user_intent
    
    return "Unknown task"


def extract_phase_and_task_context(transcript_path: str) -> Dict:
    """Extract current phase and task numbers by scanning conversation log from bottom to top"""
    context = {
        "phase_number": None,
        "task_number": None,
        "phase_task_pair": None,
        "confidence": "none"
    }
    
    if not transcript_path or not Path(transcript_path).exists():
        return context
    
    try:
        # Read transcript lines in reverse order (bottom to top)
        with open(transcript_path, 'r') as f:
            lines = f.readlines()
        
        phase_pattern = r'(?i)(?:phase|step)\s*[#:]?\s*(\d+)'
        task_pattern = r'(?i)task\s*[#:]?\s*(\d+)'
        
        # Look for phase and task mentions in recent entries
        recent_phases = []
        recent_tasks = []
        
        # Scan from bottom up, looking at last 50 entries for recent context
        for line in reversed(lines[-50:]):
            try:
                entry = json.loads(line.strip())
                
                # Look in user messages and assistant messages
                content_sources = []
                if entry.get('type') == 'user' and 'message' in entry:
                    message_content = entry['message'].get('content', '')
                    if isinstance(message_content, str):
                        content_sources.append(message_content)
                elif entry.get('type') == 'assistant' and 'message' in entry:
                    message_content = entry['message'].get('content', [])
                    if isinstance(message_content, list):
                        for content_item in message_content:
                            if isinstance(content_item, dict):
                                if content_item.get('type') == 'text':
                                    content_sources.append(content_item.get('text', ''))
                                elif content_item.get('type') == 'thinking':
                                    content_sources.append(content_item.get('thinking', ''))
                
                # Search for phase and task numbers in content
                for content in content_sources:
                    import re
                    
                    phase_matches = re.findall(phase_pattern, content)
                    task_matches = re.findall(task_pattern, content)
                    
                    # Store recent mentions with their proximity
                    for match in phase_matches:
                        recent_phases.append(int(match))
                    for match in task_matches:
                        recent_tasks.append(int(match))
                    
                    # Look for phase and task mentioned together (high confidence)
                    combined_pattern = r'(?i)(?:phase|step)\s*[#:]?\s*(\d+).*?task\s*[#:]?\s*(\d+)|task\s*[#:]?\s*(\d+).*?(?:phase|step)\s*[#:]?\s*(\d+)'
                    combined_matches = re.findall(combined_pattern, content)
                    
                    for match in combined_matches:
                        if match[0] and match[1]:  # phase first, then task
                            context.update({
                                "phase_number": int(match[0]),
                                "task_number": int(match[1]),
                                "phase_task_pair": f"Phase {match[0]}, Task {match[1]}",
                                "confidence": "high"
                            })
                            return context
                        elif match[2] and match[3]:  # task first, then phase
                            context.update({
                                "phase_number": int(match[3]),
                                "task_number": int(match[2]),
                                "phase_task_pair": f"Phase {match[3]}, Task {match[2]}",
                                "confidence": "high"
                            })
                            return context
                            
            except (json.JSONDecodeError, ValueError, KeyError):
                continue
        
        # If no combined mention found, use most recent individual mentions
        if recent_phases and recent_tasks:
            # Use the most recent mentions
            context.update({
                "phase_number": recent_phases[0],
                "task_number": recent_tasks[0], 
                "phase_task_pair": f"Phase {recent_phases[0]}, Task {recent_tasks[0]}",
                "confidence": "medium"
            })
        elif recent_phases:
            context.update({
                "phase_number": recent_phases[0],
                "phase_task_pair": f"Phase {recent_phases[0]}",
                "confidence": "low"
            })
        elif recent_tasks:
            context.update({
                "task_number": recent_tasks[0],
                "phase_task_pair": f"Task {recent_tasks[0]}",
                "confidence": "low"
            })
        
    except Exception as e:
        # Return empty context on any error
        pass
    
    return context


def generate_contextual_summary(session_id: str, cycle_id: int, output_dir: Optional[str] = None, transcript_path: Optional[str] = None) -> Dict:
    """Generate complete contextual summary from hook timeline"""
    timeline = load_hook_timeline(session_id, cycle_id, output_dir)
    
    if not timeline:
        return {"error": "No hook timeline found"}
    
    # Extract all components
    file_activities = extract_file_activities(timeline)
    subagent_tasks = extract_subagent_tasks(timeline)
    user_intent = extract_user_intent(timeline)
    agent_boundaries = identify_agent_boundaries(timeline)
    
    # Extract phase and task context from transcript
    phase_task_context = extract_phase_and_task_context(transcript_path) if transcript_path else {
        "phase_number": None,
        "task_number": None,
        "phase_task_pair": None,
        "confidence": "none"
    }
    
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
        "project_context": {
            "phase_number": phase_task_context.get("phase_number"),
            "task_number": phase_task_context.get("task_number"),
            "phase_task_pair": phase_task_context.get("phase_task_pair"),
            "context_confidence": phase_task_context.get("confidence")
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


def generate_cycle_summary_file(session_id: str, cycle_id: int, output_dir: Optional[str] = None, transcript_path: Optional[str] = None) -> Dict:
    """Generate and save a comprehensive cycle summary JSON file"""
    if output_dir is None:
        output_dir = "/Users/hanan/.claude/.claude/session_logs"
    
    # Generate the contextual summary
    summary = generate_contextual_summary(session_id, cycle_id, output_dir, transcript_path)
    
    if "error" in summary:
        return summary
    
    # Create enhanced cycle summary with additional metadata
    cycle_summary = {
        "cycle_metadata": {
            "session_id": session_id,
            "cycle_id": cycle_id,
            "generated_at": datetime.now().isoformat(),
            "data_source": "hook_timeline",
            "parser_version": "1.0"
        },
        "user_intent": summary.get("user_intent", "Unknown"),
        "execution_summary": {
            "total_edits": summary.get("total_edits_in_cycle", 0),
            "files_modified": len(summary.get("file_activities", {})),
            "subagents_used": len(summary.get("subagent_tasks", {})),
            "primary_activity": summary.get("summary", {}).get("primary_activity", "unknown"),
            "agents_involved": summary.get("agents_involved", {})
        },
        "project_context": summary.get("project_context", {}),
        "file_activities": summary.get("file_activities", {}),
        "subagent_tasks": summary.get("subagent_tasks", {}),
        "timeline_metadata": summary.get("timeline_metadata", {}),
        "workflow_insights": {
            "file_change_patterns": extract_file_change_patterns(summary.get("file_activities", {})),
            "agent_collaboration": analyze_agent_collaboration(summary.get("file_activities", {}), summary.get("subagent_tasks", {})),
            "task_complexity": assess_task_complexity(summary)
        }
    }
    
    # Save cycle summary to file
    session_short = session_id[:8] if session_id else "unknown"
    summary_file = Path(output_dir) / f"session_{session_short}_cycle_{cycle_id}_summary.json"
    
    try:
        with open(summary_file, 'w') as f:
            json.dump(cycle_summary, f, indent=2)
        
        cycle_summary["summary_file_path"] = str(summary_file)
        return cycle_summary
        
    except Exception as e:
        return {"error": f"Failed to save cycle summary: {str(e)}"}


def extract_file_change_patterns(file_activities: Dict) -> Dict:
    """Extract patterns from file modification activities"""
    patterns = {
        "multi_agent_files": [],
        "main_agent_only": [],
        "subagent_only": [],
        "heavy_edit_files": [],
        "operation_types": {}
    }
    
    for file_path, agents in file_activities.items():
        file_name = Path(file_path).name
        agent_types = list(agents.keys())
        total_edits = sum(agent_data['edit_count'] for agent_data in agents.values())
        
        # Categorize by agent involvement
        if len(agent_types) > 1:
            patterns["multi_agent_files"].append(file_name)
        elif "main_agent" in agent_types:
            patterns["main_agent_only"].append(file_name)
        elif "subagent" in agent_types:
            patterns["subagent_only"].append(file_name)
        
        # Track heavy editing
        if total_edits > 2:
            patterns["heavy_edit_files"].append({
                "file": file_name,
                "edit_count": total_edits,
                "agents": agent_types
            })
        
        # Track operation types
        for agent_data in agents.values():
            for operation in agent_data.get('operations', []):
                patterns["operation_types"][operation] = patterns["operation_types"].get(operation, 0) + 1
    
    return patterns


def analyze_agent_collaboration(file_activities: Dict, subagent_tasks: Dict) -> Dict:
    """Analyze how main agent and subagents collaborated"""
    collaboration = {
        "collaboration_type": "none",
        "handoff_files": [],
        "parallel_work": False,
        "delegation_effectiveness": "unknown"
    }
    
    # Check for file handoffs between agents
    for file_path, agents in file_activities.items():
        if len(agents) > 1:
            collaboration["handoff_files"].append(Path(file_path).name)
            collaboration["collaboration_type"] = "sequential"
    
    # Assess delegation effectiveness
    if subagent_tasks:
        completed_tasks = sum(1 for task in subagent_tasks.values() 
                            if task['work_summary']['status'] == 'completed')
        total_tasks = len(subagent_tasks)
        
        if completed_tasks == total_tasks:
            collaboration["delegation_effectiveness"] = "excellent"
        elif completed_tasks > total_tasks * 0.5:
            collaboration["delegation_effectiveness"] = "good"
        else:
            collaboration["delegation_effectiveness"] = "poor"
    
    return collaboration


def assess_task_complexity(summary: Dict) -> Dict:
    """Assess the complexity of the completed task"""
    complexity = {
        "level": "simple",
        "factors": [],
        "score": 0
    }
    
    # Factor scoring
    file_count = len(summary.get("file_activities", {}))
    edit_count = summary.get("total_edits_in_cycle", 0)
    subagent_count = len(summary.get("subagent_tasks", {}))
    timeline_events = summary.get("timeline_metadata", {}).get("total_hook_events", 0)
    
    score = 0
    
    # File complexity
    if file_count > 3:
        complexity["factors"].append("multiple files modified")
        score += 2
    elif file_count > 1:
        score += 1
    
    # Edit complexity  
    if edit_count > 5:
        complexity["factors"].append("many file modifications")
        score += 2
    elif edit_count > 2:
        score += 1
    
    # Collaboration complexity
    if subagent_count > 0:
        complexity["factors"].append("subagent delegation")
        score += 2
    
    # Timeline complexity
    if timeline_events > 20:
        complexity["factors"].append("extensive tool usage")
        score += 1
    
    # Determine level
    if score >= 5:
        complexity["level"] = "complex"
    elif score >= 3:
        complexity["level"] = "moderate"
    else:
        complexity["level"] = "simple"
    
    complexity["score"] = score
    return complexity