# 🔧 Troubleshooting Smarter-Claude

> **Ask Claude to fix it! No manual debugging needed.**

[![Claude Powered](https://img.shields.io/badge/🤖_Claude-Powered_Fixes-purple)](../README.md)
[![Zero Friction](https://img.shields.io/badge/⚡_Zero-Friction-green)](../README.md)
[![Manual Backup](https://img.shields.io/badge/🛠️_Manual-Commands_Available-gray)](#manual-troubleshooting)

## 🤖 The Claude Way

**Just copy and paste these prompts into your Claude Code session:**

💡 **Need manual commands?** Jump to [Manual Troubleshooting](#manual-troubleshooting) at the bottom.

### Installation Issues

#### Installation Script Failed
**Symptom**: The one-line installation script doesn't work

**Ask Claude to fix**:
```
The smarter-claude installation script failed. Can you help me troubleshoot what went wrong? Please check if Claude Code is installed, if I have the right permissions, and guide me through a manual installation if needed.
```

📖 [Manual steps](#installation-script-failed-manual)

#### Hook Files Not Found
**Symptom**: Claude Code starts but no database files are created

**Ask Claude to fix**:
```
Check if my smarter-claude hooks are properly installed. Look for the hook files in ~/.claude/hooks/ and verify they're executable. If anything is missing or broken, please fix it.
```

📖 [Manual steps](#hook-files-not-found-manual)

#### Python Import Errors
**Symptom**: Error messages about missing modules

**Ask Claude to fix**:
```
I'm getting Python import errors with smarter-claude hooks. Can you check the hook file structure and Python paths? Fix any import issues you find.
```

📖 [Manual steps](#python-import-errors-manual)

### TTS Issues

#### Coqui TTS Not Working
**Symptom**: TTS falls back to system voice or no audio

**Ask Claude to fix**:
```
My smarter-claude TTS isn't working properly - it's not using the Coqui voice I configured. Can you check if Coqui TTS is installed correctly and test the TTS system? If needed, please install or fix the Coqui TTS setup.
```

📖 [Manual steps](#coqui-tts-not-working-manual)

#### Male Voice Sounds Wrong
**Symptom**: Male voice is too high-pitched or distorted

**Ask Claude to fix**:
```
The male TTS voice in smarter-claude sounds wrong - it's too high-pitched or distorted. Can you check if ffmpeg is installed properly and fix the male voice audio processing?
```

📖 [Manual steps](#male-voice-sounds-wrong-manual)

#### No Audio Output
**Symptom**: No sound from any TTS engine

**Ask Claude to fix**:
```
I'm not getting any audio from smarter-claude TTS. Can you check my TTS settings, interaction level, and audio system? Please diagnose why there's no sound and fix it.
```

📖 [Manual steps](#no-audio-output-manual)

### Database Issues

#### Database Not Created
**Symptom**: No `smarter-claude.db` file in project

**Ask Claude to fix**:
```
My smarter-claude database isn't being created in this project. Can you check the project detection logic and ensure the database directory is set up correctly? Create the database structure if needed.
```

📖 [Manual steps](#database-not-created-manual)

#### Permission Denied on Database
**Symptom**: SQLite permission errors

**Ask Claude to fix**:
```
I'm getting permission errors with the smarter-claude database. Can you check and fix the file permissions for the database and its directory?
```

📖 [Manual steps](#permission-denied-on-database-manual)

#### Corrupted Database
**Symptom**: SQLite errors when querying

**Ask Claude to fix**:
```
My smarter-claude database seems corrupted - I'm getting SQLite errors. Can you check the database integrity and either repair it or recreate it safely? Please backup any existing data first.
```

📖 [Manual steps](#corrupted-database-manual)

### Notification Issues

#### Notifications Not Appearing
**Symptom**: No TTS announcements during Claude Code usage

**Ask Claude to fix**:
```
I'm not getting any TTS notifications from smarter-claude during our conversation. Can you check the notification hook system and my interaction level settings? Test and fix the notification system.
```

📖 [Manual steps](#notifications-not-appearing-manual)

#### Wrong Notification Format
**Symptom**: Garbled or incorrect notification messages

**Ask Claude to fix**:
```
The smarter-claude notifications sound garbled or have the wrong format. Can you check the notification message formatting and transcript parsing? Fix any issues with how user requests are being extracted and announced.
```

📖 [Manual steps](#wrong-notification-format-manual)

### Performance Issues

#### Slow Hook Execution
**Symptom**: Claude Code feels sluggish

**Ask Claude to fix**:
```
Claude Code is running slowly, possibly due to smarter-claude hooks taking too long. Can you check hook execution performance and optimize the settings? Maybe reduce the interaction level if needed.
```

📖 [Manual steps](#slow-hook-execution-manual)

#### Large Database File
**Symptom**: Database grows very large over time

**Ask Claude to fix**:
```
My smarter-claude database file is getting very large. Can you check the database size, vacuum it to reclaim space, and adjust the cleanup settings to prevent it from growing too large?
```

📖 [Manual steps](#large-database-file-manual)

## Debug Mode

**Ask Claude to enable debug mode**:
```
Can you enable debug mode for smarter-claude so I can troubleshoot an issue? Please turn on detailed logging and show me where to find the debug files.
```

📖 [Manual steps](#debug-mode-manual)

## System Status Check

**Ask Claude to check system status**:
```
Can you check the overall health of my smarter-claude installation? Please verify the settings, database connection, and all components are working properly.
```

📖 [Manual steps](#system-status-check-manual)

## Nuclear Option: Reset Everything

**Ask Claude to reset the system**:
```
I need to completely reset smarter-claude to a fresh state. Can you backup my current settings, then remove all project data and reset everything to default? I want to start clean.
```

📖 [Manual steps](#reset-everything-manual)

## 🆘 Still Need Help?

[![GitHub Issues](https://img.shields.io/badge/🐛_GitHub-Issues-red)](https://github.com/okets/.claude/issues)
[![Bug Report](https://img.shields.io/badge/📝_Bug-Report_Helper-blue)](#bug-report-helper)
[![Getting Started](https://img.shields.io/badge/📖_Getting-Started-green)](GETTING_STARTED.md)

### Bug Report Helper

**Ask Claude to gather diagnostic info:**
```
I need to file a bug report for smarter-claude. Can you collect my system information, Claude Code version, recent error logs, and format them for a GitHub issue?
```

---

# Manual Troubleshooting

If you prefer command-line troubleshooting or Claude can't help, here are the manual steps:

## Installation Issues

### Installation Script Failed Manual
```bash
# Check if Claude Code is installed
claude --version
# If not found, install from: https://docs.anthropic.com/en/docs/claude-code

# Check if ~/.claude directory exists
ls -la ~/.claude
# If not found, create it: mkdir -p ~/.claude

# Check internet connection and GitHub access
curl -I https://github.com/okets/smarter-claude
# Should return HTTP 200

# Try manual download
cd ~/.claude
git clone https://github.com/okets/smarter-claude .

# Make hooks executable
chmod +x hooks/*.py

# Test basic functionality
python3 -c "from hooks.utils.contextual_db import ContextualDB; print('Success')"
```

### Hook Files Not Found Manual
```bash
# Verify hooks directory structure
ls -la ~/.claude/hooks/
# Should see: notification.py, post_tool_use.py, pre_tool_use.py, stop.py

# Check hook permissions
chmod +x ~/.claude/hooks/*.py
```

### Python Import Errors Manual
```bash
# Ensure you're in the correct directory structure
cd ~/.claude
pwd  # Should show /Users/yourusername/.claude

# Check Python path in hooks
head -1 ~/.claude/hooks/stop.py
# Should show: #!/usr/bin/env python3
```

## TTS Issues

### Coqui TTS Not Working Manual
```bash
# Verify Coqui installation
uv tool list | grep coqui
tts --help

# Test Coqui manually
tts --text "test" --out_path /tmp/test.wav
afplay /tmp/test.wav
```

### Male Voice Sounds Wrong Manual
```bash
# Install ffmpeg for pitch processing
brew install ffmpeg  # macOS
sudo apt install ffmpeg  # Ubuntu

# Test ffmpeg
ffmpeg -version
```

### No Audio Output Manual
```bash
# Check system audio
afplay /System/Library/Sounds/Ping.aiff  # macOS

# Verify TTS setting
python ~/.claude/hooks/utils/manage_settings.py get tts_enabled
# Should return: True

# Check interaction level
python ~/.claude/hooks/utils/manage_settings.py get interaction_level
# Silent mode disables all audio
```

## Database Issues

### Database Not Created Manual
```bash
# Check project detection
cd /your/project
python -c "
from hooks.utils.cycle_utils import get_project_smarter_claude_dir
print(get_project_smarter_claude_dir())
"

# Manually create directory if needed
mkdir -p .claude/smarter-claude
```

### Permission Denied on Database Manual
```bash
# Check directory permissions
ls -la .claude/smarter-claude/
chmod 755 .claude/smarter-claude/
chmod 644 .claude/smarter-claude/smarter-claude.db  # if exists
```

### Corrupted Database Manual
```bash
# Backup current database
cp .claude/smarter-claude/smarter-claude.db .claude/smarter-claude/smarter-claude.db.backup

# Test database integrity
sqlite3 .claude/smarter-claude/smarter-claude.db "PRAGMA integrity_check;"

# If corrupted, remove and recreate (loses history)
rm .claude/smarter-claude/smarter-claude.db
# Database will be recreated on next Claude Code session
```

## Notification Issues

### Notifications Not Appearing Manual
```bash
# Check notification hook
ls -la ~/.claude/hooks/notification.py
# Verify it's executable

# Test notification manually
echo '{"session_id":"test","transcript_path":"","hook_event_name":"Notification"}' | ~/.claude/hooks/notification.py

# Check settings
python ~/.claude/hooks/utils/manage_settings.py get interaction_level
# Should not be "silent"
```

### Wrong Notification Format Manual
```bash
# Check debug logs
cat /tmp/claude_debug_notification.json
# Look for user_request extraction issues

# Verify transcript parsing
python -c "
from hooks.notification import get_latest_user_message_from_transcript
print(get_latest_user_message_from_transcript('/path/to/transcript.jsonl'))
"
```

## Performance Issues

### Slow Hook Execution Manual
```bash
# Check hook execution times in debug logs
grep "execution_time" /tmp/claude_debug_*.json

# Disable verbose mode if not needed
python ~/.claude/hooks/utils/manage_settings.py set interaction_level concise

# Clean up old log files
find .claude/smarter-claude/logs/ -name "*.json*" -mtime +7 -delete
```

### Large Database File Manual
```bash
# Check database size
du -h .claude/smarter-claude/smarter-claude.db

# Vacuum database to reclaim space
sqlite3 .claude/smarter-claude/smarter-claude.db "VACUUM;"

# Adjust retention policy (lower = more cleanup)
python ~/.claude/hooks/utils/manage_settings.py set cleanup_policy.retention_cycles 1
```

## Debug Mode Manual
```bash
# Enable debug logging
python ~/.claude/hooks/utils/manage_settings.py set logging_settings.debug_logging true

# Check debug output locations
ls /tmp/claude_debug_*
ls /tmp/smarter_claude_*

# Disable when done (generates lots of files)
python ~/.claude/hooks/utils/manage_settings.py set logging_settings.debug_logging false
```

## System Status Check Manual
```bash
# View current settings
python ~/.claude/hooks/utils/manage_settings.py info

# Test database connection
python -c "
from hooks.utils.contextual_db import ContextualDB
db = ContextualDB()
print('Database connected successfully' if db.connection else 'Database connection failed')
"
```

## Reset Everything Manual
```bash
# Backup your settings (optional)
cp ~/.claude/hooks/utils/smarter-claude-global.json ~/smarter-claude-backup.json

# Remove all project data
rm -rf .claude/smarter-claude/

# Remove global settings (optional - will use defaults)
rm ~/.claude/hooks/utils/smarter-claude-global.json

# Restart Claude Code - fresh installation
claude
```