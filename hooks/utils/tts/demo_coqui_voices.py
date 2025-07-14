#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "python-dotenv",
# ]
# ///

import subprocess
from pathlib import Path

def demo_voice(script_name, description, text="Hello! I'm demonstrating Coqui TTS voices. How do I sound?"):
    """Demo a specific TTS voice script"""
    print(f"\n🎙️  {description}")
    print("=" * 50)
    
    script_path = Path(__file__).parent / script_name
    if not script_path.exists():
        print(f"❌ Script not found: {script_name}")
        return
        
    try:
        subprocess.run(["uv", "run", str(script_path), text], check=True)
        print("✅ Voice demo complete!")
        input("Press Enter to continue to next voice...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error playing voice: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
        return False
    return True

def main():
    print("🎭 Coqui TTS Voice Showcase")
    print("=" * 30)
    print("Demonstrating available Coqui TTS voices...")
    print("Press Ctrl+C anytime to stop the demo")
    
    demo_text = "Hello! I'm showcasing Coqui text to speech voices. This is how I sound."
    
    voices = [
        ("coqui_tts.py", "Coqui Female VITS (High Quality)"),
        ("coqui_simple_male_tts.py", "Coqui Male Voice (VITS-based)"),
    ]
    
    for script, description in voices:
        if not demo_voice(script, description, demo_text):
            break
    
    print("\n🎉 Voice showcase complete!")
    print("\nTo switch voices:")
    print("• Edit /Users/hanan/.claude/.claude/smarter-claude/smarter-claude.json")
    print("• Change 'tts_engine' to 'coqui' or 'coqui-male'")

if __name__ == "__main__":
    main()