# Smarter-Claude Status Line Script for Windows
# Rich statusline matching macOS style

$ErrorActionPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ANSI escape codes (compatible with PowerShell 5.1+)
$ESC = [char]27
$RESET = "$ESC[0m"
$BOLD = "$ESC[1m"
$DIM = "$ESC[2m"

# Foreground colors
$FG_WHITE = "$ESC[97m"
$FG_CYAN = "$ESC[36m"
$FG_YELLOW = "$ESC[33m"
$FG_MAGENTA = "$ESC[35m"
$FG_BLUE = "$ESC[34m"
$FG_GREEN = "$ESC[32m"
$FG_ORANGE = "$ESC[38;5;208m"
$FG_RED = "$ESC[31m"
$FG_GRAY = "$ESC[90m"
$FG_ROYAL_BLUE = "$ESC[38;5;69m"
$FG_LIGHT_ORANGE = "$ESC[38;5;215m"

# Unicode symbols
$SYM_DIAMOND = [char]0x25C6      # ◆
$SYM_MODEL = [char]0x25C8        # ◈
$SYM_HOME = [char]0x2302         # ⌂
$SYM_FILLED = [char]0x25B0       # ▰
$SYM_EMPTY = [char]0x25B1        # ▱
$SYM_DOWN = [char]0x2193         # ↓
$SYM_UP = [char]0x2191           # ↑
$SYM_LIGHTNING = [char]0x26A1    # ⚡
$SYM_SIGMA = [char]0x03A3       # Σ
$SYM_SPEAK = [char]::ConvertFromUtf32(0x1F5E3)  # 🗣️ (speaking head)

# Superscript hotkey hint ⁽ᴬᴸᵀ⁺ᴾ⁾
$SYM_SUP_LPAREN = [char]0x207D   # ⁽
$SYM_SUP_A = [char]::ConvertFromUtf32(0x1D2C)   # ᴬ
$SYM_SUP_L = [char]::ConvertFromUtf32(0x1D38)   # ᴸ
$SYM_SUP_T = [char]::ConvertFromUtf32(0x1D40)   # ᵀ
$SYM_SUP_PLUS = [char]0x207A    # ⁺
$SYM_SUP_P = [char]::ConvertFromUtf32(0x1D3E)   # ᴾ
$SYM_SUP_RPAREN = [char]0x207E  # ⁾
$SYM_HOTKEY = "${SYM_SUP_LPAREN}${SYM_SUP_A}${SYM_SUP_L}${SYM_SUP_T}${SYM_SUP_PLUS}${SYM_SUP_P}${SYM_SUP_RPAREN}"

# Separator (no trailing space - parts handle their own spacing)
$SEP = "${FG_GRAY}${SYM_DIAMOND}${RESET}"

# Try to read JSON input from stdin (non-blocking)
$data = $null
try {
    $input_json = @($input) -join "`n"
    if (-not $input_json) {
        $stdin = [Console]::In
        if ($stdin.Peek() -ne -1) {
            $input_json = $stdin.ReadToEnd()
        }
    }
    if ($input_json) {
        $data = $input_json | ConvertFrom-Json
    }
} catch {
    $data = $null
}

# Helper function to format large numbers with k
function Format-K($n) {
    if ($n -ge 1000) { return "$([math]::Floor($n / 1000))k" }
    else { return "$n" }
}

# Build status components
$parts = @()

# 1. Current directory basename (cyan, bold)
if ($data -and $data.workspace.current_dir) {
    $cwd_basename = Split-Path $data.workspace.current_dir -Leaf
    $cwd_part = "${BOLD}${FG_CYAN}${cwd_basename}${RESET}"
    $parts += $cwd_part

    # Project directory (magenta) if different
    if ($data.workspace.project_dir) {
        $project_name = Split-Path $data.workspace.project_dir -Leaf
        if ($project_name -ne $cwd_basename) {
            $parts += " ${FG_MAGENTA}${BOLD}${SYM_HOME}${project_name}${RESET}"
        }
    }
}

# 2. Model name with symbol and hotkey hint
if ($data -and $data.model.id) {
    $model_id = $data.model.id
    $hotkey = "${DIM}${FG_GRAY}${SYM_HOTKEY}${RESET}"
    $model_display = ""

    if ($model_id -match "opus-4-5|opus-4\.5") {
        $model_display = "${BOLD}${FG_ORANGE}Opus 4.5${RESET}${hotkey}"
    } elseif ($model_id -match "opus-4|opus4") {
        $model_display = "${BOLD}${FG_ORANGE}Opus 4${RESET}${hotkey}"
    } elseif ($model_id -match "opus") {
        $model_display = "${BOLD}${FG_ORANGE}Opus${RESET}${hotkey}"
    } elseif ($model_id -match "sonnet-4-5|sonnet-4\.5") {
        $model_display = "${BOLD}${FG_BLUE}Sonnet 4.5${RESET}${hotkey}"
    } elseif ($model_id -match "sonnet-4|sonnet4") {
        $model_display = "${BOLD}${FG_BLUE}Sonnet 4${RESET}${hotkey}"
    } elseif ($model_id -match "sonnet") {
        $model_display = "${BOLD}${FG_BLUE}Sonnet${RESET}${hotkey}"
    } elseif ($model_id -match "haiku") {
        $model_display = "${BOLD}${FG_GREEN}Haiku${RESET}${hotkey}"
    } else {
        $model_display = "${BOLD}${FG_WHITE}$($data.model.display_name)${RESET}${hotkey}"
    }
    $parts += " $model_display"
}

