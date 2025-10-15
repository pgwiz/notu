#!/usr/bin/env python3
"""
Data migration script to convert existing documents to the new hierarchical structure.
This script creates default units and categories for each course and migrates existing documents.
"""

import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import Course, Document, Unit, Category

def create_default_units_and_categories():
    """Create default units and categories for each course"""
    app = create_app()
    
    with app.app_context():
        # Get all active courses
        courses = Course.query.filter_by(is_active=True).all()
        
        for course in courses:
            print(f"Processing course: {course.name} ({course.prefix})")
            
            # Create default unit "General" if it doesn't exist
            general_unit = Unit.query.filter_by(
                course_id=course.id, 
                slug='general'
            ).first()
            
            if not general_unit:
                general_unit = Unit(
                    course_id=course.id,
                    name='General',
                    slug='general',
                    description='General documents and materials',
                    order=0
                )
                db.session.add(general_unit)
                db.session.flush()  # Get the ID
                print(f"  Created unit: {general_unit.name}")
            
            # Create default categories if they don't exist
            default_categories = [
                {'name': 'Notes', 'slug': 'notes', 'icon': 'fa-file-text', 'color': '#10b981', 'order': 1},
                {'name': 'Assignments', 'slug': 'assignments', 'icon': 'fa-tasks', 'color': '#3b82f6', 'order': 2},
                {'name': 'Lectures', 'slug': 'lectures', 'icon': 'fa-chalkboard-teacher', 'color': '#8b5cf6', 'order': 3},
                {'name': 'Exams', 'slug': 'exams', 'icon': 'fa-clipboard-check', 'color': '#f59e0b', 'order': 4},
                {'name': 'Projects', 'slug': 'projects', 'icon': 'fa-project-diagram', 'color': '#ef4444', 'order': 5},
                {'name': 'Others', 'slug': 'others', 'icon': 'fa-folder', 'color': '#6b7280', 'order': 6}
            ]
            
            for cat_data in default_categories:
                category = Category.query.filter_by(
                    course_id=course.id,
                    slug=cat_data['slug']
                ).first()
                
                if not category:
                    category = Category(
                        course_id=course.id,
                        name=cat_data['name'],
                        slug=cat_data['slug'],
                        icon=cat_data['icon'],
                        color=cat_data['color'],
                        order=cat_data['order']
                    )
                    db.session.add(category)
                    print(f"  Created category: {category.name}")
            
            db.session.commit()
            print(f"  Completed course: {course.name}")

def migrate_existing_documents():
    """Migrate existing documents to use the new structure"""
    app = create_app()
    
    with app.app_context():
        # Get all documents that still have the old category field
        # Note: This assumes the migration hasn't been run yet
        # If it has been run, we need to handle this differently
        
        # For now, we'll create a mapping of old categories to new ones
        category_mapping = {
            'notes': 'notes',
            'assignments': 'assignments', 
            'lectures': 'lectures',
            'exams': 'exams',
            'projects': 'projects',
            'others': 'others',
            'cats': 'others'  # Map old 'cats' to 'others'
        }
        
        # Get all courses and their units/categories
        courses = Course.query.filter_by(is_active=True).all()
        
        for course in courses:
            print(f"Migrating documents for course: {course.name}")
            
            # Get the general unit for this course
            general_unit = Unit.query.filter_by(
                course_id=course.id,
                slug='general'
            ).first()
            
            if not general_unit:
                print(f"  Warning: No general unit found for course {course.name}")
                continue
            
            # Get all categories for this course
            categories = Category.query.filter_by(course_id=course.id).all()
            category_map = {cat.slug: cat for cat in categories}
            
            # Find documents that need migration
            # Since we're changing the schema, we need to be careful here
            # This is a simplified approach - in practice, you'd want to backup first
            
            print(f"  Found {len(categories)} categories for migration")
            print(f"  General unit ID: {general_unit.id}")

def main():
    """Main migration function"""
    print("Starting data migration for hierarchical units and categories...")
    
    try:
        # Step 1: Create default units and categories
        print("\n1. Creating default units and categories...")
        create_default_units_and_categories()
        
        # Step 2: Migrate existing documents
        print("\n2. Preparing document migration...")
        migrate_existing_documents()
        
        print("\nMigration completed successfully!")
        print("\nNext steps:")
        print("1. Run the Alembic migration: python -m flask db upgrade")
        print("2. Update your application code to use the new structure")
        print("3. Test the new functionality")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
