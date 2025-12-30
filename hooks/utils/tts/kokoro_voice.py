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
    print("[INSTALL] First run - installing Kokoro TTS...")
    
    # Create installer script inline
    installer_code = '''
import subprocess
import urllib.request
from pathlib import Path

install_dir = Path.home() / ".kokoro-tts" / "models"
install_dir.mkdir(parents=True, exist_ok=True)

model_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

print("[DOWNLOAD] Downloading Kokoro model...")
urllib.request.urlretrieve(model_url, install_dir / "kokoro-v1.0.onnx")
print("[DOWNLOAD] Downloading voices...")
urllib.request.urlretrieve(voices_url, install_dir / "voices-v1.0.bin")
print("[OK] Kokoro installed!")
'''
    
    try:
        subprocess.run([sys.executable, "-c", installer_code], check=True)
        return True
    except Exception as e:
        print(f"[ERROR] Installation failed: {e}")
        return False

def speak_text(text, voice="am_echo", use_streaming=False):
    """Speak text using Kokoro TTS"""
    try:
        # Import kokoro (install if needed)
        try:
            from kokoro_onnx import Kokoro
        except ImportError:
            print("[INSTALL] Installing kokoro-onnx...")
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
        print(f"[ERROR] Speech failed: {e}")
        return False

def speak_streaming(kokoro, text, voice):
    """Stream TTS for real-time playback with lock coordination"""
    import asyncio
    import soundfile as sf
    import numpy as np
    
    # Import lock functions and audio player
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    try:
        from cycle_utils import check_tts_lock, create_tts_lock, remove_tts_lock
    except ImportError:
        # If lock functions not available, proceed without locking
        def check_tts_lock(): return False
        def create_tts_lock(duration): pass
        def remove_tts_lock(): pass

    try:
        from audio_player import play_audio_file
    except ImportError:
        # Fallback to afplay on macOS if audio_player not available
        def play_audio_file(path, timeout=30):
            subprocess.run(["afplay", path], check=True, timeout=timeout)

    # Check if TTS is locked before starting stream
    if check_tts_lock():
        return True  # Skip streaming - another TTS is playing

    async def stream_and_play():
        print(f"[STREAM] Streaming with {voice}...")
        
        # Start timing from text input to first audio
        total_start = time.time()
        first_audio_time = None
        
        try:
            # Get voice-specific settings
            settings = get_voice_settings(voice)
            
            # Create streaming generator
            stream = kokoro.create_stream(
                text=text,
                voice=voice,
                speed=settings["speed"],
                lang=settings["lang"],
                trim=settings["trim"]
            )
            
            # Collect audio chunks as they arrive
            audio_chunks = []
            sample_rate = 24000  # Default Kokoro sample rate
            
            async for chunk in stream:
                if first_audio_time is None:
                    first_audio_time = time.time()
                    time_to_first_audio = (first_audio_time - total_start) * 1000
                    print(f"[PERF] Time-to-first-audio: {time_to_first_audio:.0f}ms")
                
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
                    print(f"[DEBUG] Unknown chunk format: {type(chunk)}")
                    continue
            
            # Combine all chunks and play
            if audio_chunks:
                # Concatenate all audio chunks
                full_audio = np.concatenate(audio_chunks)
                
                # Calculate duration and create lock before playback
                duration = len(full_audio) / sample_rate
                create_tts_lock(duration)
                
                try:
                    # Play the complete audio (cross-platform)
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as tmp_file:
                        sf.write(tmp_file.name, full_audio, sample_rate)
                        play_audio_file(tmp_file.name)
                finally:
                    # Always remove lock when playback completes
                    remove_tts_lock()
                
                total_time = time.time() - total_start
                rtf = (total_time - (time_to_first_audio/1000)) / duration if duration > 0 else 0
                
                print(f"[PERF] Total time: {total_time*1000:.0f}ms (RTF: {rtf:.2f}x)")
                print("[OK] Streaming speech complete!")
                return True
            else:
                print("[ERROR] No audio data received from stream")
                return False
                
        except Exception as e:
            print(f"[ERROR] Streaming error: {e}")
            return False
    
    # Run the async streaming
    try:
        return asyncio.run(stream_and_play())
    except Exception as e:
        print(f"[ERROR] Streaming failed: {e}")
        print("[FALLBACK] Falling back to standard synthesis...")
        return speak_standard(kokoro, text, voice)

