#!/usr/bin/env python3
"""
MySQL database setup script for Notu
"""
import os
import sys
import pymysql
from pymysql.cursors import DictCursor

def create_database():
    """Create MySQL database and user"""
    
    # Database configuration
    mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
    mysql_port = int(os.environ.get('MYSQL_PORT', '3306'))
    mysql_root_user = os.environ.get('MYSQL_ROOT_USER', 'root')
    mysql_root_password = os.environ.get('MYSQL_ROOT_PASSWORD', '')
    
    # Application database configuration
    mysql_user = os.environ.get('MYSQL_USER', 'notu')
    mysql_password = os.environ.get('MYSQL_PASSWORD', 'notu123')
    mysql_database = os.environ.get('MYSQL_DATABASE', 'notu')
    
    print(f"🔧 Setting up MySQL database for Notu...")
    print(f"   Host: {mysql_host}:{mysql_port}")
    print(f"   Database: {mysql_database}")
    print(f"   User: {mysql_user}")
    
    try:
        # Connect to MySQL as root
        connection = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_root_user,
            password=mysql_root_password,
            charset='utf8mb4',
            cursorclass=DictCursor
        )
        
        with connection.cursor() as cursor:
            # Create database
            print(f"📁 Creating database '{mysql_database}'...")
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{mysql_database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
            # Create user
            print(f"👤 Creating user '{mysql_user}'...")
            cursor.execute(f"CREATE USER IF NOT EXISTS '{mysql_user}'@'%' IDENTIFIED BY '{mysql_password}'")
            
            # Grant privileges
            print(f"🔑 Granting privileges...")
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{mysql_database}`.* TO '{mysql_user}'@'%'")
            cursor.execute("FLUSH PRIVILEGES")
            
            # Test connection with new user
            print(f"✅ Testing connection with new user...")
            cursor.execute(f"USE `{mysql_database}`")
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            if result and result['test'] == 1:
                print(f"✅ Database setup completed successfully!")
                print(f"\n📋 Database Information:")
                print(f"   Database: {mysql_database}")
                print(f"   User: {mysql_user}")
                print(f"   Password: {mysql_password}")
                print(f"   Host: {mysql_host}:{mysql_port}")
                print(f"\n🔗 Connection String:")
                print(f"   mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}")
                return True
            else:
                print(f"❌ Database test failed!")
                return False
                
    except pymysql.Error as e:
        print(f"❌ MySQL Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'connection' in locals():
            connection.close()

def test_connection():
    """Test database connection"""
    mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
    mysql_port = int(os.environ.get('MYSQL_PORT', '3306'))
    mysql_user = os.environ.get('MYSQL_USER', 'notu')
    mysql_password = os.environ.get('MYSQL_PASSWORD', 'notu123')
    mysql_database = os.environ.get('MYSQL_DATABASE', 'notu')
    
    try:
        connection = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password,
            database=mysql_database,
            charset='utf8mb4',
            cursorclass=DictCursor
        )
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() as version")
            result = cursor.fetchone()
            print(f"✅ Connection successful!")
            print(f"   MySQL Version: {result['version']}")
            print(f"   Database: {mysql_database}")
            return True
            
    except pymysql.Error as e:
        print(f"❌ Connection failed: {e}")
        return False
    finally:
        if 'connection' in locals():
            connection.close()

def main():
    """Main setup function"""
    print("🚀 Notu MySQL Database Setup")
    print("=" * 50)
    
    # Check if we should create database or just test
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("🧪 Testing database connection...")
        success = test_connection()
    else:
        print("🔧 Setting up database...")
        success = create_database()
        
        if success:
            print("\n🧪 Testing connection...")
            test_connection()
    
    if success:
        print("\n✅ Setup completed! You can now run the application.")
        print("\n📝 Next steps:")
        print("   1. Run: python seed.py")
        print("   2. Run: python run.py")
    else:
        print("\n❌ Setup failed! Please check your MySQL configuration.")
        print("\n📝 Troubleshooting:")
        print("   1. Make sure MySQL is running")
        print("   2. Check your environment variables")
        print("   3. Verify MySQL root credentials")

if __name__ == '__main__':
    main()
