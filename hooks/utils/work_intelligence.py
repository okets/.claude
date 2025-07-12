#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import json
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Import database utility
sys.path.append(str(Path(__file__).parent))
from db import get_db

class WorkIntelligence:
    def __init__(self, project_path: str = None):
        self.db = get_db()
        self.project_path = project_path or str(Path.cwd())
        self.project_id = None
        
        if self.db.connection:
            project_name = Path(self.project_path).name
            self.project_id = self.db.ensure_project(self.project_path, project_name)
    
    def parse_query(self, query: str, days: int = 7) -> Dict[str, Any]:
        """Parse natural language query and determine intent"""
        query_lower = query.lower().strip()
        
        # Query patterns and their intents
        patterns = {
            'recent_activity': [
                r'what.*work.*today', r'recent.*changes?', r'today.*activity',
                r'latest.*work', r'current.*progress', r'overview'
            ],
            'file_relationships': [
                r'files.*related.*to', r'files.*together', r'relationships?',
                r'commonly.*modified', r'co.*modified', r'file.*connections?'
            ],
            'active_tasks': [
                r'active.*tasks?', r'current.*tasks?', r'todo', r'in.*progress',
                r'what.*working.*on', r'assignments?'
            ],
            'phase_progress': [
                r'phase.*progress', r'phase.*status', r'.*phase.*complete',
                r'testing.*phase', r'development.*phase'
            ],
            'security_events': [
                r'blocked.*operations?', r'security.*warnings?', r'failed.*tools?',
                r'errors?', r'blocked', r'security'
            ],
            'patterns': [
                r'workflows?', r'patterns?', r'how.*usually', r'common.*way',
                r'typical.*process', r'debugging.*patterns?'
            ],
            'git_operations': [
                r'git.*operations?', r'commits?', r'pushes?', r'git.*history',
                r'version.*control'
            ],
            'tool_usage': [
                r'tool.*usage', r'tools.*used', r'commands?.*run',
                r'bash.*commands?', r'shell.*operations?'
            ],
            'conversations_by_file': [
                r'conversations?.*about.*file', r'sessions?.*involving.*file',
                r'last.*tasks?.*involving', r'history.*of.*file', r'work.*on.*file'
            ],
            'conversations_by_phase': [
                r'conversations?.*about.*phase', r'sessions?.*in.*phase',
                r'what.*did.*in.*phase', r'work.*in.*phase', r'phase.*history'
            ],
            'conversations_by_task': [
                r'conversations?.*about.*task', r'sessions?.*for.*task',
                r'work.*on.*task', r'task.*history', r'last.*time.*worked.*on'
            ],
            'conversations_by_model': [
                r'bugs.*fixed.*by.*opus', r'work.*by.*model', r'conversations?.*handled.*by',
                r'opus.*sessions?', r'sonnet.*sessions?', r'what.*model.*did'
            ],
            'lessons_learned': [
                r'lessons?.*learned', r'what.*learned.*about', r'insights?.*from',
                r'takeaways?', r'discoveries?', r'findings?'
            ],
            'chain_of_thought': [
                r'chain.*of.*thought', r'reasoning.*steps?', r'how.*solved',
                r'thought.*process', r'approach.*to', r'steps?.*taken'
            ],
            'subagent_usage': [
                r'subagents?.*used', r'tasks?.*used.*subagents?', r'which.*tasks?.*needed.*help',
                r'delegated.*tasks?', r'agent.*assistance'
            ]
        }
        
        # Determine query intent
        intent = 'recent_activity'  # default
        for intent_type, intent_patterns in patterns.items():
            for pattern in intent_patterns:
                if re.search(pattern, query_lower):
                    intent = intent_type
                    break
            if intent != 'recent_activity':
                break
        
        # Extract entities (file names, phase names, etc.)
        entities = self._extract_entities(query)
        
        # Calculate time range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return {
            'intent': intent,
            'entities': entities,
            'start_date': start_date,
            'end_date': end_date,
            'original_query': query
        }
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract file names, phase names, etc. from query"""
        entities = {
            'files': [],
            'phases': [],
            'tools': [],
            'intents': []
        }
        
        # Extract file patterns
        file_patterns = [
            r'([a-zA-Z0-9_-]+\.[a-zA-Z]{1,4})',  # file.ext
            r'(src/[a-zA-Z0-9_/-]+)',  # src paths
            r'(components?/[a-zA-Z0-9_/-]+)',  # component paths
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, query)
            entities['files'].extend(matches)
        
        # Extract common phase names
        phase_keywords = ['setup', 'development', 'testing', 'deployment', 'authentication', 'ui', 'api']
        for keyword in phase_keywords:
            if keyword in query.lower():
                entities['phases'].append(keyword)
        
        # Extract tool names
        tool_keywords = ['bash', 'git', 'npm', 'test', 'build', 'edit', 'read']
        for keyword in tool_keywords:
            if keyword in query.lower():
                entities['tools'].append(keyword)
        
        return entities
    
    def execute_query(self, parsed_query: Dict[str, Any], limit: int = 20) -> Dict[str, Any]:
        """Execute the parsed query and return results"""
        intent = parsed_query['intent']
        entities = parsed_query['entities']
        start_date = parsed_query['start_date']
        end_date = parsed_query['end_date']
        
        if not self.db.connection or not self.project_id:
            return {
                'error': 'Long-term context database not available',
                'message': 'Use Claude Code to perform some operations first to initialize the database',
                'suggestion': 'Try reading or editing files to build up context data'
            }
        
        try:
            with self.db.connection.cursor() as cursor:
                if intent == 'recent_activity':
                    return self._query_recent_activity(cursor, start_date, end_date, limit)
                elif intent == 'file_relationships':
                    return self._query_file_relationships(cursor, entities['files'], limit)
                elif intent == 'active_tasks':
                    return self._query_active_tasks(cursor, limit)
                elif intent == 'phase_progress':
                    return self._query_phase_progress(cursor, entities['phases'], limit)
                elif intent == 'security_events':
                    return self._query_security_events(cursor, start_date, end_date, limit)
                elif intent == 'patterns':
                    return self._query_patterns(cursor, entities, limit)
                elif intent == 'git_operations':
                    return self._query_git_operations(cursor, start_date, end_date, limit)
                elif intent == 'tool_usage':
                    return self._query_tool_usage(cursor, start_date, end_date, limit)
                elif intent == 'conversations_by_file':
                    return self._query_conversations_by_file(cursor, entities['files'], limit)
                elif intent == 'conversations_by_phase':
                    return self._query_conversations_by_phase(cursor, entities['phases'], limit)
                elif intent == 'conversations_by_task':
                    return self._query_conversations_by_task(cursor, entities['tools'] + entities['phases'], limit)
                elif intent == 'conversations_by_model':
                    return self._query_conversations_by_model(cursor, entities, limit)
                elif intent == 'lessons_learned':
                    return self._query_lessons_learned(cursor, entities, limit)
                elif intent == 'chain_of_thought':
                    return self._query_chain_of_thought(cursor, entities, limit)
                elif intent == 'subagent_usage':
                    return self._query_subagent_usage(cursor, start_date, end_date, limit)
                else:
                    return self._query_recent_activity(cursor, start_date, end_date, limit)
                    
        except Exception as e:
            return {'error': f"Database query failed: {e}", 'results': []}
    
    def _query_recent_activity(self, cursor, start_date, end_date, limit):
        """Query recent tool executions and activity"""
        cursor.execute("""
            SELECT te.tool_name, te.intent, te.files_touched, te.executed_at,
                   te.success, te.duration_ms
            FROM tool_executions te
            JOIN sessions s ON te.chat_session_id = s.id
            WHERE s.project_id = ?
            AND te.executed_at BETWEEN ? AND ?
            ORDER BY te.executed_at DESC
            LIMIT ?
        """, (self.project_id, start_date, end_date, limit))
        
        executions = cursor.fetchall()
        
        # Group by intent and count
        intent_summary = defaultdict(int)
        file_activity = defaultdict(int)
        
        for exec in executions:
            intent_summary[exec['intent']] += 1
            if exec['files_touched']:
                files = json.loads(exec['files_touched']) if isinstance(exec['files_touched'], str) else exec['files_touched']
                for file_path in files:
                    file_name = Path(file_path).name
                    file_activity[file_name] += 1
        
        return {
            'type': 'recent_activity',
            'executions': executions,
            'summary': {
                'total_operations': len(executions),
                'intent_breakdown': dict(intent_summary),
                'most_active_files': dict(sorted(file_activity.items(), key=lambda x: x[1], reverse=True)[:10])
            }
        }
    
    def _query_file_relationships(self, cursor, file_filters, limit):
        """Query file co-modification relationships"""
        if file_filters:
            # Query specific file relationships - build SQLite-compatible query
            conditions = []
            params = [self.project_id]
            
            for f in file_filters:
                conditions.append("(file1_path LIKE ? OR file2_path LIKE ?)")
                params.extend([f'%{f}%', f'%{f}%'])
            
            where_clause = " OR ".join(conditions)
            params.append(limit)
            
            cursor.execute(f"""
                SELECT file1_path, file2_path, co_modification_count, last_modified_together
                FROM file_relationships
                WHERE project_id = ? AND ({where_clause})
                ORDER BY co_modification_count DESC
                LIMIT ?
            """, params)
        else:
            # Query all relationships
            cursor.execute("""
                SELECT file1_path, file2_path, co_modification_count, last_modified_together
                FROM file_relationships
                WHERE project_id = ?
                ORDER BY co_modification_count DESC
                LIMIT ?
            """, (self.project_id, limit))
        
        relationships = cursor.fetchall()
        
        return {
            'type': 'file_relationships',
            'relationships': relationships,
            'summary': {
                'total_relationships': len(relationships),
                'strongest_connection': relationships[0] if relationships else None
            }
        }
    
    def _query_active_tasks(self, cursor, limit):
        """Query active tasks and assignments"""
        cursor.execute("""
            SELECT ph.name as phase_name, t.name as task_name,
                   t.description, t.status, t.priority, t.created_at,
                   COUNT(a.id) as assignment_count,
                   COUNT(CASE WHEN a.status = 'completed' THEN 1 END) as completed_assignments
            FROM tasks t
            JOIN phases ph ON t.phase_id = ph.id
            LEFT JOIN assignments a ON t.id = a.task_id
            WHERE ph.project_id = ? AND t.status IN ('todo', 'in_progress')
            GROUP BY t.id, ph.id
            ORDER BY t.priority DESC, t.created_at
            LIMIT ?
        """, (self.project_id, limit))
        
        tasks = cursor.fetchall()
        
        return {
            'type': 'active_tasks',
            'tasks': tasks,
            'summary': {
                'total_active_tasks': len(tasks),
                'high_priority_tasks': len([t for t in tasks if t['priority'] == 'high']),
                'in_progress_tasks': len([t for t in tasks if t['status'] == 'in_progress'])
            }
        }
    
    def _query_phase_progress(self, cursor, phase_filters, limit):
        """Query phase progress and status"""
        if phase_filters:
            # Build SQLite-compatible query
            conditions = []
            params = [self.project_id]
            
            for f in phase_filters:
                conditions.append("ph.name LIKE ?")
                params.append(f'%{f}%')
            
            where_clause = " OR ".join(conditions)
            params.append(limit)
            
            cursor.execute(f"""
                SELECT ph.name, ph.description, ph.status, ph.started_at, ph.completed_at,
                       COUNT(t.id) as total_tasks,
                       COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_tasks,
                       COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) as in_progress_tasks
                FROM phases ph
                LEFT JOIN tasks t ON ph.id = t.phase_id
                WHERE ph.project_id = ? AND ({where_clause})
                GROUP BY ph.id
                ORDER BY ph.created_at
                LIMIT ?
            """, params)
        else:
            cursor.execute("""
                SELECT ph.name, ph.description, ph.status, ph.started_at, ph.completed_at,
                       COUNT(t.id) as total_tasks,
                       COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_tasks,
                       COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) as in_progress_tasks
                FROM phases ph
                LEFT JOIN tasks t ON ph.id = t.phase_id
                WHERE ph.project_id = ?
                GROUP BY ph.id
                ORDER BY ph.created_at
                LIMIT ?
            """, (self.project_id, limit))
        
        phases = cursor.fetchall()
        
        return {
            'type': 'phase_progress',
            'phases': phases,
            'summary': {
                'total_phases': len(phases),
                'active_phases': len([p for p in phases if p['status'] == 'active']),
                'completed_phases': len([p for p in phases if p['status'] == 'completed'])
            }
        }
    
    def _query_security_events(self, cursor, start_date, end_date, limit):
        """Query security events and blocked operations"""
        cursor.execute("""
            SELECT event_type, tool_name, reason, created_at, tool_input
            FROM security_events se
            JOIN sessions s ON se.chat_session_id = s.id
            WHERE s.project_id = ?
            AND se.created_at BETWEEN ? AND ?
            ORDER BY se.created_at DESC
            LIMIT ?
        """, (self.project_id, start_date, end_date, limit))
        
        events = cursor.fetchall()
        
        return {
            'type': 'security_events',
            'events': events,
            'summary': {
                'total_events': len(events),
                'blocked_operations': len([e for e in events if e['event_type'] == 'blocked']),
                'warnings': len([e for e in events if e['event_type'] == 'warned'])
            }
        }
    
    def _query_patterns(self, cursor, entities, limit):
        """Query work patterns and common workflows"""
        cursor.execute("""
            SELECT pattern_name, tool_sequence, frequency_count, last_used
            FROM work_patterns
            WHERE project_id = ?
            ORDER BY frequency_count DESC
            LIMIT ?
        """, (self.project_id, limit))
        
        patterns = cursor.fetchall()
        
        return {
            'type': 'patterns',
            'patterns': patterns,
            'summary': {
                'total_patterns': len(patterns),
                'most_common_pattern': patterns[0] if patterns else None
            }
        }
    
    def _query_git_operations(self, cursor, start_date, end_date, limit):
        """Query git-related operations"""
        cursor.execute("""
            SELECT te.tool_input, te.executed_at, te.success, te.files_touched
            FROM tool_executions te
            JOIN sessions s ON te.chat_session_id = s.id
            WHERE s.project_id = ?
            AND te.intent = 'git-operation'
            AND te.executed_at BETWEEN ? AND ?
            ORDER BY te.executed_at DESC
            LIMIT ?
        """, (self.project_id, start_date, end_date, limit))
        
        git_ops = cursor.fetchall()
        
        return {
            'type': 'git_operations',
            'operations': git_ops,
            'summary': {
                'total_git_operations': len(git_ops),
                'successful_operations': len([op for op in git_ops if op['success']])
            }
        }
    
    def _query_tool_usage(self, cursor, start_date, end_date, limit):
        """Query tool usage statistics"""
        cursor.execute("""
            SELECT tool_name, intent, COUNT(*) as usage_count,
                   AVG(duration_ms) as avg_duration,
                   COUNT(CASE WHEN success = false THEN 1 END) as failure_count
            FROM tool_executions te
            JOIN sessions s ON te.chat_session_id = s.id
            WHERE s.project_id = ?
            AND te.executed_at BETWEEN ? AND ?
            GROUP BY tool_name, intent
            ORDER BY usage_count DESC
            LIMIT ?
        """, (self.project_id, start_date, end_date, limit))
        
        usage = cursor.fetchall()
        
        return {
            'type': 'tool_usage',
            'usage': usage,
            'summary': {
                'most_used_tool': usage[0]['tool_name'] if usage else None,
                'total_tool_types': len(set(u['tool_name'] for u in usage))
            }
        }
    
    def _query_conversations_by_file(self, cursor, file_filters, limit):
        """Query conversations that mentioned specific files"""
        if not file_filters:
            return {'type': 'conversations_by_file', 'conversations': [], 'error': 'No file specified'}
        
        all_conversations = []
        for file_filter in file_filters:
            conversations = self.db.get_conversations_by_file(self.project_id, file_filter, limit)
            all_conversations.extend(conversations)
        
        # Remove duplicates and sort by date
        unique_conversations = []
        seen_ids = set()
        for conv in sorted(all_conversations, key=lambda x: x.get('created_at', ''), reverse=True):
            conv_id = f"{conv.get('created_at', '')}-{conv.get('summary', '')[:50]}"
            if conv_id not in seen_ids:
                seen_ids.add(conv_id)
                unique_conversations.append(conv)
        
        return {
            'type': 'conversations_by_file',
            'conversations': unique_conversations[:limit],
            'file_filters': file_filters,
            'summary': {
                'total_conversations': len(unique_conversations),
                'files_queried': file_filters
            }
        }
    
    def _query_conversations_by_phase(self, cursor, phase_filters, limit):
        """Query conversations related to specific phases"""
        if not phase_filters:
            # Get all active phases if none specified
            cursor.execute("""
                SELECT name FROM phases 
                WHERE project_id = ? AND status IN ('active', 'in_progress')
                LIMIT 3
            """, (self.project_id,))
            phase_filters = [row['name'] for row in cursor.fetchall()]
        
        all_conversations = []
        for phase_filter in phase_filters:
            conversations = self.db.get_conversations_by_phase(self.project_id, phase_filter, limit)
            all_conversations.extend(conversations)
        
        return {
            'type': 'conversations_by_phase',
            'conversations': all_conversations[:limit],
            'phase_filters': phase_filters,
            'summary': {
                'total_conversations': len(all_conversations),
                'phases_queried': phase_filters
            }
        }
    
    def _query_conversations_by_task(self, cursor, task_filters, limit):
        """Query conversations related to specific tasks"""
        if not task_filters:
            # Get active tasks if none specified
            cursor.execute("""
                SELECT t.name FROM tasks t
                JOIN phases p ON t.phase_id = p.id
                WHERE p.project_id = ? AND t.status IN ('todo', 'in_progress')
                LIMIT 3
            """, (self.project_id,))
            task_filters = [row['name'] for row in cursor.fetchall()]
        
        all_conversations = []
        for task_filter in task_filters:
            conversations = self.db.get_conversations_by_task(self.project_id, task_filter, limit)
            all_conversations.extend(conversations)
        
        return {
            'type': 'conversations_by_task',
            'conversations': all_conversations[:limit],
            'task_filters': task_filters,
            'summary': {
                'total_conversations': len(all_conversations),
                'tasks_queried': task_filters
            }
        }
    
    
    def format_results(self, results: Dict[str, Any], format_type: str = 'summary') -> str:
        """Format query results for display"""
        if 'error' in results:
            return f"❌ Error: {results['error']}"
        
        if format_type == 'json':
            return json.dumps(results, indent=2, default=str)
        
        return self._format_summary(results)
    
    def _query_conversations_by_model(self, cursor, entities, limit):
        """Query conversations handled by specific AI models"""
        # Extract model names from query
        model_names = []
        for model in ['opus', 'sonnet', 'claude-3-opus', 'claude-3-sonnet']:
            if any(model in entity.lower() for entity_list in entities.values() for entity in entity_list):
                model_names.append(f'%{model}%')
        
        if not model_names:
            model_names = ['%opus%', '%sonnet%']  # Default to common models
        
        conversations = []
        for model_pattern in model_names:
            convs = self.db.get_conversations_by_model(self.project_id, model_pattern, limit)
            conversations.extend(convs)
        
        return {
            'type': 'conversations_by_model',
            'conversations': conversations[:limit],
            'models_queried': model_names,
            'summary': {
                'total_conversations': len(conversations),
                'models': list(set(c.get('agent_model', 'unknown') for c in conversations))
            }
        }
    
    def _query_lessons_learned(self, cursor, entities, limit):
        """Query lessons learned from conversations"""
        # Extract topic filters if any
        topic = None
        if entities.get('tools') or entities.get('phases'):
            topic = ' '.join(entities.get('tools', []) + entities.get('phases', []))
        
        lessons = self.db.get_lessons_learned(self.project_id, topic, limit)
        
        # Flatten all lessons into a single list
        all_lessons = []
        for conv in lessons:
            if conv.get('lessons_learned'):
                for lesson in conv['lessons_learned']:
                    all_lessons.append({
                        'lesson': lesson,
                        'session_id': conv['chat_session_id'],
                        'summary': conv.get('agent_summary', ''),
                        'date': conv['created_at']
                    })
        
        return {
            'type': 'lessons_learned',
            'lessons': all_lessons,
            'topic_filter': topic,
            'summary': {
                'total_lessons': len(all_lessons),
                'conversations_with_lessons': len(lessons)
            }
        }
    
    def _query_chain_of_thought(self, cursor, entities, limit):
        """Query chain of thought for recent conversations"""
        # Get recent conversation details
        cursor.execute("""
            SELECT cd.*, cs.summary
            FROM conversation_details cd
            LEFT JOIN conversation_summaries cs ON cd.chat_session_id = cs.chat_session_id
            WHERE cd.project_id = ? 
            AND cd.agent_chain_of_thought IS NOT NULL
            ORDER BY cd.created_at DESC
            LIMIT ?
        """, (self.project_id, limit))
        
        conversations = []
        for row in cursor.fetchall():
            conv = dict(row)
            if conv.get('agent_chain_of_thought'):
                try:
                    conv['agent_chain_of_thought'] = json.loads(conv['agent_chain_of_thought'])
                except:
                    pass
            conversations.append(conv)
        
        return {
            'type': 'chain_of_thought',
            'conversations': conversations,
            'summary': {
                'total_conversations': len(conversations),
                'avg_steps': sum(len(c.get('agent_chain_of_thought', [])) for c in conversations) / len(conversations) if conversations else 0
            }
        }
    
    def _query_subagent_usage(self, cursor, start_date, end_date, limit):
        """Query subagent usage and delegated tasks"""
        cursor.execute("""
            SELECT se.*, cd.user_request_summary
            FROM subagent_executions se
            JOIN conversation_details cd ON se.parent_conversation_id = cd.id
            WHERE se.started_at BETWEEN ? AND ?
            ORDER BY se.started_at DESC
            LIMIT ?
        """, (start_date, end_date, limit))
        
        subagents = cursor.fetchall()
        
        # Group by model
        model_usage = defaultdict(int)
        task_types = defaultdict(int)
        
        for subagent in subagents:
            model_usage[subagent['subagent_model']] += 1
            # Simple task categorization
            task_lower = subagent['subagent_task'].lower()
            if 'analyz' in task_lower or 'understand' in task_lower:
                task_types['analysis'] += 1
            elif 'search' in task_lower or 'find' in task_lower:
                task_types['search'] += 1
            elif 'implement' in task_lower or 'code' in task_lower:
                task_types['implementation'] += 1
            else:
                task_types['other'] += 1
        
        return {
            'type': 'subagent_usage',
            'subagents': subagents,
            'summary': {
                'total_subagent_calls': len(subagents),
                'model_breakdown': dict(model_usage),
                'task_categories': dict(task_types)
            }
        }
    
    def _format_summary(self, results: Dict[str, Any]) -> str:
        """Format results as human-readable summary"""
        result_type = results.get('type', 'unknown')
        
        if result_type == 'recent_activity':
            return self._format_recent_activity(results)
        elif result_type == 'file_relationships':
            return self._format_file_relationships(results)
        elif result_type == 'active_tasks':
            return self._format_active_tasks(results)
        elif result_type == 'phase_progress':
            return self._format_phase_progress(results)
        elif result_type == 'security_events':
            return self._format_security_events(results)
        elif result_type == 'conversations_by_file':
            return self._format_conversations_by_file(results)
        elif result_type == 'conversations_by_phase':
            return self._format_conversations_by_phase(results)
        elif result_type == 'conversations_by_task':
            return self._format_conversations_by_task(results)
        elif result_type == 'conversations_by_model':
            return self._format_conversations_by_model(results)
        elif result_type == 'lessons_learned':
            return self._format_lessons_learned(results)
        elif result_type == 'chain_of_thought':
            return self._format_chain_of_thought(results)
        elif result_type == 'subagent_usage':
            return self._format_subagent_usage(results)
        else:
            return f"📊 Query Results ({result_type}):\n{json.dumps(results, indent=2, default=str)}"
    
    def _format_recent_activity(self, results: Dict[str, Any]) -> str:
        """Format recent activity results"""
        summary = results['summary']
        executions = results['executions'][:5]  # Show top 5
        
        output = [
            "📈 Recent Activity Summary:",
            f"   Total Operations: {summary['total_operations']}",
            "",
            "🎯 Intent Breakdown:"
        ]
        
        for intent, count in summary['intent_breakdown'].items():
            output.append(f"   {intent}: {count}")
        
        output.extend([
            "",
            "📁 Most Active Files:"
        ])
        
        for file_name, count in list(summary['most_active_files'].items())[:5]:
            output.append(f"   {file_name}: {count} modifications")
        
        output.extend([
            "",
            "🕒 Recent Operations:"
        ])
        
        for exec in executions:
            timestamp = exec['executed_at'].strftime('%H:%M')
            success_icon = "✅" if exec['success'] else "❌"
            output.append(f"   {timestamp} {success_icon} {exec['tool_name']} - {exec['intent']}")
        
        return "\n".join(output)
    
    def _format_file_relationships(self, results: Dict[str, Any]) -> str:
        """Format file relationship results"""
        relationships = results['relationships'][:10]  # Show top 10
        
        output = [
            "🔗 File Relationships:",
            f"   Found {len(relationships)} relationships",
            ""
        ]
        
        for rel in relationships:
            file1 = Path(rel['file1_path']).name
            file2 = Path(rel['file2_path']).name
            count = rel['co_modification_count']
            output.append(f"   {file1} ↔ {file2} ({count} times)")
        
        return "\n".join(output)
    
    def _format_active_tasks(self, results: Dict[str, Any]) -> str:
        """Format active tasks results"""
        tasks = results['tasks']
        summary = results['summary']
        
        output = [
            "📋 Active Tasks:",
            f"   Total: {summary['total_active_tasks']} | High Priority: {summary['high_priority_tasks']} | In Progress: {summary['in_progress_tasks']}",
            ""
        ]
        
        for task in tasks:
            priority_icon = "🔴" if task['priority'] == 'high' else "🟡" if task['priority'] == 'medium' else "🟢"
            status_icon = "🚧" if task['status'] == 'in_progress' else "📝"
            progress = f"{task['completed_assignments']}/{task['assignment_count']}" if task['assignment_count'] > 0 else "0/0"
            
            output.append(f"   {priority_icon} {status_icon} [{task['phase_name']}] {task['task_name']} ({progress})")
        
        return "\n".join(output)
    
    def _format_phase_progress(self, results: Dict[str, Any]) -> str:
        """Format phase progress results"""
        phases = results['phases']
        
        output = [
            "🎯 Phase Progress:",
            ""
        ]
        
        for phase in phases:
            status_icon = {"planning": "📋", "active": "🚧", "completed": "✅", "paused": "⏸️"}.get(phase['status'], "❓")
            total_tasks = phase['total_tasks'] or 0
            completed_tasks = phase['completed_tasks'] or 0
            progress_pct = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
            
            output.append(f"   {status_icon} {phase['name']} - {progress_pct}% ({completed_tasks}/{total_tasks} tasks)")
        
        return "\n".join(output)
    
    def _format_security_events(self, results: Dict[str, Any]) -> str:
        """Format security events results"""
        events = results['events'][:10]  # Show recent 10
        summary = results['summary']
        
        output = [
            "🛡️ Security Events:",
            f"   Total: {summary['total_events']} | Blocked: {summary['blocked_operations']} | Warnings: {summary['warnings']}",
            ""
        ]
        
        for event in events:
            event_icon = "🚫" if event['event_type'] == 'blocked' else "⚠️" if event['event_type'] == 'warned' else "✅"
            timestamp = event['created_at'].strftime('%m/%d %H:%M')
            output.append(f"   {event_icon} {timestamp} {event['tool_name']} - {event['reason']}")
        
        return "\n".join(output)

    def _format_conversations_by_model(self, results: Dict[str, Any]) -> str:
        """Format conversations by model results"""
        conversations = results['conversations'][:10]
        summary = results['summary']
        
        output = [
            "🤖 Conversations by Model:",
            f"   Total: {summary['total_conversations']} conversations",
            f"   Models: {', '.join(summary['models'])}",
            ""
        ]
        
        for conv in conversations:
            model = conv.get('agent_model', 'unknown')
            date = conv.get('created_at', '')[:10] if conv.get('created_at') else 'unknown'
            summary_text = conv.get('summary', conv.get('user_request_summary', 'No summary'))[:80]
            
            output.append(f"   [{model}] {date} - {summary_text}...")
            if conv.get('accomplishments'):
                output.append(f"      ✅ {conv['accomplishments']}")
        
        return "\n".join(output)
    
    def _format_lessons_learned(self, results: Dict[str, Any]) -> str:
        """Format lessons learned results"""
        lessons = results['lessons'][:15]
        summary = results['summary']
        
        output = [
            "💡 Lessons Learned:",
            f"   Total: {summary['total_lessons']} lessons from {summary['conversations_with_lessons']} conversations",
            ""
        ]
        
        if results.get('topic_filter'):
            output.append(f"   Filtered by: {results['topic_filter']}")
            output.append("")
        
        for lesson_data in lessons:
            lesson = lesson_data['lesson']
            date = lesson_data['date'][:10] if lesson_data.get('date') else 'unknown'
            output.append(f"   • {lesson}")
            output.append(f"     ({date} - {lesson_data.get('summary', '')[:50]}...)")
        
        return "\n".join(output)
    
    def _format_chain_of_thought(self, results: Dict[str, Any]) -> str:
        """Format chain of thought results"""
        conversations = results['conversations'][:5]
        summary = results['summary']
        
        output = [
            "🧠 Chain of Thought Analysis:",
            f"   Conversations analyzed: {summary['total_conversations']}",
            f"   Average steps per conversation: {summary['avg_steps']:.1f}",
            ""
        ]
        
        for conv in conversations:
            request = conv.get('user_request_summary', 'Unknown request')
            chain = conv.get('agent_chain_of_thought', [])
            
            output.append(f"📌 Request: {request}")
            output.append("   Steps:")
            
            for step in chain[:5]:  # Show first 5 steps
                thought = step.get('thought', '')
                tool = step.get('tool', '')
                success = "✅" if step.get('success', True) else "❌"
                output.append(f"   {step.get('step', '?')}. {success} [{tool}] {thought}")
            
            if len(chain) > 5:
                output.append(f"   ... and {len(chain) - 5} more steps")
            output.append("")
        
        return "\n".join(output)
    
    def _format_subagent_usage(self, results: Dict[str, Any]) -> str:
        """Format subagent usage results"""
        subagents = results['subagents'][:10]
        summary = results['summary']
        
        output = [
            "🤝 Subagent Usage:",
            f"   Total calls: {summary['total_subagent_calls']}",
            "",
            "📊 Model Breakdown:"
        ]
        
        for model, count in summary['model_breakdown'].items():
            output.append(f"   {model}: {count} calls")
        
        output.extend([
            "",
            "📋 Task Categories:"
        ])
        
        for category, count in summary['task_categories'].items():
            output.append(f"   {category}: {count} tasks")
        
        output.extend([
            "",
            "🔍 Recent Subagent Tasks:"
        ])
        
        for subagent in subagents:
            model = subagent['subagent_model']
            task = subagent['subagent_task'][:60]
            duration = subagent.get('duration_ms', 0) / 1000
            success = "✅" if subagent.get('success', True) else "❌"
            
            output.append(f"   {success} [{model}] {task}... ({duration:.1f}s)")
            if subagent.get('subagent_response_summary'):
                output.append(f"      → {subagent['subagent_response_summary'][:80]}...")
        
        return "\n".join(output)

def main():
    """CLI entry point for work query"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Query project work intelligence')
    parser.add_argument('query', nargs='+', help='Natural language query')
    parser.add_argument('--project', help='Project path (default: current)')
    parser.add_argument('--days', type=int, default=7, help='Days to look back (default: 7)')
    parser.add_argument('--format', choices=['json', 'table', 'summary'], default='summary', help='Output format')
    parser.add_argument('--limit', type=int, default=20, help='Limit results (default: 20)')
    
    args = parser.parse_args()
    query_text = ' '.join(args.query)
    
    # Initialize work intelligence
    wi = WorkIntelligence(args.project)
    
    # Parse and execute query
    parsed_query = wi.parse_query(query_text, args.days)
    results = wi.execute_query(parsed_query, args.limit)
    
    # Format and output results
    formatted_output = wi.format_results(results, args.format)
    print(formatted_output)

if __name__ == '__main__':
    main()