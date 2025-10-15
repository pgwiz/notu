"""
Security services for file validation and security
"""
import os
import hashlib
from werkzeug.utils import secure_filename
from flask import current_app
from typing import List, Tuple, Optional
import logging

# Try to import magic, fallback to mimetypes if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

logger = logging.getLogger(__name__)

class FileValidator:
    """File validation and security utilities"""
    
    def __init__(self):
        self.allowed_extensions = set(current_app.config.get('ALLOWED_EXTENSIONS', set()))
        self.max_content_length = current_app.config.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024)
        
        # MIME type mappings
        self.mime_mappings = {
            'pdf': ['application/pdf'],
            'doc': ['application/msword'],
            'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            'txt': ['text/plain'],
            'jpg': ['image/jpeg'],
            'jpeg': ['image/jpeg'],
            'png': ['image/png'],
            'gif': ['image/gif']
        }
        
        # Dangerous extensions to block
        self.dangerous_extensions = {
            'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar', 'php',
            'asp', 'aspx', 'jsp', 'py', 'rb', 'pl', 'sh', 'ps1', 'psm1'
        }
    
    def is_allowed_extension(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        if not filename:
            return False
        
        # Get extension (handle multiple dots)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        
        # Check against dangerous extensions first
        if ext in self.dangerous_extensions:
            return False
        
        return ext in self.allowed_extensions
    
    def is_allowed_mime_type(self, file_path: str, expected_ext: str) -> bool:
        """Validate MIME type matches expected extension"""
        try:
            # Get MIME type using python-magic or mimetypes fallback
            if MAGIC_AVAILABLE and magic:
                mime_type = magic.from_file(file_path, mime=True)
            else:
                import mimetypes
                mime_type, _ = mimetypes.guess_type(file_path)
            
            # Check if MIME type matches expected extension
            expected_mimes = self.mime_mappings.get(expected_ext.lower(), [])
            return mime_type in expected_mimes
        except Exception as e:
            logger.error(f"Failed to validate MIME type for {file_path}: {e}")
            return False
    
    def validate_file(self, file_storage) -> Tuple[bool, str]:
        """
        Comprehensive file validation
        Returns (is_valid, error_message)
        """
        if not file_storage or not file_storage.filename:
            return False, "No file provided"
        
        # Check file size
        file_storage.seek(0, os.SEEK_END)
        file_size = file_storage.tell()
        file_storage.seek(0)
        
        if file_size > self.max_content_length:
            return False, f"File too large. Maximum size: {self.max_content_length // (1024*1024)}MB"
        
        if file_size == 0:
            return False, "Empty file not allowed"
        
        # Secure filename
        secure_name = secure_filename(file_storage.filename)
        if not secure_name:
            return False, "Invalid filename"
        
        # Check extension
        if not self.is_allowed_extension(secure_name):
            return False, f"File type not allowed. Allowed types: {', '.join(self.allowed_extensions)}"
        
        # Additional security checks
        if self._has_double_extension(secure_name):
            return False, "Files with double extensions are not allowed"
        
        if self._has_suspicious_content(file_storage):
            return False, "File content appears suspicious"
        
        return True, ""
    
    def _has_double_extension(self, filename: str) -> bool:
        """Check for double extensions (e.g., file.txt.exe)"""
        parts = filename.split('.')
        return len(parts) > 2 and any(part.lower() in self.dangerous_extensions for part in parts[1:])
    
    def _has_suspicious_content(self, file_storage) -> bool:
        """Basic content analysis for suspicious patterns"""
        try:
            # Read first 1KB to check for suspicious patterns
            file_storage.seek(0)
            header = file_storage.read(1024)
            file_storage.seek(0)
            
            # Check for executable signatures
            executable_signatures = [
                b'MZ',  # PE executable
                b'\x7fELF',  # ELF executable
                b'#!/',  # Shell script
                b'<script',  # JavaScript in HTML
                b'<?php',  # PHP script
            ]
            
            for signature in executable_signatures:
                if signature in header:
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking file content: {e}")
            return True  # Err on the side of caution
    
    def get_file_checksum(self, file_storage) -> str:
        """Calculate SHA-256 checksum of file"""
        sha256_hash = hashlib.sha256()
        file_storage.seek(0)
        
        while True:
            chunk = file_storage.read(8192)
            if not chunk:
                break
            sha256_hash.update(chunk)
        
        file_storage.seek(0)
        return sha256_hash.hexdigest()
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Use werkzeug's secure_filename
        sanitized = secure_filename(filename)
        
        # Additional sanitization
        sanitized = sanitized.replace(' ', '_')
        
        # Ensure it's not empty
        if not sanitized:
            sanitized = 'uploaded_file'
        
        return sanitized

class AntivirusScanner:
    """Placeholder for antivirus scanning integration"""
    
    def __init__(self):
        self.enabled = current_app.config.get('ANTIVIRUS_ENABLED', False)
        self.scanner_path = current_app.config.get('ANTIVIRUS_PATH', '/usr/bin/clamscan')
    
    def scan_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Scan file for viruses
        Returns (is_clean, message)
        """
        if not self.enabled:
            return True, "Antivirus scanning disabled"
        
        try:
            import subprocess
            
            # Run clamscan (example implementation)
            result = subprocess.run(
                [self.scanner_path, '--no-summary', file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, "File is clean"
            else:
                return False, f"Virus detected: {result.stdout}"
        
        except subprocess.TimeoutExpired:
            return False, "Antivirus scan timeout"
        except FileNotFoundError:
            logger.warning("Antivirus scanner not found, skipping scan")
            return True, "Antivirus scanner not available"
        except Exception as e:
            logger.error(f"Antivirus scan error: {e}")
            return False, f"Scan error: {str(e)}"

class SecurityUtils:
    """General security utilities"""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate secure random token"""
        import secrets
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def validate_csrf_token(token: str, session_token: str) -> bool:
        """Validate CSRF token"""
        return token == session_token and len(token) > 0
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Basic input sanitization"""
        if not text:
            return ""
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        return text.strip()
    
    @staticmethod
    def is_safe_url(target: str) -> bool:
        """Check if URL is safe for redirects"""
        if not target:
            return False
        
        # Basic URL safety check
        dangerous_protocols = ['javascript:', 'data:', 'vbscript:']
        target_lower = target.lower()
        
        for protocol in dangerous_protocols:
            if target_lower.startswith(protocol):
                return False
        
        return True
