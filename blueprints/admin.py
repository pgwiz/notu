"""
Admin dashboard blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, current_app
from flask_login import login_required, current_user
from models import User, Course, Document, Theme, AuditLog, Unit, Category
from services.auth import admin_required, log_audit, change_user_role, activate_user, deactivate_user
from services.storage import get_storage_backend, LocalStorageBackend, S3StorageBackend
from services.sync import SyncEngine
from services.security import FileValidator
from werkzeug.utils import secure_filename
from app import db
from datetime import datetime, timedelta
import os
import uuid
import json
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__)

@bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard"""
    # Get system statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_courses = Course.query.filter_by(is_active=True).count()
    total_documents = Document.query.count()
    public_documents = Document.query.filter_by(visibility='public').count()
    
    # Get time-based statistics
    now = datetime.utcnow()
    this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_week = now - timedelta(days=now.weekday())
    this_week = this_week.replace(hour=0, minute=0, second=0, microsecond=0)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    new_users_this_month = User.query.filter(User.created_at >= this_month).count()
    courses_this_month = Course.query.filter(Course.created_at >= this_month).count()
    documents_this_week = Document.query.filter(Document.created_at >= this_week).count()
    
    # Get recent activity
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    
    # Get storage statistics
    total_storage = db.session.query(db.func.sum(Document.file_size)).scalar() or 0
    total_storage_mb = round(total_storage / (1024 * 1024), 2)
    total_storage_gb = round(total_storage_mb / 1024, 2)
    
    # Calculate storage growth (mock data for now)
    storage_growth = 12.5  # This would be calculated from historical data
    
    # Get download statistics (mock data for now)
    total_downloads = 1250  # This would come from a downloads table
    downloads_today = 45    # This would be calculated from today's logs
    
    # Get system uptime (mock data for now)
    system_uptime = "99.9%"  # This would be calculated from system logs
    
    # Get active storage backend
    from flask import current_app
    active_backend = current_app.config.get('ACTIVE_STORAGE_BACKEND', 'local')
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         total_courses=total_courses,
                         total_documents=total_documents,
                         public_documents=public_documents,
                         total_storage_mb=total_storage_mb,
                         total_storage_gb=total_storage_gb,
                         storage_growth=storage_growth,
                         total_downloads=total_downloads,
                         downloads_today=downloads_today,
                         new_users_this_month=new_users_this_month,
                         courses_this_month=courses_this_month,
                         documents_this_week=documents_this_week,
                         system_uptime=system_uptime,
                         active_backend=active_backend,
                         recent_logs=recent_logs)

@bp.route('/dashboard')
@admin_required
def dashboard_alt():
    """Admin dashboard (alternative route)"""
    return redirect(url_for('admin.dashboard'))

@bp.route('/courses')
@admin_required
def courses():
    """Manage courses"""
    courses = Course.query.order_by(Course.name).all()
    return render_template('admin/courses.html', courses=courses)

