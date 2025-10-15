#!/usr/bin/env python3
"""
Database migration script for Notu
"""
import os
import sys
from flask_migrate import upgrade, init, migrate

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import User, Course, Document, Theme, AuditLog

def init_migrations():
    """Initialize Flask-Migrate"""
    print("🔧 Initializing database migrations...")
    try:
        init()
        print("✅ Migrations initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize migrations: {e}")
        return False

def create_migration(message):
    """Create a new migration"""
    print(f"📝 Creating migration: {message}")
    try:
        migrate(message=message)
        print("✅ Migration created successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to create migration: {e}")
        return False

def apply_migrations():
    """Apply all pending migrations"""
    print("🔄 Applying database migrations...")
    try:
        upgrade()
        print("✅ Migrations applied successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to apply migrations: {e}")
        return False

def create_tables():
    """Create all tables directly (for initial setup)"""
    print("🏗️ Creating database tables...")
    try:
        with app.app_context():
            db.create_all()
        print("✅ Tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 Notu Database Migration")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == 'init':
                init_migrations()
            elif command == 'create':
                message = sys.argv[2] if len(sys.argv) > 2 else 'Auto migration'
                create_migration(message)
            elif command == 'upgrade':
                apply_migrations()
            elif command == 'create-tables':
                create_tables()
            else:
                print(f"❌ Unknown command: {command}")
                print("\n📝 Available commands:")
                print("   init          - Initialize migrations")
                print("   create <msg>  - Create new migration")
                print("   upgrade       - Apply migrations")
                print("   create-tables - Create tables directly")
        else:
            print("🔧 Running full migration setup...")
            
            # Check if migrations directory exists
            if not os.path.exists('migrations'):
                print("📁 No migrations directory found, initializing...")
                if not init_migrations():
                    return
            
            # Create initial migration if no migrations exist
            if not os.path.exists('migrations/versions'):
                print("📝 Creating initial migration...")
                if not create_migration('Initial migration'):
                    return
            
            # Apply migrations
            if not apply_migrations():
                return
            
            print("\n✅ Migration setup completed!")
            print("\n📝 Next steps:")
            print("   1. Run: python seed.py")
            print("   2. Run: python run.py")

if __name__ == '__main__':
    main()
