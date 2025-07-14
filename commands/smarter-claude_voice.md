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

!SETTINGS_FILE="$HOME/.claude/.claude/smarter-claude/smarter-claude.json"
VOICE_MANAGER="$HOME/.claude/.claude/smarter-claude/manage_voices.py"

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
  if [ -f "$SETTINGS_FILE" ]; then
    echo "Current setting:"
    if command -v jq >/dev/null 2>&1; then
      jq -r '.tts_engine' "$SETTINGS_FILE"
    else
      grep '"tts_engine"' "$SETTINGS_FILE" | cut -d'"' -f4
    fi
  fi
  echo ""
  # Show voice status if voice manager is available
  if [ -f "$VOICE_MANAGER" ]; then
    echo "Voice installation status:"
    python3 "$VOICE_MANAGER" status
  fi
  exit 1
fi

if [ ! -f "$SETTINGS_FILE" ]; then
  echo "❌ smarter-claude settings file not found at: $SETTINGS_FILE"
  echo "Make sure smarter-claude is properly installed."
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

# Create backup
cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup.$(date +%s)"

# Update the tts_engine setting
if command -v jq >/dev/null 2>&1; then
  # Use jq if available (more reliable)
  jq --arg voice "$VOICE_TEXT" '.tts_engine = $voice' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
else
  # Fallback to sed
  sed -i.bak "s/\"tts_engine\": \"[^\"]*\"/\"tts_engine\": \"$VOICE_TEXT\"/" "$SETTINGS_FILE"
  rm -f "$SETTINGS_FILE.bak"
fi

if [ $? -eq 0 ]; then
  echo "✅ Successfully updated smarter-claude voice to: $VOICE_TEXT"
  echo ""
  case "$VOICE_TEXT" in
    "coqui-female")
      echo "🎤 High-quality female Coqui TTS voice enabled"
      ;;
    "coqui-male") 
      echo "🎤 High-quality male Coqui TTS voice enabled"
      ;;
    "macos-female")
      echo "🍎 macOS female voice (Samantha) enabled"
      ;;
    "macos-male")
      echo "🍎 macOS male voice (Alex) enabled"
      ;;
    "pyttsx3")
      echo "🐍 Python text-to-speech default voice enabled"
      ;;
  esac
  echo ""
  echo "Current settings:"
  if command -v jq >/dev/null 2>&1; then
    jq '.tts_engine' "$SETTINGS_FILE"
  else
    grep '"tts_engine"' "$SETTINGS_FILE"
  fi
else
  echo "❌ Failed to update settings"
  echo "Restoring backup..."
  mv "$SETTINGS_FILE.backup."* "$SETTINGS_FILE" 2>/dev/null
  exit 1
fi