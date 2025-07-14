#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import subprocess
import sys
from pathlib import Path

def test_engine(script_path, engine_name):
    """Test if a TTS engine works"""
    try:
        result = subprocess.run([
            "uv", "run", str(script_path), "test"
        ], capture_output=True, timeout=10, text=True)
        
        if result.returncode == 0:
            print(f"✅ {engine_name}: WORKS")
            return True
        else:
            print(f"❌ {engine_name}: FAILED - {result.stderr[:100]}")
            return False
    except Exception as e:
        print(f"❌ {engine_name}: ERROR - {str(e)[:100]}")
        return False

def main():
    print("🧪 Testing TTS Engines")
    print("=" * 30)
    
    tts_dir = Path(__file__).parent
    
    engines = {
        "coqui-female": tts_dir / "coqui_tts.py",
        "macos-female": tts_dir / "macos_female_tts.py",
        "macos-male": tts_dir / "macos_male_tts.py",
        "pyttsx3": tts_dir / "pyttsx3_tts.py"
    }
    
    working_engines = []
    
    for engine_name, script_path in engines.items():
        if script_path.exists():
            if test_engine(script_path, engine_name):
                working_engines.append(engine_name)
        else:
            print(f"❌ {engine_name}: SCRIPT NOT FOUND")
    
    print(f"\n🎯 Working engines: {working_engines}")
    
    if working_engines:
        best_engine = working_engines[0]  # Use first working engine
        print(f"🏆 Best engine: {best_engine}")
        return best_engine
    else:
        print("❌ No working engines found!")
        return None

if __name__ == "__main__":
    main()