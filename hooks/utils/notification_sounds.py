#!/usr/bin/env python3
"""
Notification Sound Utilities for Smarter-Claude

Provides simple sound notifications for Quiet Mode interaction level.
Uses afplay on macOS for minimal, subtle audio feedback.
"""

import subprocess
from pathlib import Path


def get_sounds_dir() -> Path:
    """Get the sounds resources directory"""
    return Path(__file__).parent / "resources" / "sounds"


def play_notification_sound():
    """Play subtle notification sound for Quiet Mode"""
    try:
        sounds_dir = get_sounds_dir()
        notification_sound = sounds_dir / "notification.mp3"
        
        if notification_sound.exists():
            # Use afplay on macOS for minimal audio feedback
            subprocess.run([
                "afplay", str(notification_sound)
            ], 
            capture_output=True,  # Suppress output
            timeout=5  # 5-second timeout
            )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fail silently if sound playback encounters issues
        pass
    except Exception:
        # Fail silently for any other errors
        pass


def play_completion_sound():
    """Play subtle completion sound for Quiet Mode (stop hook)"""
    try:
        sounds_dir = get_sounds_dir()
        completion_sound = sounds_dir / "decide.mp3"
        
        if completion_sound.exists():
            # Use afplay on macOS for minimal audio feedback
            subprocess.run([
                "afplay", str(completion_sound)
            ], 
            capture_output=True,  # Suppress output
            timeout=5  # 5-second timeout
            )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fail silently if sound playback encounters issues
        pass
    except Exception:
        # Fail silently for any other errors
        pass


def play_subagent_completion_sound():
    """Play subtle subagent completion sound for Quiet Mode"""
    try:
        sounds_dir = get_sounds_dir()
        # Use the same completion sound for subagent completion
        completion_sound = sounds_dir / "decide.mp3"
        
        if completion_sound.exists():
            # Use afplay on macOS for minimal audio feedback
            subprocess.run([
                "afplay", str(completion_sound)
            ], 
            capture_output=True,  # Suppress output
            timeout=5  # 5-second timeout
            )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fail silently if sound playback encounters issues
        pass
    except Exception:
        # Fail silently for any other errors
        pass


if __name__ == "__main__":
    # Test the sound functions
    print("Testing notification sound...")
    play_notification_sound()
    
    import time
    time.sleep(1)
    
    print("Testing completion sound...")
    play_completion_sound()
    
    print("Sound test complete!")