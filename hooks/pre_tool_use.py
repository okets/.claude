#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import json
import sys
import re
from pathlib import Path

# Import our cycle utilities
sys.path.append(str(Path(__file__).parent / 'utils'))
try:
    from cycle_utils import dump_hook_data
except ImportError:
    # Fallback if utils not available
    def dump_hook_data(hook_name, hook_data, session_id, transcript_path):
        pass


def get_project_root():
    """Find project root by looking for .git directory"""
    cwd = Path.cwd()
    current = cwd
    while current != current.parent:
        if (current / '.git').exists():
            return current
        current = current.parent
    return cwd  # Fallback to current directory

def is_outside_project(path_str):
    """Check if a path targets outside the current project"""
    try:
        project_root = get_project_root()
        target_path = Path(path_str).resolve()
        project_root = project_root.resolve()
        
        # Check if target is within project
        try:
            target_path.relative_to(project_root)
            return False  # Inside project
        except ValueError:
            return True   # Outside project
    except:
        # If we can't resolve paths, err on the side of caution
        return True

def is_dangerous_outside_project_command(command):
    """
    Check for operations targeting outside the current project.
    Allow all operations within project, block operations outside.
    """
    normalized = ' '.join(command.lower().split())
    
    # Extract potential paths from rm commands
    rm_patterns = [
        r'\brm\s+(?:-[a-z]*\s+)*([^\s]+)',  # rm [flags] path
        r'\brm\s+(?:--[a-z-]+\s+)*([^\s]+)',  # rm --flags path
    ]
    
    for pattern in rm_patterns:
        matches = re.findall(pattern, normalized)
        for match in matches:
            # Skip flags
            if match.startswith('-'):
                continue
            
            # Check specific dangerous patterns that should always be blocked
            dangerous_absolutes = [
                '/', '/usr', '/etc', '/var', '/home', '/root',
                '~', '~/', '$HOME'
            ]
            
            if match in dangerous_absolutes or match.startswith('/usr/') or match.startswith('/etc/'):
                return True
                
            # Check if targeting outside project
            if is_outside_project(match):
                return True
    
    return False

def needs_git_confirmation(command):
    """Check if git command needs user confirmation"""
    git_confirm_patterns = [
        r'\bgit\s+commit',
        r'\bgit\s+push', 
        r'\bgit\s+reset\s+--hard',
        r'\bgit\s+rebase',
        r'\bgit\s+merge\s+--no-ff',
        r'\bgit\s+force-push',
        r'\bgit\s+push\s+.*--force'
    ]
    
    command_lower = command.lower()
    return any(re.search(pattern, command_lower) for pattern in git_confirm_patterns)

def is_env_file_access(tool_name, tool_input):
    """
    Check if any tool is trying to access .env files containing sensitive data.
    """
    if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write', 'Bash']:
        # Check file paths for file-based tools
        if tool_name in ['Read', 'Edit', 'MultiEdit', 'Write']:
            file_path = tool_input.get('file_path', '')
            if '.env' in file_path and not file_path.endswith('.env.sample'):
                return True
        
        # Check bash commands for .env file access
        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            # Pattern to detect .env file access (but allow .env.sample)
            env_patterns = [
                r'\b\.env\b(?!\.sample)',  # .env but not .env.sample
                r'cat\s+.*\.env\b(?!\.sample)',  # cat .env
                r'echo\s+.*>\s*\.env\b(?!\.sample)',  # echo > .env
                r'touch\s+.*\.env\b(?!\.sample)',  # touch .env
                r'cp\s+.*\.env\b(?!\.sample)',  # cp .env
                r'mv\s+.*\.env\b(?!\.sample)',  # mv .env
            ]
            
            for pattern in env_patterns:
                if re.search(pattern, command):
                    return True
    
    return False

def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)
        
        # Dump raw hook data for analysis
        session_id = input_data.get('session_id', '')
        transcript_path = input_data.get('transcript_path', '')
        dump_hook_data('PreToolUse', input_data, session_id, transcript_path)
        
        # Optional debug logging - uncomment for debugging
        # debug_log = Path('/tmp') / 'claude_debug_pre_tool_use.json'
        # with open(debug_log, 'w') as f:
        #     json.dump(input_data, f, indent=2)
        
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        
        # Check for .env file access (blocks access to sensitive environment files)
        if is_env_file_access(tool_name, tool_input):
            print("BLOCKED: Access to .env files containing sensitive data is prohibited", file=sys.stderr)
            print("Use .env.sample for template files instead", file=sys.stderr)
            
            
            sys.exit(2)  # Exit code 2 blocks tool call and shows error to Claude
        
        # Enhanced security for bash commands
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            
            # Block operations outside project directory
            if is_dangerous_outside_project_command(command):
                print("BLOCKED: Operation targeting outside project directory", file=sys.stderr)
                print("Only operations within the current project are allowed", file=sys.stderr)
                
                
                sys.exit(2)
            
            # Git confirmation - show warning but allow
            if needs_git_confirmation(command):
                print(f"⚠️  Claude is running git command: {command}", file=sys.stderr)
                print("📋 This will affect your git history.", file=sys.stderr)
                
                try:
                    # Show current git status for context
                    import subprocess
                    result = subprocess.run(['git', 'status', '--porcelain'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        print("📁 Current changes:", file=sys.stderr)
                        for line in result.stdout.strip().split('\n')[:5]:  # Show first 5 changes
                            print(f"   {line}", file=sys.stderr)
                except:
                    pass  # Don't fail on git status error
                
                print("✅ Git command proceeding...", file=sys.stderr)
        
        
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Gracefully handle JSON decode errors
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)

if __name__ == '__main__':
    main()