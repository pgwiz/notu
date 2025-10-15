"""
User dashboard blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from models import Document, Course, User, Unit, Category
from services.auth import log_audit, get_user_stats
from services.storage import get_storage_backend
from services.security import FileValidator, AntivirusScanner
from werkzeug.utils import secure_filename
from app import db, csrf
import os
import uuid
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('user', __name__)

@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    # Get user statistics
    stats = get_user_stats(current_user.id)
    
    # Get recent uploads
    recent_docs = Document.query.filter_by(owner_id=current_user.id).order_by(
        Document.created_at.desc()
    ).limit(10).all()
    
    # Get courses for upload form
    courses = Course.query.filter_by(is_active=True).order_by(Course.name).all()
    
    return render_template('user/dashboard.html', 
                         stats=stats, 
                         recent_docs=recent_docs,
                         courses=courses)

@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload new document"""
    if request.method == 'POST':
        # Validate form data
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('user.upload'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('user.upload'))
        
        course_id = request.form.get('course_id', type=int)
        unit_id = request.form.get('unit_id', type=int)
        category_id = request.form.get('category_id', type=int)
        title = request.form.get('title', '').strip()
        visibility = request.form.get('visibility', 'private')
        
        # Validation
        if not all([course_id, unit_id, category_id, title]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('user.upload'))
        
        if visibility not in ['public', 'private']:
            visibility = 'private'
        
        # Get course, unit, and category
        course = Course.query.get(course_id)
        unit = Unit.query.filter_by(id=unit_id, course_id=course_id).first()
        category = Category.query.filter_by(id=category_id, course_id=course_id).first()
        
        if not all([course, unit, category]):
            flash('Invalid course, unit, or category selected.', 'error')
            return redirect(url_for('user.upload'))
        
        if not course.is_active:
            flash('Course is not active.', 'error')
            return redirect(url_for('user.upload'))
        
        # Validate file
        validator = FileValidator()
        is_valid, error_msg = validator.validate_file(file)
        
        if not is_valid:
            flash(f'File validation failed: {error_msg}', 'error')
            return redirect(url_for('user.upload'))
        
        try:
            # Generate storage key
            year = datetime.now().year
            month = f"{datetime.now().month:02d}"
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            storage_key = f"{course.prefix}/{unit.slug}/{category.slug}/{year}/{month}/{unique_filename}"
            
            # Get active storage backend
            storage = get_storage_backend()
            
            # Store file
            if not storage.put(file, storage_key):
                flash('Failed to store file.', 'error')
                return redirect(url_for('user.upload'))
            
            # Get file info
            file_size = file.content_length or 0
            checksum = validator.get_file_checksum(file)
            
            # Create document record
            document = Document(
                owner_id=current_user.id,
                course_id=course_id,
                unit_id=unit_id,
                category_id=category_id,
                title=title,
                original_filename=file.filename,
                storage_key=storage_key,
                storage_backend=storage.__class__.__name__.lower().replace('storagebackend', ''),
                mime_type=file.content_type or 'application/octet-stream',
                file_size=file_size,
                checksum=checksum,
                visibility=visibility
            )
            
            db.session.add(document)
            db.session.commit()
            
            # Log upload
            log_audit('document_uploaded', 'document', document.id, {
                'title': title,
                'course': course.prefix,
                'unit': unit.slug,
                'category': category.slug,
                'filename': file.filename,
                'size': file_size,
                'visibility': visibility
            })
            
            flash('File uploaded successfully!', 'success')
            return redirect(url_for('user.upload_summary', doc_id=document.id))
        
        except Exception as e:
            logger.error(f"Upload error: {e}")
            db.session.rollback()
            flash('Upload failed. Please try again.', 'error')
    
    # GET request - show upload form
    courses = Course.query.filter_by(is_active=True).order_by(Course.name).all()
    return render_template('user/upload.html', courses=courses)

@bp.route('/upload-summary/<int:doc_id>')
@login_required
def upload_summary(doc_id):
    """Show upload summary with storage information"""
    document = Document.query.get_or_404(doc_id)
    
    # Check if user owns the document or is admin
    if document.owner_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to view this document.', 'error')
        return redirect(url_for('user.dashboard'))
    
    # Get storage information for admin users
    storage_root_path = None
    s3_bucket_name = None
    
    if current_user.is_admin():
        from flask import current_app
        if document.storage_backend == 'local':
            storage_root_path = current_app.config.get('STORAGE_LOCAL_ROOT', 'storage/local')
        elif document.storage_backend == 's3':
            s3_bucket_name = current_app.config.get('S3_BUCKET_NAME', 'unknown-bucket')
    
    return render_template('user/upload_summary.html', 
                         document=document,
                         storage_root_path=storage_root_path,
                         s3_bucket_name=s3_bucket_name)

