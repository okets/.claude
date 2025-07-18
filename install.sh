#!/bin/bash
# Smarter-Claude Installation Script
# Automatically sets up smarter-claude in your ~/.claude directory

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

# Check if Claude Code is installed
check_claude_code() {
    log_info "Checking if Claude Code is installed..."
    if ! command -v claude &> /dev/null; then
        log_error "Claude Code is not installed or not in PATH"
        log_info "Please install Claude Code first: https://docs.anthropic.com/en/docs/claude-code"
        exit 1
    fi
    
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    log_success "Claude Code found: $CLAUDE_VERSION"
}

# Check if ~/.claude directory exists
check_claude_directory() {
    log_info "Checking ~/.claude directory..."
    
    CLAUDE_DIR="$HOME/.claude"
    if [ ! -d "$CLAUDE_DIR" ]; then
        log_warning "~/.claude directory not found"
        log_info "Creating ~/.claude directory..."
        mkdir -p "$CLAUDE_DIR"
    fi
    
    log_success "~/.claude directory ready"
}

# Backup existing installation
backup_existing() {
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
}

# Install Python dependencies and TTS voices
install_dependencies() {
    log_info "Installing TTS dependencies and voices..."
    
    # Use the voice manager for comprehensive installation
    VOICE_MANAGER="$HOME/.claude/hooks/utils/manage_voices.py"
    
    # Install all supported voices automatically
    if [ -f "$VOICE_MANAGER" ]; then
        log_info "Using voice manager for automatic installation..."
        python3 "$VOICE_MANAGER" install-all
        
        # Get recommended voice
        RECOMMENDED=$(python3 "$VOICE_MANAGER" recommend 2>/dev/null | grep "Recommended voice engine:" | cut -d: -f2 | xargs)
        if [ -n "$RECOMMENDED" ]; then
            log_success "Recommended voice: $RECOMMENDED"
            # This will be set in configure_settings()
        fi
    else
        # Fallback to manual installation
        log_info "Installing dependencies manually..."
        
        # Check if uv is available for Coqui TTS
        if command -v uv &> /dev/null; then
            log_info "Installing Coqui TTS for high-quality voices..."
            if uv tool install coqui-tts; then
                log_success "Coqui TTS installed successfully"
            else
                log_warning "Coqui TTS installation failed (optional)"
            fi
        else
            log_warning "uv not found - attempting to install..."
            if [[ "$OSTYPE" == "darwin"* ]]; then
                if command -v brew &> /dev/null; then
                    log_info "Installing uv via Homebrew..."
                    brew install uv && uv tool install coqui-tts
                else
                    log_info "Installing uv via curl..."
                    curl -LsSf https://astral.sh/uv/install.sh | sh
                    export PATH="$HOME/.local/bin:$PATH"
                    uv tool install coqui-tts
                fi
            else
                log_info "Installing uv via curl..."
                curl -LsSf https://astral.sh/uv/install.sh | sh
                export PATH="$HOME/.local/bin:$PATH"
                uv tool install coqui-tts
            fi
        fi
        
        # Install ffmpeg for male voice processing
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
        
        # Install pyttsx3 as fallback
        log_info "Installing pyttsx3 fallback voice..."
        if python3 -m pip install pyttsx3; then
            log_success "pyttsx3 installed successfully"
        else
            log_warning "pyttsx3 installation failed"
        fi
    fi
}