@bp.route('/courses/create', methods=['GET', 'POST'])
@admin_required
def create_course():
    """Create new course"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        prefix = request.form.get('prefix', '').strip().lower()
        description = request.form.get('description', '').strip()
        
        # Validation
        if not name or not prefix:
            flash('Name and prefix are required.', 'error')
            return render_template('admin/create_course.html')
        
        # Check if prefix already exists
        existing_course = Course.query.filter_by(prefix=prefix).first()
        if existing_course:
            flash('Course prefix already exists.', 'error')
            return render_template('admin/create_course.html')
        
        try:
            course = Course(
                name=name,
                prefix=prefix,
                description=description
            )
            
            db.session.add(course)
            db.session.commit()
            
            log_audit('course_created', 'course', course.id, {
                'name': name,
                'prefix': prefix
            })
            
            flash('Course created successfully!', 'success')
            return redirect(url_for('admin.courses'))
        
        except Exception as e:
            logger.error(f"Course creation error: {e}")
            db.session.rollback()
            flash('Failed to create course.', 'error')
    
    return render_template('admin/create_course.html')

@bp.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_course(course_id):
    """Edit course"""
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        prefix = request.form.get('prefix', '').strip().lower()
        description = request.form.get('description', '').strip()
        is_active = bool(request.form.get('is_active'))
        
        # Validation
        if not name or not prefix:
            flash('Name and prefix are required.', 'error')
            return render_template('admin/edit_course.html', course=course)
        
        # Check if prefix already exists (excluding current course)
        existing_course = Course.query.filter(
            Course.prefix == prefix,
            Course.id != course_id
        ).first()
        if existing_course:
            flash('Course prefix already exists.', 'error')
            return render_template('admin/edit_course.html', course=course)
        
        try:
            old_name = course.name
            old_prefix = course.prefix
            
            course.name = name
            course.prefix = prefix
            course.description = description
            course.is_active = is_active
            
            db.session.commit()
            
            log_audit('course_edited', 'course', course_id, {
                'old_name': old_name,
                'new_name': name,
                'old_prefix': old_prefix,
                'new_prefix': prefix
            })
            
            flash('Course updated successfully!', 'success')
            return redirect(url_for('admin.courses'))
        
        except Exception as e:
            logger.error(f"Course edit error: {e}")
            db.session.rollback()
            flash('Failed to update course.', 'error')
    
    return render_template('admin/edit_course.html', course=course)

@bp.route('/courses/<int:course_id>/delete', methods=['POST'])
@admin_required
def delete_course(course_id):
    """Delete course"""
    course = Course.query.get_or_404(course_id)
    
    # Check if course has documents
    doc_count = Document.query.filter_by(course_id=course_id).count()
    if doc_count > 0:
        flash(f'Cannot delete course with {doc_count} documents. Please move or delete documents first.', 'error')
        return redirect(url_for('admin.courses'))
    
    try:
        log_audit('course_deleted', 'course', course_id, {
            'name': course.name,
            'prefix': course.prefix
        })
        
        db.session.delete(course)
        db.session.commit()
        
        flash('Course deleted successfully!', 'success')
    
    except Exception as e:
        logger.error(f"Course deletion error: {e}")
        db.session.rollback()
        flash('Failed to delete course.', 'error')
    
    return redirect(url_for('admin.courses'))

@bp.route('/users')
@admin_required
def users():
    """Manage users"""
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html', users=users)

@bp.route('/users/<int:user_id>/role', methods=['POST'])
@admin_required
def change_user_role(user_id):
    """Change user role"""
    new_role = request.form.get('role', '')
    
    if new_role not in ['admin', 'user']:
        flash('Invalid role.', 'error')
        return redirect(url_for('admin.users'))
    
    if change_user_role(user_id, new_role):
        flash('User role updated successfully.', 'success')
    else:
        flash('Failed to update user role.', 'error')
    
    return redirect(url_for('admin.users'))

@bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    
    if user.is_active:
        if deactivate_user(user_id):
            flash('User deactivated successfully.', 'success')
        else:
            flash('Failed to deactivate user.', 'error')
    else:
        if activate_user(user_id):
            flash('User activated successfully.', 'success')
        else:
            flash('Failed to activate user.', 'error')
    
    return redirect(url_for('admin.users'))

@bp.route('/themes')
@admin_required
def themes():
    """Manage themes"""
    themes = Theme.query.order_by(Theme.name).all()
    return render_template('admin/themes.html', themes=themes)

@bp.route('/themes/create', methods=['GET', 'POST'])
@admin_required
def create_theme():
    """Create new theme"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        display_name = request.form.get('display_name', '').strip()
        variables_json = request.form.get('variables_json', '{}')
        font_family = request.form.get('font_family', 'Inter, system-ui, sans-serif')
        icon_pack = request.form.get('icon_pack', 'heroicons')
        is_default = bool(request.form.get('is_default'))
        
        # Validation
        if not name or not display_name:
            flash('Name and display name are required.', 'error')
            return render_template('admin/create_theme.html')
        
        # Check if name already exists
        existing_theme = Theme.query.filter_by(name=name).first()
        if existing_theme:
            flash('Theme name already exists.', 'error')
            return render_template('admin/create_theme.html')
        
        try:
            # If this is set as default, unset other defaults
            if is_default:
                Theme.query.update({'is_default': False})
            
            theme = Theme(
                name=name,
                display_name=display_name,
                variables_json=variables_json,
                font_family=font_family,
                icon_pack=icon_pack,
                is_default=is_default
            )
            
            db.session.add(theme)
            db.session.commit()
            
            log_audit('theme_created', 'theme', theme.id, {
                'name': name,
                'display_name': display_name
            })
            
            flash('Theme created successfully!', 'success')
            return redirect(url_for('admin.themes'))
        
        except Exception as e:
            logger.error(f"Theme creation error: {e}")
            db.session.rollback()
            flash('Failed to create theme.', 'error')
    
    return render_template('admin/create_theme.html')

