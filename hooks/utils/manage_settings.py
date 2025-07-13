#!/usr/bin/env python3
"""
Smarter-Claude Settings Management CLI

Usage:
    python manage_settings.py info                           # Show current settings info
    python manage_settings.py get <key>                      # Get a setting value
    python manage_settings.py set <key> <value>              # Set a project setting
    python manage_settings.py init                           # Create default project settings
    python manage_settings.py levels                         # Show interaction levels info
"""

import sys
import json
from pathlib import Path
from settings import get_settings, get_setting, set_project_setting, get_interaction_level


def show_info():
    """Show current settings information"""
    settings = get_settings()
    info = settings.get_settings_info()
    
    print("=== Smarter-Claude Settings Info ===")
    print(f"Project Root: {info['project_root']}")
    print()
    
    print("Settings Files:")
    for name, file_info in [("Project", info['project_settings']), ("Global", info['global_settings'])]:
        status = "✅ EXISTS" if file_info['exists'] else "❌ MISSING"
        readable = "✅ READABLE" if file_info.get('readable', False) else "❌ NOT READABLE"
        print(f"  {name}: {file_info['path']}")
        print(f"    Status: {status}")
        if file_info['exists']:
            print(f"    Access: {readable}")
        print()
    
    print("Effective Settings:")
    print(json.dumps(info['effective_settings'], indent=2))


def show_levels():
    """Show interaction levels information"""
    print("=== Interaction Levels (User-Facing Content) ===")
    current = get_interaction_level()
    
    levels = {
        "silent": {
            "description": "No user content announcements (user intent, task completion, etc.)",
            "tts": False,
            "sounds": False,
            "announcements": False
        },
        "quiet": {
            "description": "Subtle sounds only (notification.mp3, decide.mp3), no verbal announcements",
            "tts": False,
            "sounds": True,
            "announcements": False
        },
        "concise": {
            "description": "Brief TTS about task completion and user intent [DEFAULT]",
            "tts": True,
            "sounds": True,
            "announcements": True
        },
        "verbose": {
            "description": "Detailed announcements about workflow and user content",
            "tts": True,
            "sounds": True,
            "announcements": True,
            "verbose": True
        }
    }
    
    for level, config in levels.items():
        marker = ">>> " if level == current else "    "
        print(f"{marker}{level.upper()}")
        print(f"    {config['description']}")
        if level == current:
            print(f"    (Currently Active)")
        print()
    
    print("=== Infrastructure/Debug Settings ===")
    from settings import get_setting
    speak_hook_logging = get_setting("logging_settings.speak_hook_logging", False)
    debug_logging = get_setting("logging_settings.debug_logging", False)
    
    print(f"speak_hook_logging: {speak_hook_logging}")
    print("  Controls TTS for infrastructure messages (database operations, hook debugging)")
    print(f"debug_logging: {debug_logging}")
    print("  Controls debug log output")
    print()
    print("Note: Infrastructure settings are separate from user content interaction levels")


def get_value(key):
    """Get a setting value"""
    value = get_setting(key)
    if value is None:
        print(f"Setting '{key}' not found")
        return False
    
    print(f"{key} = {json.dumps(value, indent=2)}")
    return True


def set_value(key, value_str):
    """Set a project setting value"""
    # Try to parse as JSON first, then fall back to string
    try:
        value = json.loads(value_str)
    except json.JSONDecodeError:
        # If it's not valid JSON, treat as string
        value = value_str
    
    success = set_project_setting(key, value)
    if success:
        print(f"✅ Set {key} = {json.dumps(value)}")
        print("Project settings updated successfully!")
    else:
        print(f"❌ Failed to set {key}")
        return False
    return True


def init_project():
    """Initialize default project settings"""
    settings = get_settings()
    success = settings.create_default_project_settings()
    
    if success:
        project_path = settings.get_project_settings_path()
        print(f"✅ Created default project settings at:")
        print(f"   {project_path}")
        print()
        print("Default settings created:")
        with open(project_path, 'r') as f:
            print(json.dumps(json.load(f), indent=2))
    else:
        print("❌ Failed to create project settings")
        return False
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    
    if command == "info":
        show_info()
    elif command == "levels":
        show_levels()
    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: manage_settings.py get <key>")
            return
        get_value(sys.argv[2])
    elif command == "set":
        if len(sys.argv) < 4:
            print("Usage: manage_settings.py set <key> <value>")
            return
        set_value(sys.argv[2], sys.argv[3])
    elif command == "init":
        init_project()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()