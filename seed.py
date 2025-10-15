#!/usr/bin/env python3
"""
Seed script to populate initial data for Notu
"""
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import User, Course, Document, Theme, AuditLog

def create_admin_user():
    """Create initial admin user"""
    admin_email = 'admin@notu.local'
    admin_password = 'admin123'
    
    # Check if admin already exists
    existing_admin = User.query.filter_by(email=admin_email).first()
    if existing_admin:
        print(f"Admin user {admin_email} already exists")
        return existing_admin
    
    # Create admin user
    admin = User(
        email=admin_email,
        role='admin',
        is_active=True
    )
    admin.set_password(admin_password)
    
    db.session.add(admin)
    db.session.commit()
    
    print(f"Created admin user: {admin_email} (password: {admin_password})")
    return admin

def create_sample_courses():
    """Create sample courses"""
    courses_data = [
        {
            'name': 'Computer Science',
            'prefix': 'cs',
            'description': 'Computer Science course materials and notes'
        },
        {
            'name': 'Mathematics',
            'prefix': 'math',
            'description': 'Mathematics course materials and notes'
        },
        {
            'name': 'Physics',
            'prefix': 'physics',
            'description': 'Physics course materials and notes'
        },
        {
            'name': 'Chemistry',
            'prefix': 'chem',
            'description': 'Chemistry course materials and notes'
        },
        {
            'name': 'Biology',
            'prefix': 'bio',
            'description': 'Biology course materials and notes'
        }
    ]
    
    created_courses = []
    for course_data in courses_data:
        existing_course = Course.query.filter_by(prefix=course_data['prefix']).first()
        if existing_course:
            print(f"Course {course_data['name']} already exists")
            created_courses.append(existing_course)
            continue
        
        course = Course(
            name=course_data['name'],
            prefix=course_data['prefix'],
            description=course_data['description'],
            is_active=True
        )
        
        db.session.add(course)
        created_courses.append(course)
        print(f"Created course: {course_data['name']} ({course_data['prefix']})")
    
    db.session.commit()
    return created_courses

def create_sample_themes():
    """Create sample themes"""
    themes_data = [
        {
            'name': 'green-black',
            'display_name': 'Green & Black',
            'variables_json': '{"--bg-primary": "#111827", "--bg-secondary": "#1f2937", "--bg-tertiary": "#374151", "--fg-primary": "#f9fafb", "--fg-secondary": "#d1d5db", "--fg-muted": "#9ca3af", "--accent": "#10b981", "--accent-hover": "#059669", "--success": "#10b981", "--warning": "#f59e0b", "--error": "#ef4444", "--info": "#3b82f6"}',
            'font_family': 'Inter, system-ui, sans-serif',
            'icon_pack': 'heroicons',
            'is_default': True
        },
        {
            'name': 'blue-dark',
            'display_name': 'Blue & Dark',
            'variables_json': '{"--bg-primary": "#0f172a", "--bg-secondary": "#1e293b", "--bg-tertiary": "#334155", "--fg-primary": "#f8fafc", "--fg-secondary": "#cbd5e1", "--fg-muted": "#94a3b8", "--accent": "#3b82f6", "--accent-hover": "#2563eb", "--success": "#10b981", "--warning": "#f59e0b", "--error": "#ef4444", "--info": "#06b6d4"}',
            'font_family': 'Inter, system-ui, sans-serif',
            'icon_pack': 'heroicons',
            'is_default': False
        },
        {
            'name': 'purple-dark',
            'display_name': 'Purple & Dark',
            'variables_json': '{"--bg-primary": "#1a0b2e", "--bg-secondary": "#2d1b69", "--bg-tertiary": "#4c1d95", "--fg-primary": "#faf5ff", "--fg-secondary": "#d8b4fe", "--fg-muted": "#a78bfa", "--accent": "#8b5cf6", "--accent-hover": "#7c3aed", "--success": "#10b981", "--warning": "#f59e0b", "--error": "#ef4444", "--info": "#06b6d4"}',
            'font_family': 'Inter, system-ui, sans-serif',
            'icon_pack': 'heroicons',
            'is_default': False
        }
    ]
    
    created_themes = []
    for theme_data in themes_data:
        existing_theme = Theme.query.filter_by(name=theme_data['name']).first()
        if existing_theme:
            print(f"Theme {theme_data['name']} already exists")
            created_themes.append(existing_theme)
            continue
        
        theme = Theme(
            name=theme_data['name'],
            display_name=theme_data['display_name'],
            variables_json=theme_data['variables_json'],
            font_family=theme_data['font_family'],
            icon_pack=theme_data['icon_pack'],
            is_default=theme_data['is_default'],
            is_active=True
        )
        
        db.session.add(theme)
        created_themes.append(theme)
        print(f"Created theme: {theme_data['display_name']}")
    
    db.session.commit()
    return created_themes

def create_sample_user():
    """Create a sample regular user"""
    user_email = 'user@notu.local'
    user_password = 'user123'
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=user_email).first()
    if existing_user:
        print(f"User {user_email} already exists")
        return existing_user
    
    # Create user
    user = User(
        email=user_email,
        role='user',
        is_active=True
    )
    user.set_password(user_password)
    
    db.session.add(user)
    db.session.commit()
    
    print(f"Created user: {user_email} (password: {user_password})")
    return user

def main():
    """Main seed function"""
    print("🌱 Seeding Notu database...")
    
    # Create admin user
    admin = create_admin_user()
    
    # Create sample courses
    courses = create_sample_courses()
    
    # Create sample themes
    themes = create_sample_themes()
    
    # Create sample user
    user = create_sample_user()
    
    print("\n✅ Seeding completed!")
    print("\n📋 Summary:")
    print(f"   - Admin user: admin@notu.local (password: admin123)")
    print(f"   - Regular user: user@notu.local (password: user123)")
    print(f"   - Courses: {len(courses)}")
    print(f"   - Themes: {len(themes)}")
    print("\n🚀 You can now start the application with: python run.py")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        main()
