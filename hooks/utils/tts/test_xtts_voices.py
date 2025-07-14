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
import subprocess
import tempfile
from pathlib import Path

def test_xtts_voice(speaker_name, text="Hello! This is a test of Coqui XTTS voice synthesis."):
    """Test XTTS with different speakers"""
    print(f"\n🎙️  XTTS Speaker: {speaker_name}")
    print("=" * 50)
    print(f"Text: {text}")
    print("🔊 Synthesizing...")
    
    start_time = time.time()
    
    try:
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        # Run Coqui TTS with XTTS-v2 model
        tts_command = "/Users/hanan/.local/bin/tts"
        result = subprocess.run([
            tts_command, 
            "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
            "--text", text,
            "--speaker_idx", speaker_name,
            "--language_idx", "en",
            "--out_path", tmp_path
        ], capture_output=True, text=True, check=True)
        
        processing_time = time.time() - start_time
        
        print(f"✅ Generated in {processing_time:.2f}s")
        print("🔊 Playing...")
        
        # Play the generated audio
        subprocess.run(["afplay", tmp_path], check=True)
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        print("✅ Playback complete!")
        
        # Wait for user input before continuing
        input("Press Enter to continue to next voice...")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error with speaker {speaker_name}: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
    except KeyboardInterrupt:
        # Clean up and exit if user interrupts
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        print("\n🛑 Voice demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    print("🎭 Coqui XTTS Voice Demo")
    print("=" * 30)
    print("Testing XTTS-v2 with different speakers...")
    print("Press Ctrl+C anytime to stop the demo")
    
    # Test text
    demo_text = "Hello! I'm testing different XTTS voices. How do I sound today?"
    
    # Try different speaker indices for XTTS
    # Note: XTTS speaker indices are usually numerical or specific names
    speakers_to_test = ["0", "1", "2", "3", "4"]  # Start with numerical indices
    
    for speaker in speakers_to_test:
        test_xtts_voice(speaker, demo_text)
    
    print("\n🎉 XTTS voice demo complete!")
    print("XTTS also supports voice cloning from audio samples!")

if __name__ == "__main__":
    main()