#!/usr/bin/env python3
"""
Settings Management for Smarter-Claude

Implements hierarchical settings system:
project > global > defaults

Settings files:
- <project>/.claude/smarter-claude.json (project-specific overrides)
- ~/.claude/hooks/utils/smarter-claude-global.json (global config)
- Built-in defaults (fallback)
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from cycle_utils import detect_project_root, get_project_smarter_claude_dir


class SmarterClaudeSettings:
    """Hierarchical settings manager for smarter-claude"""
    
    # Default settings schema
    DEFAULT_SETTINGS = {
        "interaction_level": "verbose",  # silent, quiet, concise, verbose
        "interaction_level_options": "silent, quiet, concise, verbose",
        "tts_enabled": True,
        "tts_engine": "macos-male",  # kokoro voices, macos-female, macos-male
        "tts_engine_options": "kokoro-af_alloy, kokoro-af_river, kokoro-af_sky, kokoro-af_sarah, kokoro-af_nicole, kokoro-am_adam, kokoro-am_echo, kokoro-am_puck, kokoro-am_michael, kokoro-bf_emma, kokoro-bm_daniel, kokoro-bm_lewis, kokoro-bm_george, macos-female, macos-male",
        "notification_sounds": True,
        "cleanup_policy": {
            "retention_cycles": 2,
            "auto_cleanup": True
        },
        "database_settings": {
            "auto_ingestion": True,
            "backup_cycles": 5
        },
        "logging_settings": {
            "hook_logging": True,
            "debug_logging": False,
            "speak_hook_logging": False,
            "log_level": "info"
        }
    }
    
    def __init__(self):
        self._settings_cache = None
        self._project_root = None
        
    def get_project_root(self) -> Path:
        """Get and cache project root"""
        if self._project_root is None:
            self._project_root = detect_project_root()
        return self._project_root
        
    def get_project_settings_path(self) -> Path:
        """Get path to project-specific settings file"""
        return get_project_smarter_claude_dir() / "smarter-claude.json"
        
    def get_global_settings_path(self) -> Path:
        """Get path to global settings file"""
        return Path(__file__).parent / "smarter-claude-global.json"
        
    def load_settings(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load settings with hierarchy: project > global > defaults
        
        Args:
            force_reload: If True, ignore cache and reload from files
            
        Returns:
            Dict containing merged settings
        """
        if self._settings_cache is not None and not force_reload:
            return self._settings_cache
            
        # Start with defaults
        settings = self.DEFAULT_SETTINGS.copy()
        
        # Layer 1: Global settings (if exists)
        global_settings_path = self.get_global_settings_path()
        if global_settings_path.exists():
            try:
                with open(global_settings_path, 'r') as f:
                    global_settings = json.load(f)
                settings = self._deep_merge(settings, global_settings)
            except (json.JSONDecodeError, IOError) as e:
                # Log error but continue with defaults
                self._log_error(f"Failed to load global settings: {e}")
        
        # Layer 2: Project settings (if exists)
        project_settings_path = self.get_project_settings_path()
        if project_settings_path.exists():
            try:
                with open(project_settings_path, 'r') as f:
                    project_settings = json.load(f)
                settings = self._deep_merge(settings, project_settings)
            except (json.JSONDecodeError, IOError) as e:
                # Log error but continue with global/defaults
                self._log_error(f"Failed to load project settings: {e}")
        
        # Cache the merged settings
        self._settings_cache = settings
        return settings
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value with dot notation support
        
        Args:
            key: Setting key (supports dot notation like "cleanup_policy.retention_cycles")
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        settings = self.load_settings()
        
        # Support dot notation for nested keys
        keys = key.split('.')
        value = settings
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set_project_setting(self, key: str, value: Any) -> bool:
        """
        Set a project-specific setting
        
        Args:
            key: Setting key (supports dot notation)
            value: Setting value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing project settings or create empty dict
            project_settings_path = self.get_project_settings_path()
            
            if project_settings_path.exists():
                with open(project_settings_path, 'r') as f:
                    project_settings = json.load(f)
            else:
                project_settings = {}
            
            # Set the value using dot notation
            keys = key.split('.')
            current = project_settings
            
            # Navigate to the parent of the target key
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # Set the final value
            current[keys[-1]] = value
            
            # Ensure directory exists
            project_settings_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write back to file
            with open(project_settings_path, 'w') as f:
                json.dump(project_settings, f, indent=2)
                
            # Clear cache to force reload
            self._settings_cache = None
            
            return True
            
        except Exception as e:
            self._log_error(f"Failed to set project setting {key}: {e}")
            return False
            
    def create_default_project_settings(self) -> bool:
        """
        Create a default project settings file with common overrides
        
        Returns:
            True if successful, False otherwise
        """
        default_project_settings = {
            "interaction_level": "verbose",
            "interaction_level_options": "silent, quiet, concise, verbose",
            "tts_engine": "macos-male",
            "tts_engine_options": "kokoro-af_alloy, kokoro-af_river, kokoro-af_sky, kokoro-af_sarah, kokoro-af_nicole, kokoro-am_adam, kokoro-am_echo, kokoro-am_puck, kokoro-am_michael, kokoro-bf_emma, kokoro-bm_daniel, kokoro-bm_lewis, kokoro-bm_george, macos-female, macos-male",
            "cleanup_policy": {
                "retention_cycles": 2
            },
            "logging_settings": {
                "speak_hook_logging": False,
                "debug_logging": False
            }
        }
        
        try:
            project_settings_path = self.get_project_settings_path()
            
            # Don't overwrite existing settings
            if project_settings_path.exists():
                return True
                
            # Ensure directory exists
            project_settings_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write default settings
            with open(project_settings_path, 'w') as f:
                json.dump(default_project_settings, f, indent=2)
                
            return True
            
        except Exception as e:
            self._log_error(f"Failed to create default project settings: {e}")
            return False
            
    def get_settings_info(self) -> Dict[str, Any]:
        """
        Get information about current settings sources
        
        Returns:
            Dict with settings file paths and status
        """
        project_path = self.get_project_settings_path()
        global_path = self.get_global_settings_path()
        
        return {
            "project_root": str(self.get_project_root()),
            "project_settings": {
                "path": str(project_path),
                "exists": project_path.exists(),
                "readable": project_path.exists() and os.access(project_path, os.R_OK)
            },
            "global_settings": {
                "path": str(global_path),
                "exists": global_path.exists(),
                "readable": global_path.exists() and os.access(global_path, os.R_OK)
            },
            "effective_settings": self.load_settings()
        }
        
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries
        
        Args:
            base: Base dictionary
            override: Dictionary with override values
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def _log_error(self, message: str):
        """Log error messages (simple fallback logging)"""
        try:
            with open('/tmp/smarter_claude_settings_debug.log', 'a') as f:
                from datetime import datetime
                f.write(f"{datetime.now().isoformat()}: {message}\n")
        except:
            pass  # Fail silently


# Global settings instance
_settings_instance = None

def get_settings() -> SmarterClaudeSettings:
    """Get singleton settings instance"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SmarterClaudeSettings()
    return _settings_instance


