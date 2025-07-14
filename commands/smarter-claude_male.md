---
description: "Set smarter-claude voice to macOS male voice"
allowed-tools:
  - Bash
  - Read
  - Edit
---

# Set smarter-claude to Male Voice

I'll update your smarter-claude settings to use the macOS male voice.

!SETTINGS_FILE="$HOME/.claude/.claude/smarter-claude/smarter-claude.json"

if [ ! -f "$SETTINGS_FILE" ]; then
  echo "❌ smarter-claude settings file not found at: $SETTINGS_FILE"
  echo "Make sure smarter-claude is properly installed."
  exit 1
fi

echo "🔧 Setting smarter-claude voice to macOS male..."

# Create backup
cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup.$(date +%s)"

# Update the tts_engine setting to macos-male
if command -v jq >/dev/null 2>&1; then
  # Use jq if available (more reliable)
  jq '.tts_engine = "macos-male"' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
else
  # Fallback to sed
  sed -i.bak 's/"tts_engine": "[^"]*"/"tts_engine": "macos-male"/' "$SETTINGS_FILE"
  rm -f "$SETTINGS_FILE.bak"
fi

if [ $? -eq 0 ]; then
  echo "✅ Successfully updated smarter-claude voice to macOS male"
  echo "🔊 Your next smarter-claude TTS announcements will use the male voice"
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