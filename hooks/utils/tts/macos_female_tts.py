#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

def main():
    """
    macOS Native TTS Script
    
    Uses macOS native NSSpeechSynthesizer for fast, system-integrated text-to-speech.
    Accepts optional text prompt as command-line argument.
    
    Usage:
    - ./macos_native_tts.py                    # Uses default text
    - ./macos_native_tts.py "Your custom text" # Uses provided text
    
    Features:
    - Native macOS system voices
    - Fast startup and low latency
    - No additional model downloads
    - High system integration
    - Voice rate and pitch control
    """
    
    # Load environment variables
    load_dotenv()
    
    # Check if running on macOS
    if sys.platform != "darwin":
        print("❌ Error: This script only works on macOS")
        print("Use Kokoro TTS for cross-platform support")
        sys.exit(1)
    
    # Get text from command line argument or use default
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])  # Join all arguments as text
    else:
        text = "This is macOS native text to speech synthesis."
    
    print("🎙️  macOS Female Voice (Samantha)")
    print("=" * 32)
    print(f"🎯 Text: {text}")
    print("🔊 Speaking with system voice...")
    
    # Use command-line 'say' tool with high-quality female voice
    try:
        import subprocess
        # Available female voices: Samantha (high-quality), Victoria (British), Fiona (Scottish)
        female_voice = "Samantha"  # High-quality American English female voice
        
        subprocess.run(["say", "-v", female_voice, text], check=True)
        print("✅ Playback complete!")
        
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()