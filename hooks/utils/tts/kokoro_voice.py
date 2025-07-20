#!/usr/bin/env python3
"""
Kokoro Voice TTS - Complete Kokoro TTS implementation
Handles all 13 available Kokoro voices with installation and streaming support
"""

import sys
import subprocess
import tempfile
import time
from pathlib import Path

def is_kokoro_installed():
    """Check if Kokoro is installed"""
    kokoro_dir = Path.home() / ".kokoro-tts"
    model_file = kokoro_dir / "models" / "kokoro-v1.0.onnx"
    return model_file.exists()

def install_kokoro():
    """Install Kokoro TTS"""
    print("🚀 First run - installing Kokoro TTS...")
    
    # Create installer script inline
    installer_code = '''
import subprocess
import urllib.request
from pathlib import Path

install_dir = Path.home() / ".kokoro-tts" / "models"
install_dir.mkdir(parents=True, exist_ok=True)

model_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

print("📥 Downloading Kokoro model...")
urllib.request.urlretrieve(model_url, install_dir / "kokoro-v1.0.onnx")
print("📥 Downloading voices...")
urllib.request.urlretrieve(voices_url, install_dir / "voices-v1.0.bin")
print("✅ Kokoro installed!")
'''
    
    try:
        subprocess.run([sys.executable, "-c", installer_code], check=True)
        return True
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return False

def speak_text(text, voice="am_echo", use_streaming=False):
    """Speak text using Kokoro TTS"""
    try:
        # Import kokoro (install if needed)
        try:
            from kokoro_onnx import Kokoro
        except ImportError:
            print("📦 Installing kokoro-onnx...")
            subprocess.run([sys.executable, "-m", "pip", "install", "--user", "kokoro-onnx", "soundfile"], check=True)
            from kokoro_onnx import Kokoro
        
        # Find models
        models_dir = Path.home() / ".kokoro-tts" / "models"
        model_path = models_dir / "kokoro-v1.0.onnx"
        voices_path = models_dir / "voices-v1.0.bin"
        
        if not model_path.exists():
            if not install_kokoro():
                return False
        
        # Initialize TTS
        kokoro = Kokoro(str(model_path), str(voices_path))
        
        if use_streaming:
            return speak_streaming(kokoro, text, voice)
        else:
            return speak_standard(kokoro, text, voice)
        
    except Exception as e:
        print(f"❌ Speech failed: {e}")
        return False

def speak_streaming(kokoro, text, voice):
    """Stream TTS for real-time playback"""
    import asyncio
    import soundfile as sf
    import numpy as np
    
    async def stream_and_play():
        print(f"🔄 Streaming with {voice}...")
        
        # Start timing from text input to first audio
        total_start = time.time()
        first_audio_time = None
        
        try:
            # Create streaming generator
            stream = kokoro.create_stream(
                text=text,
                voice=voice,
                speed=1.0,
                lang="en-us"
            )
            
            # Collect audio chunks as they arrive
            audio_chunks = []
            sample_rate = 24000  # Default Kokoro sample rate
            
            async for chunk in stream:
                if first_audio_time is None:
                    first_audio_time = time.time()
                    time_to_first_audio = (first_audio_time - total_start) * 1000
                    print(f"⚡ Time-to-first-audio: {time_to_first_audio:.0f}ms")
                
                # Handle different chunk formats
                if isinstance(chunk, tuple) and len(chunk) >= 2:
                    # Format: (audio_data, sample_rate)
                    audio_data, sr = chunk[0], chunk[1]
                    sample_rate = sr
                    audio_chunks.append(audio_data)
                elif isinstance(chunk, np.ndarray):
                    # Direct audio array
                    audio_chunks.append(chunk)
                elif hasattr(chunk, 'audio'):
                    # Object with audio attribute
                    audio_chunks.append(chunk.audio)
                else:
                    print(f"🔍 Unknown chunk format: {type(chunk)}")
                    continue
            
            # Combine all chunks and play
            if audio_chunks:
                # Concatenate all audio chunks
                full_audio = np.concatenate(audio_chunks)
                
                # Play the complete audio
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as tmp_file:
                    sf.write(tmp_file.name, full_audio, sample_rate)
                    subprocess.run(["afplay", tmp_file.name], check=True)
                
                total_time = time.time() - total_start
                duration = len(full_audio) / sample_rate
                rtf = (total_time - (time_to_first_audio/1000)) / duration if duration > 0 else 0
                
                print(f"⚡ Total time: {total_time*1000:.0f}ms (RTF: {rtf:.2f}x)")
                print("✅ Streaming speech complete!")
                return True
            else:
                print("❌ No audio data received from stream")
                return False
                
        except Exception as e:
            print(f"❌ Streaming error: {e}")
            return False
    
    # Run the async streaming
    try:
        return asyncio.run(stream_and_play())
    except Exception as e:
        print(f"❌ Streaming failed: {e}")
        print("🔄 Falling back to standard synthesis...")
        return speak_standard(kokoro, text, voice)

