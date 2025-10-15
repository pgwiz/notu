<!-- b1d84348-3fda-46ed-9640-a16b5a4d20af ab7f00e5-17b8-4e25-be4c-3e490c98a3cd -->
# Hierarchical Units & Categories System with Batch Upload

## Database Schema Changes

### 1. Create New Models (models.py)

Create `Unit` and `Category` models to support the hierarchical structure:

```python
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
    documents = db.relationship('Document', backref='unit', lazy='dynamic')
    
    # Unique constraint: one slug per course
    __table_args__ = (
        db.UniqueConstraint('course_id', 'slug', name='uq_course_unit_slug'),
    )

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
    documents = db.relationship('Document', backref='category_obj', lazy='dynamic')
    
    # Unique constraint: one slug per course
    __table_args__ = (
        db.UniqueConstraint('course_id', 'slug', name='uq_course_category_slug'),
    )
```

### 2. Update Document Model (models.py)

Add foreign keys for unit and category:

```python
# In Document model, replace:
category = db.Column(db.String(20), nullable=False)

# With:
unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)

# Update indexes:
__table_args__ = (
    db.Index('idx_document_course_unit_category', 'course_id', 'unit_id', 'category_id'),
    db.Index('idx_document_visibility', 'visibility'),
    db.Index('idx_document_owner_visibility', 'owner_id', 'visibility'),
)

# Update get_storage_path method:
def get_storage_path(self):
    """Generate storage path: course/unit/category/filename"""
    return f"{self.course.prefix}/{self.unit.slug}/{self.category_obj.slug}/{self.original_filename}"
```

### 3. Create Migration Script (migrations/)

Create Alembic migration to add new tables and update existing data.

## Admin Management Interface

### 4. Admin Routes for Units (blueprints/admin.py)

Add CRUD operations for units:

```python
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
    # Handle form submission, create unit
    
@bp.route('/units/<int:unit_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_unit(unit_id):
    """Edit unit"""
    
@bp.route('/units/<int:unit_id>/delete', methods=['POST'])
@admin_required
def delete_unit(unit_id):
    """Delete unit (soft delete)"""
```

### 5. Admin Routes for Categories (blueprints/admin.py)

Add CRUD operations for categories:

```python
@bp.route('/courses/<int:course_id>/categories')
@admin_required
def manage_categories(course_id):
    """Manage categories for a course"""
    
@bp.route('/courses/<int:course_id>/categories/create', methods=['GET', 'POST'])
@admin_required
def create_category(course_id):
    """Create new category with icon and color picker"""
    
@bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    """Edit category"""
    
@bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@admin_required
def delete_category(category_id):
    """Delete category (soft delete)"""
```

### 6. Admin Templates

Create templates:

- `templates/admin/manage_units.html` - List and manage units
- `templates/admin/create_unit.html` - Create/edit unit form
- `templates/admin/manage_categories.html` - List and manage categories  
- `templates/admin/create_category.html` - Create/edit category form with color picker

## Public Routes Update

### 7. Update Public Routes (blueprints/public.py)

Modify routes to support 3-level hierarchy:

```python
@bp.route('/c/<prefix>/<unit_slug>/<category_slug>')
def course_unit_category(prefix, unit_slug, category_slug):
    """View documents in course/unit/category"""
    course = Course.query.filter_by(prefix=prefix, is_active=True).first_or_404()
    unit = Unit.query.filter_by(course_id=course.id, slug=unit_slug, is_active=True).first_or_404()
    category = Category.query.filter_by(course_id=course.id, slug=category_slug, is_active=True).first_or_404()
    
    # Get documents with pagination
    page = request.args.get('page', 1, type=int)
    documents = Document.query.filter_by(
        course_id=course.id,
        unit_id=unit.id,
        category_id=category.id,
        visibility='public'
    ).order_by(Document.created_at.desc()).paginate(page=page, per_page=12)
    
    return render_template('public/documents_list.html', 
                         course=course, unit=unit, category=category, documents=documents)

@bp.route('/c/<prefix>')
def course_overview(prefix):
    """Update to show units and categories hierarchy"""
    # Fetch units and categories for the course
    # Display as expandable tree or grid
```

