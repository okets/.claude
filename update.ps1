# Smarter-Claude Update Script for Windows
# Updates to the latest version while preserving user settings

$ErrorActionPreference = "Continue"

function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Blue }
function Write-Success { Write-Host "[OK] $args" -ForegroundColor Green }
function Write-Warning { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Write-Err { Write-Host "[ERROR] $args" -ForegroundColor Red }

$CLAUDE_DIR = "$env:USERPROFILE\.claude"
$REPO_URL = "https://api.github.com/repos/okets/.claude/releases/latest"

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "  Smarter-Claude Update" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check current version
$versionFile = "$CLAUDE_DIR\VERSION"
$currentVersion = "0.0.0"
if (Test-Path $versionFile) {
    $currentVersion = (Get-Content $versionFile -Raw).Trim()
}
Write-Info "Current version: $currentVersion"

# Get latest version from GitHub
Write-Info "Checking for updates..."
try {
    $release = Invoke-RestMethod -Uri $REPO_URL -UseBasicParsing
    $latestVersion = $release.tag_name -replace '^v', ''
    Write-Info "Latest version: $latestVersion"
} catch {
    Write-Err "Failed to check for updates: $_"
    exit 1
}

# Compare versions
if ($currentVersion -eq $latestVersion) {
    Write-Success "Already up to date!"
    exit 0
}

Write-Warning "Update available: $currentVersion -> $latestVersion"
Write-Host ""

# Prompt for confirmation
$confirm = Read-Host "Continue with update? (y/N)"
if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Write-Host "Update cancelled"
    exit 0
}

# Create backup
$backupDir = "$CLAUDE_DIR.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Write-Info "Creating backup at: $backupDir"
Copy-Item -Path $CLAUDE_DIR -Destination $backupDir -Recurse

# Preserve user settings
$preserveFiles = @(
    "hooks\utils\smarter-claude-global.json"
)

$preserved = @{}
foreach ($file in $preserveFiles) {
    $fullPath = Join-Path $CLAUDE_DIR $file
    if (Test-Path $fullPath) {
        $preserved[$file] = Get-Content $fullPath -Raw
    }
}

# Download update
$downloadUrl = "https://github.com/okets/.claude/archive/refs/tags/v$latestVersion.zip"
$tempZip = "$env:TEMP\smarter-claude-update.zip"
$tempDir = "$env:TEMP\smarter-claude-update"

try {
    Write-Info "Downloading update..."
    Invoke-WebRequest -Uri $downloadUrl -OutFile $tempZip -UseBasicParsing

    Write-Info "Extracting..."
    if (Test-Path $tempDir) {
        Remove-Item -Path $tempDir -Recurse -Force
    }
    Expand-Archive -Path $tempZip -DestinationPath $tempDir -Force

    # Find extracted directory
    $sourceDir = Get-ChildItem $tempDir -Directory | Select-Object -First 1

    # Update files (but preserve settings)
    Write-Info "Installing update..."

    # Update hooks
    if (Test-Path "$($sourceDir.FullName)\hooks") {
        Copy-Item -Path "$($sourceDir.FullName)\hooks" -Destination $CLAUDE_DIR -Recurse -Force
    }

    # Update commands
    if (Test-Path "$($sourceDir.FullName)\commands") {
        Copy-Item -Path "$($sourceDir.FullName)\commands" -Destination $CLAUDE_DIR -Recurse -Force
    }

    # Update VERSION file
    if (Test-Path "$($sourceDir.FullName)\VERSION") {
        Copy-Item -Path "$($sourceDir.FullName)\VERSION" -Destination $CLAUDE_DIR -Force
    }

    # Restore preserved settings
    foreach ($file in $preserved.Keys) {
        $fullPath = Join-Path $CLAUDE_DIR $file
        $parentDir = Split-Path $fullPath -Parent
        if (-not (Test-Path $parentDir)) {
            New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
        }
        $preserved[$file] | Out-File -FilePath $fullPath -Encoding utf8 -NoNewline
    }

    Write-Host ""
    Write-Success "Successfully updated to v$latestVersion!"
    Write-Host ""
    Write-Host "Backup saved at: $backupDir" -ForegroundColor Blue
    Write-Host "Remove backup with: Remove-Item -Recurse '$backupDir'" -ForegroundColor Blue
    Write-Host ""

} catch {
    Write-Err "Update failed: $_"
    Write-Info "Restoring from backup..."

    Remove-Item -Path $CLAUDE_DIR -Recurse -Force -ErrorAction SilentlyContinue
    Move-Item -Path $backupDir -Destination $CLAUDE_DIR

    Write-Success "Restored previous version"
    exit 1
} finally {
    # Cleanup
    Remove-Item -Path $tempZip -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