# 3. Context window percentage with bar
if ($data -and $data.context_window.current_usage) {
    $usage = $data.context_window.current_usage
    $current_input = if ($usage.input_tokens) { $usage.input_tokens } else { 0 }
    $cache_creation = if ($usage.cache_creation_input_tokens) { $usage.cache_creation_input_tokens } else { 0 }
    $cache_read = if ($usage.cache_read_input_tokens) { $usage.cache_read_input_tokens } else { 0 }
    $current_total = $current_input + $cache_creation + $cache_read
    $window_size = $data.context_window.context_window_size

    if ($window_size -gt 0) {
        $pct = [math]::Floor($current_total * 100 / $window_size)

        if ($pct -lt 50) { $pct_color = $FG_GREEN }
        elseif ($pct -lt 80) { $pct_color = $FG_ORANGE }
        else { $pct_color = $FG_RED }

        # Mini progress bar
        $filled = [math]::Floor($pct / 20)
        $empty = 5 - $filled
        $bar = ("${pct_color}${SYM_FILLED}" * $filled) + ("${FG_GRAY}${SYM_EMPTY}" * $empty)

        $parts += " ${bar}${RESET} ${BOLD}${pct_color}${pct}%${RESET}"
    }
}

# 4. Input/output tokens with arrows + cache stats
if ($data -and $data.context_window.current_usage) {
    $usage = $data.context_window.current_usage
    $in_tokens = if ($usage.input_tokens) { $usage.input_tokens } else { 0 }
    $out_tokens = if ($usage.output_tokens) { $usage.output_tokens } else { 0 }

    $in_fmt = Format-K $in_tokens
    $out_fmt = Format-K $out_tokens
    $token_part = "${FG_BLUE}${SYM_DOWN}${in_fmt}${RESET}${FG_YELLOW}${SYM_UP}${out_fmt}${RESET}"

    # Cache stats
    $cache_creation = if ($usage.cache_creation_input_tokens) { $usage.cache_creation_input_tokens } else { 0 }
    $cache_read = if ($usage.cache_read_input_tokens) { $usage.cache_read_input_tokens } else { 0 }
    if ($cache_read -gt 0 -or $cache_creation -gt 0) {
        $cc_fmt = Format-K $cache_creation
        $cr_fmt = Format-K $cache_read
        $token_part += " ${DIM}${FG_CYAN}${SYM_LIGHTNING}+${cc_fmt}${RESET}${DIM}${FG_GREEN}/${cr_fmt}${RESET}"
    }

    # 5. Session totals with sigma - combine with tokens
    if ($data.context_window) {
        $total_in = if ($data.context_window.total_input_tokens) { $data.context_window.total_input_tokens } else { 0 }
        $total_out = if ($data.context_window.total_output_tokens) { $data.context_window.total_output_tokens } else { 0 }
        $session_total = $total_in + $total_out
        if ($session_total -gt 0) {
            $sess_fmt = Format-K $session_total
            $token_part += " ${FG_MAGENTA}${SYM_SIGMA}${sess_fmt}${RESET}"
        }
    }
    $parts += " $token_part"
}

# 6. TTS status based on interaction level
$CLAUDE_DIR = "$env:USERPROFILE\.claude"
$projectRoot = Get-Location
$settingsFile = Join-Path $projectRoot ".claude\smarter-claude\smarter-claude.json"

if (-not (Test-Path $settingsFile)) {
    $settingsFile = Join-Path $CLAUDE_DIR "hooks\utils\smarter-claude-global.json"
}

$tts_display = "${FG_GRAY}${SYM_SPEAK} off${RESET}"
if (Test-Path $settingsFile) {
    try {
        $settings = Get-Content $settingsFile -Raw | ConvertFrom-Json
        $level = if ($settings.interaction_level) { $settings.interaction_level } else { "concise" }

        switch ($level) {
            "silent" {
                $tts_display = "${FG_GRAY}${SYM_SPEAK} off${RESET}"
            }
            "quiet" {
                $tts_display = "${FG_LIGHT_ORANGE}${SYM_SPEAK} beep${RESET}"
            }
            { $_ -in "concise", "verbose" } {
                $engine = $settings.tts_engine
                $voice_name = "on"
                if ($engine) {
                    if ($engine -match "kokoro-[abm][fm]_(.+)") {
                        $voice_name = $Matches[1]
                    } elseif ($engine -match "macos-(.+)") {
                        $voice_name = $Matches[1]
                    } elseif ($engine -match "windows-(.+)") {
                        $voice_name = $Matches[1]
                    } else {
                        $voice_name = $engine
                    }
                }
                $tts_display = "${FG_ROYAL_BLUE}${SYM_SPEAK} ${voice_name}${RESET}"
            }
            default {
                $tts_display = "${FG_GRAY}${SYM_SPEAK} off${RESET}"
            }
        }
    } catch {
        $tts_display = "${FG_GRAY}${SYM_SPEAK} ?${RESET}"
    }
}
$parts += " $tts_display"

# Output the status line
if ($parts.Count -gt 0) {
    Write-Output ($parts -join "$SEP")
} else {
    Write-Output "StatusLine Error"
}
