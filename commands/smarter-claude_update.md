---
description: "Updates smarter-claude to the latest version from GitHub"
allowed-tools:
  - Bash
---

# Update smarter-claude

I'll update smarter-claude to the latest version using the built-in update system.

First, let me check if this is a developer installation or a user installation:

!if [ -d ".git" ] && git rev-parse --git-dir > /dev/null 2>&1; then
  echo "🔧 Developer installation detected (git repository)"
  echo "⚠️  You're in a development environment."
  echo "For development updates, use git commands directly:"
  echo "  git pull origin main"
  echo ""
  echo "For testing the update system, you can still run:"
  echo "  bash ~/.claude/update.sh"
  echo ""
  read -p "Run the update system anyway? (y/N): " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd ~/.claude && bash update.sh
  else
    echo "Update cancelled. Use 'git pull origin main' for development updates."
  fi
else
  echo "📦 Product installation detected"
  echo "Running the update system..."
  echo ""
  
  # Check if update.sh exists
  if [ -f ~/.claude/update.sh ]; then
    cd ~/.claude && bash update.sh
  else
    echo "❌ Update script not found. This might be an old installation."
    echo ""
    echo "To fix this, please run the installer again:"
    echo "curl -fsSL https://raw.githubusercontent.com/okets/.claude/main/install.sh | bash"
  fi
fi