#!/bin/bash
# Smarter-Claude Post-Clone Setup Script
# Handles all installation steps after repository has been cloned
# Can be run independently for manual installations or troubleshooting

# Don't use set -e - we want to handle errors gracefully

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Detect script location and set paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

# Installation state tracking
INSTALL_LOG="$CLAUDE_DIR/.setup.log"
INSTALL_STATE="$CLAUDE_DIR/.setup.state"
ERROR_COUNT=0
WARNING_COUNT=0

# Setup type detection
SETUP_TYPE=""
if [ "$SCRIPT_DIR" = "$CLAUDE_DIR" ]; then
    SETUP_TYPE="manual"  # Running from ~/.claude (manual install)
else
    SETUP_TYPE="auto"    # Running from cloned repo (automated install)
fi

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

# Save installation state
save_state() {
    echo "$1" > "$INSTALL_STATE" 2>/dev/null
}

# Check if we're resuming from a previous failed installation
check_previous_state() {
    if [ -f "$INSTALL_STATE" ]; then
        PREVIOUS_STATE=$(cat "$INSTALL_STATE" 2>/dev/null || echo "unknown")
        log_warning "Previous setup detected at stage: $PREVIOUS_STATE"
        echo -e "${YELLOW}Would you like to resume from where it left off?${NC}"
        read -p "Resume setup? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            return 0
        else
            rm -f "$INSTALL_STATE"
            return 1
        fi
    fi
    return 1
}

# Validate that we have the necessary files for setup
validate_source_files() {
    save_state "validate_source_files"
    log_info "Validating source files..."
    
    local missing_files=()
    local required_files=(
        "hooks/notification.py"
        "hooks/post_tool_use.py"
        "hooks/pre_tool_use.py"
        "hooks/stop.py"
        "hooks/utils/contextual_db.py"
        "hooks/utils/manage_settings.py"
    )
    
    # Check if we're in manual mode and files are already in place
    if [ "$SETUP_TYPE" = "manual" ]; then
        SOURCE_DIR="$CLAUDE_DIR"
        log_info "Manual setup mode - validating files in ~/.claude"
    else
        SOURCE_DIR="$SCRIPT_DIR"
        log_info "Automated setup mode - validating files in source directory"
    fi
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$SOURCE_DIR/$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        log_error "Missing required files: ${missing_files[*]}"
        echo
        echo -e "${YELLOW}Troubleshooting:${NC}"
        if [ "$SETUP_TYPE" = "manual" ]; then
            echo "• Ensure you've copied all files from the cloned repository to ~/.claude"
            echo "• Check that the copy operation completed successfully"
            echo "• Run: cp -r .claude/.claude/* ~/.claude/"
        else
            echo "• Repository clone may be incomplete"
            echo "• Try cloning again: git clone https://github.com/okets/.claude.git"
            echo "• Check your internet connection"
        fi
        exit 1
    fi
    
    log_success "All required source files found"
}