def get_setting(key: str, default: Any = None) -> Any:
    """Convenience function to get a setting value"""
    return get_settings().get(key, default)


def set_project_setting(key: str, value: Any) -> bool:
    """Convenience function to set a project setting"""
    return get_settings().set_project_setting(key, value)


# Interaction level helpers
def get_interaction_level() -> str:
    """Get current interaction level"""
    return get_setting("interaction_level", "concise")


def is_tts_enabled() -> bool:
    """Check if TTS is enabled"""
    level = get_interaction_level()
    if level == "silent":
        return False
    return get_setting("tts_enabled", True)


def should_announce_hooks() -> bool:
    """Check if hook announcements should be made"""
    level = get_interaction_level()
    return level in ["concise", "verbose"]


def should_announce_verbose() -> bool:
    """Check if verbose announcements should be made"""
    level = get_interaction_level()
    return level == "verbose"


if __name__ == "__main__":
    # Test the settings system
    settings = get_settings()
    print("Settings Info:")
    info = settings.get_settings_info()
    print(json.dumps(info, indent=2))
    
    print(f"\nInteraction Level: {get_interaction_level()}")
    print(f"TTS Enabled: {is_tts_enabled()}")
    print(f"Retention Cycles: {get_setting('cleanup_policy.retention_cycles')}")