#!/bin/bash

# Read JSON input from stdin
input=$(cat)

# ANSI escape codes
RESET="\033[0m"
BOLD="\033[1m"
DIM="\033[2m"

# Foreground colors
FG_BLACK="\033[30m"
FG_WHITE="\033[97m"
FG_CYAN="\033[36m"
FG_YELLOW="\033[33m"
FG_MAGENTA="\033[35m"
FG_BLUE="\033[34m"
FG_GREEN="\033[32m"
FG_ORANGE="\033[38;5;208m"
FG_RED="\033[31m"
FG_GRAY="\033[90m"

# Sunset theme colors
FG_SUNSET_GOLD="\033[38;5;220m"
FG_SUNSET_CORAL="\033[38;5;209m"
FG_SUNSET_PEACH="\033[38;5;216m"
BG_SUNSET_PURPLE="\033[48;5;53m"
BG_SUNSET_WINE="\033[48;5;52m"
BG_SUNSET_ORANGE="\033[48;5;166m"

# Separators
SEP="${FG_GRAY}◆${RESET}"

# 1. Current directory basename (cyan, bold)
cwd=$(echo "$input" | jq -r '.workspace.current_dir')
cwd_basename=$(basename "$cwd")
cwd_display="${BOLD}${FG_CYAN}${cwd_basename}${RESET}"

# 2. Project directory basename (magenta)
project_dir=$(echo "$input" | jq -r '.workspace.project_dir // empty')
if [ -n "$project_dir" ]; then
    project_name=$(basename "$project_dir")
    # Only show if different from cwd
    if [ "$project_name" != "$cwd_basename" ]; then
        project_display=" ${FG_MAGENTA}${BOLD}⌂${project_name}${RESET}"
    else
        project_display=""
    fi
else
    project_display=""
fi

# 3. Short model name with version (model-specific colors) + hotkey hint
model_id=$(echo "$input" | jq -r '.model.id')
hotkey="${DIM}${FG_GRAY}(switch ⌥P)${RESET}"
case "$model_id" in
    *opus-4-5*|*opus-4.5*)
        model_name="${BOLD}${FG_ORANGE}◈ Opus 4.5${RESET} ${hotkey}"
        ;;
    *opus-4*|*opus4*)
        model_name="${BOLD}${FG_ORANGE}◈ Opus 4${RESET} ${hotkey}"
        ;;
    *opus*)
        model_name="${BOLD}${FG_ORANGE}◈ Opus${RESET} ${hotkey}"
        ;;
    *sonnet-4-5*|*sonnet-4.5*)
        model_name="${BOLD}${FG_BLUE}◈ Sonnet 4.5${RESET} ${hotkey}"
        ;;
    *sonnet-4*|*sonnet4*)
        model_name="${BOLD}${FG_BLUE}◈ Sonnet 4${RESET} ${hotkey}"
        ;;
    *sonnet-3-5*|*sonnet-3.5*)
        model_name="${BOLD}${FG_BLUE}◈ Sonnet 3.5${RESET} ${hotkey}"
        ;;
    *sonnet*)
        model_name="${BOLD}${FG_BLUE}◈ Sonnet${RESET} ${hotkey}"
        ;;
    *haiku-3-5*|*haiku-3.5*)
        model_name="${BOLD}${FG_GREEN}◈ Haiku 3.5${RESET} ${hotkey}"
        ;;
    *haiku*)
        model_name="${BOLD}${FG_GREEN}◈ Haiku${RESET} ${hotkey}"
        ;;
    *)
        display_name=$(echo "$input" | jq -r '.model.display_name' | awk '{print $1}')
        model_name="${BOLD}${FG_WHITE}◈ ${display_name}${RESET} ${hotkey}"
        ;;
esac

# 4. Context window percentage with color coding and bar
usage=$(echo "$input" | jq '.context_window.current_usage')
if [ "$usage" != "null" ]; then
    current_input=$(echo "$usage" | jq '.input_tokens // 0')
    cache_creation=$(echo "$usage" | jq '.cache_creation_input_tokens // 0')
    cache_read=$(echo "$usage" | jq '.cache_read_input_tokens // 0')
    current_total=$((current_input + cache_creation + cache_read))
    window_size=$(echo "$input" | jq '.context_window.context_window_size')
    pct=$((current_total * 100 / window_size))

    # Color coding: green < 50%, orange 50-80%, red > 80%
    if [ "$pct" -lt 50 ]; then
        pct_color="${FG_GREEN}"
    elif [ "$pct" -lt 80 ]; then
        pct_color="${FG_ORANGE}"
    else
        pct_color="${FG_RED}"
    fi

    # Mini progress bar (5 chars)
    filled=$((pct / 20))
    empty=$((5 - filled))
    bar=""
    for ((i=0; i<filled; i++)); do bar="${bar}${pct_color}▰"; done
    for ((i=0; i<empty; i++)); do bar="${bar}${FG_GRAY}▱"; done

    context_display="${bar}${RESET} ${BOLD}${pct_color}${pct}%${RESET}"
