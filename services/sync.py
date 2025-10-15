"""
Storage synchronization engine
"""
import os
import hashlib
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from services.storage import get_storage_backend, LocalStorageBackend, S3StorageBackend
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class SyncResult:
    """Result of a sync operation"""
    def __init__(self):
        self.files_copied = 0
        self.files_deleted = 0
        self.files_updated = 0
        self.errors = []
        self.conflicts = []
        self.dry_run = False
        self.start_time = datetime.now()
        self.end_time = None
    
    def add_error(self, error: str):
        """Add an error to the result"""
        self.errors.append(error)
        logger.error(f"Sync error: {error}")
    
    def add_conflict(self, conflict: str):
        """Add a conflict to the result"""
        self.conflicts.append(conflict)
        logger.warning(f"Sync conflict: {conflict}")
    
    def finish(self):
        """Mark sync as finished"""
        self.end_time = datetime.now()
    
    def get_duration(self) -> float:
        """Get sync duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return {
            'files_copied': self.files_copied,
            'files_deleted': self.files_deleted,
            'files_updated': self.files_updated,
            'errors': self.errors,
            'conflicts': self.conflicts,
            'dry_run': self.dry_run,
            'duration_seconds': self.get_duration(),
            'success': len(self.errors) == 0
        }

class SyncEngine:
    """Bidirectional storage synchronization engine"""
    
    def __init__(self):
        self.local_backend = LocalStorageBackend(current_app.config['STORAGE_LOCAL_ROOT'])
        self.s3_backend = None
        
        # Initialize S3 backend if configured
        if current_app.config.get('S3_BUCKET_NAME'):
            try:
                self.s3_backend = S3StorageBackend(
                    current_app.config['S3_BUCKET_NAME'],
                    current_app.config['S3_REGION'],
                    current_app.config.get('AWS_ACCESS_KEY_ID'),
                    current_app.config.get('AWS_SECRET_ACCESS_KEY'),
                    current_app.config.get('S3_ENDPOINT_URL')
                )
            except Exception as e:
                logger.error(f"Failed to initialize S3 backend: {e}")
    
    def sync_all(self, dry_run: bool = True) -> SyncResult:
        """Sync all files between backends"""
        result = SyncResult()
        result.dry_run = dry_run
        
        if not self.s3_backend:
            result.add_error("S3 backend not configured")
            result.finish()
            return result
        
        try:
            logger.info(f"Starting {'dry run' if dry_run else 'sync'} between local and S3")
            
            # Get file listings from both backends
            local_files = self._get_file_list(self.local_backend)
            s3_files = self._get_file_list(self.s3_backend)
            
            # Create file maps for easier comparison
            local_map = {f['key']: f for f in local_files}
            s3_map = {f['key']: f for f in s3_files}
            
            # Find files to sync
            all_keys = set(local_map.keys()) | set(s3_map.keys())
            
            for key in all_keys:
                local_file = local_map.get(key)
                s3_file = s3_map.get(key)
                
                if local_file and not s3_file:
                    # File exists locally but not in S3
                    self._sync_file_to_s3(key, local_file, result, dry_run)
                
                elif s3_file and not local_file:
                    # File exists in S3 but not locally
                    self._sync_file_to_local(key, s3_file, result, dry_run)
                
                elif local_file and s3_file:
                    # File exists in both, check if sync needed
                    self._sync_existing_file(key, local_file, s3_file, result, dry_run)
            
            result.finish()
            logger.info(f"Sync {'dry run' if dry_run else 'completed'} in {result.get_duration():.2f}s")
            
        except Exception as e:
            result.add_error(f"Sync failed: {str(e)}")
            result.finish()
        
        return result
    
    def sync_course(self, course_prefix: str, dry_run: bool = True) -> SyncResult:
        """Sync files for a specific course"""
        result = SyncResult()
        result.dry_run = dry_run
        
        if not self.s3_backend:
            result.add_error("S3 backend not configured")
            result.finish()
            return result
        
        try:
            logger.info(f"Starting {'dry run' if dry_run else 'sync'} for course {course_prefix}")
            
            # Get file listings with course prefix
            local_files = self._get_file_list(self.local_backend, f"{course_prefix}/")
            s3_files = self._get_file_list(self.s3_backend, f"{course_prefix}/")
            
            # Sync files
            local_map = {f['key']: f for f in local_files}
            s3_map = {f['key']: f for f in s3_files}
            
            all_keys = set(local_map.keys()) | set(s3_map.keys())
            
            for key in all_keys:
                local_file = local_map.get(key)
                s3_file = s3_map.get(key)
                
                if local_file and not s3_file:
                    self._sync_file_to_s3(key, local_file, result, dry_run)
                elif s3_file and not local_file:
                    self._sync_file_to_local(key, s3_file, result, dry_run)
                elif local_file and s3_file:
                    self._sync_existing_file(key, local_file, s3_file, result, dry_run)
            
            result.finish()
            logger.info(f"Course sync {'dry run' if dry_run else 'completed'} in {result.get_duration():.2f}s")
            
        except Exception as e:
            result.add_error(f"Course sync failed: {str(e)}")
            result.finish()
        
        return result
    
    def _get_file_list(self, backend, prefix: str = "") -> List[Dict]:
        """Get file list from backend"""
        try:
            files = backend.list(prefix)
            return files
        except Exception as e:
            logger.error(f"Failed to list files from {backend.__class__.__name__}: {e}")
            return []
    
    def _sync_file_to_s3(self, key: str, local_file: Dict, result: SyncResult, dry_run: bool):
        """Sync file from local to S3"""
        try:
            if dry_run:
                logger.info(f"DRY RUN: Would copy {key} to S3")
                result.files_copied += 1
            else:
                # Read file from local storage
                stream = self.local_backend.stream(key)
                if stream:
                    # Create a file-like object for S3 upload
                    from werkzeug.datastructures import FileStorage
                    from io import BytesIO
                    
                    content = b''.join(stream)
                    file_obj = FileStorage(
                        stream=BytesIO(content),
                        filename=os.path.basename(key),
                        content_type='application/octet-stream'
                    )
                    
                    if self.s3_backend.put(file_obj, key):
                        logger.info(f"Copied {key} to S3")
                        result.files_copied += 1
                    else:
                        result.add_error(f"Failed to copy {key} to S3")
                else:
                    result.add_error(f"Failed to read {key} from local storage")
        
        except Exception as e:
            result.add_error(f"Error syncing {key} to S3: {str(e)}")
    
    def _sync_file_to_local(self, key: str, s3_file: Dict, result: SyncResult, dry_run: bool):
        """Sync file from S3 to local"""
        try:
            if dry_run:
                logger.info(f"DRY RUN: Would copy {key} from S3 to local")
                result.files_copied += 1
            else:
                # Read file from S3
                stream = self.s3_backend.stream(key)
                if stream:
                    # Write to local storage
                    local_path = os.path.join(self.local_backend.root_path, key)
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    
                    with open(local_path, 'wb') as f:
                        for chunk in stream:
                            f.write(chunk)
                    
                    logger.info(f"Copied {key} from S3 to local")
                    result.files_copied += 1
                else:
                    result.add_error(f"Failed to read {key} from S3")
        
        except Exception as e:
            result.add_error(f"Error syncing {key} from S3: {str(e)}")
    
    def _sync_existing_file(self, key: str, local_file: Dict, s3_file: Dict, result: SyncResult, dry_run: bool):
        """Sync file that exists in both locations"""
        try:
            # Compare file sizes and modification times
            local_size = local_file.get('size', 0)
            s3_size = s3_file.get('size', 0)
            
            local_modified = local_file.get('modified', 0)
            s3_modified = s3_file.get('modified', 0)
            
            # If sizes are different, there's a conflict
            if local_size != s3_size:
                result.add_conflict(f"Size mismatch for {key}: local={local_size}, s3={s3_size}")
                
                # Use modification time to decide which version to keep
                if local_modified > s3_modified:
                    # Local is newer, sync to S3
                    self._sync_file_to_s3(key, local_file, result, dry_run)
                elif s3_modified > local_modified:
                    # S3 is newer, sync to local
                    self._sync_file_to_local(key, s3_file, result, dry_run)
                else:
                    # Same modification time but different sizes - this is a real conflict
                    result.add_error(f"Conflict for {key}: same modification time but different sizes")
            
            # If sizes are the same, files are likely in sync
            else:
                logger.debug(f"File {key} is already in sync")
        
        except Exception as e:
            result.add_error(f"Error checking sync status for {key}: {str(e)}")
    
    def get_sync_report(self) -> Dict:
        """Get a report of sync status without actually syncing"""
        if not self.s3_backend:
            return {'error': 'S3 backend not configured'}
        
        try:
            local_files = self._get_file_list(self.local_backend)
            s3_files = self._get_file_list(self.s3_backend)
            
            local_map = {f['key']: f for f in local_files}
            s3_map = {f['key']: f for f in s3_files}
            
            all_keys = set(local_map.keys()) | set(s3_map.keys())
            
            report = {
                'total_files': len(all_keys),
                'local_only': [],
                's3_only': [],
                'in_sync': [],
                'conflicts': [],
                'local_count': len(local_files),
                's3_count': len(s3_files)
            }
            
            for key in all_keys:
                local_file = local_map.get(key)
                s3_file = s3_map.get(key)
                
                if local_file and not s3_file:
                    report['local_only'].append(key)
                elif s3_file and not local_file:
                    report['s3_only'].append(key)
                elif local_file and s3_file:
                    if local_file.get('size') == s3_file.get('size'):
                        report['in_sync'].append(key)
                    else:
                        report['conflicts'].append(key)
            
            return report
        
        except Exception as e:
            logger.error(f"Failed to generate sync report: {e}")
            return {'error': str(e)}
