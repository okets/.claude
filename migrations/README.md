# Migration Scripts

This directory contains version-specific migration scripts that run during updates.

## Naming Convention
- `v1.0.1.sh` - Migration for version 1.0.1
- `v1.1.0.sh` - Migration for version 1.1.0
- etc.

## Migration Script Template
```bash
#!/bin/bash
# migrations/vX.Y.Z.sh
# Description: What this migration does

echo "Running vX.Y.Z migration..."

# Find all project databases and apply migration to each
DB_COUNT=0
while IFS= read -r -d '' db_path; do
    if [ -f "$db_path" ]; then
        echo "  🔧 Migrating: $db_path"
        
        if sqlite3 "$db_path" << 'SQL_EOF'
-- Your SQL commands here
-- Example: CREATE INDEX IF NOT EXISTS idx_example ON table_name(column);
SQL_EOF
        then
            ((DB_COUNT++))
        else
            echo "❌ Migration failed for: $db_path"
            exit 1
        fi
    fi
done < <(find "$HOME" -name "smarter-claude.db" -path "*/.claude/smarter-claude/*" -print0 2>/dev/null)

echo "✅ vX.Y.Z migration applied to $DB_COUNT database(s)"
```

## Best Practices
1. Always check if files/databases exist before modifying
2. Use `|| true` to prevent script failure on missing files
3. Echo progress for user feedback
4. Keep migrations idempotent (safe to run multiple times)