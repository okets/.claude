#!/bin/bash
# Smarter-Claude One-Line Installation Script
# Downloads repository and delegates to setup.sh for configuration

# Don't use set -e - we want to handle errors gracefully

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Installation state tracking
INSTALL_LOG="$HOME/.claude/.install.log"
ERROR_COUNT=0
WARNING_COUNT=0

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$INSTALL_LOG" 2>/dev/null
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
    echo "[SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$INSTALL_LOG" 2>/dev/null
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    echo "[WARNING] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$INSTALL_LOG" 2>/dev/null
    ((WARNING_COUNT++))
}

log_error() {
    echo -e "${RED}❌${NC} $1"
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$INSTALL_LOG" 2>/dev/null
    ((ERROR_COUNT++))
}

log_progress() {
    echo -e "${CYAN}⏳${NC} $1"
    echo "[PROGRESS] $(date '+%Y-%m-%d %H:%M:%S') $1" >> "$INSTALL_LOG" 2>/dev/null
}

# Basic validation functions for clone phase only

# Check minimal prerequisites for clone phase
check_clone_prerequisites() {
    log_info "Checking prerequisites for installation..."
    
    # Check for required commands for clone phase only
    local missing_commands=()
    for cmd in git curl; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [ ${#missing_commands[@]} -gt 0 ]; then
        log_error "Missing required commands for installation: ${missing_commands[*]}"
        log_info "Please install the missing commands and try again"
        
        # Provide platform-specific installation hints
        if [[ "$OSTYPE" == "darwin"* ]]; then
            log_info "On macOS, you can install them with Homebrew:"
            log_info "  brew install ${missing_commands[*]}"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            log_info "On Linux, you can install them with:"
            log_info "  sudo apt-get install ${missing_commands[*]}"
        fi
        exit 1
    fi
    
    # Check write permissions
    if ! mkdir -p "$HOME/.claude" 2>/dev/null || ! touch "$HOME/.claude/.test_write" 2>/dev/null; then
        log_error "No write permission to ~/.claude directory"
        log_info "Please check your permissions and try again"
        exit 1
    fi
    rm -f "$HOME/.claude/.test_write"
    
    log_success "Prerequisites for installation met"
}



# Check network connectivity for GitHub
check_network() {
    log_info "Checking network connectivity..."
    
    # Try GitHub specifically since that's what we need for clone
    if ! curl -sSf --connect-timeout 10 "https://github.com" > /dev/null 2>&1; then
        log_error "Cannot reach GitHub - please check your internet connection"
        echo
        echo -e "${YELLOW}Troubleshooting tips:${NC}"
        echo "• Check if you're behind a proxy (set HTTP_PROXY/HTTPS_PROXY if needed)"
        echo "• Try: curl -v https://github.com"
        echo "• Check firewall settings"
        echo "• Verify DNS resolution: nslookup github.com"
        exit 1
    fi
    
    log_success "Network connectivity to GitHub confirmed"
}

# Check minimal disk space for clone (just need ~50MB for repo)
check_disk_space() {
    log_info "Checking disk space..."
    
    REQUIRED_MB=100  # Just need space for repo clone
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        AVAILABLE_MB=$(df -m "$HOME" | awk 'NR==2 {print $4}')
    else
        # Linux - handle different df output formats
        AVAILABLE_MB=$(df -m "$HOME" | tail -1 | awk '{print $4}')
    fi
    
    # Validate that we got a number
    if ! [[ "$AVAILABLE_MB" =~ ^[0-9]+$ ]]; then
        log_warning "Could not determine available disk space"
        log_info "Proceeding with installation anyway..."
        return
    fi
    
    if [[ "$AVAILABLE_MB" -lt "$REQUIRED_MB" ]]; then
        log_error "Insufficient disk space for installation. Need at least ${REQUIRED_MB}MB, have ${AVAILABLE_MB}MB"
        echo
        echo -e "${YELLOW}To free up space:${NC}"
        echo "• Clear downloads: rm -rf ~/Downloads/*"
        echo "• Clear caches: brew cleanup (macOS)"
        echo "• Check large files: du -sh ~/* | sort -h"
        exit 1
    fi
    
    log_success "Sufficient disk space available: ${AVAILABLE_MB}MB"
}


# Handle existing ~/.claude directory
handle_existing_claude_dir() {
    CLAUDE_DIR="$HOME/.claude"
    
    # Check for any existing files in ~/.claude
    if [ -d "$CLAUDE_DIR" ] && [ "$(ls -A "$CLAUDE_DIR" 2>/dev/null)" ]; then
        log_warning "Existing files found in ~/.claude directory"
        log_info "This installation will overwrite your existing Claude Code configuration"
        BACKUP_DIR="$CLAUDE_DIR/backup_$(date +%Y%m%d_%H%M%S)"
        
        echo -e "${YELLOW}⚠️  WARNING: This will overwrite your ~/.claude folder${NC}"
        echo -e "${BLUE}But it's worth it! This is the Claude you need. 🤖✨${NC}"
        echo
        read -p "Create backup and continue? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Creating backup at $BACKUP_DIR..."
            mkdir -p "$BACKUP_DIR"
            cp -r "$CLAUDE_DIR"/* "$BACKUP_DIR/" 2>/dev/null || true
            log_success "Backup created - your old files are safe!"
        else
            log_info "Installation cancelled. Your files are unchanged."
            exit 0
        fi
    fi
    
    # Ensure ~/.claude exists and is writable
    mkdir -p "$CLAUDE_DIR" 2>/dev/null
    touch "$INSTALL_LOG" 2>/dev/null
}

# Download smarter-claude repository
clone_repository() {
    log_info "Downloading smarter-claude repository..."
    
    CLAUDE_DIR="$HOME/.claude"
    TEMP_DIR=$(mktemp -d)
    
    # Show download progress
    log_progress "Cloning from GitHub (this may take a moment)..."
    
    # Clone with progress indication
    if GIT_TERMINAL_PROMPT=0 git clone --progress https://github.com/okets/.claude.git "$TEMP_DIR" 2>&1 | while read -r line; do
        if [[ "$line" =~ "Receiving objects" ]] || [[ "$line" =~ "Resolving deltas" ]]; then
            echo -ne "\r${CYAN}⏳${NC} $line\033[K"
        fi
    done; then
        echo  # New line after progress
        log_success "Repository downloaded successfully"
    else
        log_error "Failed to download smarter-claude repository"
        echo
        echo -e "${YELLOW}Troubleshooting tips:${NC}"
        echo "• Check network connection: ping github.com"
        echo "• Try manual clone: git clone https://github.com/okets/.claude.git"
        echo "• Check if git is configured properly: git config --list"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Copy files to ~/.claude
    log_progress "Copying files to ~/.claude..."
    
    # Ensure target directories exist
    mkdir -p "$CLAUDE_DIR" 2>/dev/null
    
    # Copy with error checking - copy all repository content except .git
    local copy_errors=0
    
    # Copy all files from repository to ~/.claude, excluding .git
    if ! (cd "$TEMP_DIR" && cp -r . "$CLAUDE_DIR/" 2>/dev/null); then
        log_error "Failed to copy repository files"
        ((copy_errors++))
    fi
    
    # Remove .git directory if it was copied (we don't want version control in user directory)
    rm -rf "$CLAUDE_DIR/.git" 2>/dev/null
    
    # Verify essential hooks directory was copied
    if [ ! -d "$CLAUDE_DIR/hooks" ]; then
        log_error "Failed to copy essential hooks directory"
        ((copy_errors++))
    fi
    
    # Verify setup.sh was copied
    if [ ! -f "$CLAUDE_DIR/setup.sh" ]; then
        log_warning "setup.sh not found - manual setup may not work"
    fi
    
    if [ $copy_errors -gt 0 ]; then
        log_error "Repository copy failed. Installation cannot continue."
        log_info "Check permissions on ~/.claude directory"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Clean up
    rm -rf "$TEMP_DIR"
    
    log_success "Repository files copied to ~/.claude"
}

# Run setup.sh to complete installation
run_setup() {
    log_info "Running setup script to complete installation..."
    
    SETUP_SCRIPT="$HOME/.claude/setup.sh"
    
    if [ ! -f "$SETUP_SCRIPT" ]; then
        log_error "Setup script not found at $SETUP_SCRIPT"
        log_info "Installation may be incomplete - try manual installation"
        exit 1
    fi
    
    # Make setup script executable
    chmod +x "$SETUP_SCRIPT" 2>/dev/null
    
    echo
    echo -e "${CYAN}🔧 Launching setup script...${NC}"
    echo
    
    # Run setup script and forward its exit code
    if bash "$SETUP_SCRIPT"; then
        log_success "Setup completed successfully!"
    else
        local exit_code=$?
        log_error "Setup script failed with exit code: $exit_code"
        echo
        echo -e "${YELLOW}You can try running setup manually:${NC}"
        echo "bash ~/.claude/setup.sh"
        echo
        echo -e "${YELLOW}Or check the setup log:${NC}"
        echo "cat ~/.claude/.setup.log"
        exit $exit_code
    fi
}

# Main installation flow
main() {
    echo -e "${BLUE}🤖 Smarter-Claude One-Line Installation${NC}"
    echo -e "${MAGENTA}Downloads repository and runs comprehensive setup${NC}"
    echo "This will install smarter-claude to your ~/.claude directory"
    echo
    
    # Create ~/.claude directory first to ensure logs work
    mkdir -p "$HOME/.claude" 2>/dev/null
    touch "$INSTALL_LOG" 2>/dev/null
    
    # Installation steps - minimal for clone phase
    local steps=(
        "check_clone_prerequisites"
        "check_network"
        "check_disk_space"
        "handle_existing_claude_dir"
        "clone_repository"
        "run_setup"
    )
    
    # Execute steps
    for step in "${steps[@]}"; do
        echo
        log_progress "Step: $step"
        if ! $step; then
            log_error "Installation failed at step: $step"
            log_info "Check the log for details: $INSTALL_LOG"
            echo
            echo -e "${YELLOW}For manual installation:${NC}"
            echo "1. git clone https://github.com/okets/.claude.git"
            echo "2. cp -r .claude/.claude/* ~/.claude/"
            echo "3. bash ~/.claude/setup.sh"
            exit 1
        fi
    done
    
    # Clean up
    echo >> "$INSTALL_LOG"
    echo "Installation completed at $(date)" >> "$INSTALL_LOG"
    echo "Errors: $ERROR_COUNT, Warnings: $WARNING_COUNT" >> "$INSTALL_LOG"
}

# Handle interrupts gracefully
trap 'echo; log_error "Installation interrupted"; log_info "Run the script again to resume"; exit 130' INT TERM

# Run main function
main "$@"