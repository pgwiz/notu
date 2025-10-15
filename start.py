#!/usr/bin/env python3
"""
Startup script for Notu application
"""
import os
import sys
import time
import subprocess
from pathlib import Path

def check_mysql_connection():
    """Check if MySQL is accessible"""
    try:
        import pymysql
        mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
        mysql_port = int(os.environ.get('MYSQL_PORT', '3306'))
        mysql_user = os.environ.get('MYSQL_USER', 'notu')
        mysql_password = os.environ.get('MYSQL_PASSWORD', 'notu123')
        mysql_database = os.environ.get('MYSQL_DATABASE', 'notu')
        
        connection = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password,
            database=mysql_database,
            charset='utf8mb4'
        )
        connection.close()
        return True
    except Exception as e:
        print(f"❌ MySQL connection failed: {e}")
        return False

def wait_for_mysql(max_attempts=30):
    """Wait for MySQL to be available"""
    print("⏳ Waiting for MySQL to be available...")
    
    for attempt in range(max_attempts):
        if check_mysql_connection():
            print("✅ MySQL is available!")
            return True
        
        print(f"⏳ Attempt {attempt + 1}/{max_attempts} - MySQL not ready yet...")
        time.sleep(2)
    
    print("❌ MySQL is not available after maximum attempts")
    return False

def setup_database():
    """Set up the database"""
    print("🔧 Setting up database...")
    
    # Check if we need to run MySQL setup
    if not check_mysql_connection():
        print("📝 Running MySQL setup...")
        result = subprocess.run([sys.executable, 'setup_mysql.py'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ MySQL setup failed: {result.stderr}")
            return False
    
    # Run database migrations
    print("🔄 Running database migrations...")
    result = subprocess.run([sys.executable, 'migrate_db.py'], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Migration failed: {result.stderr}")
        return False
    
    # Check if database is seeded
    try:
        from app import create_app, db
        from models import User
        
        app = create_app()
        with app.app_context():
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count == 0:
                print("🌱 Seeding database...")
                result = subprocess.run([sys.executable, 'seed.py'], capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"❌ Seeding failed: {result.stderr}")
                    return False
            else:
                print("✅ Database already seeded")
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False
    
    return True

def start_application():
    """Start the Flask application"""
    print("🚀 Starting Notu application...")
    
    # Set environment variables if not set
    if not os.environ.get('FLASK_ENV'):
        os.environ['FLASK_ENV'] = 'development'
    
    if not os.environ.get('SECRET_KEY'):
        os.environ['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    
    # Start the application
    try:
        from run import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Failed to start application: {e}")

def main():
    """Main startup function"""
    print("🚀 Notu Application Startup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path('run.py').exists():
        print("❌ Please run this script from the project root directory")
        return
    
    # Wait for MySQL if using Docker
    if os.environ.get('MYSQL_HOST') == 'mysql' or os.environ.get('DOCKER_COMPOSE'):
        if not wait_for_mysql():
            return
    
    # Set up database
    if not setup_database():
        print("❌ Database setup failed!")
        return
    
    print("\n✅ Setup completed successfully!")
    print("\n🌐 Application will be available at: http://localhost:5000")
    print("👤 Admin login: admin@notu.local / admin123")
    print("👤 User login: user@notu.local / user123")
    print("\n" + "=" * 50)
    
    # Start the application
    start_application()

if __name__ == '__main__':
    main()
