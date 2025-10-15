/**
 * BatchUploadManager - Enhanced file upload with drag-and-drop and folder support
 */
class BatchUploadManager {
    constructor(dropZoneId, fileInputId) {
        this.dropZone = document.getElementById(dropZoneId);
        this.fileInput = document.getElementById(fileInputId);
        this.files = [];
        this.uploadMode = 'bulk';
        this.courses = [];
        this.units = {};
        this.categories = {};
        
        this.initEventListeners();
        this.loadCourses();
    }
    
    initEventListeners() {
        if (!this.dropZone || !this.fileInput) return;
        
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropZone.addEventListener(eventName, this.preventDefaults, false);
            document.body.addEventListener(eventName, this.preventDefaults, false);
        });
        
        // Highlight drop zone when item is dragged over it
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
        
        // Handle dropped files
        this.dropZone.addEventListener('drop', this.handleDrop.bind(this), false);
        
        // Handle file input change
        this.fileInput.addEventListener('change', this.handleFileSelect.bind(this), false);
        
        // Handle mode toggle
        const modeButtons = document.querySelectorAll('.upload-mode-btn');
        modeButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setUploadMode(e.target.dataset.mode);
            });
        });
        
        // Event delegation for remove buttons
        const fileListContainer = document.getElementById('file-list-container');
        if (fileListContainer) {
            fileListContainer.addEventListener('click', (e) => {
                if (e.target.closest('.file-remove-btn')) {
                    const index = parseInt(e.target.closest('.file-remove-btn').dataset.index);
                    this.removeFile(index);
                }
            });
        }
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
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
    
    async handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.files = this.files.concat(files);
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
    
    getFile(fileEntry) {
        return new Promise((resolve, reject) => {
            fileEntry.file(resolve, reject);
        });
    }
    
    readAllDirectoryEntries(dirReader) {
        return new Promise((resolve, reject) => {
            const entries = [];
            const readEntries = () => {
                dirReader.readEntries((results) => {
                    if (results.length === 0) {
                        resolve(entries);
                    } else {
                        entries.push(...results);
                        readEntries();
                    }
                }, reject);
            };
            readEntries();
        });
    }
    
    renderFileList() {
        const container = document.getElementById('file-list-container');
        if (!container) return;
        
        if (this.files.length === 0) {
            container.innerHTML = '<p class="tw-text-gray-400 tw-text-center tw-py-4">No files selected</p>';
            return;
        }
        
        container.innerHTML = this.files.map((file, index) => {
            const icon = this.getFileIcon(file);
            const size = this.formatFileSize(file.size);
            
            return `
                <div class="file-list-item" data-index="${index}">
                    <div class="file-icon-preview ${icon.class}">
                        <i class="${icon.icon}"></i>
                    </div>
                    <div class="file-info">
                        <div class="file-name" title="${file.name}">${file.name}</div>
                        <div class="file-size">${size}</div>
                        ${file.relativePath ? `<div class="tw-text-xs tw-text-gray-500">${file.relativePath}</div>` : ''}
                        <div class="file-progress" style="display: none;">
                            <div class="file-progress-bar"></div>
                        </div>
                    </div>
                    <div class="file-actions">
                        <button type="button" class="file-remove-btn" data-index="${index}">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    ${this.uploadMode === 'individual' ? this.renderFileMetadataForm(index) : ''}
                </div>
            `;
        }).join('');
        
        // Add event listeners for individual mode
        if (this.uploadMode === 'individual') {
            this.files.forEach((file, index) => {
                this.addFileMetadataListeners(index);
            });
        }
    }
    
    renderFileMetadataForm(index) {
        return `
            <div class="file-metadata-form">
                <div class="row">
                    <div class="col-md-3">
                        <label class="form-label">Course</label>
                        <select class="form-select" id="course_${index}" required>
                            <option value="">Select course...</option>
                            ${this.courses.map(course => 
                                `<option value="${course.id}">${course.name} (${course.prefix})</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Unit</label>
                        <select class="form-select" id="unit_${index}" required>
                            <option value="">Select unit...</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Category</label>
                        <select class="form-select" id="category_${index}" required>
                            <option value="">Select category...</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Visibility</label>
                        <select class="form-select" id="visibility_${index}">
                            <option value="private">Private</option>
                            <option value="public">Public</option>
                        </select>
                    </div>
                </div>
            </div>
        `;
    }
    
    addFileMetadataListeners(index) {
        const courseSelect = document.getElementById(`course_${index}`);
        if (courseSelect) {
            courseSelect.addEventListener('change', () => {
                this.loadUnitsForCourse(courseSelect.value, index);
            });
        }
        
        const unitSelect = document.getElementById(`unit_${index}`);
        if (unitSelect) {
            unitSelect.addEventListener('change', () => {
                this.loadCategoriesForCourse(courseSelect.value, index);
            });
        }
    }
    
    removeFile(index) {
        this.files.splice(index, 1);
        this.renderFileList();
    }
    
    setUploadMode(mode) {
        this.uploadMode = mode;
        
        // Update UI
        document.querySelectorAll('.upload-mode-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-mode="${mode}"]`).classList.add('active');
        
        // Show/hide bulk form
        const bulkForm = document.getElementById('bulk-upload-form');
        if (bulkForm) {
            bulkForm.style.display = mode === 'bulk' ? 'block' : 'none';
        }
        
        // Re-render file list
        this.renderFileList();
    }
    
    async loadCourses() {
        try {
            const response = await fetch('/api/courses');
            this.courses = await response.json();
        } catch (error) {
            console.error('Failed to load courses:', error);
        }
    }
    
    async loadUnitsForCourse(courseId, fileIndex) {
        if (!courseId) return;
        
        try {
            const response = await fetch(`/api/courses/${courseId}/units`);
            const units = await response.json();
            
            const unitSelect = document.getElementById(`unit_${fileIndex}`);
            if (unitSelect) {
                unitSelect.innerHTML = '<option value="">Select unit...</option>' +
                    units.map(unit => `<option value="${unit.id}">${unit.name}</option>`).join('');
            }
            
            // Clear categories when unit changes
            const categorySelect = document.getElementById(`category_${fileIndex}`);
            if (categorySelect) {
                categorySelect.innerHTML = '<option value="">Select category...</option>';
            }
        } catch (error) {
            console.error('Failed to load units:', error);
        }
    }
    
    async loadCategoriesForCourse(courseId, fileIndex) {
        if (!courseId) return;
        
        try {
            const response = await fetch(`/api/courses/${courseId}/categories`);
            const categories = await response.json();
            
            const categorySelect = document.getElementById(`category_${fileIndex}`);
            if (categorySelect) {
                categorySelect.innerHTML = '<option value="">Select category...</option>' +
                    categories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
            }
        } catch (error) {
            console.error('Failed to load categories:', error);
        }
    }
    
    getFileIcon(file) {
        const extension = file.name.split('.').pop().toLowerCase();
        
        const iconMap = {
            'pdf': { icon: 'fas fa-file-pdf', class: 'file-icon-pdf' },
            'doc': { icon: 'fas fa-file-word', class: 'file-icon-doc' },
            'docx': { icon: 'fas fa-file-word', class: 'file-icon-doc' },
            'txt': { icon: 'fas fa-file-alt', class: 'file-icon-default' },
            'jpg': { icon: 'fas fa-file-image', class: 'file-icon-image' },
            'jpeg': { icon: 'fas fa-file-image', class: 'file-icon-image' },
            'png': { icon: 'fas fa-file-image', class: 'file-icon-image' },
            'gif': { icon: 'fas fa-file-image', class: 'file-icon-image' },
            'mp4': { icon: 'fas fa-file-video', class: 'file-icon-video' },
            'avi': { icon: 'fas fa-file-video', class: 'file-icon-video' },
            'mp3': { icon: 'fas fa-file-audio', class: 'file-icon-audio' },
            'wav': { icon: 'fas fa-file-audio', class: 'file-icon-audio' },
            'zip': { icon: 'fas fa-file-archive', class: 'file-icon-archive' },
            'rar': { icon: 'fas fa-file-archive', class: 'file-icon-archive' },
            'js': { icon: 'fas fa-file-code', class: 'file-icon-code' },
            'html': { icon: 'fas fa-file-code', class: 'file-icon-code' },
            'css': { icon: 'fas fa-file-code', class: 'file-icon-code' },
            'py': { icon: 'fas fa-file-code', class: 'file-icon-code' }
        };
        
        return iconMap[extension] || { icon: 'fas fa-file', class: 'file-icon-default' };
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    async uploadFiles() {
        if (this.files.length === 0) {
            alert('Please select files to upload');
            return;
        }
        
        const formData = new FormData();
        
        if (this.uploadMode === 'bulk') {
            // Validate bulk form
            const courseId = document.getElementById('bulk_course_id')?.value;
            const unitId = document.getElementById('bulk_unit_id')?.value;
            const categoryId = document.getElementById('bulk_category_id')?.value;
            
            if (!courseId || !unitId || !categoryId) {
                alert('Please fill in all required fields for bulk upload');
                return;
            }
            
            // Add all files and single set of metadata
            this.files.forEach(file => formData.append('files', file));
            formData.append('course_id', courseId);
            formData.append('unit_id', unitId);
            formData.append('category_id', categoryId);
            formData.append('visibility', document.getElementById('bulk_visibility')?.value || 'private');
            formData.append('upload_mode', 'bulk');
        } else {
            // Validate individual forms
            const filesMetadata = [];
            for (let i = 0; i < this.files.length; i++) {
                const courseId = document.getElementById(`course_${i}`)?.value;
                const unitId = document.getElementById(`unit_${i}`)?.value;
                const categoryId = document.getElementById(`category_${i}`)?.value;
                
                if (!courseId || !unitId || !categoryId) {
                    alert(`Please fill in all required fields for file ${i + 1}: ${this.files[i].name}`);
                    return;
                }
                
                filesMetadata.push({
                    course_id: courseId,
                    unit_id: unitId,
                    category_id: categoryId,
                    visibility: document.getElementById(`visibility_${i}`)?.value || 'private'
                });
            }
            
            this.files.forEach(file => formData.append('files', file));
            formData.append('files_metadata', JSON.stringify(filesMetadata));
            formData.append('upload_mode', 'individual');
        }
        
        // Show progress overlay
        this.showProgressOverlay();
        
        try {
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            
            const response = await fetch('/user/batch-upload', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.hideProgressOverlay();
                this.showUploadResults(result.results);
                this.files = [];
                this.renderFileList();
            } else {
                throw new Error(result.error || 'Upload failed');
            }
        } catch (error) {
            this.hideProgressOverlay();
            console.log('Upload failed:', error.message);
            console.error('Upload error:', error);
            alert('Upload failed: ' + error.message);
        }
    }
    
    showProgressOverlay() {
        const overlay = document.createElement('div');
        overlay.className = 'upload-progress-overlay';
        overlay.id = 'upload-progress-overlay';
        overlay.innerHTML = `
            <div class="upload-progress-card">
                <div class="upload-progress-title">Uploading Files...</div>
                <div class="upload-progress-bar">
                    <div class="upload-progress-fill" style="width: 0%"></div>
                </div>
                <div class="upload-progress-text">Preparing upload...</div>
            </div>
        `;
        document.body.appendChild(overlay);
        
        // Simulate progress
        this.simulateProgress();
    }
    
    simulateProgress() {
        const fill = document.querySelector('.upload-progress-fill');
        const text = document.querySelector('.upload-progress-text');
        let progress = 0;
        
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) progress = 90;
            
            fill.style.width = progress + '%';
            text.textContent = `Uploading... ${Math.round(progress)}%`;
            
            if (progress >= 90) {
                clearInterval(interval);
            }
        }, 200);
    }
    
    hideProgressOverlay() {
        const overlay = document.getElementById('upload-progress-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
    
    showUploadResults(results) {
        const successCount = results.filter(r => r.success).length;
        const failCount = results.length - successCount;
        
        console.log('Upload results:', {
            successCount,
            failCount,
            results
        });
        
        // Redirect to batch upload summary page
        const uploadMode = document.querySelector('input[name="upload_mode"]:checked')?.value || 'bulk';
        
        fetch('/user/batch-upload-summary', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                results: results,
                upload_mode: uploadMode
            })
        })
        .then(response => {
            if (response.ok) {
                // Replace the current page content with the summary
                return response.text();
            } else {
                throw new Error('Failed to load summary page');
            }
        })
        .then(html => {
            document.body.innerHTML = html;
            // Re-initialize any necessary scripts
            if (typeof initializeScripts === 'function') {
                initializeScripts();
            }
        })
        .catch(error => {
            console.error('Error loading summary:', error);
            // Fallback to alert if summary page fails
            let message = `Upload completed!\n\n`;
            message += `✅ Successfully uploaded: ${successCount} files\n`;
            if (failCount > 0) {
                message += `❌ Failed: ${failCount} files\n\n`;
                message += `Failed files:\n`;
                results.filter(r => !r.success).forEach(r => {
                    message += `• ${r.filename}: ${r.error}\n`;
                });
            }
            alert(message);
        });
    }
}

// Initialize the upload manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('file-drop-zone')) {
        window.uploadManager = new BatchUploadManager('file-drop-zone', 'file-input');
    }
});
