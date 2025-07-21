#!/bin/bash
# Smarter-Claude Update Script
# This script remains constant across all versions

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Version comparison function
version_gt() {
    test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"
}

version_le() {
    ! version_gt "$1" "$2"
}

# Get current version
CURRENT_VERSION=$(cat ~/.claude/VERSION 2>/dev/null || echo "0.0.0")
echo -e "${BLUE}🔍 Current version: $CURRENT_VERSION${NC}"

# Get latest version from GitHub
echo "📡 Checking for updates..."
LATEST_RELEASE=$(curl -s https://api.github.com/repos/okets/.claude/releases/latest 2>/dev/null)
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to connect to GitHub${NC}"
    echo "Please check your internet connection and try again"
    exit 1
fi

LATEST_VERSION=$(echo "$LATEST_RELEASE" | grep '"tag_name"' | cut -d'"' -f4 | sed 's/^v//')

if [ -z "$LATEST_VERSION" ]; then
    echo -e "${RED}❌ Failed to parse latest version from GitHub${NC}"
    echo "GitHub API response:"
    echo "$LATEST_RELEASE" | head -5
    exit 1
fi

echo -e "${BLUE}📦 Latest version: $LATEST_VERSION${NC}"

# Check if update needed
if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    echo -e "${GREEN}✅ Already up to date!${NC}"
    exit 0
fi

echo -e "${YELLOW}🚀 Update available: $CURRENT_VERSION → $LATEST_VERSION${NC}"

# Show what will be updated
echo
echo -e "${BLUE}📋 What will be updated:${NC}"
echo "• All hook scripts and utilities"
echo "• Documentation and guides"
echo "• Slash commands"
echo "• Migration scripts (if any)"
echo
echo -e "${BLUE}📂 What will be preserved:${NC}"
echo "• Your settings and preferences"
echo "• Database and session history"
echo "• Any custom files you've added"
echo

read -p "Continue with update? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Update cancelled"
    exit 0
fi

# Create backup
BACKUP_DIR="$HOME/.claude.backup.$(date +%Y%m%d_%H%M%S)"
echo "💾 Creating backup at $BACKUP_DIR..."
if ! cp -r ~/.claude "$BACKUP_DIR"; then
    echo -e "${RED}❌ Failed to create backup${NC}"
    exit 1
fi

# Download latest release
TEMP_DIR=$(mktemp -d)
echo "📥 Downloading latest release..."
DOWNLOAD_URL="https://github.com/okets/.claude/archive/refs/tags/v${LATEST_VERSION}.tar.gz"

if ! curl -L "$DOWNLOAD_URL" -o "$TEMP_DIR/release.tar.gz" 2>/dev/null; then
    echo -e "${RED}❌ Failed to download release${NC}"
    echo "URL: $DOWNLOAD_URL"
    exit 1
fi

# Extract
echo "📦 Extracting release..."
cd "$TEMP_DIR"
if ! tar -xzf release.tar.gz; then
    echo -e "${RED}❌ Failed to extract release${NC}"
    exit 1
fi
cd - > /dev/null

# Find the extracted directory
SOURCE_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "*.claude-*" | head -1)
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}❌ Could not find extracted source directory${NC}"
    echo "Contents of temp directory:"
    ls -la "$TEMP_DIR"
    exit 1
fi

# Copy files (preserve user data)
echo "🔄 Installing update..."

# Update code files
echo "  📂 Updating hooks..."
cp -r "$SOURCE_DIR/hooks" ~/.claude/ 2>/dev/null || true

echo "  📚 Updating documentation..."
cp -r "$SOURCE_DIR/docs" ~/.claude/ 2>/dev/null || true
cp -r "$SOURCE_DIR/developer-docs" ~/.claude/ 2>/dev/null || true

echo "  ⚡ Updating commands..."
cp -r "$SOURCE_DIR/commands" ~/.claude/ 2>/dev/null || true

echo "  🔧 Updating migrations..."
cp -r "$SOURCE_DIR/migrations" ~/.claude/ 2>/dev/null || true

echo "  📄 Updating core files..."
cp "$SOURCE_DIR/VERSION" ~/.claude/ 2>/dev/null || true
cp "$SOURCE_DIR/update.sh" ~/.claude/ 2>/dev/null || true
cp "$SOURCE_DIR/README.md" ~/.claude/ 2>/dev/null || true
cp "$SOURCE_DIR/GETTING_STARTED.md" ~/.claude/ 2>/dev/null || true
cp "$SOURCE_DIR/pyproject.toml" ~/.claude/ 2>/dev/null || true

