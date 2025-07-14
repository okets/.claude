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
from dotenv import load_dotenv

def main():
    """
    Coqui TTS Script
    
    High-quality local text-to-speech using Coqui TTS VITS model.
    Provides excellent speech synthesis with good performance.
    
    Usage:
    - ./coqui_tts.py                    # Uses default text
    - ./coqui_tts.py "Your custom text" # Uses provided text
    
    Features:
    - High-quality neural speech synthesis
    - Fast processing (Real-time factor ~0.15)
    - Local processing, no internet required
    - Good naturalness and clarity
    """
    
    # Load environment variables
    load_dotenv()
    
    # Get text from command line argument or use default
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])  # Join all arguments as text
    else:
        text = "This is Coqui text to speech synthesis."
    
    print("🎙️  Coqui TTS (VITS)")
    print("=" * 25)
    print(f"🎯 Text: {text}")
    print("🔊 Synthesizing speech...")
    
    start_time = time.time()
    
    try:
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        # Run Coqui TTS with VITS model (good quality, fast)
        # Use the full path to the tts command to avoid environment issues
        tts_command = "/Users/hanan/.local/bin/tts"
        result = subprocess.run([
            tts_command, 
            "--model_name", "tts_models/en/ljspeech/vits",
            "--text", text,
            "--out_path", tmp_path
        ], capture_output=True, text=True, check=True)
        
        processing_time = time.time() - start_time
        
        # Play the generated audio
        subprocess.run(["afplay", tmp_path], check=True)
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        print(f"✅ Synthesis complete! ({processing_time:.2f}s)")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ TTS Error: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ TTS Error: Coqui TTS not found. Install with: uv tool install coqui-tts")
        sys.exit(1)
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()