def speak_standard(kokoro, text, voice):
    """Standard non-streaming TTS synthesis with lock coordination"""
    # Import lock functions and audio player
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    try:
        from cycle_utils import check_tts_lock, create_tts_lock, remove_tts_lock
    except ImportError:
        # If lock functions not available, proceed without locking
        def check_tts_lock(): return False
        def create_tts_lock(duration): pass
        def remove_tts_lock(): pass

    try:
        from audio_player import play_audio_file
    except ImportError:
        # Fallback to afplay on macOS if audio_player not available
        def play_audio_file(path, timeout=30):
            subprocess.run(["afplay", path], check=True, timeout=timeout)
    
    # Check if TTS is locked before expensive generation
    if check_tts_lock():
        return True  # Skip generation - another TTS is playing
    
    print(f"[TTS] Speaking with {voice}...")
    synthesis_start = time.time()
    
    # Get voice-specific settings
    settings = get_voice_settings(voice)
    
    # Generate audio samples
    samples, sample_rate = kokoro.create(
        text=text,
        voice=voice,
        speed=settings["speed"],
        lang=settings["lang"],
        trim=settings["trim"]
    )
    
    synthesis_time = time.time() - synthesis_start
    duration = len(samples) / sample_rate
    rtf = synthesis_time / duration if duration > 0 else 0
    
    print(f"[PERF] Synthesis: {synthesis_time*1000:.0f}ms (RTF: {rtf:.2f}x)")
    
    # Create lock with exact duration before playback
    create_tts_lock(duration)
    
    try:
        # Play the pre-generated audio (cross-platform)
        import soundfile as sf
        import os
        # On Windows, use delete=False and clean up manually to avoid file locking issues
        tmp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        tmp_path = tmp_file.name
        tmp_file.close()  # Close before writing on Windows
        try:
            sf.write(tmp_path, samples, sample_rate)
            play_audio_file(tmp_path)
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
    finally:
        # Always remove lock when playback completes
        remove_tts_lock()
    
    print("[OK] Speech complete!")
    return True

# Voice-specific settings for optimal TTS delivery
VOICE_SETTINGS = {
    "af_alloy": {"speed": 1.1, "lang": "en-us", "trim": True},
    "af_river": {"speed": 1.1, "lang": "en-us", "trim": True},  # 10% faster
    "af_sky": {"speed": 1.05, "lang": "en-us", "trim": True},
    "af_sarah": {"speed": 1.0, "lang": "en-us", "trim": True},
    "af_nicole": {"speed": 1.3, "lang": "en-us", "trim": True},
    "am_adam": {"speed": 1.0, "lang": "en-us", "trim": True},
    "am_echo": {"speed": 1.0, "lang": "en-us", "trim": True},
    "am_puck": {"speed": 0.94, "lang": "en-us", "trim": True},
    "am_michael": {"speed": 1.1, "lang": "en-us", "trim": True},
    "bf_emma": {"speed": 1.0, "lang": "en-us", "trim": True},
    "bm_daniel": {"speed": 1.3, "lang": "en-us", "trim": True},
    "bm_lewis": {"speed": 1.0, "lang": "en-us", "trim": True},
    "bm_george": {"speed": 1.2, "lang": "en-us", "trim": True}
}

def get_voice_settings(voice):
    """Get voice-specific settings with fallback to defaults."""
    return VOICE_SETTINGS.get(voice, {"speed": 1.0, "lang": "en-us", "trim": True})

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
        print("Kokoro TTS Voice Engine")
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
            print("[ERROR] Missing text for hook call")
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