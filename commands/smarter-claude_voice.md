---
description: "Set smarter-claude voice engine (coqui-female, coqui-male, macos-female, macos-male, pyttsx3)"
allowed-tools:
  - Bash
  - Read
  - Edit
---

# Set smarter-claude Voice

I'll update your smarter-claude voice engine setting.

Usage: `/smarter-claude_voice <voice>`

Valid voices:
- **coqui-female**: High-quality female Coqui TTS voice
- **coqui-male**: High-quality male Coqui TTS voice  
- **macos-female**: macOS built-in female voice (Samantha)
- **macos-male**: macOS built-in male voice (Alex)
- **pyttsx3**: Python text-to-speech default voice

!# Use the settings management system for proper cascading
MANAGE_SETTINGS="$HOME/.claude/hooks/utils/manage_settings.py"
VOICE_MANAGER="$HOME/.claude/hooks/utils/manage_voices.py"

# Get the argument (voice)
VOICE="$1"

if [ -z "$VOICE" ]; then
  echo "❌ Please specify a voice engine"
  echo ""
  echo "Usage: /smarter-claude_voice <voice>"
  echo ""
  echo "Valid voices:"
  echo "  coqui-female  - High-quality female Coqui TTS voice"
  echo "  coqui-male    - High-quality male Coqui TTS voice"
  echo "  macos-female  - macOS built-in female voice (Samantha)"
  echo "  macos-male    - macOS built-in male voice (Alex)"
  echo "  pyttsx3       - Python text-to-speech default voice"
  echo ""
  echo "Current setting:"
  python3 "$MANAGE_SETTINGS" get tts_engine 2>/dev/null || echo "Using global defaults"
  echo ""
  # Show voice status if voice manager is available
  if [ -f "$VOICE_MANAGER" ]; then
    echo "Voice installation status:"
    python3 "$VOICE_MANAGER" status
  fi
  exit 1
fi

# Validate voice option
case "$VOICE" in
  "coqui-female"|"coqui-male"|"macos-female"|"macos-male"|"pyttsx3")
    VOICE_TEXT="$VOICE"
    ;;
  *)
    echo "❌ Invalid voice: $VOICE"
    echo "Valid options: coqui-female, coqui-male, macos-female, macos-male, pyttsx3"
    exit 1
    ;;
esac

# Check if voice is installed, install if needed
if [ -f "$VOICE_MANAGER" ]; then
  echo "🔍 Checking if $VOICE_TEXT is installed..."
  if ! python3 "$VOICE_MANAGER" test --engine "$VOICE_TEXT" >/dev/null 2>&1; then
    echo "🚀 Installing $VOICE_TEXT..."
    if python3 "$VOICE_MANAGER" install --engine "$VOICE_TEXT"; then
      echo "✅ $VOICE_TEXT installed successfully"
    else
      echo "❌ Failed to install $VOICE_TEXT"
      echo "Please check the requirements and try again"
      exit 1
    fi
  else
    echo "✅ $VOICE_TEXT is already installed"
  fi
fi

echo "🔧 Setting smarter-claude voice to: $VOICE_TEXT"

# Provide working commands for installation + configuration
echo ""
echo "🔧 To install and configure $VOICE_TEXT for this project, please run these commands:"
echo ""

# Create the complete command based on voice type
if [[ "$VOICE_TEXT" == "coqui-female" || "$VOICE_TEXT" == "coqui-male" ]]; then
  echo "# Step 1: Install voice dependencies"
  echo "python3 \"$VOICE_MANAGER\" install --engine \"$VOICE_TEXT\""
  echo ""
  echo "# Step 2: Set voice in project settings"
  echo "python3 \"$MANAGE_SETTINGS\" set tts_engine \"$VOICE_TEXT\""
  echo ""
  echo "Or run both in one command:"
  echo "python3 \"$VOICE_MANAGER\" install --engine \"$VOICE_TEXT\" && python3 \"$MANAGE_SETTINGS\" set tts_engine \"$VOICE_TEXT\""
else
  # For macOS voices, no installation needed
  echo "# Set voice in project settings (no installation needed for macOS voices)"
  echo "python3 \"$MANAGE_SETTINGS\" set tts_engine \"$VOICE_TEXT\""
fi

echo ""
echo "This will:"
echo "• Install voice dependencies (if needed for Coqui voices)"
echo "• Create project-specific settings with only this voice override"
echo "• Keep all other settings inherited from global defaults"
echo ""
echo "Verify it worked:"
echo "python3 \"$MANAGE_SETTINGS\" get tts_engine"