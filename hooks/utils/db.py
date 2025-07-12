#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = ["pymysql", "cryptography"]
# ///

import os
import json
import pymysql
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

class ClaudeDB:
    def __init__(self):
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Connect to MySQL database using environment variables or defaults"""
        try:
            self.connection = pymysql.connect(
                host=os.getenv('CLAUDE_DB_HOST', 'localhost'),
                user=os.getenv('CLAUDE_DB_USER', 'root'),
                password=os.getenv('CLAUDE_DB_PASSWORD', ''),
                database=os.getenv('CLAUDE_DB_NAME', 'claude_intelligence'),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
        except Exception as e:
            # Fallback to JSON logging if DB not available
            print(f"Warning: Database connection failed: {e}", file=sys.stderr)
            self.connection = None
    
    def ensure_project(self, project_path: str, project_name: str = None) -> int:
        """Ensure project exists in database, return project_id"""
        if not self.connection:
            return None
            
        if not project_name:
            project_name = Path(project_path).name
            
        try:
            with self.connection.cursor() as cursor:
                # Try to insert, ignore if exists
                cursor.execute("""
                    INSERT IGNORE INTO projects (name, path) 
                    VALUES (%s, %s)
                """, (project_name, project_path))
                
                # Get the project ID
                cursor.execute("""
                    SELECT id FROM projects WHERE path = %s
                """, (project_path,))
                
                result = cursor.fetchone()
                return result['id'] if result else None
        except Exception as e:
            print(f"Database error in ensure_project: {e}", file=sys.stderr)
            return None
    
    def ensure_session(self, session_id: str, project_id: int) -> bool:
        """Ensure session exists in database"""
        if not self.connection or not project_id:
            return False
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT IGNORE INTO sessions (id, project_id) 
                    VALUES (%s, %s)
                """, (session_id, project_id))
                return True
        except Exception as e:
            print(f"Database error in ensure_session: {e}", file=sys.stderr)
            return False
    
    def log_tool_execution(self, session_id: str, tool_name: str, tool_input: Dict, 
                          tool_output: Dict = None, success: bool = True, 
                          intent: str = None, files_touched: List[str] = None,
                          duration_ms: int = None, assignment_id: int = None):
        """Log a tool execution"""
        if not self.connection:
            return self._fallback_log('tool_execution', {
                'session_id': session_id,
                'tool_name': tool_name,
                'tool_input': tool_input,
                'tool_output': tool_output,
                'success': success,
                'intent': intent,
                'files_touched': files_touched,
                'duration_ms': duration_ms,
                'assignment_id': assignment_id
            })
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO tool_executions 
                    (session_id, tool_name, tool_input, tool_output, success, 
                     intent, files_touched, duration_ms, assignment_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    session_id, tool_name, 
                    json.dumps(tool_input) if tool_input else None,
                    json.dumps(tool_output) if tool_output else None,
                    success, intent,
                    json.dumps(files_touched) if files_touched else None,
                    duration_ms, assignment_id
                ))
        except Exception as e:
            print(f"Database error in log_tool_execution: {e}", file=sys.stderr)
            return self._fallback_log('tool_execution', {
                'session_id': session_id,
                'tool_name': tool_name,
                'error': str(e)
            })
    
    def log_security_event(self, session_id: str, event_type: str, tool_name: str,
                          tool_input: Dict, reason: str = None):
        """Log a security event"""
        if not self.connection:
            return self._fallback_log('security_event', {
                'session_id': session_id,
                'event_type': event_type,
                'tool_name': tool_name,
                'tool_input': tool_input,
                'reason': reason
            })
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO security_events 
                    (session_id, event_type, tool_name, tool_input, reason)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    session_id, event_type, tool_name,
                    json.dumps(tool_input) if tool_input else None,
                    reason
                ))
        except Exception as e:
            print(f"Database error in log_security_event: {e}", file=sys.stderr)
            return self._fallback_log('security_event', {
                'session_id': session_id,
                'event_type': event_type,
                'error': str(e)
            })
    
    def update_file_relationships(self, project_id: int, files: List[str]):
        """Update file co-modification relationships"""
        if not self.connection or not project_id or len(files) < 2:
            return
            
        try:
            with self.connection.cursor() as cursor:
                # Create pairs of files that were modified together
                for i, file1 in enumerate(files):
                    for file2 in files[i+1:]:
                        # Ensure consistent ordering
                        if file1 > file2:
                            file1, file2 = file2, file1
                            
                        cursor.execute("""
                            INSERT INTO file_relationships 
                            (project_id, file1_path, file2_path, co_modification_count, last_modified_together)
                            VALUES (%s, %s, %s, 1, NOW())
                            ON DUPLICATE KEY UPDATE 
                            co_modification_count = co_modification_count + 1,
                            last_modified_together = NOW()
                        """, (project_id, file1, file2))
        except Exception as e:
            print(f"Database error in update_file_relationships: {e}", file=sys.stderr)
    
    def get_project_context(self, project_id: int, limit: int = 10) -> Dict[str, Any]:
        """Get recent context for a project"""
        if not self.connection:
            return {}
            
        try:
            with self.connection.cursor() as cursor:
                # Recent tool executions
                cursor.execute("""
                    SELECT tool_name, intent, files_touched, executed_at
                    FROM tool_executions te
                    JOIN sessions s ON te.session_id = s.id
                    WHERE s.project_id = %s
                    ORDER BY executed_at DESC
                    LIMIT %s
                """, (project_id, limit))
                recent_tools = cursor.fetchall()
                
                # Active tasks
                cursor.execute("""
                    SELECT ph.name as phase_name, t.name as task_name, 
                           t.status, t.priority, t.description
                    FROM tasks t
                    JOIN phases ph ON t.phase_id = ph.id
                    WHERE ph.project_id = %s AND t.status IN ('todo', 'in_progress')
                    ORDER BY t.priority DESC, t.created_at
                    LIMIT %s
                """, (project_id, limit))
                active_tasks = cursor.fetchall()
                
                # File relationships
                cursor.execute("""
                    SELECT file1_path, file2_path, co_modification_count
                    FROM file_relationships
                    WHERE project_id = %s
                    ORDER BY co_modification_count DESC
                    LIMIT %s
                """, (project_id, limit))
                file_relationships = cursor.fetchall()
                
                return {
                    'recent_tools': recent_tools,
                    'active_tasks': active_tasks,
                    'file_relationships': file_relationships
                }
        except Exception as e:
            print(f"Database error in get_project_context: {e}", file=sys.stderr)
            return {}
    
    def _fallback_log(self, log_type: str, data: Dict[str, Any]):
        """Fallback to JSON logging when database is unavailable"""
        try:
            # Use the same fallback as existing hooks
            from pathlib import Path
            project_root = Path.cwd()
            while project_root != project_root.parent:
                if (project_root / '.git').exists():
                    break
                project_root = project_root.parent
            
            log_dir = project_root / '.claude' / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{log_type}.json"
            
            # Read existing logs
            if log_file.exists():
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # Add new entry
            logs.append({
                'timestamp': datetime.now().isoformat(),
                **data
            })
            
            # Write back
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            print(f"Fallback logging failed: {e}", file=sys.stderr)
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

# Global instance
_db = None

def get_db() -> ClaudeDB:
    """Get database instance (singleton)"""
    global _db
    if _db is None:
        _db = ClaudeDB()
    return _db