### 8. Update Search and Filter

Modify search to include unit and category filters in `blueprints/public.py`.

## Batch Upload System

### 9. Batch Upload Route (blueprints/user.py)

Create new batch upload endpoint:

```python
@bp.route('/batch-upload', methods=['GET', 'POST'])
@login_required
def batch_upload():
    """Batch upload multiple files"""
    if request.method == 'POST':
        files = request.files.getlist('files')
        upload_mode = request.form.get('upload_mode')  # 'bulk' or 'individual'
        
        if upload_mode == 'bulk':
            # All files get same course/unit/category
            course_id = request.form.get('course_id')
            unit_id = request.form.get('unit_id')
            category_id = request.form.get('category_id')
            visibility = request.form.get('visibility', 'private')
            
            results = []
            for file in files:
                # Process each file with same metadata
                result = process_file_upload(file, course_id, unit_id, category_id, visibility)
                results.append(result)
                
        else:  # individual mode
            # Each file has its own metadata from JSON
            files_metadata = json.loads(request.form.get('files_metadata'))
            results = []
            for i, file in enumerate(files):
                metadata = files_metadata[i]
                result = process_file_upload(
                    file, 
                    metadata['course_id'],
                    metadata['unit_id'],
                    metadata['category_id'],
                    metadata['visibility']
                )
                results.append(result)
        
        return jsonify({'success': True, 'results': results})
    
    courses = Course.query.filter_by(is_active=True).all()
    return render_template('user/batch_upload.html', courses=courses)
```

### 10. Batch Upload Template (templates/user/batch_upload.html)

Create comprehensive batch upload interface with:

- Mode toggle (bulk assign vs individual assign)
- File list with per-file configuration in individual mode
- Progress indicators
- Drag-and-drop zone supporting multiple files and folders

## Enhanced Drag & Drop

### 11. Enhanced File Input Styling (static/css/main.css)

Add modern file input styles:

```css
.file-drop-zone {
    border: 2px dashed #10b981;
    border-radius: 12px;
    padding: 3rem;
    text-align: center;
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(16, 185, 129, 0.1) 100%);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}

.file-drop-zone.drag-over {
    border-color: #34d399;
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.2) 100%);
    transform: scale(1.02);
    box-shadow: 0 0 30px rgba(16, 185, 129, 0.3);
}

.file-drop-zone input[type="file"] {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
}

.file-list-item {
    background: #1f2937;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: all 0.2s ease;
}

.file-list-item:hover {
    border-color: #10b981;
    background: #2d3748;
}

.file-icon-preview {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #374151;
    border-radius: 8px;
    font-size: 1.5rem;
}

.file-progress {
    height: 4px;
    background: #374151;
    border-radius: 2px;
    overflow: hidden;
    margin-top: 0.5rem;
}

.file-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #10b981, #34d399);
    transition: width 0.3s ease;
    animation: progress-shimmer 1.5s infinite;
}

@keyframes progress-shimmer {
    0% { background-position: -100% 0; }
    100% { background-position: 200% 0; }
}
```

### 12. Drag & Drop JavaScript (static/js/upload.js)

Create comprehensive upload handler:

