#!/usr/bin/env python3
"""
Main application entry point for Notu
"""
import os
from app import create_app, db
from models import User, Course, Document, Theme, AuditLog

app = create_app()

@app.shell_context_processor
def make_shell_context():
    """Make database models available in Flask shell"""
    return {
        'db': db,
        'User': User,
        'Course': Course,
        'Document': Document,
        'Theme': Theme,
        'AuditLog': AuditLog
    }

if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)