# Check system prerequisites
check_prerequisites() {
    save_state "check_prerequisites"
    log_info "Checking system prerequisites..."
    
    # Check for required commands
    local missing_commands=()
    for cmd in python3; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_commands+=("$cmd")
        fi
    done
    
    # Git and curl are optional for setup phase since we already have the files
    for cmd in git curl; do
        if ! command -v "$cmd" &> /dev/null; then
            log_warning "$cmd not found - some features may be limited"
        fi
    done
    
    if [ ${#missing_commands[@]} -gt 0 ]; then
        log_error "Missing required commands: ${missing_commands[*]}"
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
    if ! touch "$CLAUDE_DIR/.test_write" 2>/dev/null; then
        log_error "No write permission to ~/.claude directory"
        log_info "Please check your permissions and try again"
        log_info "You may need to run: chmod 755 ~/.claude"
        exit 1
    fi
    rm -f "$CLAUDE_DIR/.test_write"
    
    log_success "All prerequisites met"
}

# Check if Claude Code is installed
check_claude_code() {
    save_state "check_claude_code"
    log_info "Checking if Claude Code is installed..."
    if ! command -v claude &> /dev/null; then
        log_error "Claude Code is not installed or not in PATH"
        log_info "Please install Claude Code first: https://docs.anthropic.com/en/docs/claude-code"
        echo
        echo -e "${YELLOW}Installation instructions:${NC}"
        echo "1. Visit: https://docs.anthropic.com/en/docs/claude-code/quickstart"
        echo "2. Follow the installation guide for your platform"
        echo "3. Verify with: claude --version"
        echo "4. Run this setup script again"
        exit 1
    fi
    
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    log_success "Claude Code found: $CLAUDE_VERSION"
}

# Check Python installation
check_python() {
    save_state "check_python"
    log_info "Checking Python installation..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        log_info "Please install Python 3.8 or higher"
        echo
        echo -e "${YELLOW}Installation instructions:${NC}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "• Homebrew: brew install python3"
            echo "• Official: https://www.python.org/downloads/macos/"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "• APT: sudo apt-get install python3 python3-pip"
            echo "• Official: https://www.python.org/downloads/"
        fi
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' 2>/dev/null || echo "unknown")
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 8 ]]; then
        log_error "Python 3.8 or higher is required (found: $PYTHON_VERSION)"
        echo -e "${YELLOW}Please upgrade Python to version 3.8 or higher${NC}"
        exit 1
    fi
    
    log_success "Python $PYTHON_VERSION found"
}

# Check network connectivity (optional for setup)
check_network() {
    save_state "check_network"
    log_info "Checking network connectivity for TTS downloads..."
    
    # Try multiple endpoints for resilience
    local endpoints=("https://api.github.com" "https://github.com" "https://astral.sh")
    local connected=false
    
    for endpoint in "${endpoints[@]}"; do
        if curl -sSf --connect-timeout 5 "$endpoint" > /dev/null 2>&1; then
            connected=true
            break
        fi
    done
    
    if ! $connected; then
        log_warning "Cannot reach external services - TTS model downloads will be skipped"
        echo
        echo -e "${YELLOW}Network troubleshooting tips:${NC}"
        echo "• Check if you're behind a proxy (set HTTP_PROXY/HTTPS_PROXY if needed)"
        echo "• Try: curl -v https://api.github.com"
        echo "• Check firewall settings"
        echo "• Verify DNS resolution: nslookup github.com"
        echo
        log_info "You can install TTS voices later when network is available"
        return 1
    fi
    
    log_success "Network connectivity confirmed"
    return 0
}

# Check disk space (need at least 500MB for models + installation)
check_disk_space() {
    save_state "check_disk_space"
    log_info "Checking disk space..."
    
    REQUIRED_MB=500
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
        log_error "Insufficient disk space. Need at least ${REQUIRED_MB}MB, have ${AVAILABLE_MB}MB"
        echo
        echo -e "${YELLOW}Space requirements:${NC}"
        echo "• Smarter-claude files: ~50MB"
        echo "• Kokoro TTS models: ~350MB"
        echo "• Working space: ~100MB"
        echo
        echo -e "${YELLOW}To free up space:${NC}"
        echo "• Clear downloads: rm -rf ~/Downloads/*"
        echo "• Clear caches: brew cleanup (macOS)"
        echo "• Check large files: du -sh ~/* | sort -h"
        exit 1
    fi
    
    log_success "Disk space available: ${AVAILABLE_MB}MB"
}

# Ensure ~/.claude directory structure is correct
ensure_claude_directory() {
    save_state "ensure_claude_directory"
    log_info "Ensuring ~/.claude directory structure..."
    
    # Create all necessary subdirectories
    local directories=(
        "$CLAUDE_DIR"
        "$CLAUDE_DIR/hooks"
        "$CLAUDE_DIR/hooks/utils"
        "$CLAUDE_DIR/hooks/utils/tts"
        "$CLAUDE_DIR/docs"
        "$CLAUDE_DIR/commands"
        "$CLAUDE_DIR/migrations"
        "$CLAUDE_DIR/developer-docs"
        "$CLAUDE_DIR/.claude/smarter-claude"
    )
    
    for dir in "${directories[@]}"; do
        if ! mkdir -p "$dir" 2>/dev/null; then
            log_error "Failed to create directory: $dir"
            log_info "Check permissions on parent directories"
            exit 1
        fi
    done
    
    # Initialize log file
    touch "$INSTALL_LOG" 2>/dev/null
    
    log_success "Directory structure ready"
}

