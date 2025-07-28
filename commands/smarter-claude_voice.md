---
description: "Set smarter-claude voice engine using friendly names: alloy, river, sky, sarah, nicole, adam, puck, michael, emma, daniel, lewis, george, default-male, default-female"
allowed-tools:
  - Bash
  - Read
  - Edit
---

# Set smarter-claude Voice

I'll update your smarter-claude voice engine setting.

Usage: `/smarter-claude_voice <voice_name>`

Valid voice names:

- **alloy** = Alloy (American Female)
- **river** = River (American Female)
- **sky** = Sky (American Female)
- **sarah** = Sarah (American Female)
- **nicole** = Nicole (American Female, Whispering)
- **adam** = Adam (American Male)
- **puck** = Puck (American Male)
- **michael** = Michael (American Male)
- **emma** = Emma (British Female)
- **daniel** = Daniel (British Male)
- **lewis** = Lewis (British Male)
- **george** = George (British Male)
- **default-male** = default-male (MacOS)
- **default-female** = default-female (MacOS)

!# Use the settings management system for proper cascading
MANAGE_SETTINGS="$HOME/.claude/hooks/utils/manage_settings.py"
VOICE_MANAGER="$HOME/.claude/hooks/utils/manage_voices.py"

# Get the argument (voice)
VOICE="$1"

if [ -z "$VOICE" ]; then
  echo "❌ Please specify a voice name"
  echo ""
  echo "Usage: /smarter-claude_voice <voice_name>"
  echo ""
  echo "Valid voice names:"
  echo ""
  echo "  alloy           = Alloy (American Female)"
  echo "  river           = River (American Female)"
  echo "  sky             = Sky (American Female)"
  echo "  sarah           = Sarah (American Female)"
  echo "  nicole          = Nicole (American Female, Whispering)"
  echo "  adam            = Adam (American Male)"
  echo "  puck            = Puck (American Male)"
  echo "  michael         = Michael (American Male)"
  echo "  emma            = Emma (British Female)"
  echo "  daniel          = Daniel (British Male)"
  echo "  lewis           = Lewis (British Male)"
  echo "  george          = George (British Male)"
  echo "  default-male    = default-male (MacOS)"
  echo "  default-female  = default-female (MacOS)"
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

# Map friendly names to voice IDs
case "$VOICE" in
  "alloy")
    VOICE_TEXT="kokoro-af_alloy"
    ;;
  "river")
    VOICE_TEXT="kokoro-af_river"
    ;;
  "sky")
    VOICE_TEXT="kokoro-af_sky"
    ;;
  "sarah")
    VOICE_TEXT="kokoro-af_sarah"
    ;;
  "nicole")
    VOICE_TEXT="kokoro-af_nicole"
    ;;
  "adam")
    VOICE_TEXT="kokoro-am_adam"
    ;;
  "puck")
    VOICE_TEXT="kokoro-am_puck"
    ;;
  "michael")
    VOICE_TEXT="kokoro-am_michael"
    ;;
  "emma")
    VOICE_TEXT="kokoro-bf_emma"
    ;;
  "daniel")
    VOICE_TEXT="kokoro-bm_daniel"
    ;;
  "lewis")
    VOICE_TEXT="kokoro-bm_lewis"
    ;;
  "george")
    VOICE_TEXT="kokoro-bm_george"
    ;;
  "default-male")
    VOICE_TEXT="macos-male"
    ;;
  "default-female")
    VOICE_TEXT="macos-female"
    ;;
  *)
    echo "❌ Invalid voice name: $VOICE"
    echo "Valid voice names: alloy, river, sky, sarah, nicole, adam, puck, michael, emma, daniel, lewis, george, default-male, default-female"
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

# Due to Claude Code limitations with executing commands in slash commands,
# I'll provide the command for you to run manually:

echo ""
echo "🔧 To set your voice to $VOICE_TEXT, please run this command:"
echo ""

# Provide appropriate command based on voice type
if [[ "$VOICE_TEXT" == kokoro-* ]]; then
  echo "# For Kokoro voices, ensure TTS is installed first, then set the voice:"
  echo "cd hooks/utils/tts && uv run kokoro_voice.py 'Installation test' --voice am_echo && cd - && python3 \"$MANAGE_SETTINGS\" set tts_engine \"$VOICE_TEXT\""
  echo ""
  echo "# Or run them separately:"
  echo "cd hooks/utils/tts && uv run kokoro_voice.py 'Installation test' --voice am_echo"
  echo "python3 \"$MANAGE_SETTINGS\" set tts_engine \"$VOICE_TEXT\""
else
  echo "python3 \"$MANAGE_SETTINGS\" set tts_engine \"$VOICE_TEXT\""
fi

echo ""
echo "This will:"
echo "• Install Kokoro TTS models and dependencies (if needed for Kokoro voices)"
echo "• Create project-specific settings with only this voice override"
echo "• Keep all other settings inherited from global defaults"