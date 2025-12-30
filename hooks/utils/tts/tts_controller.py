#!/usr/bin/env python3
"""
TTS Controller - Manages TTS process interruption (cross-platform)
"""

import subprocess
import sys
import os
import signal
from pathlib import Path

# Try to import psutil, but don't fail if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

def kill_all_tts():
    """Kill all running TTS processes (cross-platform)"""
    try:
        # Try to use cross-platform process_utils first
        sys.path.append(str(Path(__file__).parent.parent))
        from process_utils import stop_all_tts as _stop_tts
        _stop_tts()
    except ImportError:
        # Fallback to original behavior
        _kill_all_tts_fallback()

def _kill_all_tts_fallback():
    """Fallback TTS killing - original macOS + psutil behavior"""
    try:
        # On Unix/macOS, use pkill for native audio commands
        if sys.platform != 'win32':
            subprocess.run(["pkill", "-f", "say"], capture_output=True)
            subprocess.run(["pkill", "-f", "afplay"], capture_output=True)

        # Kill python TTS processes using psutil (cross-platform)
        if HAS_PSUTIL:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('tts' in str(arg).lower() for arg in cmdline):
                        if 'macos_' in str(cmdline) or 'kokoro_' in str(cmdline):
                            proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

    except Exception:
        pass  # Fail silently

def stop_tts():
    """Stop all TTS playback immediately"""
    kill_all_tts()

if __name__ == "__main__":
    stop_tts()