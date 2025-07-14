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

def test_voice(model_name, description, text="Hello! This is a test of male voice synthesis.", language="en"):
    """Test a specific Coqui TTS model"""
    print(f"\n🎙️  {description}")
    print("=" * 50)
    print(f"Model: {model_name}")
    print(f"Text: {text}")
    print("🔊 Synthesizing...")
    
    start_time = time.time()
    
    try:
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        # Run Coqui TTS
        tts_command = "/Users/hanan/.local/bin/tts"
        
        # Build command based on model type
        if "xtts" in model_name.lower():
            # XTTS requires language and speaker parameters
            cmd = [
                tts_command, 
                "--model_name", model_name,
                "--text", text,
                "--language_idx", language,
                "--out_path", tmp_path
            ]
        else:
            # Standard models
            cmd = [
                tts_command, 
                "--model_name", model_name,
                "--text", text,
                "--out_path", tmp_path
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
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
        print(f"❌ Error with {model_name}: {e}")
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
    print("🎭 Coqui Male Voice Demo")
    print("=" * 30)
    print("Testing different male TTS voices...")
    print("Press Ctrl+C anytime to stop the demo")
    
    # Test text
    demo_text = "Hello! I'm testing different male TTS voices. How do I sound?"
    
    # Define male voice models to test
    models_to_test = [
        ("tts_models/it/mai_male/vits", "Italian Male VITS (Good Quality)", demo_text, "it"),
        ("tts_models/it/mai_male/glow-tts", "Italian Male GlowTTS", demo_text, "it"),
        ("tts_models/bn/custom/vits-male", "Bengali Male VITS", demo_text, "bn"),
        ("tts_models/multilingual/multi-dataset/xtts_v2", "XTTS-v2 Multilingual (Try Male)", demo_text, "en"),
    ]
    
    for model_name, description, text, lang in models_to_test:
        test_voice(model_name, description, text, lang)
    
    print("\n🎉 Male voice demo complete!")
    print("Note: Some models may work better with their native language.")
    print("XTTS-v2 supports voice cloning, so you could clone a male voice!")

if __name__ == "__main__":
    main()