@bp.route('/documents')
@login_required
def documents():
    """List user's documents"""
    page = request.args.get('page', 1, type=int)
    course_id = request.args.get('course_id', type=int)
    category = request.args.get('category', '')
    visibility = request.args.get('visibility', '')
    
    # Build query
    query = Document.query.filter_by(owner_id=current_user.id)
    
    if course_id:
        query = query.filter_by(course_id=course_id)
    
    if category and category in ['notes', 'assignments', 'lectures', 'exams', 'projects', 'others']:
        query = query.filter_by(category=category)
    
    if visibility and visibility in ['public', 'private']:
        query = query.filter_by(visibility=visibility)
    
    documents = query.order_by(Document.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get courses for filter
    courses = Course.query.filter_by(is_active=True).order_by(Course.name).all()
    
    return render_template('user/documents.html', 
                         documents=documents,
                         courses=courses,
                         current_course_id=course_id,
                         current_category=category,
                         current_visibility=visibility)

@bp.route('/doc/<int:doc_id>/privacy', methods=['POST'])
@login_required
def change_privacy(doc_id):
    """Change document privacy setting"""
    document = Document.query.get_or_404(doc_id)
    
    # Check ownership
    if document.owner_id != current_user.id:
        abort(403)
    
    new_visibility = request.form.get('visibility', '')
    if new_visibility not in ['public', 'private']:
        flash('Invalid visibility setting.', 'error')
        return redirect(url_for('user.documents'))
    
    old_visibility = document.visibility
    document.visibility = new_visibility
    
    db.session.commit()
    
    # Log privacy change
    log_audit('privacy_changed', 'document', doc_id, {
        'old_visibility': old_visibility,
        'new_visibility': new_visibility,
        'title': document.title
    })
    
    flash(f'Document visibility changed to {new_visibility}.', 'success')
    return redirect(url_for('user.documents'))

@bp.route('/doc/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_document(doc_id):
    """Delete document"""
    document = Document.query.get_or_404(doc_id)
    
    # Check ownership
    if document.owner_id != current_user.id:
        abort(403)
    
    try:
        # Store course prefix before deletion (needed for logging)
        course_prefix = document.course.prefix
        
        # Delete from storage
        storage = get_storage_backend(document.storage_backend)
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
    
    except Exception as e:
        logger.error(f"Delete error: {e}")
        db.session.rollback()
        flash('Failed to delete document.', 'error')
    
    return redirect(url_for('user.documents'))

@bp.route('/doc/<int:doc_id>/edit', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def edit_document(doc_id):
    """Edit document metadata"""
    document = Document.query.get_or_404(doc_id)
    
    # Check ownership
    if document.owner_id != current_user.id:
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '')
        visibility = request.form.get('visibility', '')
        
        # Validation
        if not title:
            flash('Title is required.', 'error')
            return redirect(url_for('user.edit_document', doc_id=doc_id))
        
        if category not in ['notes', 'assignments', 'lectures', 'exams', 'projects', 'others']:
            flash('Invalid category.', 'error')
            return redirect(url_for('user.edit_document', doc_id=doc_id))
        
        if visibility not in ['public', 'private']:
            visibility = document.visibility
        
        # Find the category object
        category_obj = Category.query.filter_by(course_id=document.course_id, slug=category, is_active=True).first()
        if not category_obj:
            flash('Invalid category.', 'error')
            return redirect(url_for('user.edit_document', doc_id=doc_id))
        
        # Update document
        old_title = document.title
        old_category = document.category_obj.slug if document.category_obj else 'unknown'
        old_visibility = document.visibility
        
        document.title = title
        document.category_id = category_obj.id
        document.visibility = visibility
        
        db.session.commit()
        
        # Log edit
        log_audit('document_edited', 'document', doc_id, {
            'old_title': old_title,
            'new_title': title,
            'old_category': old_category,
            'new_category': category,
            'old_visibility': old_visibility,
            'new_visibility': visibility
        })
        
        flash('Document updated successfully.', 'success')
        return redirect(url_for('user.documents'))
    
    # GET request - show edit form
    courses = Course.query.filter_by(is_active=True).order_by(Course.name).all()
    return render_template('user/edit_document.html', 
                         document=document, 
                         courses=courses)

@bp.route('/stats')
@login_required
def stats():
    """User statistics page"""
    stats = get_user_stats(current_user.id)
    
    # Get documents by category
    categories = ['notes', 'assignments', 'lectures', 'exams', 'projects', 'others']
    category_stats = {}
    
    for category in categories:
        category_stats[category] = Document.query.filter_by(
            owner_id=current_user.id,
            category=category
        ).count()
    
    # Get documents by course
    course_stats = db.session.query(
        Course.name,
        Course.prefix,
        db.func.count(Document.id).label('count')
    ).join(Document).filter(
        Document.owner_id == current_user.id
    ).group_by(Course.id).all()
    
    return render_template('user/stats.html',
                         stats=stats,
                         category_stats=category_stats,
                         course_stats=course_stats)

@bp.route('/batch-upload', methods=['GET', 'POST'])
@login_required
def batch_upload():
    """Batch upload multiple files"""
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

@bp.route('/batch-upload-summary', methods=['POST'])
@login_required
def batch_upload_summary():
    """Show batch upload summary with storage information"""
    data = request.get_json()
    results = data.get('results', [])
    upload_mode = data.get('upload_mode', 'bulk')
    
    # Calculate summary statistics
    successful_uploads = sum(1 for r in results if r.get('success', False))
    failed_uploads = len(results) - successful_uploads
    total_files = len(results)
    
    # Get total size of successful uploads
    total_size = 0
    documents = {}
    
    for result in results:
        if result.get('success') and result.get('document_id'):
            doc = Document.query.get(result['document_id'])
            if doc:
                documents[result['document_id']] = doc
                total_size += doc.file_size
    
    # Get storage information for admin users
    storage_backend = None
    storage_root_path = None
    s3_bucket_name = None
    
    if current_user.is_admin() and successful_uploads > 0:
        from flask import current_app
        # Get storage backend from first successful upload
        first_successful = next((r for r in results if r.get('success')), None)
        if first_successful and first_successful.get('document_id'):
            doc = Document.query.get(first_successful['document_id'])
            if doc:
                storage_backend = doc.storage_backend
                if storage_backend == 'local':
                    storage_root_path = current_app.config.get('STORAGE_LOCAL_ROOT', 'storage/local')
                elif storage_backend == 's3':
                    s3_bucket_name = current_app.config.get('S3_BUCKET_NAME', 'unknown-bucket')
    
    return render_template('user/batch_upload_summary.html',
                         results=results,
                         documents=documents,
                         successful_uploads=successful_uploads,
                         failed_uploads=failed_uploads,
                         total_files=total_files,
                         total_size=total_size,
                         upload_mode=upload_mode,
                         upload_time=datetime.now(),
                         storage_backend=storage_backend,
                         storage_root_path=storage_root_path,
                         s3_bucket_name=s3_bucket_name)

def process_file_upload(file, course_id, unit_id, category_id, visibility):
    """Process a single file upload"""
    try:
        if not file or not file.filename:
            return {
                'filename': file.filename if file else 'unknown',
                'success': False,
                'error': 'No file provided'
            }
        
        # Read file content first to avoid I/O issues
        file.seek(0)  # Ensure we're at the beginning
        file_content = file.read()
        file_size = len(file_content)
        
        # Create a temporary file object for validation
        from io import BytesIO
        from werkzeug.datastructures import FileStorage
        
        temp_file = FileStorage(
            stream=BytesIO(file_content),
            filename=file.filename,
            content_type=file.content_type
        )
        
        # Validate file using the temporary file object
        validator = FileValidator()
        is_valid, error_message = validator.validate_file(temp_file)
        if not is_valid:
            return {
                'filename': file.filename,
                'success': False,
                'error': error_message
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
        
        # Create a new file object for storage
        file_for_storage = FileStorage(
            stream=BytesIO(file_content),
            filename=file.filename,
            content_type=file.content_type
        )
        
        # Store file
        if not storage_backend.put(file_for_storage, storage_key):
            return {
                'filename': file.filename,
                'success': False,
                'error': 'Failed to store file'
            }
        
        # Calculate checksum from file content
        import hashlib
        checksum = hashlib.sha256(file_content).hexdigest()
        
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
            file_size=file_size,
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
