"""
API blueprint for frontend interactions
"""
from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from models import Document, Course, Theme, User, Unit, Category
from services.auth import admin_required, log_audit
from services.storage import get_storage_backend
from app import db
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('api', __name__)

@bp.route('/documents/<int:doc_id>/toggle-privacy', methods=['POST'])
@login_required
def toggle_document_privacy(doc_id):
    """Toggle document privacy via API"""
    document = Document.query.get_or_404(doc_id)
    
    # Check ownership
    if document.owner_id != current_user.id and not current_user.is_admin():
        abort(403)
    
    new_visibility = 'public' if document.visibility == 'private' else 'private'
    old_visibility = document.visibility
    
    document.visibility = new_visibility
    db.session.commit()
    
    log_audit('privacy_toggled', 'document', doc_id, {
        'old_visibility': old_visibility,
        'new_visibility': new_visibility,
        'title': document.title
    })
    
    return jsonify({
        'success': True,
        'new_visibility': new_visibility,
        'message': f'Document visibility changed to {new_visibility}'
    })

@bp.route('/documents/<int:doc_id>/delete', methods=['DELETE'])
@login_required
def delete_document_api(doc_id):
    """Delete document via API"""
    document = Document.query.get_or_404(doc_id)
    
    # Check ownership
    if document.owner_id != current_user.id and not current_user.is_admin():
        abort(403)
    
    try:
        # Store course prefix before deletion (needed for logging)
        course_prefix = document.course.prefix
        
        # Delete from storage
        storage = get_storage_backend(document.storage_backend)
        storage.delete(document.storage_key)
        
        # Log deletion
        log_audit('document_deleted_api', 'document', doc_id, {
            'title': document.title,
            'course': course_prefix,
            'category': document.category
        })
        
        # Delete from database
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Document deleted successfully'
        })
    
    except Exception as e:
        logger.error(f"API delete error: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Failed to delete document'
        }), 500

@bp.route('/courses/<int:course_id>/documents')
def get_course_documents(course_id):
    """Get documents for a course via API"""
    course = Course.query.get_or_404(course_id)
    
    # Get query parameters
    category = request.args.get('category', '')
    visibility = request.args.get('visibility', 'public')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    # Build query
    query = Document.query.filter_by(course_id=course_id)
    
    if category and category in ['notes', 'assignments', 'lectures', 'exams', 'projects', 'others']:
        query = query.filter_by(category=category)
    
    if visibility == 'public':
        query = query.filter_by(visibility='public')
    elif visibility == 'private' and current_user.is_authenticated:
        query = query.filter_by(owner_id=current_user.id, visibility='private')
    elif visibility == 'all' and current_user.is_authenticated:
        # Show all documents user can access
        if not current_user.is_admin():
            query = query.filter(
                (Document.visibility == 'public') |
                (Document.owner_id == current_user.id)
            )
    
    documents = query.order_by(Document.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'documents': [{
            'id': doc.id,
            'title': doc.title,
            'original_filename': doc.original_filename,
            'category': doc.category_obj.slug,
            'visibility': doc.visibility,
            'file_size': doc.file_size,
            'mime_type': doc.mime_type,
            'created_at': doc.created_at.isoformat(),
            'owner': {
                'id': doc.owner.id,
                'email': doc.owner.email
            } if doc.owner else None
        } for doc in documents.items],
        'pagination': {
            'page': documents.page,
            'pages': documents.pages,
            'per_page': documents.per_page,
            'total': documents.total,
            'has_next': documents.has_next,
            'has_prev': documents.has_prev
        }
    })

@bp.route('/themes')
def get_themes():
    """Get available themes via API"""
    themes = Theme.query.filter_by(is_active=True).all()
    
    return jsonify({
        'themes': [{
            'id': theme.id,
            'name': theme.name,
            'display_name': theme.display_name,
            'variables': theme.get_variables(),
            'font_family': theme.font_family,
            'icon_pack': theme.icon_pack,
            'is_default': theme.is_default
        } for theme in themes]
    })

