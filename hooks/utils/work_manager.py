#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import json
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import database utility
sys.path.append(str(Path(__file__).parent))
from db import get_db

class WorkManager:
    def __init__(self, project_path: str = None):
        self.db = get_db()
        self.project_path = project_path or str(Path.cwd())
        self.project_id = None
        
        if self.db.connection:
            project_name = Path(self.project_path).name
            self.project_id = self.db.ensure_project(self.project_path, project_name)
    
    def create_phase(self, name: str, description: str = None, status: str = 'planning') -> bool:
        """Create a new phase"""
        if not self.db.connection or not self.project_id:
            return self._fallback_create('phase', {'name': name, 'description': description, 'status': status})
        
        try:
            with self.db.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO phases (project_id, name, description, status)
                    VALUES (%s, %s, %s, %s)
                """, (self.project_id, name, description, status))
                
                if status == 'active':
                    cursor.execute("""
                        UPDATE phases SET started_at = NOW() 
                        WHERE project_id = %s AND name = %s
                    """, (self.project_id, name))
                
                print(f"✅ Created phase: {name} (status: {status})")
                return True
        except Exception as e:
            print(f"❌ Error creating phase: {e}")
            return False
    
    def create_task(self, phase_name: str, task_name: str, description: str = None, 
                   priority: str = 'medium', status: str = 'todo') -> bool:
        """Create a new task within a phase"""
        if not self.db.connection or not self.project_id:
            return self._fallback_create('task', {
                'phase_name': phase_name, 'name': task_name, 
                'description': description, 'priority': priority, 'status': status
            })
        
        try:
            with self.db.connection.cursor() as cursor:
                # Get phase ID
                cursor.execute("""
                    SELECT id FROM phases WHERE project_id = %s AND name = %s
                """, (self.project_id, phase_name))
                
                phase = cursor.fetchone()
                if not phase:
                    print(f"❌ Phase '{phase_name}' not found. Create it first.")
                    return False
                
                phase_id = phase['id']
                
                cursor.execute("""
                    INSERT INTO tasks (phase_id, name, description, priority, status)
                    VALUES (%s, %s, %s, %s, %s)
                """, (phase_id, task_name, description, priority, status))
                
                if status == 'in_progress':
                    cursor.execute("""
                        UPDATE tasks SET started_at = NOW() 
                        WHERE phase_id = %s AND name = %s
                    """, (phase_id, task_name))
                
                print(f"✅ Created task: {task_name} in phase {phase_name} (priority: {priority})")
                return True
        except Exception as e:
            print(f"❌ Error creating task: {e}")
            return False
    
    def create_assignment(self, task_name: str, description: str, 
                         file_pattern: str = None) -> bool:
        """Create a new assignment within a task"""
        if not self.db.connection or not self.project_id:
            return self._fallback_create('assignment', {
                'task_name': task_name, 'description': description, 'file_pattern': file_pattern
            })
        
        try:
            with self.db.connection.cursor() as cursor:
                # Find task across all phases
                cursor.execute("""
                    SELECT t.id FROM tasks t
                    JOIN phases p ON t.phase_id = p.id
                    WHERE p.project_id = %s AND t.name = %s
                """, (self.project_id, task_name))
                
                task = cursor.fetchone()
                if not task:
                    print(f"❌ Task '{task_name}' not found.")
                    return False
                
                task_id = task['id']
                
                cursor.execute("""
                    INSERT INTO assignments (task_id, description, file_pattern)
                    VALUES (%s, %s, %s)
                """, (task_id, description, file_pattern))
                
                print(f"✅ Created assignment: {description}")
                if file_pattern:
                    print(f"   📁 File pattern: {file_pattern}")
                return True
        except Exception as e:
            print(f"❌ Error creating assignment: {e}")
            return False
    
    def list_phases(self) -> List[Dict[str, Any]]:
        """List all phases in the project"""
        if not self.db.connection or not self.project_id:
            return self._fallback_list('phases')
        
        try:
            with self.db.connection.cursor() as cursor:
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
                """, (self.project_id,))
                
                phases = cursor.fetchall()
                
                print("🎯 Project Phases:")
                print()
                
                for phase in phases:
                    status_icon = {
                        'planning': '📋', 'active': '🚧', 
                        'completed': '✅', 'paused': '⏸️'
                    }.get(phase['status'], '❓')
                    
                    total_tasks = phase['total_tasks'] or 0
                    completed_tasks = phase['completed_tasks'] or 0
                    progress_pct = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
                    
                    print(f"{status_icon} {phase['name']} ({phase['status']})")
                    if phase['description']:
                        print(f"   📝 {phase['description']}")
                    print(f"   📊 Progress: {progress_pct}% ({completed_tasks}/{total_tasks} tasks)")
                    
                    if phase['started_at']:
                        print(f"   🕐 Started: {phase['started_at'].strftime('%Y-%m-%d')}")
                    if phase['completed_at']:
                        print(f"   ✅ Completed: {phase['completed_at'].strftime('%Y-%m-%d')}")
                    print()
                
                return phases
        except Exception as e:
            print(f"❌ Error listing phases: {e}")
            return []
    
    def list_tasks(self, phase_name: str = None) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by phase"""
        if not self.db.connection or not self.project_id:
            return self._fallback_list('tasks', {'phase_name': phase_name})
        
        try:
            with self.db.connection.cursor() as cursor:
                if phase_name:
                    cursor.execute("""
                        SELECT t.name, t.description, t.status, t.priority, t.created_at,
                               ph.name as phase_name,
                               COUNT(a.id) as assignment_count,
                               COUNT(CASE WHEN a.status = 'completed' THEN 1 END) as completed_assignments
                        FROM tasks t
                        JOIN phases ph ON t.phase_id = ph.id
                        LEFT JOIN assignments a ON t.id = a.task_id
                        WHERE ph.project_id = %s AND ph.name = %s
                        GROUP BY t.id
                        ORDER BY t.priority DESC, t.created_at
                    """, (self.project_id, phase_name))
                else:
                    cursor.execute("""
                        SELECT t.name, t.description, t.status, t.priority, t.created_at,
                               ph.name as phase_name,
                               COUNT(a.id) as assignment_count,
                               COUNT(CASE WHEN a.status = 'completed' THEN 1 END) as completed_assignments
                        FROM tasks t
                        JOIN phases ph ON t.phase_id = ph.id
                        LEFT JOIN assignments a ON t.id = a.task_id
                        WHERE ph.project_id = %s
                        GROUP BY t.id
                        ORDER BY t.priority DESC, t.created_at
                    """, (self.project_id,))
                
                tasks = cursor.fetchall()
                
                title = f"📋 Tasks in {phase_name}:" if phase_name else "📋 All Tasks:"
                print(title)
                print()
                
                for task in tasks:
                    priority_icon = {
                        'urgent': '🔴', 'high': '🟠', 
                        'medium': '🟡', 'low': '🟢'
                    }.get(task['priority'], '⚪')
                    
                    status_icon = {
                        'todo': '📝', 'in_progress': '🚧', 'completed': '✅', 'blocked': '🚫'
                    }.get(task['status'], '❓')
                    
                    assignment_count = task['assignment_count'] or 0
                    completed_assignments = task['completed_assignments'] or 0
                    progress = f"({completed_assignments}/{assignment_count})" if assignment_count > 0 else ""
                    
                    print(f"{priority_icon} {status_icon} [{task['phase_name']}] {task['name']} {progress}")
                    if task['description']:
                        print(f"      📝 {task['description']}")
                    print()
                
                return tasks
        except Exception as e:
            print(f"❌ Error listing tasks: {e}")
            return []
    
    def list_assignments(self, task_name: str) -> List[Dict[str, Any]]:
        """List assignments for a specific task"""
        if not self.db.connection or not self.project_id:
            return self._fallback_list('assignments', {'task_name': task_name})
        
        try:
            with self.db.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT a.description, a.file_pattern, a.status, a.created_at, a.completed_at,
                           t.name as task_name, ph.name as phase_name
                    FROM assignments a
                    JOIN tasks t ON a.task_id = t.id
                    JOIN phases ph ON t.phase_id = ph.id
                    WHERE ph.project_id = %s AND t.name = %s
                    ORDER BY a.created_at
                """, (self.project_id, task_name))
                
                assignments = cursor.fetchall()
                
                print(f"📌 Assignments for task: {task_name}")
                print()
                
                for assignment in assignments:
                    status_icon = {
                        'todo': '📝', 'in_progress': '🚧', 'completed': '✅'
                    }.get(assignment['status'], '❓')
                    
                    print(f"{status_icon} {assignment['description']}")
                    if assignment['file_pattern']:
                        print(f"      📁 Files: {assignment['file_pattern']}")
                    if assignment['completed_at']:
                        print(f"      ✅ Completed: {assignment['completed_at'].strftime('%Y-%m-%d %H:%M')}")
                    print()
                
                return assignments
        except Exception as e:
            print(f"❌ Error listing assignments: {e}")
            return []
    
    def update_status(self, item_type: str, name: str, status: str) -> bool:
        """Update status of phase, task, or assignment"""
        if not self.db.connection or not self.project_id:
            return self._fallback_update(item_type, name, status)
        
        try:
            with self.db.connection.cursor() as cursor:
                if item_type == 'phase':
                    cursor.execute("""
                        UPDATE phases 
                        SET status = %s,
                            started_at = CASE WHEN %s = 'active' AND started_at IS NULL THEN NOW() ELSE started_at END,
                            completed_at = CASE WHEN %s = 'completed' THEN NOW() ELSE NULL END
                        WHERE project_id = %s AND name = %s
                    """, (status, status, status, self.project_id, name))
                    
                elif item_type == 'task':
                    cursor.execute("""
                        UPDATE tasks t
                        JOIN phases ph ON t.phase_id = ph.id
                        SET t.status = %s,
                            t.started_at = CASE WHEN %s = 'in_progress' AND t.started_at IS NULL THEN NOW() ELSE t.started_at END,
                            t.completed_at = CASE WHEN %s = 'completed' THEN NOW() ELSE NULL END
                        WHERE ph.project_id = %s AND t.name = %s
                    """, (status, status, status, self.project_id, name))
                
                if cursor.rowcount > 0:
                    print(f"✅ Updated {item_type} '{name}' status to: {status}")
                    return True
                else:
                    print(f"❌ {item_type.title()} '{name}' not found")
                    return False
                    
        except Exception as e:
            print(f"❌ Error updating {item_type}: {e}")
            return False
    
    def overview(self) -> Dict[str, Any]:
        """Show current work overview"""
        print("🎯 Project Work Overview")
        print("=" * 50)
        print()
        
        phases = self.list_phases()
        print()
        
        # Show current active work
        if self.db.connection and self.project_id:
            try:
                with self.db.connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT ph.name as phase_name, t.name as task_name, 
                               t.priority, COUNT(a.id) as assignments
                        FROM tasks t
                        JOIN phases ph ON t.phase_id = ph.id
                        LEFT JOIN assignments a ON t.id = a.task_id AND a.status != 'completed'
                        WHERE ph.project_id = %s AND t.status = 'in_progress'
                        GROUP BY t.id
                        ORDER BY t.priority DESC
                    """, (self.project_id,))
                    
                    active_tasks = cursor.fetchall()
                    
                    if active_tasks:
                        print("🚧 Currently In Progress:")
                        for task in active_tasks:
                            priority_icon = {'urgent': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(task['priority'], '⚪')
                            print(f"   {priority_icon} [{task['phase_name']}] {task['task_name']} ({task['assignments']} assignments)")
                        print()
                    
                    # Show next high priority tasks
                    cursor.execute("""
                        SELECT ph.name as phase_name, t.name as task_name, t.priority
                        FROM tasks t
                        JOIN phases ph ON t.phase_id = ph.id
                        WHERE ph.project_id = %s AND t.status = 'todo' AND t.priority IN ('urgent', 'high')
                        ORDER BY t.priority DESC, t.created_at
                        LIMIT 5
                    """, (self.project_id,))
                    
                    next_tasks = cursor.fetchall()
                    
                    if next_tasks:
                        print("⭐ Next High Priority Tasks:")
                        for task in next_tasks:
                            priority_icon = {'urgent': '🔴', 'high': '🟠'}.get(task['priority'], '⚪')
                            print(f"   {priority_icon} [{task['phase_name']}] {task['task_name']}")
                        print()
            
            except Exception as e:
                print(f"❌ Error getting overview: {e}")
        
        return {'phases': phases}
    
    def auto_complete(self, file_path: str) -> bool:
        """Auto-complete assignments based on file work"""
        if not self.db.connection or not self.project_id:
            print("⚠️  Auto-complete requires database connection")
            return False
        
        try:
            with self.db.connection.cursor() as cursor:
                # Find assignments that match this file
                cursor.execute("""
                    SELECT a.id, a.description, a.file_pattern, t.name as task_name
                    FROM assignments a
                    JOIN tasks t ON a.task_id = t.id
                    JOIN phases ph ON t.phase_id = ph.id
                    WHERE ph.project_id = %s 
                    AND a.status != 'completed'
                    AND (a.file_pattern IS NULL OR %s LIKE CONCAT('%%', a.file_pattern, '%%'))
                """, (self.project_id, file_path))
                
                matching_assignments = cursor.fetchall()
                
                if not matching_assignments:
                    print(f"🔍 No matching assignments found for: {file_path}")
                    return False
                
                print(f"🎯 Found {len(matching_assignments)} matching assignments for: {file_path}")
                print()
                
                for assignment in matching_assignments:
                    print(f"✅ Completing: {assignment['description']}")
                    print(f"   📋 Task: {assignment['task_name']}")
                    
                    cursor.execute("""
                        UPDATE assignments 
                        SET status = 'completed', completed_at = NOW()
                        WHERE id = %s
                    """, (assignment['id'],))
                
                print(f"\n🎉 Completed {len(matching_assignments)} assignments!")
                return True
                
        except Exception as e:
            print(f"❌ Error auto-completing: {e}")
            return False
    
    def _fallback_create(self, item_type: str, data: Dict[str, Any]) -> bool:
        """Fallback creation when database unavailable"""
        print(f"⚠️  Database unavailable. Saving {item_type} to JSON fallback.")
        
        try:
            project_root = Path(self.project_path)
            work_dir = project_root / '.claude' / 'work'
            work_dir.mkdir(parents=True, exist_ok=True)
            
            work_file = work_dir / f'{item_type}s.json'
            
            if work_file.exists():
                with open(work_file, 'r') as f:
                    items = json.load(f)
            else:
                items = []
            
            data['created_at'] = datetime.now().isoformat()
            items.append(data)
            
            with open(work_file, 'w') as f:
                json.dump(items, f, indent=2)
            
            print(f"✅ Saved {item_type} to {work_file}")
            return True
            
        except Exception as e:
            print(f"❌ Fallback save failed: {e}")
            return False
    
    def _fallback_list(self, item_type: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Fallback listing when database unavailable"""
        print(f"⚠️  Database unavailable. Reading {item_type} from JSON fallback.")
        
        try:
            project_root = Path(self.project_path)
            work_file = project_root / '.claude' / 'work' / f'{item_type}.json'
            
            if not work_file.exists():
                print(f"📝 No {item_type} found.")
                return []
            
            with open(work_file, 'r') as f:
                items = json.load(f)
            
            # Apply basic filtering
            if filters:
                filtered_items = []
                for item in items:
                    match = True
                    for key, value in filters.items():
                        if value and item.get(key) != value:
                            match = False
                            break
                    if match:
                        filtered_items.append(item)
                items = filtered_items
            
            for item in items:
                print(f"📌 {item.get('name', item.get('description', 'Unknown'))}")
                if 'status' in item:
                    print(f"   Status: {item['status']}")
                print()
            
            return items
            
        except Exception as e:
            print(f"❌ Fallback read failed: {e}")
            return []
    
    def _fallback_update(self, item_type: str, name: str, status: str) -> bool:
        """Fallback update when database unavailable"""
        print(f"⚠️  Database unavailable. Cannot update {item_type} status.")
        return False

