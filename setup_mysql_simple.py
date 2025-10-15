#!/usr/bin/env python3
"""
Simple MySQL setup script for Notu
"""
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_mysql():
    """Setup MySQL database and user"""
    
    # Get MySQL root credentials
    root_password = input("Enter MySQL root password: ")
    
    try:
        # Connect as root
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password=root_password,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Create database
            print("Creating database 'notu'...")
            cursor.execute("CREATE DATABASE IF NOT EXISTS notu CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
            # Create user
            print("Creating user 'notu'...")
            cursor.execute("CREATE USER IF NOT EXISTS 'notu'@'localhost' IDENTIFIED BY 'notu123'")
            
            # Grant privileges
            print("Granting privileges...")
            cursor.execute("GRANT ALL PRIVILEGES ON notu.* TO 'notu'@'localhost'")
            cursor.execute("FLUSH PRIVILEGES")
            
            print("✅ MySQL setup completed successfully!")
            print("Database: notu")
            print("User: notu")
            print("Password: notu123")
            
    except Exception as e:
        print(f"❌ MySQL setup failed: {e}")
        return False
    
    finally:
        if 'connection' in locals():
            connection.close()
    
    return True

if __name__ == "__main__":
    print("🔧 Notu MySQL Setup")
    print("=" * 50)
    setup_mysql()