else
    context_display="${FG_GRAY}▱▱▱▱▱ 0%${RESET}"
fi

# 5. Current input/output tokens (blue for in, yellow for out)
if [ "$usage" != "null" ]; then
    input_tokens=$(echo "$usage" | jq '.input_tokens // 0')
    output_tokens=$(echo "$usage" | jq '.output_tokens // 0')
    token_display="${FG_BLUE}↓${input_tokens}${RESET} ${FG_YELLOW}↑${output_tokens}${RESET}"
else
    token_display="${FG_GRAY}↓0 ↑0${RESET}"
fi

# 6. Cache stats (dim, with icons) - format large numbers with k
format_k() {
    local n=$1
    if [ "$n" -ge 1000 ]; then
        echo "$((n / 1000))k"
    else
        echo "$n"
    fi
}

if [ "$usage" != "null" ]; then
    cache_creation=$(echo "$usage" | jq '.cache_creation_input_tokens // 0')
    cache_read=$(echo "$usage" | jq '.cache_read_input_tokens // 0')
    if [ "$cache_read" -gt 0 ] || [ "$cache_creation" -gt 0 ]; then
        cache_display="${DIM}${FG_CYAN}⚡+$(format_k $cache_creation)${RESET}${DIM}${FG_GREEN}/$(format_k $cache_read)${RESET}"
    else
        cache_display="${DIM}${FG_GRAY}⚡0/0${RESET}"
    fi
else
    cache_display="${DIM}${FG_GRAY}⚡0/0${RESET}"
fi

# 7. Session totals
total_in=$(echo "$input" | jq '.context_window.total_input_tokens // 0')
total_out=$(echo "$input" | jq '.context_window.total_output_tokens // 0')
session_total=$((total_in + total_out))
session_display="${FG_MAGENTA}Σ$(format_k $session_total)${RESET}"

# 8. TTS Voice status (single compact segment based on interaction level)
CLAUDE_DIR="$HOME/.claude"
project_settings="$cwd/.claude/smarter-claude/smarter-claude.json"
global_settings="$CLAUDE_DIR/hooks/utils/smarter-claude-global.json"

# Colors for TTS display
FG_ROYAL_BLUE="\033[38;5;69m"
FG_LIGHT_ORANGE="\033[38;5;215m"

tts_display="${FG_GRAY}TTS:off${RESET}"
settings_file=""

if [ -f "$project_settings" ]; then
    settings_file="$project_settings"
elif [ -f "$global_settings" ]; then
    settings_file="$global_settings"
fi

if [ -n "$settings_file" ]; then
    level=$(jq -r '.interaction_level // "concise"' "$settings_file" 2>/dev/null)
    tts_engine=$(jq -r '.tts_engine // ""' "$settings_file" 2>/dev/null)

    case "$level" in
        silent)
            tts_display="${FG_GRAY}TTS:off${RESET}"
            ;;
        quiet)
            tts_display="${FG_LIGHT_ORANGE}TTS:beep${RESET}"
            ;;
        concise|verbose)
            # Extract just the voice name
            voice_name="on"
            if [ -n "$tts_engine" ] && [ "$tts_engine" != "null" ]; then
                if [[ "$tts_engine" =~ kokoro-[abm][fm]_(.+) ]]; then
                    voice_name="${BASH_REMATCH[1]}"
                elif [[ "$tts_engine" =~ macos-(.+) ]]; then
                    voice_name="${BASH_REMATCH[1]}"
                elif [[ "$tts_engine" =~ windows-(.+) ]]; then
                    voice_name="${BASH_REMATCH[1]}"
                else
                    voice_name="$tts_engine"
                fi
            fi
            tts_display="${FG_ROYAL_BLUE}TTS:${voice_name}${RESET}"
            ;;
        *)
            tts_display="${FG_GRAY}TTS:off${RESET}"
            ;;
    esac
fi

# Assemble status line - only include project separator if project exists
if [ -n "$project_display" ]; then
    printf "%b%b %b %b %b %b %b %b %b %b %b %b\n" \
        "$cwd_display" \
        "$project_display" \
        "$SEP" \
        "$model_name" \
        "$SEP" \
        "$context_display" \
        "$SEP" \
        "$token_display $cache_display" \
        "$SEP" \
        "$session_display" \
        "$SEP" \
        "$tts_display"
else
    printf "%b %b %b %b %b %b %b %b %b %b %b\n" \
        "$cwd_display" \
        "$SEP" \
        "$model_name" \
        "$SEP" \
        "$context_display" \
        "$SEP" \
        "$token_display $cache_display" \
        "$SEP" \
        "$session_display" \
        "$SEP" \
        "$tts_display"
fi
