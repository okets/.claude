# Smarter-Claude Setup Script for Windows
# Installs dependencies and configures the system
#
# Run after cloning the repository or as standalone setup

$ErrorActionPreference = "Continue"

function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Blue }
function Write-Success { Write-Host "[OK] $args" -ForegroundColor Green }
function Write-Warning { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Write-Err { Write-Host "[ERROR] $args" -ForegroundColor Red }

$CLAUDE_DIR = "$env:USERPROFILE\.claude"

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  Smarter-Claude Windows Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Install Python dependencies
Write-Info "Installing Python dependencies..."

$deps = @(
    "pygame",      # Cross-platform audio playback
    "psutil",      # Cross-platform process management
    "soundfile",   # Audio file handling for Kokoro TTS
    "python-dotenv" # Environment variable support
)

foreach ($dep in $deps) {
    Write-Host "  Installing $dep..." -NoNewline
    try {
        $output = pip install --user $dep 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host " OK" -ForegroundColor Green
        } else {
            Write-Host " SKIP" -ForegroundColor Yellow
        }
    } catch {
        Write-Host " FAIL" -ForegroundColor Red
    }
}

# Install Kokoro TTS (optional but recommended)
Write-Info "Checking Kokoro TTS..."
$kokoroDir = "$env:USERPROFILE\.kokoro-tts\models"

if (Test-Path "$kokoroDir\kokoro-v1.0.onnx") {
    Write-Success "Kokoro TTS already installed"
} else {
    Write-Info "Installing Kokoro TTS..."

    # Install kokoro-onnx package
    Write-Host "  Installing kokoro-onnx..." -NoNewline
    pip install --user kokoro-onnx 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK" -ForegroundColor Green
    } else {
        Write-Host " FAIL" -ForegroundColor Red
    }

    # Create models directory
    New-Item -ItemType Directory -Path $kokoroDir -Force | Out-Null

    # Download model files
    $modelUrl = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
    $voicesUrl = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

    Write-Host "  Downloading Kokoro model (this may take a few minutes)..." -NoNewline
    try {
        Invoke-WebRequest -Uri $modelUrl -OutFile "$kokoroDir\kokoro-v1.0.onnx" -UseBasicParsing
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " FAIL" -ForegroundColor Red
        Write-Warning "You can download manually later"
    }

    Write-Host "  Downloading voices..." -NoNewline
    try {
        Invoke-WebRequest -Uri $voicesUrl -OutFile "$kokoroDir\voices-v1.0.bin" -UseBasicParsing
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " FAIL" -ForegroundColor Red
    }
}

# Generate settings.json with Windows paths
Write-Info "Generating settings.json for Windows..."

$settingsFile = "$CLAUDE_DIR\settings.json"
$settingsContent = @'
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash(mkdir:*)",
      "Bash(uv:*)",
      "Bash(find:*)",
      "Bash(mv:*)",
      "Bash(grep:*)",
      "Bash(npm:*)",
      "Bash(ls:*)",
      "Bash(cp:*)",
      "Write",
      "Edit",
      "Bash(chmod:*)",
      "Bash(touch:*)",
      "Bash(powershell -Command:*)",
      "Bash(git add:*)",
      "Bash(python -m py_compile:*)"
    ],
    "deny": []
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run %USERPROFILE%\\.claude\\hooks\\pre_tool_use.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run %USERPROFILE%\\.claude\\hooks\\post_tool_use.py"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run %USERPROFILE%\\.claude\\hooks\\notification.py --notify"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run %USERPROFILE%\\.claude\\hooks\\stop.py"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run %USERPROFILE%\\.claude\\hooks\\subagent_stop.py"
          }
        ]
      }
    ]
  },
  "statusLine": {
    "type": "command",
    "command": "powershell -ExecutionPolicy Bypass -File %USERPROFILE%\\.claude\\statusline-command.ps1"
  }
}
'@

$settingsContent | Out-File -FilePath $settingsFile -Encoding utf8
Write-Success "settings.json generated with Windows paths"

# Configure default TTS settings
Write-Info "Configuring default settings..."

$globalSettings = "$CLAUDE_DIR\hooks\utils\smarter-claude-global.json"
if (-not (Test-Path $globalSettings)) {
    $defaultSettings = @{
        interaction_level = "concise"
        tts_enabled = $true
        tts_engine = "kokoro-am_puck"
        notification_sounds = $true
    } | ConvertTo-Json -Depth 2

    $defaultSettings | Out-File -FilePath $globalSettings -Encoding utf8
    Write-Success "Default TTS settings created"
} else {
    Write-Success "Settings already configured"
}

# Verify installation
Write-Host ""
Write-Info "Verifying installation..."

$checks = @(
    @{ Name = "Python dependencies"; Check = { python -c "import pygame, psutil, soundfile" 2>&1; $LASTEXITCODE -eq 0 } },
    @{ Name = "Hooks directory"; Check = { Test-Path "$CLAUDE_DIR\hooks" } },
    @{ Name = "Settings file"; Check = { Test-Path "$CLAUDE_DIR\settings.json" -or Test-Path "$CLAUDE_DIR\settings-windows.json" } }
)

$allPassed = $true
foreach ($check in $checks) {
    $result = & $check.Check
    if ($result) {
        Write-Host "  [PASS] $($check.Name)" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $($check.Name)" -ForegroundColor Red
        $allPassed = $false
    }
}

Write-Host ""
if ($allPassed) {
    Write-Success "Setup completed successfully!"
} else {
    Write-Warning "Setup completed with some issues. Check the failures above."
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Interaction level: concise"
Write-Host "  TTS engine: kokoro-am_echo (Echo voice)"
Write-Host ""
Write-Host "Customize with slash commands in Claude:" -ForegroundColor Cyan
Write-Host "  /smarter-claude_interaction_level verbose"
Write-Host "  /smarter-claude_voice puck"
Write-Host ""
