# Smarter-Claude One-Line Installation Script for Windows
# Downloads repository and delegates to setup.ps1 for configuration
#
# Usage: irm https://raw.githubusercontent.com/okets/.claude/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Blue }
function Write-Success { Write-Host "[OK] $args" -ForegroundColor Green }
function Write-Warning { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Write-Err { Write-Host "[ERROR] $args" -ForegroundColor Red }

$CLAUDE_DIR = "$env:USERPROFILE\.claude"
$REPO_URL = "https://github.com/okets/.claude.git"

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Smarter-Claude Windows Installation" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Info "Checking prerequisites..."

# Check for git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Err "Git is not installed."
    Write-Host "  Please install Git from: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}
Write-Success "Git found"

# Check for Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Err "Python is not installed."
    Write-Host "  Please install Python 3.8+ from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}
$pythonVersion = python --version 2>&1
Write-Success "Python found: $pythonVersion"

# Check for uv (optional but recommended)
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Success "UV package manager found"
} else {
    Write-Warning "UV not installed (recommended for faster installs)"
    Write-Host "  Install with: irm https://astral.sh/uv/install.ps1 | iex" -ForegroundColor Yellow
}

# Check network connectivity
Write-Info "Checking network connectivity..."
try {
    $null = Invoke-WebRequest -Uri "https://github.com" -UseBasicParsing -TimeoutSec 10
    Write-Success "Network connectivity confirmed"
} catch {
    Write-Err "Cannot reach GitHub. Please check your internet connection."
    exit 1
}

# Backup existing .claude directory if it exists
if (Test-Path $CLAUDE_DIR) {
    $backupDir = "$CLAUDE_DIR.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Write-Warning "Existing .claude directory found"
    Write-Info "Creating backup at: $backupDir"
    Move-Item -Path $CLAUDE_DIR -Destination $backupDir
}

# Clone repository
Write-Info "Downloading smarter-claude..."
try {
    git clone --depth 1 $REPO_URL $CLAUDE_DIR 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Git clone failed"
    }

    # Remove .git directory (we don't need version control for user installation)
    Remove-Item -Path "$CLAUDE_DIR\.git" -Recurse -Force -ErrorAction SilentlyContinue

    Write-Success "Repository downloaded successfully"
} catch {
    Write-Err "Failed to download repository: $_"
    exit 1
}

# Run setup script (generates settings.json with Windows paths)
$setupScript = "$CLAUDE_DIR\setup.ps1"
if (Test-Path $setupScript) {
    Write-Info "Running setup script..."
    & powershell -ExecutionPolicy Bypass -File $setupScript
} else {
    Write-Warning "Setup script not found, skipping additional configuration"
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Open a new terminal"
Write-Host "  2. Navigate to any project: cd your-project"
Write-Host "  3. Start Claude Code: claude"
Write-Host ""
Write-Host "The smarter-claude hooks will automatically enhance your Claude experience!"
Write-Host ""
