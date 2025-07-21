# Smarter-Claude Version System

This document describes the version control and update system for smarter-claude. Use this as a reference for both initial implementation and future releases.

## Table of Contents
1. [System Overview](#system-overview)
2. [Update Flow Diagram](#update-flow-diagram)
3. [Initial Implementation (v1.0.0)](#initial-implementation-v100)
4. [Release Process](#release-process)
5. [Migration Scripts](#migration-scripts)
6. [Update Flow](#update-flow)
7. [Troubleshooting](#troubleshooting)

## System Overview

The version system consists of:
- **VERSION file** - Contains current version number (e.g., `1.0.0`)
- **update.sh** - Permanent update script that handles all updates
- **migrations/** - Directory containing version-specific migration scripts
- **GitHub Actions** - Automatically creates releases when VERSION changes

### Key Principles
1. The `update.sh` script never changes after v1.0.0
2. Each release can include a migration script (`migrations/v1.0.1.sh`)
3. Updates preserve user data (settings, database, custom files)
4. GitHub releases are created automatically via CI/CD
5. **Multi-database support** - Migrations automatically find and update all project databases

### Database Architecture
- **Global Installation**: `~/.claude/` (hooks, docs, migrations, update scripts)
- **Project Databases**: `<project>/.claude/smarter-claude/smarter-claude.db` (one per project)
- **Migration Strategy**: Find all project databases and apply schema changes to each
- **Backup Strategy**: Individual timestamped backups before migration

## Initial Implementation (v1.0.0)

### Checklist for First Release

- [ ] **1. Create VERSION file**
  ```bash
  echo "1.0.0" > VERSION
  ```

- [ ] **2. Create empty migrations directory**
  ```bash
  mkdir -p migrations
  echo "# Migration scripts go here" > migrations/README.md
  ```

- [ ] **3. Create update.sh**
  ```bash
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
  
  # Get current version
  CURRENT_VERSION=$(cat ~/.claude/VERSION 2>/dev/null || echo "0.0.0")
  echo -e "${BLUE}Current version: $CURRENT_VERSION${NC}"
  
  # Get latest version from GitHub
  echo "Checking for updates..."
  LATEST_RELEASE=$(curl -s https://api.github.com/repos/okets/.claude/releases/latest)
  LATEST_VERSION=$(echo "$LATEST_RELEASE" | grep '"tag_name"' | cut -d'"' -f4 | sed 's/^v//')
  
  if [ -z "$LATEST_VERSION" ]; then
      echo -e "${RED}Failed to check latest version${NC}"
      exit 1
  fi
  
  echo -e "${BLUE}Latest version: $LATEST_VERSION${NC}"
  
  # Check if update needed
  if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
      echo -e "${GREEN}Already up to date!${NC}"
      exit 0
  fi
  
  echo -e "${YELLOW}Update available: $CURRENT_VERSION → $LATEST_VERSION${NC}"
  read -p "Continue with update? (y/N): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Update cancelled"
      exit 0
  fi
  
  # Create backup
  BACKUP_DIR="$HOME/.claude.backup.$(date +%Y%m%d_%H%M%S)"
  echo "Creating backup at $BACKUP_DIR..."
  cp -r ~/.claude "$BACKUP_DIR"
  
  # Download latest release
  TEMP_DIR=$(mktemp -d)
  echo "Downloading latest release..."
  curl -L "https://github.com/okets/.claude/archive/refs/tags/v${LATEST_VERSION}.tar.gz" -o "$TEMP_DIR/release.tar.gz"
  
  # Extract
  cd "$TEMP_DIR"
  tar -xzf release.tar.gz
  cd -
  
  # Copy files (preserve user data)
  echo "Installing update..."
  SOURCE_DIR="$TEMP_DIR/.claude-${LATEST_VERSION}"
  
  # Update code files
  cp -r "$SOURCE_DIR/hooks" ~/.claude/
  cp -r "$SOURCE_DIR/docs" ~/.claude/
  cp -r "$SOURCE_DIR/commands" ~/.claude/ 2>/dev/null || true
  cp -r "$SOURCE_DIR/migrations" ~/.claude/
  cp "$SOURCE_DIR/VERSION" ~/.claude/
  cp "$SOURCE_DIR/update.sh" ~/.claude/
  cp "$SOURCE_DIR/README.md" ~/.claude/
  cp "$SOURCE_DIR/VERSIONING.md" ~/.claude/
  cp "$SOURCE_DIR/GETTING_STARTED.md" ~/.claude/
  
  # Make scripts executable
  chmod +x ~/.claude/update.sh
  chmod +x ~/.claude/hooks/*.py
  find ~/.claude/hooks/utils -name "*.py" -type f -exec chmod +x {} \;
  
  # Run migrations
  echo "Checking for migrations..."
  for migration in ~/.claude/migrations/v*.sh; do
      [ -f "$migration" ] || continue
      MIGRATION_VERSION=$(basename "$migration" .sh | sed 's/^v//')
      
      # Only run if migration version is between current and latest
      if version_gt "$MIGRATION_VERSION" "$CURRENT_VERSION" && ! version_gt "$MIGRATION_VERSION" "$LATEST_VERSION"; then
          echo "Running migration: v$MIGRATION_VERSION"
          bash "$migration"
          if [ $? -ne 0 ]; then
              echo -e "${RED}Migration failed! Restoring backup...${NC}"
              rm -rf ~/.claude
              mv "$BACKUP_DIR" ~/.claude
              exit 1
          fi
      fi
  done
  
  # Update VERSION file
  echo "$LATEST_VERSION" > ~/.claude/VERSION
  
  # Cleanup
  rm -rf "$TEMP_DIR"
  
  echo -e "${GREEN}✅ Successfully updated to v$LATEST_VERSION${NC}"
  echo
  echo "Backup saved at: $BACKUP_DIR"
  echo "Run 'rm -rf $BACKUP_DIR' to remove backup after verifying the update"
  ```

- [ ] **4. Update install.sh to include update.sh**
  Add to install.sh after copying files:
  ```bash
  # Copy update script
  cp "$TEMP_DIR"/update.sh "$CLAUDE_DIR/"
  chmod +x "$CLAUDE_DIR/update.sh"
  
  # Create migrations directory
  mkdir -p "$CLAUDE_DIR/migrations"
  ```

- [ ] **5. Fix /smarter-claude_update.md**
  Replace complex git logic with:
  ```bash
  cd ~/.claude && bash update.sh
  ```

- [ ] **6. Create GitHub Action (.github/workflows/release.yml)**
  ```yaml
  name: Auto Release
  
  on:
    push:
      branches: [main]
      paths:
        - 'VERSION'
  
  jobs:
    create-release:
      runs-on: ubuntu-latest
      steps:
        - name: Checkout
          uses: actions/checkout@v4
          with:
            fetch-depth: 0
        
        - name: Get version
          id: version
          run: |
            VERSION=$(cat VERSION)
            echo "version=$VERSION" >> $GITHUB_OUTPUT
            echo "tag=v$VERSION" >> $GITHUB_OUTPUT
        
        - name: Check if tag exists
          id: check_tag
          run: |
            if git rev-parse "${{ steps.version.outputs.tag }}" >/dev/null 2>&1; then
              echo "exists=true" >> $GITHUB_OUTPUT
            else
              echo "exists=false" >> $GITHUB_OUTPUT
            fi
        
        - name: Get previous tag
          if: steps.check_tag.outputs.exists == 'false'
          id: prev_tag
          run: |
            PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
            echo "prev_tag=$PREV_TAG" >> $GITHUB_OUTPUT
        
        - name: Generate changelog
          if: steps.check_tag.outputs.exists == 'false'
          id: changelog
          run: |
            VERSION="${{ steps.version.outputs.version }}"
            PREV_TAG="${{ steps.prev_tag.outputs.prev_tag }}"
            
            {
              echo "## 🚀 Smarter-Claude v$VERSION"
              echo
              
              # Check for migration
              if [ -f "migrations/v${VERSION}.sh" ]; then
                echo "⚠️ **This release includes database migrations**"
                echo
              fi
              
              echo "### What's Changed"
              echo
              
              # Get commit messages
              if [ -z "$PREV_TAG" ]; then
                git log --pretty=format:"- %s" --reverse
              else
                git log ${PREV_TAG}..HEAD --pretty=format:"- %s" --reverse
              fi
              
              echo
              echo
              echo "### Update Instructions"
              echo '```bash'
              echo '/smarter-claude_update'
              echo '```'
              echo
              echo "**Full Changelog**: https://github.com/${{ github.repository }}/compare/${PREV_TAG}...${{ steps.version.outputs.tag }}"
            } > changelog.md
            
            # Set output
            echo "changelog<<EOF" >> $GITHUB_OUTPUT
            cat changelog.md >> $GITHUB_OUTPUT
            echo "EOF" >> $GITHUB_OUTPUT
        
        - name: Create Release
          if: steps.check_tag.outputs.exists == 'false'
          uses: actions/create-release@v1
          env:
            GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          with:
            tag_name: ${{ steps.version.outputs.tag }}
            release_name: v${{ steps.version.outputs.version }}
            body: ${{ steps.changelog.outputs.changelog }}
            draft: false
            prerelease: false
  ```

- [ ] **7. Commit and push everything**
  ```bash
  git add VERSION update.sh migrations/ .github/workflows/release.yml
  git add install.sh commands/smarter-claude_update.md VERSIONING.md
  git commit -m "feat: Implement version system for v1.0.0"
  git push origin main
  ```

## Release Process

### Creating a New Release (e.g., v1.0.1)

1. **Update VERSION file**
   ```bash
   echo "1.0.1" > VERSION
   ```

2. **Create migration script if needed**
   ```bash
   # Only if database or file structure changes are needed
   cat > migrations/v1.0.1.sh << 'EOF'
   #!/bin/bash
   echo "Running v1.0.1 migration..."
   
   # Example: Add index to database
   sqlite3 ~/.claude/.claude/smarter-claude/smarter-claude.db << SQL
   CREATE INDEX IF NOT EXISTS idx_file_contexts_timestamp 
   ON file_contexts(timestamp);
   SQL
   
   echo "✅ v1.0.1 migration complete"
   EOF
   
   chmod +x migrations/v1.0.1.sh
   ```

3. **Commit and push**
   ```bash
   git add VERSION migrations/v1.0.1.sh
   git commit -m "Release v1.0.1: Fix TTS timing issues"
   git push origin main
   ```

4. **GitHub automatically:**
   - Detects VERSION change
   - Creates tag v1.0.1
   - Generates changelog from commits
   - Creates GitHub release

5. **Users update by running:**
   ```bash
   /smarter-claude_update
   ```

## Migration Scripts

### Multi-Database Migration Approach

Smarter-claude uses a **centralized migration system** that automatically:
1. **Discovers** all project databases across the user's system
2. **Backs up** each database individually before migration
3. **Applies** schema changes to all databases simultaneously
4. **Rolls back** all databases if any migration fails

This ensures all projects stay synchronized with the latest database schema.

### When to Create a Migration

Create a migration script when:
- Database schema changes (tables, columns, indexes)
- File locations change
- Settings format changes
- Breaking changes that need data transformation

### Migration Script Template

```bash
#!/bin/bash
# migrations/vX.Y.Z.sh
# Description: What this migration does

echo "Running vX.Y.Z migration..."

# Database changes - Apply to ALL project databases
DB_COUNT=0
while IFS= read -r -d '' db_path; do
    if [ -f "$db_path" ]; then
        echo "  🔧 Migrating: $db_path"
        
        if sqlite3 "$db_path" << 'SQL_EOF'
-- Your SQL commands here
CREATE INDEX IF NOT EXISTS idx_example ON table_name(column);
SQL_EOF
        then
            ((DB_COUNT++))
        else
            echo "❌ Migration failed for: $db_path"
            exit 1
        fi
    fi
done < <(find "$HOME" -name "smarter-claude.db" -path "*/.claude/smarter-claude/*" -print0 2>/dev/null)

echo "  ✅ Database migration applied to $DB_COUNT database(s)"

# File structure changes (global)
# mkdir -p ~/.claude/new_directory
# mv ~/.claude/old_file ~/.claude/new_location 2>/dev/null || true

# Settings updates (can be global or per-project)
# python3 << EOF
# import json
# # Python code to update settings
# EOF

echo "✅ vX.Y.Z migration complete"
```

### Migration Best Practices

1. **Always check if files/databases exist before modifying**
2. **Use `|| true` to prevent script failure on missing files**
3. **Echo progress for user feedback**
4. **Test migration on a backup first**
5. **Keep migrations idempotent (safe to run multiple times)**

## Update Flow

### What Happens During Update

1. **User runs** `/smarter-claude_update`
2. **update.sh checks** current version vs. latest GitHub release
3. **If update available:**
   - Creates timestamped backup of ~/.claude
   - Downloads latest release tarball
   - Copies new code files
   - Preserves user data (settings, database, custom files)
   - **Scans for all project databases** across the system
   - **Backs up each database** individually
   - **Runs migrations on all databases** between versions
   - Updates VERSION file
4. **User sees** success message with backup locations

### Files That Get Updated
- ✅ All Python scripts in hooks/
- ✅ All documentation in docs/
- ✅ Slash commands in commands/
- ✅ Migration scripts
- ✅ VERSION file
- ✅ README files

### Files That Are Preserved
- ✅ User settings (.claude/smarter-claude/smarter-claude.json)
- ✅ Database (.claude/smarter-claude/smarter-claude.db)
- ✅ Any user-created files
- ✅ Logs and session data

## Troubleshooting

### Common Issues

**"Failed to check latest version"**
- Check internet connection
- Verify GitHub API is accessible: `curl https://api.github.com`

**"Migration failed"**
- Check migration script for errors
- Restore from backup: `mv ~/.claude.backup.* ~/.claude`
- Report issue with migration script output

**"Already up to date" but want to force update**
- Delete VERSION file: `rm ~/.claude/VERSION`
- Run update again

**Permission errors**
- Ensure scripts are executable: `chmod +x ~/.claude/update.sh`
- Check directory permissions

### Manual Update Process

If automatic update fails:
```bash
# 1. Backup current installation
cp -r ~/.claude ~/.claude.backup

# 2. Download latest release
curl -L https://github.com/okets/.claude/archive/refs/tags/vX.Y.Z.tar.gz -o release.tar.gz

# 3. Extract and copy files
tar -xzf release.tar.gz
cp -r .claude-X.Y.Z/* ~/.claude/

# 4. Run migrations manually
bash ~/.claude/migrations/vX.Y.Z.sh

# 5. Update VERSION
echo "X.Y.Z" > ~/.claude/VERSION
```

### Debug Mode

Run update with debug output:
```bash
bash -x ~/.claude/update.sh
```

---

## Quick Reference

### Release Checklist
- [ ] Update VERSION file
- [ ] Create migration script (if needed)
- [ ] Test migration on backup
- [ ] Commit with descriptive message
- [ ] Push to main
- [ ] Verify GitHub release created
- [ ] Test update process

### Version Numbering
- **Major (X.0.0)**: Breaking changes, major features
- **Minor (1.X.0)**: New features, backwards compatible
- **Patch (1.0.X)**: Bug fixes, small improvements

### Important Paths
- Version file: `~/.claude/VERSION`
- Update script: `~/.claude/update.sh`
- Migrations: `~/.claude/migrations/`
- User settings: `~/.claude/.claude/smarter-claude/smarter-claude.json`
- Database: `~/.claude/.claude/smarter-claude/smarter-claude.db`