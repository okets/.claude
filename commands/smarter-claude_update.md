---
description: "Updates smarter-claude to the latest version from GitHub"
allowed-tools:
  - Bash
  - Read
---

# Update smarter-claude

I'll help you update smarter-claude to the latest version. Let me check how smarter-claude is installed and choose the appropriate update method.

First, let me check if this is a git repository (developer installation) or a product installation:

!if [ -d ".git" ] && git rev-parse --git-dir > /dev/null 2>&1; then
  echo "🔧 Developer installation detected (git repository)"
  echo "Checking git status..."
  git status --porcelain
  
  if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  You have uncommitted changes. I'll stash them before updating."
    echo "Your changes will be preserved and can be restored with: git stash pop"
    read -p "Continue with stashing and updating? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      git stash push -m "Auto-stash before smarter-claude update $(date)"
      echo "✅ Changes stashed"
    else
      echo "❌ Update cancelled. Please commit or stash your changes manually."
      exit 1
    fi
  fi
  
  echo "📡 Fetching latest changes from GitHub..."
  git fetch origin
  
  echo "📊 Changes to be applied:"
  git log --oneline HEAD..origin/main
  
  echo "⬇️  Pulling latest updates..."
  git pull origin main
  
  if [ $? -eq 0 ]; then
    echo "✅ smarter-claude updated successfully!"
    echo "📋 Recent changes:"
    git log --oneline -5
  else
    echo "❌ Update failed. Please resolve any conflicts manually."
    exit 1
  fi
  
else
  echo "📦 Product installation detected (no git repository)"
  echo "Downloading latest installer from GitHub..."
  
  # Create temporary directory for download
  TEMP_DIR=$(mktemp -d)
  cd "$TEMP_DIR"
  
  # Download latest install.sh
  echo "📡 Downloading install.sh..."
  if curl -fsSL https://raw.githubusercontent.com/okets/.claude/main/install.sh -o install.sh; then
    echo "✅ Download successful"
    
    # Make executable
    chmod +x install.sh
    
    echo "🔄 Running installer to update smarter-claude..."
    echo "This will update your smarter-claude installation with the latest version."
    
    # Run the installer
    ./install.sh
    
    if [ $? -eq 0 ]; then
      echo "✅ smarter-claude updated successfully!"
    else
      echo "❌ Update failed during installation."
      exit 1
    fi
    
    # Clean up
    cd - > /dev/null
    rm -rf "$TEMP_DIR"
    
  else
    echo "❌ Failed to download installer from GitHub."
    echo "Please check your internet connection and try again."
    rm -rf "$TEMP_DIR"
    exit 1
  fi
fi

echo ""
echo "🎉 Update complete! Your smarter-claude installation is now up to date."
echo "💡 Tip: Use this command anytime to get the latest features and improvements."