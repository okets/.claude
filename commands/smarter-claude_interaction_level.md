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

!# Use the settings management system for proper cascading
MANAGE_SETTINGS="$HOME/.claude/hooks/utils/manage_settings.py"

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
  echo "Current setting:"
  python3 "$MANAGE_SETTINGS" get interaction_level 2>/dev/null || echo "Using global defaults"
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

# Due to slash command execution issues, provide the command for manual execution
echo ""
echo "🔧 To set your project interaction level to $LEVEL_TEXT, please run this command:"
echo ""
echo "python3 \"$MANAGE_SETTINGS\" set interaction_level \"$LEVEL_TEXT\""
echo ""
echo "This will create a project-specific settings file with only this interaction level override,"
echo "while keeping all other settings inherited from global defaults."
echo ""
case "$LEVEL_TEXT" in
  "silent")
    echo "This will disable TTS announcements for this project."
    ;;
  "quiet") 
    echo "This will enable only sound notifications for this project."
    ;;
  "concise")
    echo "This will enable brief planning and completion announcements for this project."
    ;;
  "verbose")
    echo "This will enable detailed workflow narration for this project."
    ;;
esac
echo ""
echo "After running the command, you can verify it worked with:"
echo "python3 \"$MANAGE_SETTINGS\" get interaction_level"