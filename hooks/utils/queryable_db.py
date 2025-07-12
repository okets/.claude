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
from typing import Optional, Dict, Any, List, Tuple

class QueryableContextDB:
    """New event-driven, tag-based context database for tracking file changes with rich context"""
    
    def __init__(self):
        self.connection = None
        self.current_session_id = None
        self.event_sequence = 0
        self._connect()
    
    def _connect(self):
        """Connect to the new queryable-context.db"""
        try:
            # Find project root by looking for .git directory
            project_root = self._find_project_root()
            
            # Create .claude directory in project root
            project_claude_dir = project_root / '.claude'
            project_claude_dir.mkdir(exist_ok=True)
            
            # New database for contextual changelog
            db_path = project_claude_dir / 'queryable-context.db'
            
            self.connection = sqlite3.connect(str(db_path), check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            
            # Enable foreign keys
            self.connection.execute("PRAGMA foreign_keys = ON")
            
            # Initialize schema
            self._initialize_database()
            
        except Exception as e:
            print(f"Error connecting to queryable context database: {e}", file=sys.stderr)
            self.connection = None
    
    def _find_project_root(self):
        """Find project root by looking for .git directory"""
        cwd = Path.cwd()
        current = cwd
        
        while current != current.parent:
            if (current / '.git').exists():
                return current
            current = current.parent
        
        return cwd
    
    def _initialize_database(self):
        """Create the new event-driven schema"""
        if not self.connection:
            return
            
        cursor = self.connection.cursor()
        
        # Create schema exactly as designed
        cursor.executescript("""
        -- Core event stream table
        CREATE TABLE IF NOT EXISTS session_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            event_sequence INTEGER NOT NULL,
            event_type TEXT NOT NULL CHECK (event_type IN (
                'session_start', 'user_request', 'security_check', 
                'tool_execution', 'file_change', 'subagent_start', 
                'subagent_complete', 'session_end'
            )),
            event_data JSON NOT NULL,
            parent_event_id INTEGER REFERENCES session_events(id),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_id, event_sequence)
        );
        
        CREATE INDEX IF NOT EXISTS idx_session_events_session ON session_events(session_id);
        CREATE INDEX IF NOT EXISTS idx_session_events_type ON session_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_session_events_parent ON session_events(parent_event_id);
        
        -- File changes (the contextual changelog)
        CREATE TABLE IF NOT EXISTS file_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            event_id INTEGER NOT NULL REFERENCES session_events(id),
            file_path TEXT NOT NULL,
            change_type TEXT NOT NULL CHECK (change_type IN ('created', 'modified', 'deleted', 'renamed')),
            change_summary TEXT NOT NULL,
            diff_stats JSON,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_file_changes_path ON file_changes(file_path);
        CREATE INDEX IF NOT EXISTS idx_file_changes_session ON file_changes(session_id);
        CREATE INDEX IF NOT EXISTS idx_file_changes_timestamp ON file_changes(timestamp);
        
        -- Change context
        CREATE TABLE IF NOT EXISTS change_context (
            change_id INTEGER PRIMARY KEY REFERENCES file_changes(id),
            user_request TEXT NOT NULL,
            agent_reasoning TEXT,
            task_context TEXT,
            phase_context TEXT,
            related_files JSON,
            test_results TEXT,
            iteration_count INTEGER DEFAULT 1,
            prompted_by TEXT CHECK (prompted_by IN ('user_request', 'test_failure', 'refactoring', 'bug_fix'))
        );
        
        -- Session tags for navigation
        CREATE TABLE IF NOT EXISTS session_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            tag_type TEXT NOT NULL CHECK (tag_type IN (
                'complexity', 'phase', 'task', 'file', 'directory',
                'topic', 'outcome', 'pattern', 'model', 'duration'
            )),
            tag_value TEXT NOT NULL,
            tag_metadata JSON,
            confidence REAL DEFAULT 1.0,
            UNIQUE(session_id, tag_type, tag_value)
        );
        
        CREATE INDEX IF NOT EXISTS idx_session_tags_type_value ON session_tags(tag_type, tag_value);
        CREATE INDEX IF NOT EXISTS idx_session_tags_session ON session_tags(session_id);
        
        -- Sessions metadata
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            project_path TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            user_request_summary TEXT,
            final_outcome TEXT,
            total_tokens INTEGER,
            total_file_changes INTEGER,
            model TEXT
        );
        """)
        
        self.connection.commit()
    
    # Core event management
    
    def create_session(self, session_id: str, project_path: str, model: str = None):
        """Create a new session"""
        if not self.connection:
            return
        
        self.current_session_id = session_id
        self.event_sequence = 0
        
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO sessions (id, project_path, model)
            VALUES (?, ?, ?)
        """, (session_id, project_path, model))
        self.connection.commit()
    
    def add_event(self, session_id: str, event_type: str, event_data: Dict[str, Any], 
                  parent_event_id: Optional[int] = None) -> Optional[int]:
        """Add an event to the stream"""
        if not self.connection:
            return None
        
        self.event_sequence += 1
        
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO session_events (session_id, event_sequence, event_type, event_data, parent_event_id)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, self.event_sequence, event_type, json.dumps(event_data), parent_event_id))
        
        self.connection.commit()
        return cursor.lastrowid
    
    # File change tracking
    
    def track_file_change(self, session_id: str, file_path: str, change_type: str,
                         change_summary: str, diff_stats: Optional[Dict] = None,
                         context: Optional[Dict] = None) -> Optional[int]:
        """Track a file modification with full context"""
        if not self.connection:
            return None
        
        # Add file change event
        event_data = {
            'file_path': file_path,
            'change_type': change_type,
            'change_summary': change_summary,
            'diff_stats': diff_stats
        }
        
        event_id = self.add_event(session_id, 'file_change', event_data)
        if not event_id:
            return None
        
        # Insert into file_changes table
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO file_changes (session_id, event_id, file_path, change_type, change_summary, diff_stats)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, event_id, file_path, change_type, change_summary, 
              json.dumps(diff_stats) if diff_stats else None))
        
        change_id = cursor.lastrowid
        
        # Add context if provided
        if context and change_id:
            cursor.execute("""
                INSERT INTO change_context (
                    change_id, user_request, agent_reasoning, task_context,
                    phase_context, related_files, test_results, iteration_count, prompted_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                change_id,
                context.get('user_request', ''),
                context.get('agent_reasoning'),
                context.get('task_context'),
                context.get('phase_context'),
                json.dumps(context.get('related_files', [])),
                context.get('test_results'),
                context.get('iteration_count', 1),
                context.get('prompted_by', 'user_request')
            ))
        
        self.connection.commit()
        return change_id
    
    # Tag management
    
    def add_session_tags(self, session_id: str, tags: List[Tuple[str, str, Optional[Dict]]]):
        """Add multiple tags to a session"""
        if not self.connection:
            return
        
        cursor = self.connection.cursor()
        for tag in tags:
            tag_type, tag_value = tag[0], tag[1]
            tag_metadata = tag[2] if len(tag) > 2 else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO session_tags (session_id, tag_type, tag_value, tag_metadata)
                VALUES (?, ?, ?, ?)
            """, (session_id, tag_type, tag_value, 
                  json.dumps(tag_metadata) if tag_metadata else None))
        
        self.connection.commit()
    
    # Session management
    
    def update_session_summary(self, session_id: str, user_request_summary: str):
        """Update session with user request summary"""
        if not self.connection:
            return
        
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE sessions 
            SET user_request_summary = ?
            WHERE id = ?
        """, (user_request_summary, session_id))
        self.connection.commit()
    
    def close_session(self, session_id: str, final_outcome: str = None, 
                     total_tokens: int = None, total_file_changes: int = None):
        """Close a session with final metadata"""
        if not self.connection:
            return
        
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE sessions 
            SET ended_at = CURRENT_TIMESTAMP,
                final_outcome = ?,
                total_tokens = ?,
                total_file_changes = ?
            WHERE id = ?
        """, (final_outcome, total_tokens, total_file_changes, session_id))
        self.connection.commit()
    
    # Query helpers
    
    def get_current_user_request(self, session_id: str) -> Optional[str]:
        """Get the current user request for a session"""
        if not self.connection:
            return None
        
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT user_request_summary FROM sessions WHERE id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        return row['user_request_summary'] if row else None
    
    def get_session_modified_files(self, session_id: str) -> List[str]:
        """Get all files modified in a session"""
        if not self.connection:
            return []
        
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT DISTINCT file_path FROM file_changes WHERE session_id = ?
        """, (session_id,))
        
        return [row['file_path'] for row in cursor.fetchall()]
    
    def get_recent_sessions_with_context(self, limit: int = 10) -> List[Dict]:
        """Get recent sessions with full context"""
        if not self.connection:
            return []
        
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                s.id,
                s.user_request_summary,
                s.started_at,
                s.final_outcome,
                s.model,
                GROUP_CONCAT(DISTINCT fc.file_path) as modified_files,
                GROUP_CONCAT(DISTINCT st.tag_value) as topics
            FROM sessions s
            LEFT JOIN file_changes fc ON s.id = fc.session_id
            LEFT JOIN session_tags st ON s.id = st.session_id AND st.tag_type = 'topic'
            GROUP BY s.id
            ORDER BY s.started_at DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_file_change_history(self, file_path: str, limit: int = 20) -> List[Dict]:
        """Get contextual history of changes to a file"""
        if not self.connection:
            return []
        
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                fc.timestamp,
                fc.change_summary,
                cc.user_request,
                cc.agent_reasoning,
                cc.task_context,
                cc.test_results,
                s.model
            FROM file_changes fc
            JOIN change_context cc ON fc.id = cc.change_id
            JOIN sessions s ON fc.session_id = s.id
            WHERE fc.file_path = ?
            ORDER BY fc.timestamp DESC
            LIMIT ?
        """, (file_path, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # Essential missing functionality for hook compatibility
    
    def ensure_project(self, project_path: str, project_name: str) -> int:
        """Ensure project exists and return project ID (compatibility method)"""
        # For now, just return 1 as we don't use separate project IDs in new schema
        # All sessions are tied to the project via the project_path
        return 1
    
    def ensure_session(self, session_id: str, project_id: int = None):
        """Ensure session exists (compatibility method)"""
        # Session is already created in create_session, this is a no-op for compatibility
        pass
    
    def log_tool_execution(self, chat_session_id: str, tool_name: str, tool_input: Dict,
                          tool_output: Dict, success: bool, intent: str,
                          files_touched: List[str], duration_ms: int,
                          assignment_id: int = None, task_context_id: int = None,
                          user_context: str = None, error_message: str = None):
        """Log tool execution with full metadata (compatibility with old system)"""
        # Infer success from tool_response if not provided
        if success is None:
            success = self._infer_success_from_tool_response(tool_name, tool_output)
        
        # Add tool execution event
        event_data = {
            'tool': tool_name,
            'input': tool_input,
            'output': tool_output,
            'success': success,
            'intent': intent,
            'files_touched': files_touched,
            'duration_ms': duration_ms,
            'assignment_id': assignment_id,
            'task_context_id': task_context_id,
            'user_context': user_context,
            'error_message': error_message
        }
        return self.add_event(chat_session_id, 'tool_execution', event_data)
    
    def _infer_success_from_tool_response(self, tool_name: str, tool_output: Dict) -> bool:
        """Infer success from tool response structure"""
        if not tool_output:
            return False
        
        # For Bash tools - check if interrupted or has stderr
        if tool_name == 'Bash':
            if tool_output.get('interrupted', False):
                return False
            # Consider stderr as potential failure indicator, but not always
            return True  # Most commands succeed even with stderr
        
        # For file tools - presence of filePath usually indicates success
        if tool_name in ['Read', 'Write', 'Edit', 'MultiEdit']:
            return 'filePath' in tool_output or 'file' in tool_output
        
        # Default to success
        return True
    
    def log_security_event(self, chat_session_id: str, event_type: str, tool_name: str,
                          tool_input: Dict, reason: str):
        """Log security events (pre_tool_use compatibility)"""
        event_data = {
            'event_type': event_type,
            'tool_name': tool_name,
            'tool_input': tool_input,
            'reason': reason
        }
        return self.add_event(chat_session_id, 'security_check', event_data)
    
    def update_file_relationships(self, project_id: int, files: List[str]):
        """Track file co-modification patterns (compatibility method)"""
        # For the new system, we track this through related_files in change_context
        # This is a no-op for now, but we could implement file relationship tracking
        pass
    
    def save_conversation_summary(self, chat_session_id: str, project_id: int, summary: str,
                                 key_topics: List[str] = None, files_mentioned: List[str] = None,
                                 phase_tags: List[str] = None, task_tags: List[str] = None,
                                 assignment_tags: List[str] = None, accomplishments: str = None,
                                 next_steps: str = None, mood: str = None,
                                 complexity_level: str = None, tools_used_count: int = None,
                                 files_touched_count: int = None, session_duration_minutes: int = None):
        """Save conversation summary (compatibility method)"""
        # In the new system, this is handled by session tags and final session metadata
        tags = []
        
        # Add topic tags
        if key_topics:
            for topic in key_topics:
                tags.append(('topic', topic))
        
        # Add file tags
        if files_mentioned:
            for file in files_mentioned:
                tags.append(('file', file))
        
        # Add complexity if provided
        if complexity_level:
            tags.append(('complexity', complexity_level, {
                'accomplishments': accomplishments,
                'tools_used_count': tools_used_count,
                'session_duration_minutes': session_duration_minutes
            }))
        
        if tags:
            self.add_session_tags(chat_session_id, tags)
        
        return True
    
    def get_conversation_details(self, session_id: str) -> Optional[Dict]:
        """Get conversation details (compatibility method)"""
        if not self.connection:
            return None
        
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM sessions WHERE id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def save_conversation_details(self, chat_session_id: str, project_id: int,
                                 user_request_summary: str, user_request_raw: str = None,
                                 agent_model: str = None, agent_chain_of_thought: List = None,
                                 tools_used: List = None, subagents_used: List = None,
                                 agent_summary: str = None, lessons_learned: List = None,
                                 duration_seconds: int = None, token_count: int = None):
        """Save detailed conversation metadata (compatibility method)"""
        # Update session with additional metadata
        if not self.connection:
            return
        
        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE sessions 
            SET user_request_summary = ?, final_outcome = ?, total_tokens = ?, model = ?
            WHERE id = ?
        """, (user_request_summary, agent_summary, token_count, agent_model, chat_session_id))
        self.connection.commit()