@bp.route('/themes/<theme_name>/variables')
def get_theme_variables(theme_name):
    """Get theme variables via API"""
    theme = Theme.query.filter_by(name=theme_name, is_active=True).first()
    
    if not theme:
        abort(404)
    
    return jsonify({
        'name': theme.name,
        'display_name': theme.display_name,
        'variables': theme.get_variables(),
        'font_family': theme.font_family,
        'icon_pack': theme.icon_pack
    })

@bp.route('/user/stats')
@login_required
def get_user_stats():
    """Get user statistics via API"""
    from services.auth import get_user_stats
    
    stats = get_user_stats(current_user.id)
    
    return jsonify({
        'stats': stats,
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'role': current_user.role,
            'created_at': current_user.created_at.isoformat()
        }
    })

@bp.route('/admin/stats')
@admin_required
def get_admin_stats():
    """Get admin statistics via API"""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_courses = Course.query.filter_by(is_active=True).count()
    total_documents = Document.query.count()
    public_documents = Document.query.filter_by(visibility='public').count()
    
    # Get storage statistics
    total_storage = db.session.query(db.func.sum(Document.file_size)).scalar() or 0
    
    return jsonify({
        'users': {
            'total': total_users,
            'active': active_users
        },
        'courses': {
            'total': total_courses
        },
        'documents': {
            'total': total_documents,
            'public': public_documents,
            'private': total_documents - public_documents
        },
        'storage': {
            'total_bytes': total_storage,
            'total_mb': round(total_storage / (1024 * 1024), 2)
        }
    })

@bp.route('/search')
def search_documents():
    """Search documents via API"""
    query = request.args.get('q', '').strip()
    course_prefix = request.args.get('course', '')
    category = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    if not query:
        return jsonify({'documents': [], 'pagination': {}})
    
    # Build search query
    search_query = Document.query.filter_by(visibility='public')
    
    # Filter by course if specified
    if course_prefix:
        course = Course.query.filter_by(prefix=course_prefix, is_active=True).first()
        if course:
            search_query = search_query.filter_by(course_id=course.id)
    
    # Filter by category if specified
    if category and category in ['notes', 'assignments', 'lectures', 'exams', 'projects', 'others']:
        search_query = search_query.filter_by(category=category)
    
    # Search in title and filename
    from sqlalchemy import or_
    search_query = search_query.filter(
        or_(
            Document.title.ilike(f'%{query}%'),
            Document.original_filename.ilike(f'%{query}%')
        )
    )
    
    results = search_query.order_by(Document.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'documents': [{
            'id': doc.id,
            'title': doc.title,
            'original_filename': doc.original_filename,
            'category': doc.category_obj.slug,
            'file_size': doc.file_size,
            'mime_type': doc.mime_type,
            'created_at': doc.created_at.isoformat(),
            'course': {
                'id': doc.course.id,
                'name': doc.course.name,
                'prefix': doc.course.prefix
            },
            'owner': {
                'id': doc.owner.id,
                'email': doc.owner.email
            }
        } for doc in results.items],
        'pagination': {
            'page': results.page,
            'pages': results.pages,
            'per_page': results.per_page,
            'total': results.total,
            'has_next': results.has_next,
            'has_prev': results.has_prev
        }
    })

@bp.route('/sync/status')
@admin_required
def get_sync_status():
    """Get sync status via API"""
    # This would typically check the status of a background sync job
    # For now, return a simple status
    return jsonify({
        'status': 'idle',
        'last_sync': None,
        'next_sync': None
    })

@bp.errorhandler(404)
def api_not_found(error):
    """API 404 handler"""
    return jsonify({'error': 'Not found'}), 404

@bp.errorhandler(403)
def api_forbidden(error):
    """API 403 handler"""
    return jsonify({'error': 'Forbidden'}), 403

