#!/usr/bin/env python3
"""
Notification Sound Utilities for Smarter-Claude

Provides simple sound notifications for Quiet Mode interaction level.
Cross-platform audio playback (macOS afplay, Windows pygame/winsound, Linux aplay).
"""

import subprocess
from pathlib import Path

# Import cross-platform audio player
try:
    from audio_player import play_audio_file
except ImportError:
    # Fallback to afplay on macOS if audio_player not available
    def play_audio_file(path, timeout=30):
        subprocess.run(["afplay", str(path)], capture_output=True, timeout=timeout)


def get_sounds_dir() -> Path:
    """Get the sounds resources directory"""
    return Path(__file__).parent / "resources" / "sounds"


def play_notification_sound():
    """Play subtle notification sound for Quiet Mode"""
    try:
        sounds_dir = get_sounds_dir()
        notification_sound = sounds_dir / "notification.mp3"

        if notification_sound.exists():
            # Cross-platform audio playback
            play_audio_file(str(notification_sound), timeout=5)
    except Exception:
        # Fail silently if sound playback encounters issues
        pass


def play_completion_sound():
    """Play subtle completion sound for Quiet Mode (stop hook)"""
    try:
        sounds_dir = get_sounds_dir()
        completion_sound = sounds_dir / "decide.mp3"

        if completion_sound.exists():
            # Cross-platform audio playback
            play_audio_file(str(completion_sound), timeout=5)
    except Exception:
        # Fail silently if sound playback encounters issues
        pass


def play_subagent_completion_sound():
    """Play subtle subagent completion sound for Quiet Mode"""
    try:
        sounds_dir = get_sounds_dir()
        # Use the same completion sound for subagent completion
        completion_sound = sounds_dir / "decide.mp3"

        if completion_sound.exists():
            # Cross-platform audio playback
            play_audio_file(str(completion_sound), timeout=5)
    except Exception:
        # Fail silently if sound playback encounters issues
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