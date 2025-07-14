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
    Coqui Male TTS Script
    
    Creates a true male voice by pitch-shifting the Coqui VITS model output.
    Uses ffmpeg for high-quality audio processing to create a deeper, masculine voice.
    
    Usage:
    - ./coqui_male_tts.py                    # Uses default text
    - ./coqui_male_tts.py "Your custom text" # Uses provided text
    
    Features:
    - Genuine male-sounding voice using pitch modification
    - Fast processing (Real-time factor ~0.25)
    - Local processing, no internet required
    - Professional audio processing with ffmpeg
    """
    
    # Load environment variables
    load_dotenv()
    
    # Get text from command line argument or use default
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])  # Join all arguments as text
    else:
        text = "This is Coqui text to speech with a realistic male voice."
    
    print("🎙️  Coqui Male TTS (VITS + Audio Processing)")
    print("=" * 45)
    print(f"🎯 Text: {text}")
    print("🔊 Synthesizing speech...")
    
    start_time = time.time()
    
    try:
        # Create temporary files for processing pipeline
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as processed_file:
            processed_path = processed_file.name
        
        # Step 1: Generate base voice using Coqui VITS
        tts_command = "/Users/hanan/.local/bin/tts"
        result = subprocess.run([
            tts_command, 
            "--model_name", "tts_models/en/ljspeech/vits",
            "--text", text,
            "--out_path", tmp_path
        ], capture_output=True, text=True, check=True)
        
        tts_time = time.time() - start_time
        print(f"✅ TTS synthesis complete! ({tts_time:.2f}s)")
        print("🎚️  Applying male voice transformation...")
        
        # Step 2: Advanced audio processing for masculine voice
        processing_start = time.time()
        
        # Natural male voice transformation (no extortion vibes):
        # - Moderate pitch lowering by 4 semitones (0.757 = 2^(-4/12)) for natural male tone
        # - Light tempo reduction (0.97) for slightly more relaxed speech
        # - Minimal EQ - just gentle bass enhancement for warmth
        # - Keep it conversational, not threatening!
        ffmpeg_result = subprocess.run([
            "ffmpeg", "-y",  # -y to overwrite output file
            "-i", tmp_path,
            "-af", "rubberband=pitch=0.757:tempo=0.97,bass=g=1",  
            "-ar", "22050",  # Standard sample rate
            "-ac", "1",      # Mono for consistency
            "-b:a", "128k",  # Good quality bitrate
            processed_path
        ], capture_output=True, text=True, check=True)
        
        processing_time = time.time() - processing_start
        total_time = time.time() - start_time
        
        print(f"✅ Voice processing complete! ({processing_time:.2f}s)")
        print("🔊 Playing male voice...")
        
        # Play the processed male voice
        subprocess.run(["afplay", processed_path], check=True)
        
        # Clean up temporary files
        os.unlink(tmp_path)
        os.unlink(processed_path)
        
        print(f"✅ Total processing time: {total_time:.2f}s")
        print("🎭 Male voice transformation complete!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Processing Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError as e:
        if "tts" in str(e):
            print("❌ TTS Error: Coqui TTS not found. Install with: uv tool install coqui-tts")
        elif "ffmpeg" in str(e):
            print("❌ Audio Processing Error: ffmpeg not found. Install with: brew install ffmpeg")
        else:
            print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()