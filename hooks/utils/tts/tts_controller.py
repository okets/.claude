#!/usr/bin/env python3
"""
TTS Controller - Manages TTS process interruption
"""

import subprocess
import psutil
import os
import signal
from pathlib import Path

def kill_all_tts():
    """Kill all running TTS processes"""
    try:
        # Kill macOS 'say' processes
        subprocess.run(["pkill", "-f", "say"], capture_output=True)
        
        # Kill any afplay processes (audio playback)
        subprocess.run(["pkill", "-f", "afplay"], capture_output=True)
        
        # Kill python TTS processes
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