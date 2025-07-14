#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "pyttsx3",
# ]
# ///

import sys
import time

def main():
    """Test all available pyttsx3 voices"""
    
    try:
        import pyttsx3
        
        # Initialize TTS engine
        engine = pyttsx3.init()
        
        # Get all available voices
        voices = engine.getProperty('voices')
        
        print("🎭 Available pyttsx3 Voices:")
        print("=" * 35)
        
        # Show all voices first
        print("\nAll available voices:")
        for i, voice in enumerate(voices, 1):
            print(f"{i}. {voice.name} - {voice.id}")
        
        test_text = "Hello, I am testing this voice for quality and naturalness. This is voice number"
        
        print(f"\n🔊 Testing voices with slow, clear speech...")
        print("(Each voice will identify itself by number)\n")
        
        # Test each voice individually with clear identification
        for i, voice in enumerate(voices, 1):
            print(f"Testing Voice {i}: {voice.name}")
            
            # Configure for slow, clear speech
            engine.setProperty('voice', voice.id)
            engine.setProperty('rate', 140)     # Slower rate
            engine.setProperty('volume', 0.9)   # Higher volume
            
            # Speak with voice number identification
            full_text = f"{test_text} {i}. My name is {voice.name.split()[0]}."
            
            engine.say(full_text)
            engine.runAndWait()
            
            # Wait between voices
            time.sleep(2)
            
            # Stop after 6 voices to avoid overwhelming
            if i >= 6:
                print(f"\nShowing first 6 voices. Total available: {len(voices)}")
                break
        
        print("\n✅ Voice testing complete!")
        print("Choose your preferred voices for male and female options")
        
    except ImportError:
        print("❌ Error: pyttsx3 package not installed")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()