# Copy files from source to ~/.claude (only for automated setup)
copy_source_files() {
    if [ "$SETUP_TYPE" = "manual" ]; then
        log_info "Manual setup - skipping file copy (files should already be in place)"
        return 0
    fi
    
    save_state "copy_source_files"
    log_info "Copying source files to ~/.claude..."
    
    SOURCE_DIR="$SCRIPT_DIR"
    local copy_errors=0
    
    # Copy with error checking
    if ! cp -r "$SOURCE_DIR"/hooks "$CLAUDE_DIR/" 2>/dev/null; then
        log_error "Failed to copy hooks directory"
        ((copy_errors++))
    fi
    
    if ! cp -r "$SOURCE_DIR"/docs "$CLAUDE_DIR/" 2>/dev/null; then
        log_error "Failed to copy docs directory"
        ((copy_errors++))
    fi
    
    cp -r "$SOURCE_DIR"/commands "$CLAUDE_DIR/" 2>/dev/null || log_warning "No commands directory found - slash commands may not be available"
    
    # Copy individual files
    for file in README.md CONTEXTUAL-LOGGING-IMPLEMENTATION-PLAN.md GETTING_STARTED.md VERSION update.sh; do
        if [ -f "$SOURCE_DIR/$file" ]; then
            cp "$SOURCE_DIR/$file" "$CLAUDE_DIR/" 2>/dev/null || log_warning "Could not copy $file"
        fi
    done
    
    # Copy migrations and developer docs
    cp -r "$SOURCE_DIR"/migrations "$CLAUDE_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR"/developer-docs "$CLAUDE_DIR/" 2>/dev/null || true
    
    if [ $copy_errors -gt 0 ]; then
        log_error "Some files failed to copy. Installation may be incomplete."
        log_info "Try running with elevated permissions or check ~/.claude permissions"
        exit 1
    fi
    
    log_success "Source files copied successfully"
}

# Set proper file permissions
set_permissions() {
    save_state "set_permissions"
    log_info "Setting proper file permissions..."
    
    # Make hooks and scripts executable
    find "$CLAUDE_DIR/hooks" -name "*.py" -type f -exec chmod +x {} \; 2>/dev/null
    find "$CLAUDE_DIR/hooks/utils/tts" -name "*.py" -type f -exec chmod +x {} \; 2>/dev/null
    find "$CLAUDE_DIR/migrations" -name "*.sh" -type f -exec chmod +x {} \; 2>/dev/null
    chmod +x "$CLAUDE_DIR/update.sh" 2>/dev/null || true
    
    # Ensure scripts can be imported by Python
    find "$CLAUDE_DIR/hooks" -name "*.py" -type f -exec chmod 644 {} \; 2>/dev/null
    find "$CLAUDE_DIR/hooks/utils" -name "*.py" -type f -exec chmod 644 {} \; 2>/dev/null
    
    log_success "File permissions set correctly"
}

