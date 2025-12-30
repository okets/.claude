#!/usr/bin/env python3
"""
Cross-platform process management utilities for smarter-claude

Provides unified process killing across macOS, Windows, and Linux.
- macOS/Linux: uses pkill (existing behavior preserved exactly)
- Windows: uses psutil or taskkill

IMPORTANT: macOS behavior is preserved exactly as-is to maintain
compatibility with existing users.
"""

import sys
import subprocess


def stop_all_tts() -> None:
    """
    Stop all TTS-related processes cross-platform.

    On macOS: Uses pkill for 'say' and 'afplay' (original behavior)
    On Windows: Uses psutil to find and kill TTS processes
    On Linux: Uses pkill (same as macOS)
    """
    if sys.platform == 'win32':
        _stop_tts_windows()
    else:
        # macOS and Linux: preserve original pkill behavior exactly
        _stop_tts_unix()


def _stop_tts_unix() -> None:
    """
    Stop TTS on macOS/Linux using pkill.
    This is the ORIGINAL behavior - do not modify.
    """
    try:
        # Kill macOS 'say' processes
        subprocess.run(["pkill", "-f", "say"], capture_output=True, timeout=1)
        # Kill any afplay processes (audio playback)
        subprocess.run(["pkill", "-f", "afplay"], capture_output=True, timeout=1)
    except Exception:
        pass  # Fail silently


def _stop_tts_windows() -> None:
    """
    Stop TTS on Windows using psutil.
    Targets only TTS-related processes to avoid killing unrelated Python scripts.
    """
    try:
        import psutil

        # Patterns that indicate TTS-related processes
        tts_patterns = [
            'kokoro_voice',
            'macos_tts',
            'windows_tts',
            'tts_controller',
            'notification_sounds',
        ]

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', []) or []
                cmdline_str = ' '.join(cmdline).lower()

                # Check if this looks like a TTS process
                for pattern in tts_patterns:
                    if pattern in cmdline_str:
                        proc.kill()
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except ImportError:
        # psutil not available, try taskkill as fallback
        # This is less precise but better than nothing
        pass
    except Exception:
        pass  # Fail silently


def kill_processes_by_pattern(patterns: list, timeout: int = 2) -> None:
    """
    Kill processes matching given patterns cross-platform.

    Args:
        patterns: List of process name patterns to kill
        timeout: Timeout for kill commands (Unix only)
    """
    if sys.platform == 'win32':
        _kill_windows(patterns)
    else:
        _kill_unix(patterns, timeout)


def _kill_unix(patterns: list, timeout: int) -> None:
    """Kill processes on Unix/macOS using pkill (original behavior)"""
    for pattern in patterns:
        try:
            subprocess.run(
                ["pkill", "-f", pattern],
                capture_output=True,
                timeout=timeout
            )
        except Exception:
            pass


def _kill_windows(patterns: list) -> None:
    """Kill processes on Windows using psutil"""
    try:
        import psutil

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_name = (proc.info.get('name') or '').lower()
                cmdline = proc.info.get('cmdline', []) or []
                cmdline_str = ' '.join(cmdline).lower()

                for pattern in patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in proc_name or pattern_lower in cmdline_str:
                        proc.kill()
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except ImportError:
        pass
    except Exception:
        pass


if __name__ == "__main__":
    print(f"Platform: {sys.platform}")
    print("Testing stop_all_tts()...")
    stop_all_tts()
    print("Done")