# Download and install smarter-claude
install_smarter_claude() {
    log_info "Installing smarter-claude..."
    
    CLAUDE_DIR="$HOME/.claude"
    TEMP_DIR=$(mktemp -d)
    
    # Clone the repository to temp directory
    log_info "Downloading from GitHub..."
    if git clone https://github.com/okets/.claude.git "$TEMP_DIR"; then
        log_success "Download completed"
    else
        log_error "Failed to download smarter-claude"
        log_info "Please check your internet connection and try again"
        exit 1
    fi
    
    # Copy files to ~/.claude
    log_info "Installing files..."
    cp -r "$TEMP_DIR"/hooks "$CLAUDE_DIR/"
    cp -r "$TEMP_DIR"/docs "$CLAUDE_DIR/"
    cp -r "$TEMP_DIR"/commands "$CLAUDE_DIR/" 2>/dev/null || log_warning "No commands directory found - slash commands may not be available"
    cp "$TEMP_DIR"/README.md "$CLAUDE_DIR/"
    cp "$TEMP_DIR"/CONTEXTUAL-LOGGING-IMPLEMENTATION-PLAN.md "$CLAUDE_DIR/"
    
    # Create smarter-claude directory and copy voice manager
    mkdir -p "$CLAUDE_DIR/.claude/smarter-claude"
    cp "$TEMP_DIR"/hooks/utils/manage_voices.py "$CLAUDE_DIR/hooks/utils/" 2>/dev/null || true
    
    # Make hooks and scripts executable
    chmod +x "$CLAUDE_DIR"/hooks/*.py
    chmod +x "$CLAUDE_DIR"/.claude/smarter-claude/*.py 2>/dev/null || true
    
    # Clean up
    rm -rf "$TEMP_DIR"
    
    log_success "Smarter-claude installed successfully"
}

# Configure default settings
configure_settings() {
    log_info "Configuring default settings..."
    
    SETTINGS_SCRIPT="$HOME/.claude/hooks/utils/manage_settings.py"
    VOICE_MANAGER="$HOME/.claude/hooks/utils/manage_voices.py"
    
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
                if command -v tts &> /dev/null; then
                    python3 "$SETTINGS_SCRIPT" set tts_engine coqui-female
                    log_success "Configured to use Coqui female voice"
                elif [[ "$OSTYPE" == "darwin"* ]]; then
                    python3 "$SETTINGS_SCRIPT" set tts_engine macos-female
                    log_success "Configured to use macOS female voice"
                else
                    python3 "$SETTINGS_SCRIPT" set tts_engine pyttsx3
                    log_success "Configured to use pyttsx3 voice"
                fi
            fi
        else
            # Original fallback logic
            if command -v tts &> /dev/null; then
                python3 "$SETTINGS_SCRIPT" set tts_engine coqui-female
                log_success "Configured to use Coqui female voice"
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
    log_info "Testing installation..."
    
    # Check if hooks are executable
    HOOKS_DIR="$HOME/.claude/hooks"
    for hook in notification.py post_tool_use.py pre_tool_use.py stop.py; do
        if [ -x "$HOOKS_DIR/$hook" ]; then
            log_success "$hook is executable"
        else
            log_error "$hook is not executable"
            return 1
        fi
    done
    
    # Test Python imports
    if python3 -c "from hooks.utils.contextual_db import ContextualDB; print('Import test passed')" 2>/dev/null; then
        log_success "Python imports working"
    else
        log_warning "Python import test failed - check Python environment"
    fi
    
    # Check if slash commands are installed
    COMMANDS_DIR="$HOME/.claude/commands"
    if [ -d "$COMMANDS_DIR" ]; then
        COMMAND_COUNT=$(ls "$COMMANDS_DIR"/*.md 2>/dev/null | wc -l)
        if [ "$COMMAND_COUNT" -gt 0 ]; then
            log_success "Slash commands installed ($COMMAND_COUNT commands available)"
        else
            log_warning "Commands directory exists but no .md files found"
        fi
    else
        log_warning "Commands directory not found - slash commands not available"
    fi
    
    log_success "Installation test completed"
}

# Show next steps
show_next_steps() {
    echo
    log_success "🎉 Smarter-Claude installation completed!"
    echo
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Start Claude Code in any project: ${YELLOW}claude${NC}"
    echo "2. After your first interaction, check: ${YELLOW}ls .claude/smarter-claude/${NC}"
    echo "3. You should see a database file created automatically"
    echo
    echo -e "${BLUE}Configuration:${NC}"
    echo "• Interaction level: ${YELLOW}concise${NC} (balanced feedback)"
    echo "• TTS engine: ${YELLOW}$(python3 ~/.claude/hooks/utils/manage_settings.py get tts_engine 2>/dev/null || echo 'default')${NC}"
    echo
    echo -e "${BLUE}Customize settings:${NC}"
    echo "• Change interaction level: ${YELLOW}/smarter-claude_interaction_level verbose${NC}"
    echo "• Change TTS voice: ${YELLOW}/smarter-claude_voice coqui-male${NC}"
    echo "• Update smarter-claude: ${YELLOW}/smarter-claude_update${NC}"
    echo "• Or use CLI: ${YELLOW}python ~/.claude/hooks/utils/manage_settings.py set <key> <value>${NC}"
    echo
    echo -e "${BLUE}Need help?${NC}"
    echo "• Read: ${YELLOW}~/.claude/docs/GETTING_STARTED.md${NC}"
    echo "• Troubleshoot: ${YELLOW}~/.claude/docs/TROUBLESHOOTING.md${NC}"
    echo "• Or just ask Claude: ${YELLOW}'Help me configure smarter-claude'${NC}"
    echo
}

# Main installation flow
main() {
    echo -e "${BLUE}🤖 Smarter-Claude Installation Script${NC}"
    echo "This will install smarter-claude to your ~/.claude directory"
    echo
    
    check_claude_code
    check_claude_directory
    backup_existing
    install_dependencies
    install_smarter_claude
    configure_settings
    test_installation
    show_next_steps
}

# Run main function
main "$@"