# Install Python dependencies and TTS voices
install_dependencies() {
    save_state "install_dependencies"
    log_info "Installing TTS dependencies and voices..."
    
    # Check if network is available for downloads
    local network_available=true
    if ! check_network; then
        network_available=false
        log_warning "Network not available - skipping TTS model downloads"
        log_info "You can install TTS voices later when network is available"
    fi
    
    # First check if UV needs to be installed
    if ! command -v uv &> /dev/null && [ "$network_available" = true ]; then
        log_progress "UV not found - installing for Kokoro TTS support..."
        if ! install_uv_package_manager; then
            log_warning "UV installation failed - Kokoro TTS will not be available"
            log_info "You can install UV later from: https://github.com/astral-sh/uv"
        fi
    elif command -v uv &> /dev/null; then
        log_success "UV package manager found"
    fi
    
    # Use the voice manager for comprehensive installation
    VOICE_MANAGER="$CLAUDE_DIR/hooks/utils/manage_voices.py"
    
    # Install all supported voices automatically (only if network available)
    if [ -f "$VOICE_MANAGER" ] && [ "$network_available" = true ]; then
        log_progress "Installing voice engines (this may take several minutes)..."
        
        # Run voice manager with error handling
        if python3 "$VOICE_MANAGER" install-all 2>&1 | while read -r line; do
            if [[ "$line" =~ "Installing" ]]; then
                log_progress "$line"
            elif [[ "$line" =~ "✅" ]]; then
                log_success "${line#*✅}"
            elif [[ "$line" =~ "❌" ]]; then
                log_error "${line#*❌}"
            else
                echo "  $line"
            fi
        done; then
            # Get recommended voice
            RECOMMENDED=$(python3 "$VOICE_MANAGER" recommend 2>/dev/null | grep "Recommended voice engine:" | cut -d: -f2 | xargs)
            if [ -n "$RECOMMENDED" ]; then
                log_success "Recommended voice: $RECOMMENDED"
            fi
        else
            log_warning "Voice installation encountered issues"
            log_info "The system will use fallback voices"
        fi
    elif [ -f "$VOICE_MANAGER" ]; then
        log_info "Voice manager found but network unavailable - using local voices only"
    else
        # Fallback to manual installation
        log_warning "Voice manager not found - using fallback installation"
        
        # Install ffmpeg for male voice processing (only if network available)
        if [ "$network_available" = true ]; then
            if command -v ffmpeg &> /dev/null; then
                log_success "ffmpeg found - male voice processing available"
            else
                log_info "Installing ffmpeg for male voice processing..."
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    if command -v brew &> /dev/null; then
                        brew install ffmpeg
                        log_success "ffmpeg installed via Homebrew"
                    else
                        log_warning "Homebrew not found - install ffmpeg manually: brew install ffmpeg"
                    fi
                elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
                    if command -v apt-get &> /dev/null; then
                        sudo apt-get update && sudo apt-get install -y ffmpeg
                        log_success "ffmpeg installed via apt"
                    else
                        log_warning "Package manager not found - install ffmpeg manually"
                    fi
                fi
            fi
            
            # Try to install Kokoro manually if UV is available
            if command -v uv &> /dev/null; then
                install_kokoro_manually
            fi
        fi
    fi
}

# Separate function for UV installation
install_uv_package_manager() {
    log_progress "Installing UV package manager..."
    
    local install_method=""
    local install_success=false
    
    if [[ "$OSTYPE" == "darwin"* ]] && command -v brew &> /dev/null; then
        # Try Homebrew first on macOS
        log_progress "Using Homebrew to install UV..."
        if brew install uv 2>&1 | grep -v "Warning:"; then
            install_method="Homebrew"
            install_success=true
        fi
    fi
    
    # If Homebrew failed or not available, use curl installer
    if ! $install_success; then
        log_progress "Using official installer for UV..."
        if curl -LsSf https://astral.sh/uv/install.sh 2>/dev/null | sh 2>&1; then
            # Add to PATH for current session
            export PATH="$HOME/.local/bin:$PATH"
            install_method="official installer"
            install_success=true
        fi
    fi
    
    # Verify installation
    if $install_success && command -v uv &> /dev/null; then
        log_success "UV installed successfully via $install_method"
        
        # Check if PATH needs to be updated
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            log_warning "UV installed to ~/.local/bin but not in PATH"
            echo
            echo -e "${YELLOW}Add UV to your PATH by adding this to your shell config:${NC}"
            echo "export PATH=\"\$HOME/.local/bin:\$PATH\""
            echo
            echo "For bash: echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
            echo "For zsh:  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc"
        fi
        return 0
    else
        return 1
    fi
}