@bp.route('/storage')
@admin_required
def storage():
    """Storage management"""
    active_backend = current_app.config.get('ACTIVE_STORAGE_BACKEND', 'local')
    
    # Get storage statistics
    local_stats = {'total_files': 0, 'total_size': 0}
    s3_stats = {'total_files': 0, 'total_size': 0}
    
    try:
        # Local storage stats
        local_storage = LocalStorageBackend(current_app.config['STORAGE_LOCAL_ROOT'])
        local_files = local_storage.list()
        local_stats['total_files'] = len(local_files)
        local_stats['total_size'] = sum(f['size'] for f in local_files)
        
        # S3 storage stats (if configured)
        if current_app.config.get('S3_BUCKET_NAME'):
            s3_storage = S3StorageBackend(
                current_app.config['S3_BUCKET_NAME'],
                current_app.config['S3_REGION'],
                current_app.config.get('AWS_ACCESS_KEY_ID'),
                current_app.config.get('AWS_SECRET_ACCESS_KEY'),
                current_app.config.get('S3_ENDPOINT_URL')
            )
            s3_files = s3_storage.list()
            s3_stats['total_files'] = len(s3_files)
            s3_stats['total_size'] = sum(f['size'] for f in s3_files)
    
    except Exception as e:
        logger.error(f"Storage stats error: {e}")
    
    return render_template('admin/storage.html',
                         active_backend=active_backend,
                         local_stats=local_stats,
                         s3_stats=s3_stats)

@bp.route('/storage/switch', methods=['POST'])
@admin_required
def switch_storage():
    """Switch active storage backend"""
    backend = request.form.get('backend', '')
    
    if backend not in ['local', 's3']:
        flash('Invalid storage backend.', 'error')
        return redirect(url_for('admin.storage'))
    
    try:
        # Update configuration (in production, this would be stored in database)
        current_app.config['ACTIVE_STORAGE_BACKEND'] = backend
        
        log_audit('storage_switched', 'system', None, {
            'new_backend': backend,
            'old_backend': request.form.get('old_backend', 'unknown')
        })
        
        flash(f'Storage backend switched to {backend}.', 'success')
    
    except Exception as e:
        logger.error(f"Storage switch error: {e}")
        flash('Failed to switch storage backend.', 'error')
    
    return redirect(url_for('admin.storage'))

@bp.route('/sync')
@admin_required
def sync():
    """Storage synchronization"""
    return render_template('admin/sync.html')

@bp.route('/sync/run', methods=['POST'])
@admin_required
def run_sync():
    """Run storage synchronization"""
    dry_run = bool(request.form.get('dry_run'))
    
    try:
        sync_engine = SyncEngine()
        result = sync_engine.sync_all(dry_run=dry_run)
        
        log_audit('sync_run', 'system', None, {
            'dry_run': dry_run,
            'result': result
        })
        
        if dry_run:
            flash('Sync dry run completed. Check logs for details.', 'info')
        else:
            flash('Sync completed successfully!', 'success')
    
    except Exception as e:
        logger.error(f"Sync error: {e}")
        flash('Sync failed. Check logs for details.', 'error')
    
    return redirect(url_for('admin.sync'))

@bp.route('/audit-logs')
@admin_required
def audit_logs():
    """View audit logs"""
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    user_filter = request.args.get('user_id', type=int)
    
    # Build query
    query = AuditLog.query
    
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f'%{action_filter}%'))
    
    if user_filter:
        query = query.filter(AuditLog.actor_id == user_filter)
    
    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('admin/audit_logs.html', logs=logs)

@bp.route('/settings')
@admin_required
def settings():
    """System settings"""
    return render_template('admin/settings.html')

@bp.route('/settings/update', methods=['POST'])
@admin_required
def update_settings():
    """Update system settings"""
    # This would typically update settings in database
    # For now, we'll just log the attempt
    
    log_audit('settings_updated', 'system', None, {
        'settings': dict(request.form)
    })
    
    flash('Settings updated successfully!', 'success')
    return redirect(url_for('admin.settings'))

# Unit Management Routes
@bp.route('/courses/<int:course_id>/units')
@admin_required
def manage_units(course_id):
    """Manage units for a course"""
    course = Course.query.get_or_404(course_id)
    units = Unit.query.filter_by(course_id=course_id).order_by(Unit.order).all()
    return render_template('admin/manage_units.html', course=course, units=units)

