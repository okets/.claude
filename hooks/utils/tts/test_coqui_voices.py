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

def test_voice(model_name, description, text="Hello! This is a test of Coqui text to speech synthesis."):
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
        result = subprocess.run([
            tts_command, 
            "--model_name", model_name,
            "--text", text,
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
    print("🎭 Coqui TTS Voice Demo")
    print("=" * 30)
    print("Testing different TTS models and voices...")
    print("Press Ctrl+C anytime to stop the demo")
    
    # Test text
    demo_text = "Hello! I'm testing different Coqui TTS voices. How do I sound?"
    
    # Define models to test (in order of quality/interest)
    models_to_test = [
        ("tts_models/en/ljspeech/vits", "VITS - High Quality Female (LJSpeech)"),
        ("tts_models/en/ljspeech/vits--neon", "VITS Neon - Enhanced Female"),
        ("tts_models/en/ljspeech/fast_pitch", "FastPitch - Fast Female"),
        ("tts_models/en/ljspeech/tacotron2-DDC", "Tacotron2 DDC - Classic Female"),
        ("tts_models/en/ek1/tacotron2", "Tacotron2 EK1 - Alternative Voice"),
    ]
    
    for model_name, description in models_to_test:
        test_voice(model_name, description, demo_text)
    
    print("\n🎉 Voice demo complete!")
    print("Choose your favorite and we can set it as default in the settings.")

if __name__ == "__main__":
    main()