# Manual Kokoro installation
install_kokoro_manually() {
    log_progress "Installing Kokoro TTS (downloading ~350MB models)..."
    log_info "This may take several minutes depending on your internet connection"
    
    KOKORO_SCRIPT="$CLAUDE_DIR/hooks/utils/tts/kokoro_voice.py"
    if [ -f "$KOKORO_SCRIPT" ]; then
        # Try up to 3 times in case of network issues
        RETRY_COUNT=0
        MAX_RETRIES=3
        DOWNLOAD_STARTED=false
        
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            log_progress "Downloading Kokoro models (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)..."
            
            # Run with progress monitoring
            if uv run "$KOKORO_SCRIPT" "Installation test" --voice am_echo 2>&1 | while read -r line; do
                if [[ "$line" =~ "Downloading" ]] || [[ "$line" =~ "%" ]]; then
                    DOWNLOAD_STARTED=true
                    echo -ne "\r${CYAN}⏳${NC} $line\033[K"
                elif [[ "$line" =~ "Error" ]] || [[ "$line" =~ "error" ]]; then
                    echo
                    log_error "$line"
                else
                    [ "$DOWNLOAD_STARTED" = true ] && echo  # New line after download progress
                    echo "  $line"
                fi
            done; then
                echo  # Ensure we're on a new line
                log_success "Kokoro TTS installed successfully"
                break
            else
                RETRY_COUNT=$((RETRY_COUNT + 1))
                if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                    log_warning "Download interrupted, retrying in 5 seconds..."
                    sleep 5
                else
                    log_warning "Kokoro TTS installation failed after $MAX_RETRIES attempts"
                    echo
                    echo -e "${YELLOW}You can install Kokoro TTS later by running:${NC}"
                    echo "cd ~/.claude && uv run hooks/utils/tts/kokoro_voice.py 'test'"
                    echo
                    log_info "The system will use system voices as fallback"
                fi
            fi
        done
    else
        log_warning "Kokoro script not found - TTS will use system voices"
    fi
}

# Configure default settings
configure_settings() {
    save_state "configure_settings"
    log_info "Configuring default settings..."
    
    SETTINGS_SCRIPT="$CLAUDE_DIR/hooks/utils/manage_settings.py"
    VOICE_MANAGER="$CLAUDE_DIR/hooks/utils/manage_voices.py"
    
    if [ -f "$SETTINGS_SCRIPT" ]; then
        # Set reasonable defaults
        python3 "$SETTINGS_SCRIPT" set interaction_level concise
        
        # Set TTS engine based on voice manager recommendation
        if [ -f "$VOICE_MANAGER" ]; then
            RECOMMENDED=$(python3 "$VOICE_MANAGER" recommend 2>/dev/null | grep "Recommended voice engine:" | cut -d: -f2 | xargs)
            if [ -n "$RECOMMENDED" ]; then
                python3 "$SETTINGS_SCRIPT" set tts_engine "$RECOMMENDED"
                log_success "Configured to use recommended voice: $RECOMMENDED"
            else
                # Fallback to manual detection
                if command -v uv &> /dev/null; then
                    python3 "$SETTINGS_SCRIPT" set tts_engine kokoro-af_alloy
                    log_success "Configured to use Kokoro Alloy voice"
                elif [[ "$OSTYPE" == "darwin"* ]]; then
                    # Try Kokoro first, fallback to macOS
                    if python3 "$SETTINGS_SCRIPT" set tts_engine kokoro-af_alloy 2>/dev/null; then
                        log_success "Configured to use Kokoro Alloy voice"
                    else
                        python3 "$SETTINGS_SCRIPT" set tts_engine macos-female
                        log_success "Configured to use macOS female voice"
                    fi
                else
                    # Non-macOS systems use Kokoro
                    python3 "$SETTINGS_SCRIPT" set tts_engine kokoro-af_alloy
                    log_success "Configured to use Kokoro Alloy voice"
                fi
            fi
        else
            # Original fallback logic
            if command -v uv &> /dev/null; then
                python3 "$SETTINGS_SCRIPT" set tts_engine kokoro-af_alloy
                log_success "Configured to use Kokoro Alloy voice"
            else
                python3 "$SETTINGS_SCRIPT" set tts_engine macos
                log_success "Configured to use system TTS"
            fi
        fi
        
        log_success "Default settings configured"
    else
        log_warning "Settings script not found - using built-in defaults"
    fi
}

