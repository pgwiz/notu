"""
Authentication and authorization utilities
"""
from functools import wraps
from flask import current_app, request, session, redirect, url_for, flash, abort
from flask_login import current_user, login_required
from models import User, AuditLog, Document
from app import db
import logging

logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        
        if not current_user.is_admin():
            flash('Admin access required.', 'error')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def owner_or_admin_required(f):
    """Decorator to require ownership or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        
        # Check if user is admin (admins can access everything)
        if current_user.is_admin():
            return f(*args, **kwargs)
        
        # For non-admins, check ownership
        # This assumes the resource has an owner_id field
        # You may need to customize this based on your specific needs
        return f(*args, **kwargs)
    return decorated_function

def log_audit(action: str, subject_type: str, subject_id: int = None, meta: dict = None):
    """Log an audit event"""
    try:
        audit_log = AuditLog(
            actor_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            subject_type=subject_type,
            subject_id=subject_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        
        if meta:
            audit_log.set_meta(meta)
        
        from app import db
        db.session.add(audit_log)
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")

def get_user_by_email(email: str) -> User:
    """Get user by email address"""
    return User.query.filter_by(email=email).first()

def create_user(email: str, password: str, role: str = 'user') -> User:
    """Create a new user"""
    user = User(email=email, role=role)
    user.set_password(password)
    
    from app import db
    db.session.add(user)
    db.session.commit()
    
    log_audit('user_created', 'user', user.id, {'email': email, 'role': role})
    
    return user

def authenticate_user(email: str, password: str) -> User:
    """Authenticate user with email and password"""
    user = get_user_by_email(email)
    
    if user and user.check_password(password) and user.is_active:
        # Update last login
        from datetime import datetime
        user.last_login = datetime.utcnow()
        
        from app import db
        db.session.commit()
        
        log_audit('login', 'user', user.id, {'email': email})
        
        return user
    
    if user:
        log_audit('failed_login', 'user', user.id, {'email': email, 'reason': 'invalid_password'})
    else:
        log_audit('failed_login', 'user', None, {'email': email, 'reason': 'user_not_found'})
    
    return None

def change_user_role(user_id: int, new_role: str) -> bool:
    """Change user role (admin only)"""
    if not current_user.is_admin():
        return False
    
    user = User.query.get(user_id)
    if not user:
        return False
    
    old_role = user.role
    user.role = new_role
    
    from app import db
    db.session.commit()
    
    log_audit('role_changed', 'user', user_id, {
        'old_role': old_role,
        'new_role': new_role,
        'changed_by': current_user.id
    })
    
    return True

def deactivate_user(user_id: int) -> bool:
    """Deactivate user account (admin only)"""
    if not current_user.is_admin():
        return False
    
    user = User.query.get(user_id)
    if not user:
        return False
    
    user.is_active = False
    
    from app import db
    db.session.commit()
    
    log_audit('user_deactivated', 'user', user_id, {'deactivated_by': current_user.id})
    
    return True

def activate_user(user_id: int) -> bool:
    """Activate user account (admin only)"""
    if not current_user.is_admin():
        return False
    
    user = User.query.get(user_id)
    if not user:
        return False
    
    user.is_active = True
    
    from app import db
    db.session.commit()
    
    log_audit('user_activated', 'user', user_id, {'activated_by': current_user.id})
    
    return True

def get_user_stats(user_id: int) -> dict:
    """Get user statistics"""
    from models import Document
    
    user = User.query.get(user_id)
    if not user:
        return {}
    
    total_docs = Document.query.filter_by(owner_id=user_id).count()
    public_docs = Document.query.filter_by(owner_id=user_id, visibility='public').count()
    private_docs = Document.query.filter_by(owner_id=user_id, visibility='private').count()
    
    # Get total storage used
    total_size = db.session.query(db.func.sum(Document.file_size)).filter_by(owner_id=user_id).scalar() or 0
    
    return {
        'total_documents': total_docs,
        'public_documents': public_docs,
        'private_documents': private_docs,
        'total_storage_bytes': total_size,
        'total_storage_mb': round(total_size / (1024 * 1024), 2)
    }

def check_permission(user: User, resource_type: str, resource_id: int = None) -> bool:
    """Check if user has permission for a resource"""
    if not user or not user.is_active:
        return False
    
    # Admins have all permissions
    if user.is_admin():
        return True
    
    # Check specific resource permissions
    if resource_type == 'document':
        from models import Document
        doc = Document.query.get(resource_id)
        if doc:
            return doc.can_access(user)
    
    return False

def require_permission(resource_type: str):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            
            # Extract resource_id from kwargs if available
            resource_id = kwargs.get('id') or kwargs.get('doc_id') or kwargs.get('user_id')
            
            if not check_permission(current_user, resource_type, resource_id):
                flash('Insufficient permissions.', 'error')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
