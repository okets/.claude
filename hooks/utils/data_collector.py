#!/usr/bin/env python3
"""
Data Collector for Phase 5 Implementation

Parse existing JSONL timeline files and cycle summary files 
to populate the contextual database.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import our database and hook parser
sys.path.append(str(Path(__file__).parent))
from contextual_db import ContextualDB
from hook_parser import generate_contextual_summary, load_hook_timeline
from cycle_utils import get_project_smarter_claude_logs_dir


class DataCollector:
    """Collect data from existing hook files into contextual database"""
    
    def __init__(self, session_logs_dir: str = None):
        if session_logs_dir is None:
            session_logs_dir = str(get_project_smarter_claude_logs_dir())
        
        self.session_logs_dir = Path(session_logs_dir)
        self.db = ContextualDB()
        
    def collect_all_data(self):
        """Collect data from all existing hook files"""
        if not self.session_logs_dir.exists():
            print("No session logs directory found")
            return
        
        # Find all summary files (these contain the processed data we want)
        summary_files = list(self.session_logs_dir.glob("session_*_cycle_*_summary.json"))
        
        print(f"Found {len(summary_files)} cycle summary files")
        
        for summary_file in summary_files:
            try:
                self._process_summary_file(summary_file)
            except Exception as e:
                print(f"Error processing {summary_file}: {e}", file=sys.stderr)
        
        print("Data collection complete!")
    
    def _process_summary_file(self, summary_file: Path):
        """Process a single cycle summary file"""
        with open(summary_file, 'r') as f:
            summary_data = json.load(f)
        
        # Extract cycle metadata
        cycle_metadata = summary_data.get("cycle_metadata", {})
        session_id = cycle_metadata.get("session_id", "")
        cycle_id = cycle_metadata.get("cycle_id", 0)
        
        # Extract core cycle data
        user_intent = summary_data.get("user_intent", "")
        project_context = summary_data.get("project_context", {})
        phase_number = project_context.get("phase_number")
        task_number = project_context.get("task_number")
        
        timeline_metadata = summary_data.get("timeline_metadata", {})
        start_time = timeline_metadata.get("start_time")
        end_time = timeline_metadata.get("end_time")
        
        execution_summary = summary_data.get("execution_summary", {})
        primary_activity = execution_summary.get("primary_activity", "unknown")
        
        print(f"Processing cycle {cycle_id} - {user_intent[:50]}...")
        
        # Insert cycle data
        self.db.insert_cycle(
            session_id=session_id,
            cycle_id=cycle_id,
            user_intent=user_intent,
            phase_number=phase_number,
            task_number=task_number,
            start_time=start_time,
            end_time=end_time,
            primary_activity=primary_activity
        )
        
        # Insert file contexts
        file_activities = summary_data.get("file_activities", {})
        for file_path, agents in file_activities.items():
            for agent_type, activity in agents.items():
                operations = activity.get("operations", [])
                edit_count = activity.get("edit_count", 0)
                reasons = activity.get("reasons", [])
                timestamps = activity.get("timestamps", [])
                
                # Combine reasons for change context
                change_reason = "; ".join(reasons) if reasons else ""
                
                # Use first timestamp if available
                timestamp = timestamps[0] if timestamps else start_time
                
                # Determine operation type (use most common)
                operation_type = operations[0] if operations else "unknown"
                
                self.db.insert_file_context(
                    cycle_id=cycle_id,
                    file_path=file_path,
                    agent_type=agent_type,
                    operation_type=operation_type,
                    change_reason=change_reason,
                    edit_count=edit_count,
                    timestamp=timestamp
                )
        
        # Insert LLM summaries
        summary_types = [
            ("user_intent", user_intent),
            ("execution_summary", json.dumps(execution_summary)),
            ("project_context", json.dumps(project_context))
        ]
        
        for summary_type, summary_text in summary_types:
            if summary_text:
                confidence = "high" if project_context.get("context_confidence") == "high" else "medium"
                self.db.insert_llm_summary(
                    cycle_id=cycle_id,
                    summary_text=summary_text,
                    summary_type=summary_type,
                    confidence_level=confidence
                )
        
        # Insert subagent tasks
        subagent_tasks = summary_data.get("subagent_tasks", {})
        for task_id, task_data in subagent_tasks.items():
            delegation_info = task_data.get("delegation_info", {})
            work_summary = task_data.get("work_summary", {})
            
            task_description = delegation_info.get("description", "") or delegation_info.get("prompt", "")
            files_modified = work_summary.get("files_modified", [])
            status = work_summary.get("status", "unknown")
            completion_time = work_summary.get("completion_time")
            
            if task_description:  # Only insert if we have meaningful data
                self.db.insert_subagent_task(
                    cycle_id=cycle_id,
                    task_description=task_description,
                    files_modified=files_modified,
                    status=status,
                    completion_time=completion_time
                )
    
    def test_queries(self):
        """Test some basic queries to verify data collection"""
        print("\n=== Testing Contextual Database Queries ===")
        
        # Test file context query
        print("\n1. File context for hook_parser.py:")
        file_contexts = self.db.get_file_context("hook_parser.py", limit=3)
        for ctx in file_contexts:
            print(f"  - {ctx['operation_type']}: {ctx['change_reason'][:80]}...")
        
        # Test phase/task context
        print("\n2. Phase 2 context:")
        phase_contexts = self.db.get_phase_task_context(2)
        for ctx in phase_contexts:
            print(f"  - Task {ctx['task_number']}: {ctx['user_intent'][:60]}...")
        
        print("\nData collection and testing complete!")


def main():
    """Main entry point for data collection"""
    collector = DataCollector()
    collector.collect_all_data()
    collector.test_queries()


if __name__ == "__main__":
    main()