# Test the installation
test_installation() {
    save_state "test_installation"
    log_info "Running installation verification..."
    
    local test_failures=0
    
    # Check if hooks are executable and importable
    log_progress "Checking hook files..."
    HOOKS_DIR="$CLAUDE_DIR/hooks"
    for hook in notification.py post_tool_use.py pre_tool_use.py stop.py; do
        if [ -f "$HOOKS_DIR/$hook" ]; then
            if [ -r "$HOOKS_DIR/$hook" ]; then
                log_success "$hook is properly installed"
            else
                log_error "$hook is not readable"
                chmod 644 "$HOOKS_DIR/$hook" 2>/dev/null && log_info "Fixed permissions for $hook"
                ((test_failures++))
            fi
        else
            log_error "$hook is missing"
            ((test_failures++))
        fi
    done
    
    # Test Python imports
    log_progress "Checking Python environment..."
    cd "$CLAUDE_DIR" 2>/dev/null
    if python3 -c "import sys; sys.path.insert(0, '.'); from hooks.utils.contextual_db import ContextualDB" 2>/dev/null; then
        log_success "Python imports working"
    else
        log_warning "Python import test failed - this may be normal on first install"
        log_info "Imports will work when Claude Code runs"
    fi
    
    # Check if slash commands are installed
    log_progress "Checking slash commands..."
    COMMANDS_DIR="$CLAUDE_DIR/commands"
    if [ -d "$COMMANDS_DIR" ]; then
        COMMAND_COUNT=$(find "$COMMANDS_DIR" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
        if [ "$COMMAND_COUNT" -gt 0 ]; then
            log_success "Slash commands installed ($COMMAND_COUNT commands available)"
        else
            log_warning "Commands directory exists but no .md files found"
            ((test_failures++))
        fi
    else
        log_warning "Commands directory not found - slash commands not available"
        log_info "You can add custom commands later to ~/.claude/commands/"
    fi
    
    # Check TTS availability
    log_progress "Checking TTS system..."
    if command -v uv &> /dev/null && [ -f "$CLAUDE_DIR/hooks/utils/tts/kokoro_voice.py" ]; then
        log_success "Kokoro TTS system available"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        log_success "macOS TTS system available"
    else
        log_warning "No TTS system detected - voice features disabled"
    fi
    
    # Test settings management
    log_progress "Checking settings system..."
    SETTINGS_SCRIPT="$CLAUDE_DIR/hooks/utils/manage_settings.py"
    if [ -f "$SETTINGS_SCRIPT" ]; then
        if python3 "$SETTINGS_SCRIPT" get interaction_level >/dev/null 2>&1; then
            log_success "Settings system working"
        else
            log_warning "Settings system may not be working correctly"
            ((test_failures++))
        fi
    else
        log_error "Settings script not found"
        ((test_failures++))
    fi
    
    # Final status
    if [ $test_failures -eq 0 ]; then
        log_success "All installation tests passed!"
    else
        log_warning "Installation completed with $test_failures warnings"
        log_info "The system should still work correctly"
    fi
    
    # Clean up installation state on success
    rm -f "$INSTALL_STATE" 2>/dev/null
}

# Show next steps
show_next_steps() {
    echo
    if [ $ERROR_COUNT -eq 0 ]; then
        log_success "🎉 Smarter-Claude setup completed successfully!"
    else
        log_warning "⚠️  Setup completed with some issues"
        log_info "Check $INSTALL_LOG for details"
    fi
    
    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Start Claude Code in any project: ${YELLOW}claude${NC}"
    echo "2. After your first interaction, check: ${YELLOW}ls .claude/smarter-claude/${NC}"
    echo "3. You should see a database file created automatically"
    echo
    echo -e "${BLUE}Configuration:${NC}"
    echo "• Interaction level: ${YELLOW}concise${NC} (balanced feedback)"
    echo "• TTS engine: ${YELLOW}$(python3 ~/.claude/hooks/utils/manage_settings.py get tts_engine 2>/dev/null || echo 'default')${NC}"
    
    # Show available voices
    if [ -f "$CLAUDE_DIR/hooks/utils/manage_voices.py" ]; then
        echo
        echo -e "${BLUE}Available voices:${NC}"
        python3 "$CLAUDE_DIR/hooks/utils/manage_voices.py" status 2>/dev/null | grep "✅ Installed" | head -5 || true
    fi
    
    echo
    echo -e "${BLUE}Customize settings:${NC}"
    echo "• Change interaction level: ${YELLOW}/smarter-claude_interaction_level verbose${NC}"
    echo "• Change TTS voice: ${YELLOW}/smarter-claude_voice puck${NC}"
    echo "• Update smarter-claude: ${YELLOW}/smarter-claude_update${NC}"
    echo "• Or use CLI: ${YELLOW}python ~/.claude/hooks/utils/manage_settings.py set <key> <value>${NC}"
    echo
    echo -e "${BLUE}Need help?${NC}"
    echo "• Read: ${YELLOW}~/.claude/GETTING_STARTED.md${NC}"
    echo "• Troubleshoot: ${YELLOW}~/.claude/docs/TROUBLESHOOTING.md${NC}"
    echo "• Check logs: ${YELLOW}cat ~/.claude/.setup.log${NC}"
    echo "• Or just ask Claude: ${YELLOW}'Help me configure smarter-claude'${NC}"
    
    if [ $WARNING_COUNT -gt 0 ]; then
        echo
        echo -e "${YELLOW}⚠️  There were $WARNING_COUNT warnings during setup${NC}"
        echo "These are usually not critical - the system should work fine"
    fi
    
    echo
    echo -e "${GREEN}Happy coding with your smarter Claude! 🚀${NC}"
    echo
}

# Main setup flow
main() {
    echo -e "${BLUE}🔧 Smarter-Claude Setup Script${NC}"
    echo -e "${MAGENTA}Post-Clone Configuration and Installation${NC}"
    echo "This will configure smarter-claude in your ~/.claude directory"
    echo
    
    # Detect setup type
    if [ "$SETUP_TYPE" = "manual" ]; then
        echo -e "${CYAN}Manual setup mode detected${NC}"
        echo "Running from ~/.claude directory"
    else
        echo -e "${CYAN}Automated setup mode detected${NC}"
        echo "Running from source directory: $SCRIPT_DIR"
    fi
    echo
    
    # Check if resuming from previous attempt
    if check_previous_state; then
        PREVIOUS_STATE=$(cat "$INSTALL_STATE" 2>/dev/null || echo "unknown")
        log_info "Resuming from: $PREVIOUS_STATE"
    fi
    
    # Create ~/.claude directory first to ensure logs work
    mkdir -p "$CLAUDE_DIR" 2>/dev/null
    
    # Installation steps with state tracking
    local steps=(
        "validate_source_files"
        "check_prerequisites"
        "check_claude_code"
        "check_python"
        "check_disk_space"
        "ensure_claude_directory"
        "copy_source_files"
        "set_permissions"
        "install_dependencies"
        "configure_settings"
        "test_installation"
    )
    
    # Execute steps
    for step in "${steps[@]}"; do
        # Skip if already completed
        if [ -f "$INSTALL_STATE" ]; then
            CURRENT_STATE=$(cat "$INSTALL_STATE" 2>/dev/null)
            if [[ " ${steps[@]} " =~ " ${CURRENT_STATE} " ]]; then
                # Find if we should skip this step
                local skip=true
                for s in "${steps[@]}"; do
                    if [ "$s" = "$CURRENT_STATE" ]; then
                        skip=false
                    fi
                    if [ "$s" = "$step" ] && [ "$skip" = "true" ]; then
                        log_info "Skipping already completed: $step"
                        continue 2
                    fi
                done
            fi
        fi
        
        # Run the step
        echo
        log_progress "Step: $step"
        if ! $step; then
            log_error "Setup failed at step: $step"
            log_info "You can resume setup by running this script again"
            log_info "Check the log for details: $INSTALL_LOG"
            exit 1
        fi
    done
    
    # Show completion
    show_next_steps
    
    # Clean up installation files
    rm -f "$INSTALL_STATE" 2>/dev/null
    
    # Save summary to log
    echo >> "$INSTALL_LOG"
    echo "Setup completed at $(date)" >> "$INSTALL_LOG"
    echo "Setup type: $SETUP_TYPE" >> "$INSTALL_LOG"
    echo "Errors: $ERROR_COUNT, Warnings: $WARNING_COUNT" >> "$INSTALL_LOG"
}

# Handle interrupts gracefully
trap 'echo; log_error "Setup interrupted"; log_info "Run the script again to resume"; exit 130' INT TERM

# Run main function
main "$@"