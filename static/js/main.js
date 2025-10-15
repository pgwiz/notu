// Main JavaScript for Notu

document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme
    initializeTheme();
    
    // Initialize file upload
    initializeFileUpload();
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize modals
    initializeModals();
    
    // Initialize AJAX forms
    initializeAjaxForms();
    
    // Initialize text wrapping for card titles
    initializeTextWrapping();
});

// Theme Management
function initializeTheme() {
    // Load saved theme from localStorage
    const savedTheme = localStorage.getItem('notu-theme');
    if (savedTheme) {
        applyTheme(savedTheme);
    }
    
    // Handle theme selector clicks
    document.querySelectorAll('.theme-selector').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const themeName = this.getAttribute('href').split('/').pop();
            applyTheme(themeName);
            localStorage.setItem('notu-theme', themeName);
        });
    });
}

function applyTheme(themeName) {
    // This would typically make an API call to get theme variables
    // For now, we'll use the default green/black theme
    document.documentElement.setAttribute('data-theme', themeName);
    
    // Update theme selector active state
    document.querySelectorAll('.theme-selector').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href').includes(themeName)) {
            link.classList.add('active');
        }
    });
}

// File Upload Management
function initializeFileUpload() {
    const uploadArea = document.querySelector('.upload-area');
    const fileInput = document.querySelector('#file-input');
    
    if (!uploadArea || !fileInput) return;
    
    // Drag and drop events
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            updateFilePreview(files[0]);
        }
    });
    
    // File input change
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            updateFilePreview(e.target.files[0]);
        }
    });
    
    // Click to upload
    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });
}

function updateFilePreview(file) {
    const preview = document.querySelector('.file-preview');
    if (!preview) return;
    
    const fileName = document.querySelector('.file-name');
    const fileSize = document.querySelector('.file-size');
    const fileIcon = document.querySelector('.file-icon');
    
    if (fileName) fileName.textContent = file.name;
    if (fileSize) fileSize.textContent = formatFileSize(file.size);
    
    // Update icon based on file type
    if (fileIcon) {
        const iconClass = getFileIcon(file.type);
        fileIcon.className = `file-icon ${iconClass}`;
    }
    
    preview.style.display = 'block';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getFileIcon(mimeType) {
    if (mimeType.includes('pdf')) return 'fas fa-file-pdf text-danger';
    if (mimeType.includes('word') || mimeType.includes('document')) return 'fas fa-file-word text-primary';
    if (mimeType.includes('image')) return 'fas fa-file-image text-success';
    if (mimeType.includes('text')) return 'fas fa-file-alt text-info';
    return 'fas fa-file text-muted';
}

// Tooltip Management
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Modal Management
function initializeModals() {
    // Auto-hide modals after successful actions
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('hidden.bs.modal', function() {
            // Clear form data if needed
            const form = modal.querySelector('form');
            if (form) {
                form.reset();
            }
        });
    });
}

// AJAX Form Management
function initializeAjaxForms() {
    document.querySelectorAll('.ajax-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            handleAjaxForm(this);
        });
    });
}

function handleAjaxForm(form) {
    const formData = new FormData(form);
    const url = form.getAttribute('action') || window.location.href;
    const method = form.getAttribute('method') || 'POST';
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    
    fetch(url, {
        method: method,
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message || 'Operation completed successfully', 'success');
            if (data.redirect) {
                window.location.href = data.redirect;
            }
        } else {
            showNotification(data.message || 'Operation failed', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred. Please try again.', 'error');
    })
    .finally(() => {
        // Restore button state
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    });
}

// Notification System
function showNotification(message, type = 'info') {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';
    
    const iconClass = {
        'success': 'fas fa-check-circle',
        'error': 'fas fa-exclamation-triangle',
        'warning': 'fas fa-exclamation-circle',
        'info': 'fas fa-info-circle'
    }[type] || 'fas fa-info-circle';
    
    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            <i class="${iconClass} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Insert at the top of the main content
    const main = document.querySelector('main');
    if (main) {
        main.insertAdjacentHTML('afterbegin', alertHtml);
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            const alert = main.querySelector('.alert');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }
}

// Document Management
function toggleDocumentPrivacy(docId) {
    fetch(`/api/documents/${docId}/toggle-privacy`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            // Update UI to reflect new privacy setting
            updatePrivacyButton(docId, data.new_visibility);
        } else {
            showNotification(data.message || 'Failed to change privacy', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred. Please try again.', 'error');
    });
}

function updatePrivacyButton(docId, newVisibility) {
    const button = document.querySelector(`[data-doc-id="${docId}"] .privacy-btn`);
    if (button) {
        button.textContent = newVisibility === 'public' ? 'Make Private' : 'Make Public';
        button.className = `btn btn-sm ${newVisibility === 'public' ? 'btn-warning' : 'btn-success'} privacy-btn`;
    }
}

function deleteDocument(docId) {
    if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
        return;
    }
    
    fetch(`/api/documents/${docId}/delete`, {
        method: 'DELETE',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            // Remove document from UI
            const docElement = document.querySelector(`[data-doc-id="${docId}"]`);
            if (docElement) {
                docElement.remove();
            }
        } else {
            showNotification(data.message || 'Failed to delete document', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred. Please try again.', 'error');
    });
}

// Search Enhancement
function initializeSearch() {
    const searchInput = document.querySelector('#search-input');
    if (!searchInput) return;
    
    let searchTimeout;
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performSearch(this.value);
        }, 300);
    });
}

function performSearch(query) {
    if (query.length < 2) return;
    
    fetch(`/api/search?q=${encodeURIComponent(query)}`)
    .then(response => response.json())
    .then(data => {
        updateSearchResults(data.documents);
    })
    .catch(error => {
        console.error('Search error:', error);
    });
}

function updateSearchResults(documents) {
    const resultsContainer = document.querySelector('#search-results');
    if (!resultsContainer) return;
    
    if (documents.length === 0) {
        resultsContainer.innerHTML = '<p class="text-muted">No documents found.</p>';
        return;
    }
    
    const resultsHtml = documents.map(doc => `
        <div class="card mb-3">
            <div class="card-body">
                <h6 class="card-title">
                    <i class="${getFileIcon(doc.mime_type)} me-2"></i>
                    ${doc.title}
                </h6>
                <p class="card-text text-muted">
                    ${doc.course.name} • ${doc.category} • ${formatFileSize(doc.file_size)}
                </p>
                <a href="/view/${doc.id}" class="btn btn-primary btn-sm">View</a>
                <a href="/download/${doc.id}" class="btn btn-outline-primary btn-sm">Download</a>
            </div>
        </div>
    `).join('');
    
    resultsContainer.innerHTML = resultsHtml;
}

// Utility Functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Text Wrapping for Card Titles
function initializeTextWrapping() {
    // Process all card titles to improve text wrapping
    const cardTitles = document.querySelectorAll('.card-title');
    
    cardTitles.forEach(title => {
        // Add zero-width space after underscores to allow breaking
        const originalText = title.textContent;
        const processedText = originalText
            .replace(/_/g, '_\u200B') // Add zero-width space after underscores
            .replace(/([A-Z])([A-Z])/g, '$1\u200B$2') // Add break between consecutive capitals
            .replace(/([a-z])([A-Z])/g, '$1\u200B$2'); // Add break between camelCase
        
        title.textContent = processedText;
        
        // Add CSS class for additional styling
        title.classList.add('text-wrap-enhanced');
    });
}

// Re-run text wrapping when new content is loaded (for AJAX updates)
function refreshTextWrapping() {
    initializeTextWrapping();
}
