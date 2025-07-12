#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# dependencies = ["pymysql", "cryptography"]
# ///

import os
import sys
import pymysql
from pathlib import Path

def create_database():
    """Create the Claude intelligence database and tables"""
    
    # Database connection parameters
    host = os.getenv('CLAUDE_DB_HOST', 'localhost')
    user = os.getenv('CLAUDE_DB_USER', 'root')
    password = os.getenv('CLAUDE_DB_PASSWORD', '')
    
    print(f"Connecting to MySQL at {host} as {user}...")
    
    try:
        # Connect to MySQL server (without database)
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # Read and execute schema
            schema_path = Path(__file__).parent / 'schema.sql'
            
            if not schema_path.exists():
                print("❌ Error: schema.sql not found!")
                return False
            
            print("📋 Reading schema.sql...")
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Split into individual statements
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            print(f"🔧 Executing {len(statements)} SQL statements...")
            
            for i, statement in enumerate(statements, 1):
                try:
                    cursor.execute(statement)
                    print(f"   ✅ Statement {i}/{len(statements)}")
                except Exception as e:
                    print(f"   ⚠️  Statement {i} warning: {e}")
            
        connection.commit()
        print("✅ Database setup completed successfully!")
        
        # Test the connection with our database utility
        print("🧪 Testing database connection...")
        sys.path.append(str(Path(__file__).parent / 'hooks' / 'utils'))
        from db import get_db
        
        db = get_db()
        if db.connection:
            print("✅ Database connection test successful!")
            
            # Test project creation
            test_project_id = db.ensure_project('/test/project', 'test-project')
            if test_project_id:
                print("✅ Project creation test successful!")
                
                # Clean up test project
                with db.connection.cursor() as cursor:
                    cursor.execute("DELETE FROM projects WHERE id = %s", (test_project_id,))
                print("🧹 Test data cleaned up")
            else:
                print("⚠️  Project creation test failed")
        else:
            print("❌ Database connection test failed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return False
    finally:
        if 'connection' in locals():
            connection.close()

def print_setup_instructions():
    """Print setup instructions for environment variables"""
    print("\n" + "="*60)
    print("🚀 Claude Code MySQL Intelligence Setup")
    print("="*60)
    print()
    print("📋 Required Environment Variables:")
    print("   export CLAUDE_DB_HOST=localhost      # MySQL host")
    print("   export CLAUDE_DB_USER=root           # MySQL user")
    print("   export CLAUDE_DB_PASSWORD=your_pass  # MySQL password")
    print("   export CLAUDE_DB_NAME=claude_intelligence  # Database name")
    print()
    print("💡 Add these to your ~/.bashrc, ~/.zshrc, or ~/.profile")
    print()
    print("🔧 To run setup:")
    print("   python setup_database.py")
    print()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print_setup_instructions()
        return
    
    # Check if MySQL connection info is available
    if not os.getenv('CLAUDE_DB_PASSWORD'):
        print("⚠️  CLAUDE_DB_PASSWORD environment variable not set!")
        print("   Set your MySQL password with: export CLAUDE_DB_PASSWORD=your_password")
        print()
        print("   Or run: python setup_database.py --help for full instructions")
        return
    
    success = create_database()
    
    if success:
        print("\n🎉 Setup complete! Your Claude Code hooks will now use MySQL for intelligent project tracking.")
        print("\n📖 Available slash commands:")
        print("   /work_query overview")
        print("   /work_query \"files that change together\"")
        print("   /work_query \"active tasks\"")
        print("   /work_query \"recent git operations\"")
    else:
        print("\n❌ Setup failed. Check your MySQL connection and try again.")

if __name__ == '__main__':
    main()