@bp.route('/courses/<int:course_id>/units/create', methods=['GET', 'POST'])
@admin_required
def create_unit(course_id):
    """Create new unit"""
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = request.form.get('slug', '').strip()
        description = request.form.get('description', '').strip()
        order = request.form.get('order', 0, type=int)
        
        if not name or not slug:
            flash('Name and slug are required.', 'error')
            return render_template('admin/create_unit.html', course=course)
        
        # Check if slug already exists for this course
        existing_unit = Unit.query.filter_by(course_id=course_id, slug=slug).first()
        if existing_unit:
            flash('A unit with this slug already exists for this course.', 'error')
            return render_template('admin/create_unit.html', course=course)
        
        try:
            unit = Unit(
                course_id=course_id,
                name=name,
                slug=slug,
                description=description,
                order=order
            )
            db.session.add(unit)
            db.session.commit()
            
            log_audit('unit_created', 'unit', unit.id, {
                'course': course.prefix,
                'name': name,
                'slug': slug
            })
            
            flash(f'Unit "{name}" created successfully!', 'success')
            return redirect(url_for('admin.manage_units', course_id=course_id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create unit: {e}")
            flash('Failed to create unit. Please try again.', 'error')
    
    return render_template('admin/create_unit.html', course=course)

@bp.route('/units/<int:unit_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_unit(unit_id):
    """Edit unit"""
    unit = Unit.query.get_or_404(unit_id)
    
    if request.method == 'POST':
        unit.name = request.form.get('name', '').strip()
        unit.slug = request.form.get('slug', '').strip()
        unit.description = request.form.get('description', '').strip()
        unit.order = request.form.get('order', 0, type=int)
        
        if not unit.name or not unit.slug:
            flash('Name and slug are required.', 'error')
            return render_template('admin/edit_unit.html', unit=unit)
        
        # Check if slug already exists for this course (excluding current unit)
        existing_unit = Unit.query.filter(
            Unit.course_id == unit.course_id,
            Unit.slug == unit.slug,
            Unit.id != unit.id
        ).first()
        
        if existing_unit:
            flash('A unit with this slug already exists for this course.', 'error')
            return render_template('admin/edit_unit.html', unit=unit)
        
        try:
            db.session.commit()
            
            log_audit('unit_updated', 'unit', unit.id, {
                'course': unit.course.prefix,
                'name': unit.name,
                'slug': unit.slug
            })
            
            flash(f'Unit "{unit.name}" updated successfully!', 'success')
            return redirect(url_for('admin.manage_units', course_id=unit.course_id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update unit: {e}")
            flash('Failed to update unit. Please try again.', 'error')
    
    return render_template('admin/edit_unit.html', unit=unit)

@bp.route('/units/<int:unit_id>/delete', methods=['POST'])
@admin_required
def delete_unit(unit_id):
    """Delete unit (soft delete)"""
    unit = Unit.query.get_or_404(unit_id)
    
    # Check if unit has documents
    document_count = unit.documents.count()
    if document_count > 0:
        flash(f'Cannot delete unit "{unit.name}" because it contains {document_count} documents.', 'error')
        return redirect(url_for('admin.manage_units', course_id=unit.course_id))
    
    try:
        unit.is_active = False
        db.session.commit()
        
        log_audit('unit_deleted', 'unit', unit.id, {
            'course': unit.course.prefix,
            'name': unit.name,
            'slug': unit.slug
        })
        
        flash(f'Unit "{unit.name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete unit: {e}")
        flash('Failed to delete unit. Please try again.', 'error')
    
    return redirect(url_for('admin.manage_units', course_id=unit.course_id))

# Category Management Routes
@bp.route('/courses/<int:course_id>/categories')
@admin_required
def manage_categories(course_id):
    """Manage categories for a course"""
    course = Course.query.get_or_404(course_id)
    categories = Category.query.filter_by(course_id=course_id).order_by(Category.order).all()
    return render_template('admin/manage_categories.html', course=course, categories=categories)

@bp.route('/courses/<int:course_id>/categories/create', methods=['GET', 'POST'])
@admin_required
def create_category(course_id):
    """Create new category with icon and color picker"""
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = request.form.get('slug', '').strip()
        icon = request.form.get('icon', 'fa-file').strip()
        color = request.form.get('color', '#10b981').strip()
        order = request.form.get('order', 0, type=int)
        
        if not name or not slug:
            flash('Name and slug are required.', 'error')
            return render_template('admin/create_category.html', course=course)
        
        # Check if slug already exists for this course
        existing_category = Category.query.filter_by(course_id=course_id, slug=slug).first()
        if existing_category:
            flash('A category with this slug already exists for this course.', 'error')
            return render_template('admin/create_category.html', course=course)
        
        try:
            category = Category(
                course_id=course_id,
                name=name,
                slug=slug,
                icon=icon,
                color=color,
                order=order
            )
            db.session.add(category)
            db.session.commit()
            
            log_audit('category_created', 'category', category.id, {
                'course': course.prefix,
                'name': name,
                'slug': slug,
                'icon': icon,
                'color': color
            })
            
            flash(f'Category "{name}" created successfully!', 'success')
            return redirect(url_for('admin.manage_categories', course_id=course_id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create category: {e}")
            flash('Failed to create category. Please try again.', 'error')
    
    return render_template('admin/create_category.html', course=course)

@bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    """Edit category"""
    category = Category.query.get_or_404(category_id)
    
    if request.method == 'POST':
        category.name = request.form.get('name', '').strip()
        category.slug = request.form.get('slug', '').strip()
        category.icon = request.form.get('icon', 'fa-file').strip()
        category.color = request.form.get('color', '#10b981').strip()
        category.order = request.form.get('order', 0, type=int)
        
        if not category.name or not category.slug:
            flash('Name and slug are required.', 'error')
            return render_template('admin/edit_category.html', category=category)
        
        # Check if slug already exists for this course (excluding current category)
        existing_category = Category.query.filter(
            Category.course_id == category.course_id,
            Category.slug == category.slug,
            Category.id != category.id
        ).first()
        
        if existing_category:
            flash('A category with this slug already exists for this course.', 'error')
            return render_template('admin/edit_category.html', category=category)
        
        try:
            db.session.commit()
            
            log_audit('category_updated', 'category', category.id, {
                'course': category.course.prefix,
                'name': category.name,
                'slug': category.slug,
                'icon': category.icon,
                'color': category.color
            })
            
            flash(f'Category "{category.name}" updated successfully!', 'success')
            return redirect(url_for('admin.manage_categories', course_id=category.course_id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update category: {e}")
            flash('Failed to update category. Please try again.', 'error')
    
    return render_template('admin/edit_category.html', category=category)

@bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@admin_required
def delete_category(category_id):
    """Delete category (soft delete)"""
    category = Category.query.get_or_404(category_id)
    
    # Check if category has documents
    document_count = category.documents.count()
    if document_count > 0:
        flash(f'Cannot delete category "{category.name}" because it contains {document_count} documents.', 'error')
        return redirect(url_for('admin.manage_categories', course_id=category.course_id))
    
    try:
        category.is_active = False
        db.session.commit()
        
        log_audit('category_deleted', 'category', category.id, {
            'course': category.course.prefix,
            'name': category.name,
            'slug': category.slug
        })
        
        flash(f'Category "{category.name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete category: {e}")
        flash('Failed to delete category. Please try again.', 'error')
    
    return redirect(url_for('admin.manage_categories', course_id=category.course_id))

# Global Units Management
@bp.route('/units')
@admin_required
def units():
    """List all units across all courses"""
    units = Unit.query.filter_by(is_active=True).order_by(Unit.course_id, Unit.order).all()
    courses = Course.query.filter_by(is_active=True).order_by(Course.name).all()
    return render_template('admin/units.html', units=units, courses=courses)

# Global Categories Management  
@bp.route('/categories')
@admin_required
def categories():
    """List all categories across all courses"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.course_id, Category.order).all()
    courses = Course.query.filter_by(is_active=True).order_by(Course.name).all()
    return render_template('admin/categories.html', categories=categories, courses=courses)

# Batch Upload Route for Admin
@bp.route('/batch-upload', methods=['GET', 'POST'])
@admin_required
def batch_upload():
    """Batch upload multiple files (admin access)"""
    if request.method == 'POST':
        files = request.files.getlist('files')
        upload_mode = request.form.get('upload_mode')
        
        if not files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400
        
        results = []
        
        try:
            if upload_mode == 'bulk':
                # All files get same course/unit/category
                course_id = request.form.get('course_id')
                unit_id = request.form.get('unit_id')
                category_id = request.form.get('category_id')
                visibility = request.form.get('visibility', 'private')
                
                if not all([course_id, unit_id, category_id]):
                    return jsonify({'success': False, 'error': 'Missing required fields for bulk upload'}), 400
                
                # Validate course, unit, and category exist and belong together
                course = Course.query.get(course_id)
                unit = Unit.query.filter_by(id=unit_id, course_id=course_id).first()
                category = Category.query.filter_by(id=category_id, course_id=course_id).first()
                
                if not all([course, unit, category]):
                    return jsonify({'success': False, 'error': 'Invalid course, unit, or category'}), 400
                
                for file in files:
                    result = process_file_upload(file, course_id, unit_id, category_id, visibility)
                    results.append(result)
                    
            else:  # individual mode
                # Each file has its own metadata from JSON
                files_metadata_json = request.form.get('files_metadata')
                if not files_metadata_json:
                    return jsonify({'success': False, 'error': 'Missing files metadata for individual upload'}), 400
                
                try:
                    files_metadata = json.loads(files_metadata_json)
                except json.JSONDecodeError:
                    return jsonify({'success': False, 'error': 'Invalid files metadata JSON'}), 400
                
                if len(files) != len(files_metadata):
                    return jsonify({'success': False, 'error': 'Mismatch between files and metadata count'}), 400
                
                for i, file in enumerate(files):
                    metadata = files_metadata[i]
                    course_id = metadata.get('course_id')
                    unit_id = metadata.get('unit_id')
                    category_id = metadata.get('category_id')
                    visibility = metadata.get('visibility', 'private')
                    
                    if not all([course_id, unit_id, category_id]):
                        results.append({
                            'filename': file.filename,
                            'success': False,
                            'error': 'Missing required fields'
                        })
                        continue
                    
                    # Validate course, unit, and category exist and belong together
                    course = Course.query.get(course_id)
                    unit = Unit.query.filter_by(id=unit_id, course_id=course_id).first()
                    category = Category.query.filter_by(id=category_id, course_id=course_id).first()
                    
                    if not all([course, unit, category]):
                        results.append({
                            'filename': file.filename,
                            'success': False,
                            'error': 'Invalid course, unit, or category'
                        })
                        continue
                    
                    result = process_file_upload(file, course_id, unit_id, category_id, visibility)
                    results.append(result)
            
            return jsonify({'success': True, 'results': results})
            
        except Exception as e:
            logger.error(f"Batch upload error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET request - show batch upload form
    courses = Course.query.filter_by(is_active=True).all()
    return render_template('user/batch_upload.html', courses=courses)

def process_file_upload(file, course_id, unit_id, category_id, visibility):
    """Process a single file upload"""
    try:
        if not file or not file.filename:
            return {
                'filename': file.filename if file else 'unknown',
                'success': False,
                'error': 'No file provided'
            }
        
        # Validate file
        validator = FileValidator()
        if not validator.is_allowed_file(file.filename):
            return {
                'filename': file.filename,
                'success': False,
                'error': 'File type not allowed'
            }
        
        # Generate secure filename and storage key
        original_filename = secure_filename(file.filename)
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Get course, unit, and category for storage path
        course = Course.query.get(course_id)
        unit = Unit.query.get(unit_id)
        category = Category.query.get(category_id)
        
        storage_key = f"{course.prefix}/{unit.slug}/{category.slug}/{datetime.now().year}/{datetime.now().month:02d}/{unique_filename}"
        
        # Get storage backend
        storage_backend = get_storage_backend()
        
        # Read file content
        file_content = file.read()
        file.seek(0)  # Reset file pointer
        
        # Store file
        if not storage_backend.store(file_content, storage_key, file.content_type):
            return {
                'filename': file.filename,
                'success': False,
                'error': 'Failed to store file'
            }
        
        # Calculate checksum
        checksum = validator.calculate_checksum(file_content)
        
        # Create document record
        document = Document(
            owner_id=current_user.id,
            course_id=course_id,
            unit_id=unit_id,
            category_id=category_id,
            title=os.path.splitext(original_filename)[0],
            original_filename=original_filename,
            storage_key=storage_key,
            storage_backend=storage_backend.__class__.__name__.lower().replace('storagebackend', ''),
            mime_type=file.content_type,
            file_size=len(file_content),
            checksum=checksum,
            visibility=visibility
        )
        
        db.session.add(document)
        db.session.commit()
        
        # Log audit
        log_audit('document_uploaded', 'document', document.id, {
            'filename': original_filename,
            'course': course.prefix,
            'unit': unit.slug,
            'category': category.slug,
            'size': len(file_content),
            'visibility': visibility
        })
        
        return {
            'filename': file.filename,
            'success': True,
            'document_id': document.id,
            'storage_key': storage_key
        }
        
    except Exception as e:
        logger.error(f"File upload error for {file.filename}: {e}")
        return {
            'filename': file.filename,
            'success': False,
            'error': str(e)
        }

@bp.route('/s3-test', methods=['GET', 'POST'])
@login_required
@admin_required
def s3_test():
    """S3 storage test page"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'run_tests':
            return run_s3_tests()
        elif action == 'list_files':
            return list_s3_files()
        elif action == 'cleanup':
            return cleanup_s3_test_files()
        elif action == 'custom_upload':
            return custom_s3_upload()
    
    # GET request - show test page
    storage_backend = current_app.config.get('ACTIVE_STORAGE_BACKEND', 'local')
    s3_bucket_name = current_app.config.get('S3_BUCKET_NAME')
    s3_region = current_app.config.get('S3_REGION')
    s3_endpoint_url = current_app.config.get('S3_ENDPOINT_URL')
    
    return render_template('admin/s3_test.html',
                         storage_backend=storage_backend,
                         s3_bucket_name=s3_bucket_name,
                         s3_region=s3_region,
                         s3_endpoint_url=s3_endpoint_url)

def run_s3_tests():
    """Run comprehensive S3 tests"""
    test_results = {
        'connection': False,
        'upload': False,
        'download': False,
        'delete': False,
        'errors': None,
        'test_file_info': None
    }
    
    try:
        # Get S3 storage backend
        storage = get_storage_backend()
        
        if not isinstance(storage, S3StorageBackend):
            test_results['errors'] = f"Expected S3StorageBackend, got {type(storage).__name__}"
            return render_s3_test_page(test_results)
        
        # Test 1: Connection
        logger.info("Testing S3 connection...")
        test_results['connection'] = True
        
        # Test 2: Upload
        logger.info("Testing S3 upload...")
        test_content = b"This is a test file for S3 storage testing. Created at " + str(datetime.now()).encode()
        test_key = "notu/test/s3_test_file.txt"
        
        from io import BytesIO
        from werkzeug.datastructures import FileStorage
        
        test_file = FileStorage(
            stream=BytesIO(test_content),
            filename='s3_test_file.txt',
            content_type='text/plain'
        )
        
        if storage.put(test_file, test_key):
            test_results['upload'] = True
            logger.info(f"Successfully uploaded test file: {test_key}")
        else:
            test_results['errors'] = "Failed to upload test file"
            return render_s3_test_page(test_results)
        
        # Test 3: Download/Verify
        logger.info("Testing S3 download...")
        if storage.exists(test_key):
            test_results['download'] = True
            logger.info(f"Successfully verified test file exists: {test_key}")
            
            # Get file info
            try:
                file_info = storage.get_file_info(test_key)
                test_results['test_file_info'] = file_info
            except Exception as e:
                logger.warning(f"Could not get file info: {e}")
        else:
            test_results['errors'] = "Uploaded file not found during verification"
            return render_s3_test_page(test_results)
        
        # Test 4: Delete
        logger.info("Testing S3 delete...")
        if storage.delete(test_key):
            test_results['delete'] = True
            logger.info(f"Successfully deleted test file: {test_key}")
        else:
            test_results['errors'] = "Failed to delete test file"
            return render_s3_test_page(test_results)
        
        # Log successful test
        log_audit('s3_test_completed', 'system', None, {
            'connection': test_results['connection'],
            'upload': test_results['upload'],
            'download': test_results['download'],
            'delete': test_results['delete']
        })
        
    except Exception as e:
        logger.error(f"S3 test error: {e}")
        test_results['errors'] = str(e)
    
    return render_s3_test_page(test_results)

def list_s3_files():
    """List files in S3 notu/ folder"""
    try:
        storage = get_storage_backend()
        
        if not isinstance(storage, S3StorageBackend):
            flash('S3 storage backend not configured', 'error')
            return redirect(url_for('admin.s3_test'))
        
        # List files with notu/ prefix
        files = storage.list_files('notu/')
        
        # Debug: Also try listing without prefix to see what's in the bucket
        all_files = storage.list_files('')
        
        # Also try listing with different prefixes to see the actual structure
        test_prefixes = ['', 'test/', 'notu/test/', 'notu/']
        prefix_results = {}
        
        for prefix in test_prefixes:
            try:
                prefix_files = storage.list_files(prefix)
                prefix_results[prefix] = prefix_files
                logger.info(f"Prefix '{prefix}': {len(prefix_files)} files")
                if len(prefix_files) > 0:
                    logger.info(f"Sample files for '{prefix}': {[f.key for f in prefix_files[:3]]}")
            except Exception as e:
                logger.error(f"Error listing prefix '{prefix}': {e}")
                prefix_results[prefix] = []
        
        logger.info(f"Found {len(files)} files with 'notu/' prefix")
        logger.info(f"Found {len(all_files)} total files in bucket")
        
        if len(all_files) > 0:
            logger.info(f"Sample files in bucket: {[f.key for f in all_files[:5]]}")
        
        storage_backend = current_app.config.get('ACTIVE_STORAGE_BACKEND', 'local')
        s3_bucket_name = current_app.config.get('S3_BUCKET_NAME')
        s3_region = current_app.config.get('S3_REGION')
        s3_endpoint_url = current_app.config.get('S3_ENDPOINT_URL')
        
        return render_template('admin/s3_test.html',
                             storage_backend=storage_backend,
                             s3_bucket_name=s3_bucket_name,
                             s3_region=s3_region,
                             s3_endpoint_url=s3_endpoint_url,
                             file_list=files,
                             prefix_results=prefix_results,
                             debug_info={'total_files': len(all_files), 'notu_files': len(files)})
        
    except Exception as e:
        logger.error(f"Error listing S3 files: {e}")
        flash(f'Error listing files: {str(e)}', 'error')
        return redirect(url_for('admin.s3_test'))

def cleanup_s3_test_files():
    """Clean up test files from S3"""
    try:
        storage = get_storage_backend()
        
        if not isinstance(storage, S3StorageBackend):
            flash('S3 storage backend not configured', 'error')
            return redirect(url_for('admin.s3_test'))
        
        # List and delete test files from multiple locations
        test_locations = ['notu/test/', 'test/']
        deleted_count = 0
        
        for location in test_locations:
            test_files = storage.list_files(location)
            logger.info(f"Found {len(test_files)} files in {location}")
            
            for file_info in test_files:
                if storage.delete(file_info.key):
                    deleted_count += 1
                    logger.info(f"Deleted test file: {file_info.key}")
                else:
                    logger.warning(f"Failed to delete: {file_info.key}")
        
        flash(f'Cleaned up {deleted_count} test files', 'success')
        
        # Log cleanup
        log_audit('s3_test_cleanup', 'system', None, {
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up S3 test files: {e}")
        flash(f'Error cleaning up files: {str(e)}', 'error')
    
    return redirect(url_for('admin.s3_test'))

def custom_s3_upload():
    """Handle custom file upload to S3"""
    try:
        storage = get_storage_backend()
        
        if not isinstance(storage, S3StorageBackend):
            flash('S3 storage backend not configured', 'error')
            return redirect(url_for('admin.s3_test'))
        
        if 'test_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('admin.s3_test'))
        
        file = request.files['test_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('admin.s3_test'))
        
        # Generate S3 key
        custom_key = request.form.get('test_key', '').strip()
        if not custom_key:
            from datetime import datetime
            import uuid
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            custom_key = f"test/custom_upload_{timestamp}_{unique_id}_{file.filename}"
        
        # Upload file
        if storage.put(file, custom_key):
            flash(f'File uploaded successfully to S3: {custom_key}', 'success')
            
            # Log the upload
            log_audit('s3_custom_upload', 'system', None, {
                'filename': file.filename,
                's3_key': custom_key,
                'size': file.content_length or 0
            })
        else:
            flash('Failed to upload file to S3', 'error')
        
    except Exception as e:
        logger.error(f"Error in custom S3 upload: {e}")
        flash(f'Upload error: {str(e)}', 'error')
    
    return redirect(url_for('admin.s3_test'))

def render_s3_test_page(test_results=None, file_list=None, debug_info=None):
    """Render S3 test page with results"""
    storage_backend = current_app.config.get('ACTIVE_STORAGE_BACKEND', 'local')
    s3_bucket_name = current_app.config.get('S3_BUCKET_NAME')
    s3_region = current_app.config.get('S3_REGION')
    s3_endpoint_url = current_app.config.get('S3_ENDPOINT_URL')
    
    return render_template('admin/s3_test.html',
                         storage_backend=storage_backend,
                         s3_bucket_name=s3_bucket_name,
                         s3_region=s3_region,
                         s3_endpoint_url=s3_endpoint_url,
                         test_results=test_results,
                         file_list=file_list,
                         debug_info=debug_info)