def main():
    """CLI entry point for work management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage project work phases, tasks, and assignments')
    parser.add_argument('command', choices=[
        'create-phase', 'create-task', 'create-assignment',
        'list-phases', 'list-tasks', 'list-assignments',
        'update-phase', 'update-task', 'complete-phase', 'complete-task',
        'overview', 'current', 'next', 'auto-complete'
    ], help='Command to execute')
    
    parser.add_argument('name', nargs='?', help='Name of phase/task/assignment')
    parser.add_argument('description', nargs='?', help='Description (for create commands)')
    parser.add_argument('--status', help='Status to set')
    parser.add_argument('--priority', choices=['low', 'medium', 'high', 'urgent'], help='Priority level')
    parser.add_argument('--files', help='File pattern for assignments')
    parser.add_argument('--file', help='File path for auto-complete')
    parser.add_argument('--project', help='Project path (default: current)')
    
    args = parser.parse_args()
    
    # Initialize work manager
    wm = WorkManager(args.project)
    
    # Execute command
    if args.command == 'create-phase':
        if not args.name:
            print("❌ Phase name required")
            return
        wm.create_phase(args.name, args.description, args.status or 'planning')
    
    elif args.command == 'create-task':
        if not args.name or not args.description:
            print("❌ Phase name and task description required")
            return
        wm.create_task(args.name, args.description, None, args.priority or 'medium')
    
    elif args.command == 'create-assignment':
        if not args.name or not args.description:
            print("❌ Task name and assignment description required")
            return
        wm.create_assignment(args.name, args.description, args.files)
    
    elif args.command == 'list-phases':
        wm.list_phases()
    
    elif args.command == 'list-tasks':
        wm.list_tasks(args.name)
    
    elif args.command == 'list-assignments':
        if not args.name:
            print("❌ Task name required")
            return
        wm.list_assignments(args.name)
    
    elif args.command in ['update-phase', 'update-task']:
        if not args.name or not args.status:
            print("❌ Name and status required")
            return
        item_type = args.command.split('-')[1]
        wm.update_status(item_type, args.name, args.status)
    
    elif args.command in ['complete-phase', 'complete-task']:
        if not args.name:
            print("❌ Name required")
            return
        item_type = args.command.split('-')[1]
        wm.update_status(item_type, args.name, 'completed')
    
    elif args.command == 'overview':
        wm.overview()
    
    elif args.command == 'current':
        wm.list_tasks()  # This will show in-progress tasks
    
    elif args.command == 'auto-complete':
        if not args.file:
            print("❌ File path required")
            return
        wm.auto_complete(args.file)
    
    else:
        print(f"❌ Unknown command: {args.command}")

if __name__ == '__main__':
    main()