---
description: "Set smarter-claude voice engine (13 Kokoro voices: af_alloy, af_river, af_sky, af_sarah, af_nicole, am_adam, am_echo, am_puck, am_michael, bf_emma, bm_daniel, bm_lewis, bm_george + macos-female, macos-male)"
allowed-tools:
  - Bash
  - Read
  - Edit
---

# Set smarter-claude Voice

I'll update your smarter-claude voice engine setting.

Usage: `/smarter-claude_voice <voice>`

Valid voices:

**Kokoro Voices (High-Quality Neural TTS):**
- **kokoro-af_alloy**: Alloy female voice (neutral)
- **kokoro-af_river**: River female voice 
- **kokoro-af_sky**: Sky female voice
- **kokoro-af_sarah**: Sarah female voice
- **kokoro-af_nicole**: Nicole female voice
- **kokoro-am_adam**: Adam male voice
- **kokoro-am_echo**: Echo male voice (expressive)
- **kokoro-am_puck**: Puck male voice (young)
- **kokoro-am_michael**: Michael male voice
- **kokoro-bf_emma**: Emma bright female voice
- **kokoro-bm_daniel**: Daniel male voice (British)
- **kokoro-bm_lewis**: Lewis male voice (British)
- **kokoro-bm_george**: George male voice (British)

**System Voices:**
- **macos-female**: macOS built-in female voice (Samantha)
- **macos-male**: macOS built-in male voice (Alex)

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
  echo ""
  echo "Kokoro Voices (High-Quality Neural TTS):"
  echo "  kokoro-af_alloy   - Alloy female voice (neutral)"
  echo "  kokoro-af_river   - River female voice"
  echo "  kokoro-af_sky     - Sky female voice"
  echo "  kokoro-af_sarah   - Sarah female voice"
  echo "  kokoro-af_nicole  - Nicole female voice"
  echo "  kokoro-am_adam    - Adam male voice"
  echo "  kokoro-am_echo    - Echo male voice (expressive)"
  echo "  kokoro-am_puck    - Puck male voice (young)"
  echo "  kokoro-am_michael - Michael male voice"
  echo "  kokoro-bf_emma    - Emma bright female voice"
  echo "  kokoro-bm_daniel  - Daniel male voice (British)"
  echo "  kokoro-bm_lewis   - Lewis male voice (British)"
  echo "  kokoro-bm_george  - George male voice (British)"
  echo ""
  echo "System Voices:"
  echo "  macos-female      - macOS built-in female voice (Samantha)"
  echo "  macos-male        - macOS built-in male voice (Alex)"
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
  "kokoro-af_alloy"|"kokoro-af_river"|"kokoro-af_sky"|"kokoro-af_sarah"|"kokoro-af_nicole"|"kokoro-am_adam"|"kokoro-am_echo"|"kokoro-am_puck"|"kokoro-am_michael"|"kokoro-bf_emma"|"kokoro-bm_daniel"|"kokoro-bm_lewis"|"kokoro-bm_george"|"macos-female"|"macos-male")
    VOICE_TEXT="$VOICE"
    ;;
  *)
    echo "❌ Invalid voice: $VOICE"
    echo "Valid Kokoro voices: kokoro-af_alloy, kokoro-af_river, kokoro-af_sky, kokoro-af_sarah, kokoro-af_nicole, kokoro-am_adam, kokoro-am_echo, kokoro-am_puck, kokoro-am_michael, kokoro-bf_emma, kokoro-bm_daniel, kokoro-bm_lewis, kokoro-bm_george"
    echo "Valid system voices: macos-female, macos-male"
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
if [[ "$VOICE_TEXT" == kokoro-* ]]; then
  echo "# Step 1: Install Kokoro TTS (first time only)"
  echo "cd hooks/utils/tts && uv run kokoro_voice.py 'Installation test' --voice am_echo"
  echo ""
  echo "# Step 2: Set voice in project settings"
  echo "python3 \"$MANAGE_SETTINGS\" set tts_engine \"$VOICE_TEXT\""
  echo ""
  echo "Or run both in one command:"
  echo "cd hooks/utils/tts && uv run kokoro_voice.py 'Installation test' --voice am_echo && cd - && python3 \"$MANAGE_SETTINGS\" set tts_engine \"$VOICE_TEXT\""
else
  # For macOS voices, no installation needed
  echo "# Set voice in project settings (no installation needed for macOS voices)"
  echo "python3 \"$MANAGE_SETTINGS\" set tts_engine \"$VOICE_TEXT\""
fi

echo ""
echo "This will:"
echo "• Install Kokoro TTS models and dependencies (if needed for Kokoro voices)"
echo "• Create project-specific settings with only this voice override"
echo "• Keep all other settings inherited from global defaults"
echo ""
echo "Verify it worked:"
echo "python3 \"$MANAGE_SETTINGS\" get tts_engine"