```javascript
class BatchUploadManager {
    constructor(dropZoneId, fileInputId) {
        this.dropZone = document.getElementById(dropZoneId);
        this.fileInput = document.getElementById(fileInputId);
        this.files = [];
        this.uploadMode = 'bulk';
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        // Drag and drop events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, this.preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, () => {
                this.dropZone.classList.add('drag-over');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, () => {
                this.dropZone.classList.remove('drag-over');
            }, false);
        });
        
        this.dropZone.addEventListener('drop', this.handleDrop.bind(this), false);
        this.fileInput.addEventListener('change', this.handleFileSelect.bind(this), false);
    }
    
    async handleDrop(e) {
        const items = e.dataTransfer.items;
        
        // Support folder drag and drop
        for (let i = 0; i < items.length; i++) {
            const item = items[i].webkitGetAsEntry();
            if (item) {
                await this.traverseFileTree(item);
            }
        }
        
        this.renderFileList();
    }
    
    async traverseFileTree(item, path = '') {
        if (item.isFile) {
            const file = await this.getFile(item);
            file.relativePath = path + file.name;
            this.files.push(file);
        } else if (item.isDirectory) {
            const dirReader = item.createReader();
            const entries = await this.readAllDirectoryEntries(dirReader);
            for (const entry of entries) {
                await this.traverseFileTree(entry, path + item.name + '/');
            }
        }
    }
    
    renderFileList() {
        // Render files with individual configuration options
        // Show file type icons, size, and metadata inputs
    }
    
    async uploadFiles() {
        const formData = new FormData();
        
        if (this.uploadMode === 'bulk') {
            // Add all files and single set of metadata
            this.files.forEach(file => formData.append('files', file));
            formData.append('course_id', document.getElementById('course_id').value);
            formData.append('unit_id', document.getElementById('unit_id').value);
            formData.append('category_id', document.getElementById('category_id').value);
            formData.append('visibility', document.getElementById('visibility').value);
            formData.append('upload_mode', 'bulk');
        } else {
            // Add files and individual metadata
            const filesMetadata = this.files.map((file, index) => ({
                course_id: document.getElementById(`course_${index}`).value,
                unit_id: document.getElementById(`unit_${index}`).value,
                category_id: document.getElementById(`category_${index}`).value,
                visibility: document.getElementById(`visibility_${index}`).value
            }));
            
            this.files.forEach(file => formData.append('files', file));
            formData.append('files_metadata', JSON.stringify(filesMetadata));
            formData.append('upload_mode', 'individual');
        }
        
        // Upload with progress tracking
        await this.uploadWithProgress(formData);
    }
}
```

### 13. Update Single Upload Template (templates/user/upload.html)

Enhance existing upload with:

- Dynamic unit dropdown based on selected course
- Dynamic category dropdown based on selected course
- Improved file input styling
- Better drag-and-drop visual feedback

### 14. AJAX Endpoints for Dynamic Dropdowns (blueprints/api.py)

Add endpoints to fetch units and categories:

```python
@bp.route('/courses/<int:course_id>/units')
def get_course_units(course_id):
    """Get units for a course"""
    units = Unit.query.filter_by(course_id=course_id, is_active=True).order_by(Unit.order).all()
    return jsonify([{'id': u.id, 'name': u.name, 'slug': u.slug} for u in units])

@bp.route('/courses/<int:course_id>/categories')
def get_course_categories(course_id):
    """Get categories for a course"""
    categories = Category.query.filter_by(course_id=course_id, is_active=True).order_by(Category.order).all()
    return jsonify([{
        'id': c.id, 
        'name': c.name, 
        'slug': c.slug,
        'icon': c.icon,
        'color': c.color
    } for c in categories])
```

## Data Migration

### 15. Migration Script (migrations/migrate_to_units.py)

Create script to migrate existing documents:

- Create default units for each course (e.g., "General")
- Convert old category strings to Category objects
- Update all document references

## Testing & Validation

### 16. Update Validation (services/security.py)

Ensure file validation works with batch uploads and maintains security.

### 17. Update Tests

Add tests for:

- Unit and category CRUD operations
- Batch upload functionality
- Folder structure preservation
- Dynamic dropdown loading

### To-dos

- [ ] Create Unit and Category models in models.py with relationships
- [ ] Update Document model to use unit_id and category_id foreign keys
- [ ] Create Alembic migration for new tables and document updates
- [ ] Add admin routes for unit CRUD operations
- [ ] Add admin routes for category CRUD operations
- [ ] Create admin templates for managing units and categories
- [ ] Update public routes to support course/unit/category hierarchy
- [ ] Create batch upload route with bulk and individual modes
- [ ] Create batch upload template with mode toggle and file list
- [ ] Add enhanced file input and drag-drop styling to main.css
- [ ] Create upload.js with BatchUploadManager class for folder support
- [ ] Update single upload template with dynamic unit/category dropdowns
- [ ] Add API endpoints for fetching units and categories by course
- [ ] Create migration script to convert existing documents to new structure
- [ ] Update search and filter functionality for new hierarchy