#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import os
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

class ClaudeDB:
    def __init__(self):
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Connect to SQLite database - per-project configuration"""
        try:
            # Find project root by looking for .git directory
            project_root = self._find_project_root()
            
            # Create .claude directory in project root
            project_claude_dir = project_root / '.claude'
            project_claude_dir.mkdir(exist_ok=True)
            
            # Database lives in project's .claude directory
            db_path = project_claude_dir / 'project-context.db'
            
            self.connection = sqlite3.connect(str(db_path), check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Dict-like access
            
            # Initialize database if needed
            self._initialize_database()
            
        except Exception as e:
            print(f"💾 Project context database not yet created. First tool use will initialize it.", file=sys.stderr)
            self.connection = None
    
    def _find_project_root(self):
        """Find project root by looking for .git directory"""
        cwd = Path.cwd()
        current = cwd
        
        while current != current.parent:
            if (current / '.git').exists():
                return current
            current = current.parent
        
        # If no git root found, use current directory
        return cwd
    
    def _initialize_database(self):
        """Create tables if they don't exist"""
        try:
            cursor = self.connection.cursor()
            
            # Create tables with SQLite syntax
            cursor.executescript("""
            -- Projects table
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Sessions table
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                project_id INTEGER NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP NULL,
                summary TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            
            -- Phases table
            CREATE TABLE IF NOT EXISTS phases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'planning' CHECK (status IN ('planning', 'active', 'completed', 'paused')),
                chat_session_id TEXT, -- Session when phase was created
                started_at TIMESTAMP NULL,
                completed_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, name)
            );
            
            -- Tasks table
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phase_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'completed', 'blocked')),
                priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
                chat_session_id TEXT, -- Session when task was created
                created_by_chat_session TEXT, -- Original creation session
                last_worked_chat_session TEXT, -- Most recent session that worked on this
                estimated_hours REAL, -- Time estimate
                actual_hours REAL, -- Time actually spent
                tags TEXT, -- JSON array of custom tags
                started_at TIMESTAMP NULL,
                completed_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (phase_id) REFERENCES phases(id) ON DELETE CASCADE
            );
            
            -- Assignments table
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                file_pattern TEXT,
                status TEXT DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'completed')),
                chat_session_id TEXT, -- Session when assignment was created
                completed_by_chat_session TEXT, -- Session that completed this
                difficulty TEXT CHECK (difficulty IN ('easy', 'medium', 'hard')), -- Complexity estimate
                actual_changes_made TEXT, -- Description of what was actually done
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            );
            
            -- Tool executions table
            CREATE TABLE IF NOT EXISTS tool_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_session_id TEXT NOT NULL, -- Renamed from session_id for consistency
                tool_name TEXT NOT NULL,
                tool_input TEXT,  -- JSON as TEXT
                tool_output TEXT, -- JSON as TEXT
                success BOOLEAN DEFAULT 1,
                intent TEXT,
                files_touched TEXT, -- JSON array as TEXT
                duration_ms INTEGER,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assignment_id INTEGER NULL,
                task_context_id INTEGER NULL, -- Which task was being worked on
                error_message TEXT, -- Capture any errors that occurred
                user_context TEXT, -- Additional context about what user was trying to do
                FOREIGN KEY (chat_session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE SET NULL,
                FOREIGN KEY (task_context_id) REFERENCES tasks(id) ON DELETE SET NULL
            );
            
            -- Security events table
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_session_id TEXT NOT NULL, -- Renamed for consistency
                event_type TEXT NOT NULL CHECK (event_type IN ('blocked', 'warned', 'allowed')),
                tool_name TEXT NOT NULL,
                tool_input TEXT, -- JSON as TEXT
                reason TEXT,
                severity TEXT CHECK (severity IN ('low', 'medium', 'high', 'critical')), -- Risk level
                remediation_suggested TEXT, -- What should user do about this
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            
            -- File relationships table
            CREATE TABLE IF NOT EXISTS file_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                file1_path TEXT NOT NULL,
                file2_path TEXT NOT NULL,
                co_modification_count INTEGER DEFAULT 1,
                last_modified_together TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_chat_session_id TEXT, -- Most recent session that modified both files
                relationship_strength REAL, -- Calculated strength of relationship (0-1)
                common_tasks TEXT, -- JSON array of tasks that involved both files
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, file1_path, file2_path)
            );
            
            -- Conversation summaries table
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_session_id TEXT NOT NULL, -- Renamed for consistency
                project_id INTEGER NOT NULL,
                summary TEXT NOT NULL,
                key_topics TEXT, -- JSON array of topics discussed
                files_mentioned TEXT, -- JSON array of files discussed/modified
                phase_tags TEXT, -- JSON array of phase names mentioned
                task_tags TEXT, -- JSON array of task names mentioned
                assignment_tags TEXT, -- JSON array of assignment descriptions
                accomplishments TEXT, -- What was actually completed
                next_steps TEXT, -- What should be done next
                mood TEXT, -- Overall tone: productive, frustrating, exploratory, etc.
                complexity_level TEXT CHECK (complexity_level IN ('simple', 'moderate', 'complex', 'very_complex')),
                tools_used_count INTEGER, -- Total number of tool executions
                files_touched_count INTEGER, -- Number of unique files touched
                session_duration_minutes INTEGER, -- How long the session lasted
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            
            -- Create indexes for better performance
            CREATE INDEX IF NOT EXISTS idx_sessions_project_started ON sessions(project_id, started_at);
            CREATE INDEX IF NOT EXISTS idx_tool_executions_session_executed ON tool_executions(chat_session_id, executed_at);
            CREATE INDEX IF NOT EXISTS idx_security_events_session_type ON security_events(chat_session_id, event_type);
            CREATE INDEX IF NOT EXISTS idx_file_relationships_project ON file_relationships(project_id, file1_path, file2_path);
            CREATE INDEX IF NOT EXISTS idx_conversation_summaries_session ON conversation_summaries(chat_session_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_conversation_summaries_files ON conversation_summaries(project_id, files_mentioned);
            
            -- Additional useful indexes for new fields
            CREATE INDEX IF NOT EXISTS idx_tasks_chat_session ON tasks(chat_session_id, status);
            CREATE INDEX IF NOT EXISTS idx_tasks_last_worked ON tasks(last_worked_chat_session, updated_at);
            CREATE INDEX IF NOT EXISTS idx_assignments_chat_session ON assignments(chat_session_id, status);
            CREATE INDEX IF NOT EXISTS idx_phases_chat_session ON phases(chat_session_id, status);
            CREATE INDEX IF NOT EXISTS idx_tool_executions_task_context ON tool_executions(task_context_id, executed_at);
            CREATE INDEX IF NOT EXISTS idx_file_relationships_session ON file_relationships(last_chat_session_id, relationship_strength);
            """)
            
            self.connection.commit()
            
        except Exception as e:
            print(f"Warning: Database initialization failed: {e}", file=sys.stderr)
    
    def ensure_project(self, project_path: str, project_name: str = None) -> int:
        """Ensure project exists in database, return project_id"""
        if not self.connection:
            return None
            
        if not project_name:
            project_name = Path(project_path).name
            
        try:
            cursor = self.connection.cursor()
            # Try to insert, ignore if exists
            cursor.execute("""
                INSERT OR IGNORE INTO projects (name, path) 
                VALUES (?, ?)
            """, (project_name, project_path))
            
            # Get the project ID
            cursor.execute("""
                SELECT id FROM projects WHERE path = ?
            """, (project_path,))
            
            result = cursor.fetchone()
            self.connection.commit()
            return result['id'] if result else None
        except Exception as e:
            print(f"Database error in ensure_project: {e}", file=sys.stderr)
            return None
    
    def ensure_session(self, chat_session_id: str, project_id: int) -> bool:
        """Ensure session exists in database"""
        if not self.connection or not project_id:
            return False
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO sessions (id, project_id) 
                VALUES (?, ?)
            """, (chat_session_id, project_id))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Database error in ensure_session: {e}", file=sys.stderr)
            return False
    
    def log_tool_execution(self, chat_session_id: str, tool_name: str, tool_input: Dict, 
                          tool_output: Dict = None, success: bool = True, 
                          intent: str = None, files_touched: List[str] = None,
                          duration_ms: int = None, assignment_id: int = None):
        """Log a tool execution"""
        if not self.connection:
            return self._fallback_log('tool_execution', {
                'chat_session_id': chat_session_id,
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
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO tool_executions 
                (chat_session_id, tool_name, tool_input, tool_output, success, 
                 intent, files_touched, duration_ms, assignment_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chat_session_id, tool_name, 
                json.dumps(tool_input) if tool_input else None,
                json.dumps(tool_output) if tool_output else None,
                success, intent,
                json.dumps(files_touched) if files_touched else None,
                duration_ms, assignment_id
            ))
            self.connection.commit()
        except Exception as e:
            print(f"Database error in log_tool_execution: {e}", file=sys.stderr)
            return self._fallback_log('tool_execution', {
                'chat_session_id': chat_session_id,
                'tool_name': tool_name,
                'error': str(e)
            })
    
    def log_security_event(self, chat_session_id: str, event_type: str, tool_name: str,
                          tool_input: Dict, reason: str = None):
        """Log a security event"""
        if not self.connection:
            return self._fallback_log('security_event', {
                'chat_session_id': chat_session_id,
                'event_type': event_type,
                'tool_name': tool_name,
                'tool_input': tool_input,
                'reason': reason
            })
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO security_events 
                (chat_session_id, event_type, tool_name, tool_input, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (
                chat_session_id, event_type, tool_name,
                json.dumps(tool_input) if tool_input else None,
                reason
            ))
            self.connection.commit()
        except Exception as e:
            print(f"Database error in log_security_event: {e}", file=sys.stderr)
            return self._fallback_log('security_event', {
                'chat_session_id': chat_session_id,
                'event_type': event_type,
                'error': str(e)
            })
    
    def update_file_relationships(self, project_id: int, files: List[str]):
        """Update file co-modification relationships"""
        if not self.connection or not project_id or len(files) < 2:
            return
            
        try:
            cursor = self.connection.cursor()
            # Create pairs of files that were modified together
            for i, file1 in enumerate(files):
                for file2 in files[i+1:]:
                    # Ensure consistent ordering
                    if file1 > file2:
                        file1, file2 = file2, file1
                        
                    cursor.execute("""
                        INSERT INTO file_relationships 
                        (project_id, file1_path, file2_path, co_modification_count, last_modified_together)
                        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                        ON CONFLICT(project_id, file1_path, file2_path) 
                        DO UPDATE SET 
                        co_modification_count = co_modification_count + 1,
                        last_modified_together = CURRENT_TIMESTAMP
                    """, (project_id, file1, file2))
            
            self.connection.commit()
        except Exception as e:
            print(f"Database error in update_file_relationships: {e}", file=sys.stderr)
    
    def get_project_context(self, project_id: int, limit: int = 10) -> Dict[str, Any]:
        """Get recent context for a project"""
        if not self.connection:
            return {}
            
        try:
            cursor = self.connection.cursor()
            
            # Recent tool executions
            cursor.execute("""
                SELECT tool_name, intent, files_touched, executed_at
                FROM tool_executions te
                JOIN sessions s ON te.chat_session_id = s.id
                WHERE s.project_id = ?
                ORDER BY executed_at DESC
                LIMIT ?
            """, (project_id, limit))
            recent_tools = [dict(row) for row in cursor.fetchall()]
            
            # Active tasks
            cursor.execute("""
                SELECT ph.name as phase_name, t.name as task_name, 
                       t.status, t.priority, t.description
                FROM tasks t
                JOIN phases ph ON t.phase_id = ph.id
                WHERE ph.project_id = ? AND t.status IN ('todo', 'in_progress')
                ORDER BY t.priority DESC, t.created_at
                LIMIT ?
            """, (project_id, limit))
            active_tasks = [dict(row) for row in cursor.fetchall()]
            
            # File relationships
            cursor.execute("""
                SELECT file1_path, file2_path, co_modification_count
                FROM file_relationships
                WHERE project_id = ?
                ORDER BY co_modification_count DESC
                LIMIT ?
            """, (project_id, limit))
            file_relationships = [dict(row) for row in cursor.fetchall()]
            
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
    
    def save_conversation_summary(self, chat_session_id: str, project_id: int, 
                                 summary: str, key_topics: List[str] = None,
                                 files_mentioned: List[str] = None, 
                                 phase_tags: List[str] = None,
                                 task_tags: List[str] = None,
                                 assignment_tags: List[str] = None,
                                 accomplishments: str = None,
                                 next_steps: str = None):
        """Save conversation summary with smart tags"""
        if not self.connection:
            return self._fallback_log('conversation_summary', {
                'chat_session_id': chat_session_id,
                'summary': summary,
                'key_topics': key_topics,
                'files_mentioned': files_mentioned,
                'phase_tags': phase_tags,
                'task_tags': task_tags,
                'assignment_tags': assignment_tags,
                'accomplishments': accomplishments,
                'next_steps': next_steps
            })
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO conversation_summaries 
                (chat_session_id, project_id, summary, key_topics, files_mentioned, 
                 phase_tags, task_tags, assignment_tags, accomplishments, next_steps)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chat_session_id, project_id, summary,
                json.dumps(key_topics) if key_topics else None,
                json.dumps(files_mentioned) if files_mentioned else None,
                json.dumps(phase_tags) if phase_tags else None,
                json.dumps(task_tags) if task_tags else None,
                json.dumps(assignment_tags) if assignment_tags else None,
                accomplishments, next_steps
            ))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Database error in save_conversation_summary: {e}", file=sys.stderr)
            return False
    
    def get_conversations_by_file(self, project_id: int, file_path: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get last N conversations that mentioned a specific file"""
        if not self.connection:
            return []
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT summary, accomplishments, next_steps, created_at, key_topics,
                       phase_tags, task_tags, assignment_tags
                FROM conversation_summaries
                WHERE project_id = ? AND files_mentioned LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (project_id, f'%{file_path}%', limit))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Database error in get_conversations_by_file: {e}", file=sys.stderr)
            return []
    
    def get_conversations_by_phase(self, project_id: int, phase_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversations related to a specific phase"""
        if not self.connection:
            return []
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT summary, accomplishments, next_steps, created_at, files_mentioned,
                       task_tags, assignment_tags
                FROM conversation_summaries
                WHERE project_id = ? AND phase_tags LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (project_id, f'%{phase_name}%', limit))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Database error in get_conversations_by_phase: {e}", file=sys.stderr)
            return []
    
    def get_conversations_by_task(self, project_id: int, task_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversations related to a specific task"""
        if not self.connection:
            return []
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT summary, accomplishments, next_steps, created_at, files_mentioned,
                       phase_tags, assignment_tags
                FROM conversation_summaries
                WHERE project_id = ? AND task_tags LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (project_id, f'%{task_name}%', limit))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Database error in get_conversations_by_task: {e}", file=sys.stderr)
            return []

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