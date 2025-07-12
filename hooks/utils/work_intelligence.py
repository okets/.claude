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
            return self._fallback_query(parsed_query, limit)
        
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
            JOIN sessions s ON te.session_id = s.id
            WHERE s.project_id = %s 
            AND te.executed_at BETWEEN %s AND %s
            ORDER BY te.executed_at DESC
            LIMIT %s
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
            # Query specific file relationships
            placeholders = ','.join(['%s'] * len(file_filters))
            cursor.execute(f"""
                SELECT file1_path, file2_path, co_modification_count, last_modified_together
                FROM file_relationships
                WHERE project_id = %s
                AND (file1_path LIKE ANY(ARRAY[{placeholders}]) OR file2_path LIKE ANY(ARRAY[{placeholders}]))
                ORDER BY co_modification_count DESC
                LIMIT %s
            """, [self.project_id] + [f'%{f}%' for f in file_filters] * 2 + [limit])
        else:
            # Query all relationships
            cursor.execute("""
                SELECT file1_path, file2_path, co_modification_count, last_modified_together
                FROM file_relationships
                WHERE project_id = %s
                ORDER BY co_modification_count DESC
                LIMIT %s
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
            WHERE ph.project_id = %s AND t.status IN ('todo', 'in_progress')
            GROUP BY t.id, ph.id
            ORDER BY t.priority DESC, t.created_at
            LIMIT %s
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
            placeholders = ','.join(['%s'] * len(phase_filters))
            cursor.execute(f"""
                SELECT ph.name, ph.description, ph.status, ph.started_at, ph.completed_at,
                       COUNT(t.id) as total_tasks,
                       COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_tasks,
                       COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) as in_progress_tasks
                FROM phases ph
                LEFT JOIN tasks t ON ph.id = t.phase_id
                WHERE ph.project_id = %s
                AND ph.name LIKE ANY(ARRAY[{placeholders}])
                GROUP BY ph.id
                ORDER BY ph.created_at
                LIMIT %s
            """, [self.project_id] + [f'%{f}%' for f in phase_filters] + [limit])
        else:
            cursor.execute("""
                SELECT ph.name, ph.description, ph.status, ph.started_at, ph.completed_at,
                       COUNT(t.id) as total_tasks,
                       COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_tasks,
                       COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) as in_progress_tasks
                FROM phases ph
                LEFT JOIN tasks t ON ph.id = t.phase_id
                WHERE ph.project_id = %s
                GROUP BY ph.id
                ORDER BY ph.created_at
                LIMIT %s
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
            JOIN sessions s ON se.session_id = s.id
            WHERE s.project_id = %s
            AND se.created_at BETWEEN %s AND %s
            ORDER BY se.created_at DESC
            LIMIT %s
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
            WHERE project_id = %s
            ORDER BY frequency_count DESC
            LIMIT %s
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
            JOIN sessions s ON te.session_id = s.id
            WHERE s.project_id = %s
            AND te.intent = 'git-operation'
            AND te.executed_at BETWEEN %s AND %s
            ORDER BY te.executed_at DESC
            LIMIT %s
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
            JOIN sessions s ON te.session_id = s.id
            WHERE s.project_id = %s
            AND te.executed_at BETWEEN %s AND %s
            GROUP BY tool_name, intent
            ORDER BY usage_count DESC
            LIMIT %s
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
    
    def _fallback_query(self, parsed_query: Dict[str, Any], limit: int) -> Dict[str, Any]:
        """Fallback to JSON file querying when database is unavailable"""
        try:
            project_root = Path(self.project_path)
            log_dir = project_root / '.claude' / 'logs'
            
            if not log_dir.exists():
                return {'error': 'No logs found and database unavailable', 'results': []}
            
            # Read JSON logs
            post_log = log_dir / 'post_tool_use.json'
            pre_log = log_dir / 'pre_tool_use.json'
            
            results = []
            
            if post_log.exists():
                with open(post_log, 'r') as f:
                    post_data = json.load(f)
                    results.extend(post_data[-limit:])  # Get recent entries
            
            return {
                'type': 'fallback',
                'results': results,
                'warning': 'Database unavailable, using JSON fallback'
            }
            
        except Exception as e:
            return {'error': f"Fallback query failed: {e}", 'results': []}
    
    def format_results(self, results: Dict[str, Any], format_type: str = 'summary') -> str:
        """Format query results for display"""
        if 'error' in results:
            return f"❌ Error: {results['error']}"
        
        if format_type == 'json':
            return json.dumps(results, indent=2, default=str)
        
        return self._format_summary(results)
    
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