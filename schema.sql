-- Claude Code Project Intelligence Database Schema
-- Supports project work tracking with phases, tasks, and assignments

CREATE DATABASE IF NOT EXISTS claude_intelligence;
USE claude_intelligence;

-- Projects table - each codebase you work on
CREATE TABLE projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    path VARCHAR(500) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_path (path)
);

-- Sessions - each time you work with Claude on a project
CREATE TABLE sessions (
    id VARCHAR(50) PRIMARY KEY, -- UUID from Claude
    project_id INT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL,
    summary TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    INDEX idx_project_started (project_id, started_at)
);

-- Phases - high-level project phases (e.g., "Setup", "Core Development", "Testing")
CREATE TABLE phases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status ENUM('planning', 'active', 'completed', 'paused') DEFAULT 'planning',
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE KEY unique_phase_per_project (project_id, name),
    INDEX idx_project_status (project_id, status)
);

-- Tasks - specific work items within phases
CREATE TABLE tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phase_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status ENUM('todo', 'in_progress', 'completed', 'blocked') DEFAULT 'todo',
    priority ENUM('low', 'medium', 'high', 'urgent') DEFAULT 'medium',
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (phase_id) REFERENCES phases(id) ON DELETE CASCADE,
    INDEX idx_phase_status (phase_id, status),
    INDEX idx_priority_status (priority, status)
);

-- Assignments - specific code changes or actions within tasks
CREATE TABLE assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    description TEXT NOT NULL,
    file_pattern VARCHAR(255), -- e.g., "src/components/*.tsx"
    status ENUM('todo', 'in_progress', 'completed') DEFAULT 'todo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    INDEX idx_task_status (task_id, status)
);

-- Tool executions - every tool Claude uses
CREATE TABLE tool_executions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    tool_input JSON,
    tool_output JSON,
    success BOOLEAN DEFAULT TRUE,
    intent VARCHAR(100), -- e.g., "reading-file", "modifying-file", "git-operation"
    files_touched JSON, -- Array of file paths
    duration_ms INT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assignment_id INT NULL, -- Link to assignment if applicable
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE SET NULL,
    INDEX idx_session_executed (session_id, executed_at),
    INDEX idx_tool_intent (tool_name, intent),
    INDEX idx_assignment (assignment_id)
);

-- Security events - blocked operations, warnings, etc.
CREATE TABLE security_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    event_type ENUM('blocked', 'warned', 'allowed') NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    tool_input JSON,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_session_type (session_id, event_type),
    INDEX idx_created (created_at)
);

-- File relationships - which files are often modified together
CREATE TABLE file_relationships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    file1_path VARCHAR(500) NOT NULL,
    file2_path VARCHAR(500) NOT NULL,
    co_modification_count INT DEFAULT 1,
    last_modified_together TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE KEY unique_file_pair (project_id, file1_path, file2_path),
    INDEX idx_project_files (project_id, file1_path, file2_path)
);

-- Work patterns - common sequences of operations
CREATE TABLE work_patterns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    pattern_name VARCHAR(255) NOT NULL,
    tool_sequence JSON, -- Array of tool names in order
    frequency_count INT DEFAULT 1,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    INDEX idx_project_pattern (project_id, pattern_name)
);

-- Views for common queries
CREATE VIEW active_work AS
SELECT 
    p.name as project_name,
    ph.name as phase_name,
    t.name as task_name,
    t.status as task_status,
    t.priority,
    COUNT(a.id) as assignment_count,
    COUNT(CASE WHEN a.status = 'completed' THEN 1 END) as completed_assignments
FROM projects p
JOIN phases ph ON p.id = ph.project_id
JOIN tasks t ON ph.id = t.phase_id
LEFT JOIN assignments a ON t.id = a.task_id
WHERE t.status IN ('todo', 'in_progress')
GROUP BY p.id, ph.id, t.id
ORDER BY t.priority DESC, t.created_at;

CREATE VIEW recent_activity AS
SELECT 
    p.name as project_name,
    s.id as session_id,
    te.tool_name,
    te.intent,
    te.files_touched,
    te.executed_at
FROM projects p
JOIN sessions s ON p.id = s.project_id
JOIN tool_executions te ON s.id = te.session_id
WHERE te.executed_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY te.executed_at DESC;