def speak_standard(kokoro, text, voice):
    """Standard non-streaming TTS synthesis"""
    print(f"🗣️  Speaking with {voice}...")
    synthesis_start = time.time()
    
    samples, sample_rate = kokoro.create(
        text=text,
        voice=voice,
        speed=1.0,
        lang="en-us"
    )
    
    synthesis_time = time.time() - synthesis_start
    duration = len(samples) / sample_rate
    rtf = synthesis_time / duration if duration > 0 else 0
    
    print(f"⚡ Synthesis: {synthesis_time*1000:.0f}ms (RTF: {rtf:.2f}x)")
    
    # Play directly (no file saved)
    import soundfile as sf
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as tmp_file:
        sf.write(tmp_file.name, samples, sample_rate)
        subprocess.run(["afplay", tmp_file.name], check=True)
    
    print("✅ Speech complete!")
    return True

def main():
    """Main entry point - handles both hook calls and direct usage"""
    
    # Map friendly names to actual Kokoro voice IDs
    voice_mapping = {
        "kokoro-af_alloy": "af_alloy",
        "kokoro-af_river": "af_river", 
        "kokoro-af_sky": "af_sky",
        "kokoro-af_sarah": "af_sarah",
        "kokoro-af_nicole": "af_nicole",
        "kokoro-am_adam": "am_adam",
        "kokoro-am_echo": "am_echo",
        "kokoro-am_puck": "am_puck",
        "kokoro-am_michael": "am_michael",
        "kokoro-bf_emma": "bf_emma",
        "kokoro-bm_daniel": "bm_daniel",
        "kokoro-bm_lewis": "bm_lewis",
        "kokoro-bm_george": "bm_george"
    }
    
    if len(sys.argv) < 2:
        print("🎤 Kokoro TTS Voice Engine")
        print("Usage:")
        print("  Hook call:   uv run kokoro_voice.py <voice_id> <text>")
        print("  Direct call: uv run kokoro_voice.py '<text>' [--voice VOICE] [--stream]")
        print("")
        print("Available voices:")
        for voice_name in voice_mapping.keys():
            actual_voice = voice_mapping[voice_name]
            print(f"  {voice_name} ({actual_voice})")
        return
    
    # Detect call type: hook call (voice_id first) vs direct call (text first)
    first_arg = sys.argv[1]
    
    if first_arg in voice_mapping:
        # Hook call: kokoro_voice.py kokoro-af_sarah "text"
        if len(sys.argv) < 3:
            print("❌ Missing text for hook call")
            sys.exit(1)
        
        voice_id = first_arg
        text = " ".join(sys.argv[2:])
        actual_voice = voice_mapping[voice_id]
        use_streaming = False  # Hooks use standard for reliability
        
    else:
        # Direct call: kokoro_voice.py "text" --voice af_sarah --stream
        args = sys.argv[1:]
        use_streaming = False
        voice = "am_echo"  # Default voice
        
        # Parse voice argument
        if "--voice" in args:
            voice_index = args.index("--voice")
            if voice_index + 1 < len(args):
                voice_arg = args[voice_index + 1]
                # Handle both formats: "af_sarah" or "kokoro-af_sarah"
                if voice_arg in voice_mapping:
                    voice = voice_mapping[voice_arg]
                else:
                    voice = voice_arg  # Direct voice name
                args.remove("--voice")
                args.remove(voice_arg)
        
        # Parse streaming argument
        if "--stream" in args:
            use_streaming = True
            args.remove("--stream")
        
        text = " ".join(args)
        actual_voice = voice
    
    # Speak the text
    success = speak_text(text, voice=actual_voice, use_streaming=use_streaming)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()