# Make scripts executable
chmod +x ~/.claude/update.sh
chmod +x ~/.claude/hooks/*.py 2>/dev/null || true
find ~/.claude/hooks/utils -name "*.py" -type f -exec chmod +x {} \; 2>/dev/null || true
find ~/.claude/migrations -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null || true

# Find and backup all project databases
echo "🔍 Scanning for project databases..."
DB_LIST=()
while IFS= read -r -d '' db_path; do
    if [ -f "$db_path" ]; then
        DB_LIST+=("$db_path")
        echo "  📊 Found: $db_path"
    fi
done < <(find "$HOME" -name "smarter-claude.db" -path "*/.claude/smarter-claude/*" -print0 2>/dev/null)

if [ ${#DB_LIST[@]} -eq 0 ]; then
    echo "ℹ️  No project databases found"
else
    echo "📊 Found ${#DB_LIST[@]} project database(s)"
    
    # Create database backups
    echo "💾 Creating database backups..."
    DB_BACKUPS=()
    for db_path in "${DB_LIST[@]}"; do
        backup_path="${db_path}.backup.$(date +%Y%m%d_%H%M%S)"
        if cp "$db_path" "$backup_path"; then
            DB_BACKUPS+=("$backup_path")
            echo "  ✅ Backed up: $(basename "$(dirname "$db_path")")/$(basename "$db_path")"
        else
            echo -e "${RED}❌ Failed to backup: $db_path${NC}"
            # Clean up any successful backups
            for backup in "${DB_BACKUPS[@]}"; do
                rm -f "$backup"
            done
            exit 1
        fi
    done
fi

# Run migrations
echo "🔄 Checking for migrations..."
MIGRATION_COUNT=0
MIGRATIONS_TO_RUN=()

# First, identify which migrations need to run
for migration in ~/.claude/migrations/v*.sh; do
    [ -f "$migration" ] || continue
    MIGRATION_VERSION=$(basename "$migration" .sh | sed 's/^v//')
    
    # Only run if migration version is between current and latest
    if version_gt "$MIGRATION_VERSION" "$CURRENT_VERSION" && version_le "$MIGRATION_VERSION" "$LATEST_VERSION"; then
        MIGRATIONS_TO_RUN+=("$migration")
    fi
done

if [ ${#MIGRATIONS_TO_RUN[@]} -eq 0 ]; then
    echo "✅ No migrations needed"
else
    echo "🔧 Will apply ${#MIGRATIONS_TO_RUN[@]} migration(s) to ${#DB_LIST[@]} database(s)"
    
    # Run each migration
    for migration in "${MIGRATIONS_TO_RUN[@]}"; do
        MIGRATION_VERSION=$(basename "$migration" .sh | sed 's/^v//')
        echo "  🔧 Running migration: v$MIGRATION_VERSION"
        
        # Execute migration (it will handle all databases)
        if bash "$migration"; then
            ((MIGRATION_COUNT++))
        else
            echo -e "${RED}❌ Migration v$MIGRATION_VERSION failed! Restoring database backups...${NC}"
            
            # Restore all database backups
            for i in "${!DB_LIST[@]}"; do
                if [ -f "${DB_BACKUPS[$i]}" ]; then
                    cp "${DB_BACKUPS[$i]}" "${DB_LIST[$i]}"
                    echo "  ↩️  Restored: ${DB_LIST[$i]}"
                fi
            done
            
            # Also restore the main installation
            rm -rf ~/.claude
            mv "$BACKUP_DIR" ~/.claude
            exit 1
        fi
    done
    
    echo "✅ Applied $MIGRATION_COUNT migration(s) to all databases"
    
    # Clean up database backups on success (keep them for now, user can clean up)
    echo "📁 Database backups preserved (clean up manually after verifying):"
    for backup in "${DB_BACKUPS[@]}"; do
        echo "  🗂️  $backup"
    done
fi

# Update VERSION file
echo "$LATEST_VERSION" > ~/.claude/VERSION

# Cleanup
rm -rf "$TEMP_DIR"

echo
echo -e "${GREEN}🎉 Successfully updated to v$LATEST_VERSION!${NC}"
echo
echo -e "${BLUE}📁 Backup saved at:${NC} $BACKUP_DIR"
echo -e "${BLUE}🗑️  Remove backup with:${NC} rm -rf $BACKUP_DIR"
echo
echo -e "${BLUE}💡 Tip:${NC} Test your installation and remove the backup once you're satisfied"
echo

# Show release notes if available
RELEASE_NOTES=$(echo "$LATEST_RELEASE" | grep '"body"' | cut -d'"' -f4 | head -3)
if [ -n "$RELEASE_NOTES" ]; then
    echo -e "${BLUE}📝 Release highlights:${NC}"
    echo "$RELEASE_NOTES" | sed 's/\\n/\n/g' | head -3
    echo
fi