@bp.errorhandler(500)
def api_internal_error(error):
    """API 500 handler"""
    return jsonify({'error': 'Internal server error'}), 500

# Course Management API Endpoints
@bp.route('/courses')
def get_courses():
    """Get all active courses"""
    courses = Course.query.filter_by(is_active=True).order_by(Course.name).all()
    return jsonify([{
        'id': course.id,
        'name': course.name,
        'prefix': course.prefix,
        'description': course.description
    } for course in courses])

@bp.route('/courses/<int:course_id>/units')
def get_course_units(course_id):
    """Get units for a course"""
    course = Course.query.get_or_404(course_id)
    units = Unit.query.filter_by(course_id=course_id, is_active=True).order_by(Unit.order).all()
    return jsonify([{
        'id': unit.id,
        'name': unit.name,
        'slug': unit.slug,
        'description': unit.description,
        'order': unit.order
    } for unit in units])

@bp.route('/courses/<int:course_id>/categories')
def get_course_categories(course_id):
    """Get categories for a course"""
    course = Course.query.get_or_404(course_id)
    categories = Category.query.filter_by(course_id=course_id, is_active=True).order_by(Category.order).all()
    return jsonify([{
        'id': category.id,
        'name': category.name,
        'slug': category.slug,
        'icon': category.icon,
        'color': category.color,
        'order': category.order
    } for category in categories])

@bp.route('/units/<int:unit_id>')
def get_unit(unit_id):
    """Get a specific unit"""
    unit = Unit.query.get_or_404(unit_id)
    return jsonify({
        'id': unit.id,
        'name': unit.name,
        'slug': unit.slug,
        'description': unit.description,
        'order': unit.order,
        'course_id': unit.course_id,
        'course_name': unit.course.name,
        'course_prefix': unit.course.prefix
    })

@bp.route('/categories/<int:category_id>')
def get_category(category_id):
    """Get a specific category"""
    category = Category.query.get_or_404(category_id)
    return jsonify({
        'id': category.id,
        'name': category.name,
        'slug': category.slug,
        'icon': category.icon,
        'color': category.color,
        'order': category.order,
        'course_id': category.course_id,
        'course_name': category.course.name,
        'course_prefix': category.course.prefix
    })

# Document Management API Endpoints
@bp.route('/documents')
@login_required
def get_documents():
    """Get documents for the current user with filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    course_id = request.args.get('course_id', type=int)
    unit_id = request.args.get('unit_id', type=int)
    category_id = request.args.get('category_id', type=int)
    visibility = request.args.get('visibility')
    
    query = Document.query.filter_by(owner_id=current_user.id)
    
    if course_id:
        query = query.filter_by(course_id=course_id)
    if unit_id:
        query = query.filter_by(unit_id=unit_id)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if visibility:
        query = query.filter_by(visibility=visibility)
    
    documents = query.order_by(Document.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'documents': [{
            'id': doc.id,
            'title': doc.title,
            'original_filename': doc.original_filename,
            'mime_type': doc.mime_type,
            'file_size': doc.file_size,
            'visibility': doc.visibility,
            'created_at': doc.created_at.isoformat(),
            'course': {
                'id': doc.course.id,
                'name': doc.course.name,
                'prefix': doc.course.prefix
            },
            'unit': {
                'id': doc.unit.id,
                'name': doc.unit.name,
                'slug': doc.unit.slug
            },
            'category': {
                'id': doc.category_obj.id,
                'name': doc.category_obj.name,
                'slug': doc.category_obj.slug,
                'icon': doc.category_obj.icon,
                'color': doc.category_obj.color
            }
        } for doc in documents.items],
        'pagination': {
            'page': documents.page,
            'pages': documents.pages,
            'per_page': documents.per_page,
            'total': documents.total,
            'has_next': documents.has_next,
            'has_prev': documents.has_prev
        }
    })
