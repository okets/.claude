#!/usr/bin/env python3
"""
Contextual Database Module for Phase 5 Implementation

Simple 4-table schema for fast context retrieval:
- cycles: user intent, phase/task tracking  
- file_contexts: file changes with WHY context
- llm_summaries: generated insights per cycle
- subagent_tasks: delegation context
"""

import json
import sqlite3
import sys
import random
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from cycle_utils import get_project_smarter_claude_dir, announce_user_content


class ContextualDB:
    """Phase 5 contextual database for file/task/phase context retrieval"""

    def __init__(self, db_path: Optional[str] = None):
        self.connection = None
        if db_path is None:
            # Default to project-specific smarter-claude directory
            db_path = get_project_smarter_claude_dir() / "smarter-claude.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)

        # Auto-create project settings with random voice if not exists
        self._ensure_project_settings()

        self._connect()

    def _ensure_project_settings(self):
        """Create default project settings if they don't exist"""
        try:
            from settings import get_settings
            get_settings().create_default_project_settings()
        except Exception:
            pass  # Fail silently - settings are optional
    
    def _connect(self):
        """Connect to SQLite database"""
        try:
            self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON")
            self._initialize_schema()
        except Exception as e:
            print(f"Error connecting to contextual database: {e}", file=sys.stderr)
            self.connection = None
    
    def _initialize_schema(self):
        """Create the 4-table schema for contextual logging"""
        if not self.connection:
            return
        
        cursor = self.connection.cursor()
        cursor.executescript("""
        -- Core cycle tracking
        CREATE TABLE IF NOT EXISTS cycles (
            cycle_id INTEGER PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_intent TEXT,           -- Primary driver 
            phase_number INTEGER,       -- Primary driver  
            task_number INTEGER,        -- Primary driver
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            primary_activity TEXT       -- file_modification, testing, etc.
        );
        
        CREATE INDEX IF NOT EXISTS idx_cycles_session ON cycles(session_id);
        CREATE INDEX IF NOT EXISTS idx_cycles_phase_task ON cycles(phase_number, task_number);
        
        -- File changes with WHY context
        CREATE TABLE IF NOT EXISTS file_contexts (
            id INTEGER PRIMARY KEY,
            cycle_id INTEGER REFERENCES cycles(cycle_id),
            file_path TEXT NOT NULL,    -- Primary driver
            agent_type TEXT,            -- main_agent, subagent
            operation_type TEXT,        -- edit, write, multiedit
            change_reason TEXT,         -- WHY context from tool input
            edit_count INTEGER,
            timestamp TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_file_contexts_path ON file_contexts(file_path);
        CREATE INDEX IF NOT EXISTS idx_file_contexts_cycle ON file_contexts(cycle_id);
        
        -- LLM summaries - Generated insights per cycle
        CREATE TABLE IF NOT EXISTS llm_summaries (
            id INTEGER PRIMARY KEY, 
            cycle_id INTEGER REFERENCES cycles(cycle_id),
            intent_sequence INTEGER,   -- For multi-intent cycles
            summary_text TEXT,
            summary_type TEXT,         -- user_intent, execution_summary, etc.
            confidence_level TEXT     -- high, medium, low
        );
        
        CREATE INDEX IF NOT EXISTS idx_llm_summaries_cycle ON llm_summaries(cycle_id);
        CREATE INDEX IF NOT EXISTS idx_llm_summaries_type ON llm_summaries(summary_type);
        
        -- Subagent tasks - Delegation context
        CREATE TABLE IF NOT EXISTS subagent_tasks (
            id INTEGER PRIMARY KEY,
            cycle_id INTEGER REFERENCES cycles(cycle_id), 
            task_description TEXT,
            files_modified TEXT,        -- JSON array as text
            status TEXT,               -- completed, failed, in_progress
            completion_time TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_subagent_tasks_cycle ON subagent_tasks(cycle_id);
        """)
        
        self.connection.commit()
    
    def _announce_save(self):
        """Announce database save with randomized messages - disabled to avoid interfering with completion summaries"""
        try:
            import random
            # Disabled: These announcements interfere with clean completion summaries
            if False:  # Previously: random.random() < 0.1
                save_announcements = [
                    "saving to my long context database",
                    "saving to my long term memory", 
                    "storing in my memory database",
                    "recording to my context memory",
                    "updating my long term storage",
                    "saving to my persistent memory",
                    "storing in my knowledge base"
                ]
                announcement = random.choice(save_announcements)
                announce_user_content(announcement, level="concise")  # Use concise for saves
        except:
            pass  # Fail silently if TTS not available
    
    # Data insertion methods
    
    def insert_cycle(self, session_id: str, cycle_id: int, user_intent: str = None,
                    phase_number: int = None, task_number: int = None,
                    start_time: str = None, end_time: str = None,
                    primary_activity: str = None) -> bool:
        """Insert cycle data"""
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO cycles 
                (cycle_id, session_id, user_intent, phase_number, task_number, 
                 start_time, end_time, primary_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cycle_id, session_id, user_intent, phase_number, task_number,
                  start_time, end_time, primary_activity))
            
            self.connection.commit()
            self._announce_save()
            return True
        except Exception as e:
            print(f"Error inserting cycle: {e}", file=sys.stderr)
            return False
    
    def insert_file_context(self, cycle_id: int, file_path: str, agent_type: str = None,
                           operation_type: str = None, change_reason: str = None,
                           edit_count: int = None, timestamp: str = None) -> bool:
        """Insert file context data"""
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO file_contexts 
                (cycle_id, file_path, agent_type, operation_type, change_reason, edit_count, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cycle_id, file_path, agent_type, operation_type, change_reason, edit_count, timestamp))
            
            self.connection.commit()
            self._announce_save()
            return True
        except Exception as e:
            print(f"Error inserting file context: {e}", file=sys.stderr)
            return False
    
    def insert_llm_summary(self, cycle_id: int, summary_text: str, summary_type: str,
                          intent_sequence: int = 1, confidence_level: str = "medium") -> bool:
        """Insert LLM summary data"""
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO llm_summaries 
                (cycle_id, intent_sequence, summary_text, summary_type, confidence_level)
                VALUES (?, ?, ?, ?, ?)
            """, (cycle_id, intent_sequence, summary_text, summary_type, confidence_level))
            
            self.connection.commit()
            self._announce_save()
            return True
        except Exception as e:
            print(f"Error inserting LLM summary: {e}", file=sys.stderr)
            return False
    
    def insert_subagent_task(self, cycle_id: int, task_description: str, files_modified: List[str] = None,
                            status: str = "completed", completion_time: str = None) -> bool:
        """Insert subagent task data"""
        if not self.connection:
            return False
        
        try:
            files_json = json.dumps(files_modified) if files_modified else "[]"
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO subagent_tasks 
                (cycle_id, task_description, files_modified, status, completion_time)
                VALUES (?, ?, ?, ?, ?)
            """, (cycle_id, task_description, files_json, status, completion_time))
            
            self.connection.commit()
            self._announce_save()
            return True
        except Exception as e:
            print(f"Error inserting subagent task: {e}", file=sys.stderr)
            return False
    
    # Query methods for context retrieval
    
    def get_file_context(self, file_path: str, limit: int = 10) -> List[Dict]:
        """Get context for a specific file"""
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT c.user_intent, c.phase_number, c.task_number, c.primary_activity,
                       fc.agent_type, fc.operation_type, fc.change_reason, fc.edit_count, fc.timestamp
                FROM file_contexts fc
                JOIN cycles c ON fc.cycle_id = c.cycle_id
                WHERE fc.file_path LIKE ?
                ORDER BY fc.timestamp DESC
                LIMIT ?
            """, (f"%{file_path}%", limit))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error querying file context: {e}", file=sys.stderr)
            return []
    
    def get_phase_task_context(self, phase_number: int, task_number: int = None) -> List[Dict]:
        """Get context for specific phase/task"""
        if not self.connection:
            return []
        
        try:
            cursor = self.connection.cursor()
            if task_number is not None:
                cursor.execute("""
                    SELECT * FROM cycles 
                    WHERE phase_number = ? AND task_number = ?
                    ORDER BY start_time DESC
                """, (phase_number, task_number))
            else:
                cursor.execute("""
                    SELECT * FROM cycles 
                    WHERE phase_number = ?
                    ORDER BY start_time DESC
                """, (phase_number,))
            
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error querying phase/task context: {e}", file=sys.stderr)
            return []
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()