#!/usr/bin/env python3
"""
Cross-platform audio playback utility for smarter-claude

Provides unified audio playback across macOS, Windows, and Linux.
- macOS: uses afplay (native)
- Windows: uses pygame (with winsound fallback for WAV)
- Linux: uses aplay or pygame
"""

import sys
import subprocess
import time
from pathlib import Path


def play_audio_file(file_path: str, timeout: int = 30) -> bool:
    """
    Play an audio file using platform-appropriate method.

    Args:
        file_path: Path to audio file (WAV or MP3)
        timeout: Maximum playback time in seconds

    Returns:
        bool: True if playback succeeded
    """
    if sys.platform == 'darwin':
        return _play_macos(file_path, timeout)
    elif sys.platform == 'win32':
        return _play_windows(file_path, timeout)
    else:
        return _play_linux(file_path, timeout)


def _play_macos(file_path: str, timeout: int) -> bool:
    """macOS audio playback using afplay"""
    try:
        subprocess.run(["afplay", file_path], check=True, timeout=timeout)
        return True
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        return False


def _play_windows(file_path: str, timeout: int) -> bool:
    """Windows audio playback using pygame or winsound"""
    file_ext = Path(file_path).suffix.lower()

    # Try pygame first (supports WAV and MP3)
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()

        # Wait for playback to complete or timeout
        start = time.time()
        while pygame.mixer.music.get_busy():
            if time.time() - start > timeout:
                pygame.mixer.music.stop()
                break
            time.sleep(0.1)
        return True
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: winsound for WAV files only
    if file_ext == '.wav':
        try:
            import winsound
            winsound.PlaySound(file_path, winsound.SND_FILENAME)
            return True
        except Exception:
            pass

    # Last resort: PowerShell MediaPlayer
    try:
        # Escape path for PowerShell
        escaped_path = file_path.replace("'", "''")
        ps_cmd = f'''
Add-Type -AssemblyName presentationCore
$mediaPlayer = New-Object System.Windows.Media.MediaPlayer
$mediaPlayer.Open([Uri]'{escaped_path}')
$mediaPlayer.Play()
Start-Sleep -Seconds {min(timeout, 10)}
'''
        subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True,
            timeout=timeout + 2
        )
        return True
    except Exception:
        return False


def _play_linux(file_path: str, timeout: int) -> bool:
    """Linux audio playback using aplay or pygame"""
    file_ext = Path(file_path).suffix.lower()

    # Try aplay first (for WAV)
    if file_ext == '.wav':
        try:
            subprocess.run(["aplay", file_path], check=True, timeout=timeout)
            return True
        except (FileNotFoundError, subprocess.SubprocessError):
            pass

    # Try pygame
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()

        start = time.time()
        while pygame.mixer.music.get_busy():
            if time.time() - start > timeout:
                pygame.mixer.music.stop()
                break
            time.sleep(0.1)
        return True
    except ImportError:
        pass
    except Exception:
        pass

    # Try ffplay as last resort
    try:
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", file_path],
            capture_output=True,
            timeout=timeout
        )
        return True
    except Exception:
        return False


if __name__ == "__main__":
    # Test audio playback
    if len(sys.argv) < 2:
        print("Usage: audio_player.py <audio_file>")
        sys.exit(1)

    audio_file = sys.argv[1]
    print(f"Playing: {audio_file}")
    success = play_audio_file(audio_file)
    print(f"Playback {'succeeded' if success else 'failed'}")
    sys.exit(0 if success else 1)
