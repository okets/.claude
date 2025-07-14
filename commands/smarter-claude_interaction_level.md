---
description: "Set smarter-claude interaction level (0-4 or silent/quiet/concise/verbose)"
allowed-tools:
  - Bash
  - Read
  - Edit
---

# Set smarter-claude Interaction Level

I'll update your smarter-claude interaction level setting.

Usage: `/smarter-claude_interaction_level <level>`

Valid levels:
- **0** or **silent**: No TTS announcements
- **1** or **quiet**: Sound notifications only  
- **2** or **concise**: Brief planning and completion announcements
- **3** or **verbose**: Detailed workflow narration with context awareness
- **4**: Maximum verbosity (same as verbose currently)

!SETTINGS_FILE="$HOME/.claude/.claude/smarter-claude/smarter-claude.json"

# Get the argument (interaction level)
LEVEL="$1"

if [ -z "$LEVEL" ]; then
  echo "❌ Please specify an interaction level"
  echo ""
  echo "Usage: /smarter-claude_interaction_level <level>"
  echo ""
  echo "Valid levels:"
  echo "  0 or silent  - No TTS announcements"
  echo "  1 or quiet   - Sound notifications only"
  echo "  2 or concise - Brief announcements"
  echo "  3 or verbose - Detailed workflow narration"
  echo "  4           - Maximum verbosity"
  echo ""
  if [ -f "$SETTINGS_FILE" ]; then
    echo "Current setting:"
    if command -v jq >/dev/null 2>&1; then
      jq -r '.interaction_level' "$SETTINGS_FILE"
    else
      grep '"interaction_level"' "$SETTINGS_FILE" | cut -d'"' -f4
    fi
  fi
  exit 1
fi

if [ ! -f "$SETTINGS_FILE" ]; then
  echo "❌ smarter-claude settings file not found at: $SETTINGS_FILE"
  echo "Make sure smarter-claude is properly installed."
  exit 1
fi

# Convert numeric levels to text
case "$LEVEL" in
  0) LEVEL_TEXT="silent" ;;
  1) LEVEL_TEXT="quiet" ;;
  2) LEVEL_TEXT="concise" ;;
  3|4) LEVEL_TEXT="verbose" ;;
  "silent"|"quiet"|"concise"|"verbose") LEVEL_TEXT="$LEVEL" ;;
  *)
    echo "❌ Invalid interaction level: $LEVEL"
    echo "Valid options: 0-4 or silent/quiet/concise/verbose"
    exit 1
    ;;
esac

echo "🔧 Setting smarter-claude interaction level to: $LEVEL_TEXT"

# Create backup
cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup.$(date +%s)"

# Update the interaction_level setting
if command -v jq >/dev/null 2>&1; then
  # Use jq if available (more reliable)
  jq --arg level "$LEVEL_TEXT" '.interaction_level = $level' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
else
  # Fallback to sed
  sed -i.bak "s/\"interaction_level\": \"[^\"]*\"/\"interaction_level\": \"$LEVEL_TEXT\"/" "$SETTINGS_FILE"
  rm -f "$SETTINGS_FILE.bak"
fi

if [ $? -eq 0 ]; then
  echo "✅ Successfully updated smarter-claude interaction level to: $LEVEL_TEXT"
  echo ""
  case "$LEVEL_TEXT" in
    "silent")
      echo "🔇 TTS announcements are now disabled"
      ;;
    "quiet") 
      echo "🔔 Only sound notifications will play"
      ;;
    "concise")
      echo "📝 Brief planning and completion announcements enabled"
      ;;
    "verbose")
      echo "🗣️  Detailed workflow narration with context awareness enabled"
      ;;
  esac
  echo ""
  echo "Current settings:"
  if command -v jq >/dev/null 2>&1; then
    jq '.interaction_level' "$SETTINGS_FILE"
  else
    grep '"interaction_level"' "$SETTINGS_FILE"
  fi
else
  echo "❌ Failed to update settings"
  echo "Restoring backup..."
  mv "$SETTINGS_FILE.backup."* "$SETTINGS_FILE" 2>/dev/null
  exit 1
fi