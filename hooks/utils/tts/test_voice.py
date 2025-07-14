#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pyttsx3",
# ]
# ///

import sys

def main():
    try:
        import pyttsx3
        engine = pyttsx3.init()
        
        voice_id = sys.argv[1] if len(sys.argv) > 1 else None
        text = sys.argv[2] if len(sys.argv) > 2 else "Testing voice quality"
        
        if voice_id:
            engine.setProperty('voice', voice_id)
        
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.8)
        
        engine.say(text)
        engine.runAndWait()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()