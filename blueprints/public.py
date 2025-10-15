"""
Public blueprint for unauthenticated pages
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_file, Response
from flask_login import current_user, login_required
from models import Course, Document, Theme, Unit, Category
from services.auth import log_audit
from services.storage import get_storage_backend
from sqlalchemy import or_
from app import db
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('public', __name__)

@bp.route('/')
def index():
    """Landing page with theme selector and featured content"""
    # Get active themes
    themes = Theme.query.filter_by(is_active=True).all()
    
    # Get featured public documents (recent uploads)
    featured_docs = Document.query.filter_by(visibility='public').order_by(
        Document.created_at.desc()
    ).limit(6).all()
    
    # Get course statistics
    total_courses = Course.query.filter_by(is_active=True).count()
    total_documents = Document.query.filter_by(visibility='public').count()
    
    return render_template('public/index.html', 
                         themes=themes,
                         featured_docs=featured_docs,
                         total_courses=total_courses,
                         total_documents=total_documents)

@bp.route('/courses')
def courses():
    """List all active courses"""
    courses = Course.query.filter_by(is_active=True).order_by(Course.name).all()
    
    # Get document counts per course using the new category relationship
    course_stats = {}
    for course in courses:
        # Get all categories for this course
        categories = Category.query.filter_by(course_id=course.id, is_active=True).all()
        category_counts = {}
        
        for category in categories:
            count = Document.query.filter_by(
                course_id=course.id, 
                category_id=category.id, 
                visibility='public'
            ).count()
            category_counts[category.slug] = count
        
        course_stats[course.id] = {
            'total': Document.query.filter_by(course_id=course.id, visibility='public').count(),
            'notes': category_counts.get('notes', 0),
            'assignments': category_counts.get('assignments', 0),
            'lectures': category_counts.get('lectures', 0),
            'exams': category_counts.get('exams', 0),
            'projects': category_counts.get('projects', 0),
            'others': category_counts.get('others', 0)
        }
    
    return render_template('public/courses.html', courses=courses, course_stats=course_stats)

@bp.route('/c/<prefix>')
def course_overview(prefix):
    """Course overview page with pagination and search"""
    course = Course.query.filter_by(prefix=prefix, is_active=True).first_or_404()
    
    # Get search and filter parameters
    search_query = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # Build documents query
    documents_query = Document.query.filter_by(
        course_id=course.id,
        visibility='public'
    )
    
    # Apply category filter if specified
    if category_filter and category_filter in ['notes', 'assignments', 'lectures', 'exams', 'projects', 'others']:
        # Find the category by slug
        category_obj = Category.query.filter_by(course_id=course.id, slug=category_filter, is_active=True).first()
        if category_obj:
            documents_query = documents_query.filter_by(category_id=category_obj.id)
    
    # Apply search filter if specified
    if search_query:
        documents_query = documents_query.filter(
            or_(
                Document.title.ilike(f'%{search_query}%'),
                Document.original_filename.ilike(f'%{search_query}%')
            )
        )
    
    # Get paginated documents
    documents = documents_query.order_by(Document.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get document counts by category
    categories = ['notes', 'assignments', 'lectures', 'exams', 'projects', 'others']
    category_stats = {}
    
    for category_slug in categories:
        category_obj = Category.query.filter_by(course_id=course.id, slug=category_slug, is_active=True).first()
        if category_obj:
            category_stats[category_slug] = Document.query.filter_by(
                course_id=course.id, 
                category_id=category_obj.id, 
                visibility='public'
            ).count()
        else:
            category_stats[category_slug] = 0
    
    return render_template('public/course_overview.html', 
                         course=course, 
                         documents=documents,
                         category_stats=category_stats,
                         search_query=search_query,
                         category_filter=category_filter)

@bp.route('/c/<prefix>/<category>')
def course_category(prefix, category):
    """List documents in a specific course category"""
    if category not in ['notes', 'assignments', 'lectures', 'exams', 'projects', 'others']:
        abort(404)
    
    course = Course.query.filter_by(prefix=prefix, is_active=True).first_or_404()
    
    # Find the category by slug
    category_obj = Category.query.filter_by(course_id=course.id, slug=category, is_active=True).first()
    if not category_obj:
        abort(404)
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    documents = Document.query.filter_by(
        course_id=course.id,
        category_id=category_obj.id,
        visibility='public'
    ).order_by(Document.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('public/course_category.html',
                         course=course,
                         category=category,
                         documents=documents)

@bp.route('/view/<int:doc_id>')
def view_document(doc_id):
    """View document inline (if allowed)"""
    document = Document.query.get_or_404(doc_id)
    
    # Check access permissions
    if not document.can_access(current_user):
        flash('You do not have permission to view this document.', 'error')
        return redirect(url_for('public.index'))
    
    # Log view
    log_audit('document_viewed', 'document', doc_id, {
        'title': document.title,
        'course': document.course.prefix,
        'category': document.category_obj.slug if document.category_obj else 'unknown'
    })
    
    # Get storage backend
    storage = get_storage_backend(document.storage_backend)
    
    # Check if we can display inline
    can_display_inline = document.mime_type in ['application/pdf', 'text/plain']
    is_document_file = document.mime_type in [
        'application/pdf', 
        'text/plain',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    
    if can_display_inline and document.mime_type == 'application/pdf':
        # For PDFs, we'll embed them
        # Get related documents from the same course
        related_documents = Document.query.filter(
            Document.course_id == document.course_id,
            Document.id != document.id,
            Document.visibility == 'public'
        ).order_by(Document.created_at.desc()).limit(5).all()
        
        return render_template('public/view_pdf.html', 
                             document=document, 
                             related_documents=related_documents)
    elif can_display_inline and document.mime_type == 'text/plain':
        # For text files, display content
        try:
            stream = storage.stream(document.storage_key)
            if stream:
                content = b''.join(stream).decode('utf-8', errors='ignore')
                return render_template('public/view_text.html', 
                                     document=document, 
                                     content=content)
        except Exception as e:
            logger.error(f"Failed to read text file {doc_id}: {e}")
            flash('Failed to display file content.', 'error')
    
    # For document files (DOCX, DOC) or other files, show preview page
    if is_document_file:
        # Get related documents from the same course
        related_documents = Document.query.filter(
            Document.course_id == document.course_id,
            Document.id != document.id,
            Document.visibility == 'public'
        ).order_by(Document.created_at.desc()).limit(5).all()
        
        return render_template('public/view_pdf.html', 
                             document=document, 
                             related_documents=related_documents)
    
    # Fallback to download for other file types
    return redirect(url_for('public.download_document', doc_id=doc_id))

@bp.route('/serve/<int:doc_id>')
def serve_document(doc_id):
    """Serve document content directly for embedding"""
    document = Document.query.get_or_404(doc_id)
    
    # Check access permissions
    if not document.can_access(current_user):
        abort(403)
    
    # Get storage backend
    storage = get_storage_backend(document.storage_backend)
    
    try:
        # Stream the file content
        stream = storage.stream(document.storage_key)
        if not stream:
            abort(404)
        
        # Create response with proper headers to prevent IDM interception
        response = Response(stream, mimetype=document.mime_type)
        response.headers['Content-Disposition'] = f'inline; filename="{document.original_filename}"'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Add CORS headers for PDF.js
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        response.headers['Access-Control-Allow-Headers'] = 'Range, Content-Range'
        
        # Add Range support for PDF.js
        response.headers['Accept-Ranges'] = 'bytes'
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to serve document {doc_id}: {e}")
        abort(500)

@bp.route('/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_document(doc_id):
    """Delete document"""
    document = Document.query.get_or_404(doc_id)
    
    # Check permissions - only owner or admin can delete
    if current_user.id != document.owner_id and current_user.role != 'admin':
        flash('You do not have permission to delete this document.', 'error')
        return redirect(url_for('public.view_document', doc_id=doc_id))
    
    try:
        # Store course prefix before deletion (needed for redirect)
        course_prefix = document.course.prefix
        
        # Get storage backend
        storage = get_storage_backend(document.storage_backend)
        
        # Delete from storage
        if storage.exists(document.storage_key):
            storage.delete(document.storage_key)
        
        # Log deletion
        log_audit('document_deleted', 'document', doc_id, {
            'title': document.title,
            'course': course_prefix,
            'category': document.category_obj.slug if document.category_obj else 'unknown',
            'filename': document.original_filename
        })
        
        # Delete from database
        db.session.delete(document)
        db.session.commit()
        
        flash('Document deleted successfully.', 'success')
        return redirect(url_for('public.course_overview', prefix=course_prefix))
        
    except Exception as e:
        logger.error(f"Failed to delete document {doc_id}: {e}")
        flash('Failed to delete document.', 'error')
        return redirect(url_for('public.view_document', doc_id=doc_id))

@bp.route('/download/<int:doc_id>')
def download_document(doc_id):
    """Download document"""
    document = Document.query.get_or_404(doc_id)
    
    # Check access permissions
    if not document.can_access(current_user):
        flash('You do not have permission to download this document.', 'error')
        return redirect(url_for('public.index'))
    
    # Log download
    log_audit('document_downloaded', 'document', doc_id, {
        'title': document.title,
        'course': document.course.prefix,
        'category': document.category_obj.slug if document.category_obj else 'unknown'
    })
    
    # Get storage backend
    storage = get_storage_backend(document.storage_backend)
    
    try:
        # Get file stream
        stream = storage.stream(document.storage_key)
        if not stream:
            flash('File not found.', 'error')
            return redirect(url_for('public.index'))
        
        # Create response with appropriate headers
        response = Response(stream, mimetype=document.mime_type)
        response.headers['Content-Disposition'] = f'attachment; filename="{document.original_filename}"'
        response.headers['Content-Length'] = str(document.file_size)
        
        return response
    
    except Exception as e:
        logger.error(f"Failed to download document {doc_id}: {e}")
        flash('Failed to download file.', 'error')
        return redirect(url_for('public.index'))

@bp.route('/search')
def search():
    """Search public documents"""
    query = request.args.get('q', '').strip()
    course_prefix = request.args.get('course', '')
    category = request.args.get('category', '')
    
    # Get all courses for the filter dropdown
    courses = Course.query.filter_by(is_active=True).order_by(Course.name).all()
    
    if not query:
        return render_template('public/search.html', results=[], query='', courses=courses)
    
    # Build search query
    search_query = Document.query.filter_by(visibility='public')
    
    # Filter by course if specified
    if course_prefix:
        course = Course.query.filter_by(prefix=course_prefix, is_active=True).first()
        if course:
            search_query = search_query.filter_by(course_id=course.id)
    
    # Filter by category if specified
    if category and category in ['notes', 'assignments', 'lectures', 'exams', 'projects', 'others']:
        # Find category by slug for the course if specified
        if course_prefix:
            course = Course.query.filter_by(prefix=course_prefix, is_active=True).first()
            if course:
                category_obj = Category.query.filter_by(course_id=course.id, slug=category, is_active=True).first()
                if category_obj:
                    search_query = search_query.filter_by(category_id=category_obj.id)
        else:
            # Search across all courses for this category
            category_objs = Category.query.filter_by(slug=category, is_active=True).all()
            if category_objs:
                category_ids = [cat.id for cat in category_objs]
                search_query = search_query.filter(Document.category_id.in_(category_ids))
    
    # Search in title and filename
    search_query = search_query.filter(
        or_(
            Document.title.ilike(f'%{query}%'),
            Document.original_filename.ilike(f'%{query}%')
        )
    )
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    results = search_query.order_by(Document.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('public/search.html', 
                         results=results, 
                         query=query,
                         course_prefix=course_prefix,
                         category=category,
                         courses=courses)

@bp.route('/theme/<theme_name>')
def set_theme(theme_name):
    """Set active theme"""
    theme = Theme.query.filter_by(name=theme_name, is_active=True).first()
    
    if theme:
        # Store theme preference in session
        session['active_theme'] = theme_name
        flash(f'Theme changed to {theme.display_name}', 'success')
    else:
        flash('Theme not found.', 'error')
    
    # Redirect back to referring page or home
    return redirect(request.referrer or url_for('public.index'))