# Singleton instance
_db_instance = None

def get_queryable_db() -> QueryableContextDB:
    """Get or create the singleton database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = QueryableContextDB()
    return _db_instance

# Helper functions for easy access

def create_session(session_id: str, project_path: str, model: str = None):
    """Create a new session"""
    db = get_queryable_db()
    return db.create_session(session_id, project_path, model)

def add_event(session_id: str, event_type: str, event_data: Dict[str, Any], 
              parent_event_id: Optional[int] = None) -> Optional[int]:
    """Add an event to the stream"""
    db = get_queryable_db()
    return db.add_event(session_id, event_type, event_data, parent_event_id)

def track_file_change(session_id: str, file_path: str, change_type: str,
                     change_summary: str, diff_stats: Optional[Dict] = None,
                     context: Optional[Dict] = None) -> Optional[int]:
    """Track a file modification with full context"""
    db = get_queryable_db()
    return db.track_file_change(session_id, file_path, change_type, change_summary, diff_stats, context)

def add_session_tags(session_id: str, tags: List[Tuple[str, str, Optional[Dict]]]):
    """Add tags to a session"""
    db = get_queryable_db()
    return db.add_session_tags(session_id, tags)

def get_current_user_request(session_id: str) -> Optional[str]:
    """Get the current user request for a session"""
    db = get_queryable_db()
    return db.get_current_user_request(session_id)

def get_session_modified_files(session_id: str) -> List[str]:
    """Get all files modified in a session"""
    db = get_queryable_db()
    return db.get_session_modified_files(session_id)

def close_session(session_id: str, final_outcome: str = None, 
                 total_tokens: int = None, total_file_changes: int = None):
    """Close a session with final metadata"""
    db = get_queryable_db()
    return db.close_session(session_id, final_outcome, total_tokens, total_file_changes)

def update_session_summary(session_id: str, user_request_summary: str):
    """Update session with user request summary"""
    db = get_queryable_db()
    return db.update_session_summary(session_id, user_request_summary)

def log_security_event(chat_session_id: str, event_type: str, tool_name: str,
                      tool_input: Dict, reason: str):
    """Log security events"""
    db = get_queryable_db()
    return db.log_security_event(chat_session_id, event_type, tool_name, tool_input, reason)

def log_tool_execution(chat_session_id: str, tool_name: str, tool_input: Dict,
                      tool_output: Dict, success: bool, intent: str,
                      files_touched: List[str], duration_ms: int,
                      assignment_id: int = None, task_context_id: int = None,
                      user_context: str = None, error_message: str = None):
    """Log tool execution with full metadata"""
    db = get_queryable_db()
    return db.log_tool_execution(chat_session_id, tool_name, tool_input, tool_output,
                                success, intent, files_touched, duration_ms,
                                assignment_id, task_context_id, user_context, error_message)

def update_file_relationships(project_id: int, files: List[str]):
    """Track file co-modification patterns"""
    db = get_queryable_db()
    return db.update_file_relationships(project_id, files)

def save_conversation_summary(chat_session_id: str, project_id: int, summary: str,
                             key_topics: List[str] = None, files_mentioned: List[str] = None,
                             phase_tags: List[str] = None, task_tags: List[str] = None,
                             assignment_tags: List[str] = None, accomplishments: str = None,
                             next_steps: str = None, mood: str = None,
                             complexity_level: str = None, tools_used_count: int = None,
                             files_touched_count: int = None, session_duration_minutes: int = None):
    """Save conversation summary"""
    db = get_queryable_db()
    return db.save_conversation_summary(chat_session_id, project_id, summary,
                                       key_topics, files_mentioned, phase_tags, task_tags,
                                       assignment_tags, accomplishments, next_steps, mood,
                                       complexity_level, tools_used_count, files_touched_count,
                                       session_duration_minutes)