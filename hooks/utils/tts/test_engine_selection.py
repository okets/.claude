#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

import sys
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent))

def test_tts_selection():
    try:
        from cycle_utils import get_tts_script_path
        
        print("🧪 Testing TTS Engine Selection")
        print("=" * 35)
        
        script_path = get_tts_script_path()
        
        if script_path:
            print(f"✅ Selected TTS script: {script_path}")
            script_name = Path(script_path).name
            print(f"🎯 Script name: {script_name}")
            
            if Path(script_path).exists():
                print("✅ Script file exists")
            else:
                print("❌ Script file NOT found")
        else:
            print("❌ No TTS script selected")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_tts_selection()