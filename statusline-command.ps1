# Smarter-Claude Status Line Script for Windows
# Displays current smarter-claude status in Claude Code status bar

$ErrorActionPreference = "SilentlyContinue"

# Get .claude directory
$CLAUDE_DIR = "$env:USERPROFILE\.claude"

# Try to find project-specific settings first, then global
$projectRoot = Get-Location
$settingsFile = Join-Path $projectRoot ".claude\smarter-claude\smarter-claude.json"

if (-not (Test-Path $settingsFile)) {
    $settingsFile = Join-Path $CLAUDE_DIR "hooks\utils\smarter-claude-global.json"
}

# Default values
$interactionLevel = "concise"
$ttsEngine = "kokoro"

# Try to read settings
if (Test-Path $settingsFile) {
    try {
        $settings = Get-Content $settingsFile -Raw | ConvertFrom-Json
        if ($settings.interaction_level) {
            $interactionLevel = $settings.interaction_level
        }
        if ($settings.tts_engine) {
            $ttsEngine = $settings.tts_engine
        }
    } catch {
        # Ignore errors, use defaults
    }
}

# Build status string
$status = "SC: $interactionLevel"

# Add TTS status indicator
$kokoroModels = "$env:USERPROFILE\.kokoro-tts\models\kokoro-v1.0.onnx"
if (Test-Path $kokoroModels) {
    $status += " | TTS: OK"
} else {
    $status += " | TTS: --"
}

Write-Output $status
