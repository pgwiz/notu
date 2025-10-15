"""
SQLAlchemy models for the Notes Upload app
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
import uuid

from app import db

class User(UserMixin, db.Model):
    """User model with Flask-Login compatibility"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin', 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    documents = db.relationship('Document', backref='owner', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='actor', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.email}>'

class Course(db.Model):
    """Course model for organizing documents"""
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    prefix = db.Column(db.String(20), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    documents = db.relationship('Document', backref='course', lazy='dynamic')
    
    def __repr__(self):
        return f'<Course {self.prefix}: {self.name}>'

class Unit(db.Model):
    """Unit model for organizing documents within courses"""
    __tablename__ = 'units'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), nullable=False)  # URL-friendly name (e.g., 'dbms', 'algorithms')
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)  # For sorting
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    course = db.relationship('Course', backref='units')
    documents = db.relationship('Document', backref='unit', lazy='dynamic')
    
    # Unique constraint: one slug per course
    __table_args__ = (
        db.UniqueConstraint('course_id', 'slug', name='uq_course_unit_slug'),
    )
    
    def __repr__(self):
        return f'<Unit {self.slug}: {self.name}>'

class Category(db.Model):
    """Category model for document types within units"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(50), nullable=False)  # e.g., 'notes', 'assignments'
    icon = db.Column(db.String(50), default='fa-file')  # FontAwesome icon class
    color = db.Column(db.String(20), default='#10b981')  # Hex color
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    course = db.relationship('Course', backref='categories')
    documents = db.relationship('Document', backref='category_obj', lazy='dynamic')
    
    # Unique constraint: one slug per course
    __table_args__ = (
        db.UniqueConstraint('course_id', 'slug', name='uq_course_category_slug'),
    )
    
    def __repr__(self):
        return f'<Category {self.slug}: {self.name}>'

class Document(db.Model):
    """Document model for uploaded files"""
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    storage_key = db.Column(db.String(500), nullable=False, unique=True, index=True)
    storage_backend = db.Column(db.String(20), nullable=False)  # 'local', 's3'
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    checksum = db.Column(db.String(64), nullable=False)  # SHA-256
    visibility = db.Column(db.String(20), nullable=False, default='private')  # 'public', 'private'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for common queries
    __table_args__ = (
        db.Index('idx_document_course_unit_category', 'course_id', 'unit_id', 'category_id'),
        db.Index('idx_document_visibility', 'visibility'),
        db.Index('idx_document_owner_visibility', 'owner_id', 'visibility'),
    )
    
    def is_public(self):
        """Check if document is public"""
        return self.visibility == 'public'
    
    def can_access(self, user):
        """Check if user can access this document"""
        if self.is_public():
            return True
        if user and (user.id == self.owner_id or user.is_admin()):
            return True
        return False
    
    def get_storage_path(self):
        """Generate storage path: course/unit/category/filename"""
        year = self.created_at.year
        month = f"{self.created_at.month:02d}"
        filename = f"{uuid.uuid4()}_{self.original_filename}"
        return f"{self.course.prefix}/{self.unit.slug}/{self.category_obj.slug}/{year}/{month}/{filename}"
    
    def __repr__(self):
        return f'<Document {self.title}>'

class Theme(db.Model):
    """Theme model for UI customization"""
    __tablename__ = 'themes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    variables_json = db.Column(db.Text, nullable=False)  # JSON string of CSS variables
    font_family = db.Column(db.String(100), default='Inter, system-ui, sans-serif')
    icon_pack = db.Column(db.String(50), default='heroicons')
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_variables(self):
        """Parse variables JSON"""
        try:
            return json.loads(self.variables_json)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_variables(self, variables_dict):
        """Set variables from dict"""
        self.variables_json = json.dumps(variables_dict)
    
    def __repr__(self):
        return f'<Theme {self.name}>'

class AuditLog(db.Model):
    """Audit log for tracking actions"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # None for anonymous
    action = db.Column(db.String(50), nullable=False)  # 'upload', 'delete', 'privacy_change', etc.
    subject_type = db.Column(db.String(50), nullable=False)  # 'document', 'course', 'user', etc.
    subject_id = db.Column(db.Integer, nullable=True)
    meta_json = db.Column(db.Text)  # Additional metadata as JSON
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Indexes for common queries
    __table_args__ = (
        db.Index('idx_audit_actor', 'actor_id'),
        db.Index('idx_audit_subject', 'subject_type', 'subject_id'),
        db.Index('idx_audit_action', 'action'),
        db.Index('idx_audit_created', 'created_at'),
    )
    
    def get_meta(self):
        """Parse meta JSON"""
        try:
            return json.loads(self.meta_json) if self.meta_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_meta(self, meta_dict):
        """Set meta from dict"""
        self.meta_json = json.dumps(meta_dict) if meta_dict else None
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.subject_type}>'
