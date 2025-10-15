"""
Storage backend interface and implementations
"""
import os
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, BinaryIO, Iterator, List
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from werkzeug.datastructures import FileStorage
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class IStorageBackend(ABC):
    """Abstract storage backend interface"""
    
    @abstractmethod
    def put(self, file: FileStorage, key: str) -> bool:
        """Store file with given key. Returns success status."""
        pass
    
    @abstractmethod
    def get_url(self, key: str, public: bool = False, expires_in: int = 3600) -> Optional[str]:
        """Get URL to access file. For private files, returns signed URL."""
        pass
    
    @abstractmethod
    def stream(self, key: str) -> Optional[Iterator[bytes]]:
        """Stream file content."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete file. Returns success status."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    def list(self, prefix: str = "") -> list:
        """List files with optional prefix filter."""
        pass
    
    @abstractmethod
    def get_checksum(self, key: str) -> Optional[str]:
        """Get file checksum (SHA-256)."""
        pass
    
    @abstractmethod
    def get_size(self, key: str) -> Optional[int]:
        """Get file size in bytes."""
        pass

class LocalStorageBackend(IStorageBackend):
    """Local filesystem storage backend"""
    
    def __init__(self, root_path: str):
        self.root_path = root_path
        os.makedirs(root_path, exist_ok=True)
    
    def _get_full_path(self, key: str) -> str:
        """Get full filesystem path for key"""
        return os.path.join(self.root_path, key)
    
    def put(self, file: FileStorage, key: str) -> bool:
        """Store file locally"""
        try:
            full_path = self._get_full_path(key)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            file.seek(0)
            file.save(full_path)
            logger.info(f"Stored file locally: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to store file locally {key}: {e}")
            return False
    
    def get_url(self, key: str, public: bool = False, expires_in: int = 3600) -> Optional[str]:
        """Get local file URL"""
        if not self.exists(key):
            return None
        
        # For local storage, we'll serve files through Flask routes
        # This is a placeholder - actual implementation would depend on your routing
        return f"/storage/local/{key}"
    
    def stream(self, key: str) -> Optional[Iterator[bytes]]:
        """Stream local file"""
        try:
            full_path = self._get_full_path(key)
            if not os.path.exists(full_path):
                return None
            
            def generate():
                with open(full_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        yield chunk
            
            return generate()
        except Exception as e:
            logger.error(f"Failed to stream local file {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete local file"""
        try:
            full_path = self._get_full_path(key)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Deleted local file: {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete local file {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if local file exists"""
        return os.path.exists(self._get_full_path(key))
    
    def list(self, prefix: str = "") -> list:
        """List local files with prefix"""
        try:
            files = []
            search_path = self._get_full_path(prefix) if prefix else self.root_path
            
            for root, dirs, filenames in os.walk(search_path):
                for filename in filenames:
                    rel_path = os.path.relpath(os.path.join(root, filename), self.root_path)
                    files.append({
                        'key': rel_path.replace('\\', '/'),  # Normalize path separators
                        'size': os.path.getsize(os.path.join(root, filename)),
                        'modified': os.path.getmtime(os.path.join(root, filename))
                    })
            
            return files
        except Exception as e:
            logger.error(f"Failed to list local files with prefix {prefix}: {e}")
            return []
    
    def get_checksum(self, key: str) -> Optional[str]:
        """Get local file checksum"""
        try:
            full_path = self._get_full_path(key)
            if not os.path.exists(full_path):
                return None
            
            sha256_hash = hashlib.sha256()
            with open(full_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to get checksum for local file {key}: {e}")
            return None
    
    def get_size(self, key: str) -> Optional[int]:
        """Get local file size"""
        try:
            full_path = self._get_full_path(key)
            if os.path.exists(full_path):
                return os.path.getsize(full_path)
            return None
        except Exception as e:
            logger.error(f"Failed to get size for local file {key}: {e}")
            return None

class S3StorageBackend(IStorageBackend):
    """S3-compatible storage backend (AWS S3, Scaleway, etc.)"""
    
    def __init__(self, bucket_name: str, region: str = 'us-east-1', 
                 access_key: str = None, secret_key: str = None, 
                 endpoint_url: str = None):
        self.bucket_name = bucket_name
        self.region = region
        self.endpoint_url = endpoint_url
        
        # Initialize S3 client
        try:
            client_config = {
                'region_name': region,
            }
            
            # Add endpoint URL for S3-compatible services (like Scaleway)
            if endpoint_url:
                client_config['endpoint_url'] = endpoint_url
            
            if access_key and secret_key:
                client_config.update({
                    'aws_access_key_id': access_key,
                    'aws_secret_access_key': secret_key
                })
            
            self.s3_client = boto3.client('s3', **client_config)
            
            # Test connection
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Connected to S3 bucket: {bucket_name} (endpoint: {endpoint_url or 'default'})")
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Failed to connect to S3: {e}")
            raise
    
    def put(self, file: FileStorage, key: str) -> bool:
        """Store file in S3"""
        try:
            file.seek(0)
            # Add 'notu/' prefix to the key to organize files in a folder
            prefixed_key = f"notu/{key}"
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                prefixed_key,
                ExtraArgs={'ContentType': file.content_type or 'application/octet-stream'}
            )
            logger.info(f"Stored file in S3: {prefixed_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to store file in S3 {key}: {e}")
            return False
    
    def get_url(self, key: str, public: bool = False, expires_in: int = 3600) -> Optional[str]:
        """Get S3 file URL"""
        try:
            # Add 'notu/' prefix to the key
            prefixed_key = f"notu/{key}"
            
            if public:
                # Public URL - handle custom endpoints
                if self.endpoint_url:
                    # For custom endpoints (like Scaleway), construct URL differently
                    base_url = self.endpoint_url.rstrip('/')
                    return f"{base_url}/{self.bucket_name}/{prefixed_key}"
                else:
                    # Standard AWS S3 URL
                    return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{prefixed_key}"
            else:
                # Signed URL for private access
                return self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': prefixed_key},
                    ExpiresIn=expires_in
                )
        except Exception as e:
            logger.error(f"Failed to get URL for S3 file {key}: {e}")
            return None
    
    def stream(self, key: str) -> Optional[Iterator[bytes]]:
        """Stream S3 file"""
        try:
            # Add 'notu/' prefix to the key
            prefixed_key = f"notu/{key}"
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=prefixed_key)
            
            def generate():
                for chunk in response['Body'].iter_chunks(chunk_size=8192):
                    yield chunk
            
            return generate()
        except Exception as e:
            logger.error(f"Failed to stream S3 file {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete S3 file"""
        try:
            # Add 'notu/' prefix to the key
            prefixed_key = f"notu/{key}"
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=prefixed_key)
            logger.info(f"Deleted S3 file: {prefixed_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete S3 file {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if S3 file exists"""
        try:
            # Add 'notu/' prefix to the key
            prefixed_key = f"notu/{key}"
            self.s3_client.head_object(Bucket=self.bucket_name, Key=prefixed_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking S3 file existence {key}: {e}")
            return False
    
    def list(self, prefix: str = "") -> list:
        """List S3 files with prefix"""
        try:
            files = []
            # Add 'notu/' prefix to the search prefix
            search_prefix = f"notu/{prefix}" if prefix else "notu/"
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=search_prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Remove 'notu/' prefix from the returned key for consistency
                        key = obj['Key']
                        if key.startswith('notu/'):
                            key = key[5:]  # Remove 'notu/' prefix
                        
                        files.append({
                            'key': key,
                            'size': obj['Size'],
                            'modified': obj['LastModified'].timestamp()
                        })
            
            return files
        except Exception as e:
            logger.error(f"Failed to list S3 files with prefix {prefix}: {e}")
            return []
    
    def list_files(self, prefix: str = '') -> List[dict]:
        """List files in S3 with optional prefix - returns file info objects"""
        try:
            files = []
            # Add 'notu/' prefix to the search prefix
            search_prefix = f"notu/{prefix}" if prefix else "notu/"
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=search_prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Remove 'notu/' prefix from the returned key for consistency
                        key = obj['Key']
                        if key.startswith('notu/'):
                            key = key[5:]  # Remove 'notu/' prefix
                        
                        # Create a file info object with attributes
                        file_info = type('FileInfo', (), {
                            'key': key,
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'etag': obj.get('ETag', '').strip('"')
                        })()
                        
                        files.append(file_info)
            
            return files
        except Exception as e:
            logger.error(f"Failed to list S3 files with prefix {prefix}: {e}")
            return []
    
    def get_checksum(self, key: str) -> Optional[str]:
        """Get S3 file checksum (ETag)"""
        try:
            # Add 'notu/' prefix to the key
            prefixed_key = f"notu/{key}"
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=prefixed_key)
            # ETag is usually MD5, but for multipart uploads it's different
            # For SHA-256, we'd need to calculate it ourselves or use S3 checksums
            return response.get('ETag', '').strip('"')
        except Exception as e:
            logger.error(f"Failed to get checksum for S3 file {key}: {e}")
            return None
    
    def get_size(self, key: str) -> Optional[int]:
        """Get S3 file size"""
        try:
            # Add 'notu/' prefix to the key
            prefixed_key = f"notu/{key}"
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=prefixed_key)
            return response['ContentLength']
        except Exception as e:
            logger.error(f"Failed to get size for S3 file {key}: {e}")
            return None
    
    def get_file_info(self, key: str) -> dict:
        """Get comprehensive file information"""
        try:
            # Add 'notu/' prefix to the key
            prefixed_key = f"notu/{key}"
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=prefixed_key)
            
            return {
                'key': key,
                'size': response['ContentLength'],
                'etag': response.get('ETag', '').strip('"'),
                'last_modified': response['LastModified'],
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'metadata': response.get('Metadata', {})
            }
        except Exception as e:
            logger.error(f"Failed to get file info for S3 file {key}: {e}")
            raise

def get_storage_backend(backend_type: str = None) -> IStorageBackend:
    """Factory function to get storage backend instance"""
    if backend_type is None:
        backend_type = current_app.config.get('ACTIVE_STORAGE_BACKEND', 'local')
    
    if backend_type == 's3':
        return S3StorageBackend(
            bucket_name=current_app.config['S3_BUCKET_NAME'],
            region=current_app.config['S3_REGION'],
            access_key=current_app.config.get('AWS_ACCESS_KEY_ID'),
            secret_key=current_app.config.get('AWS_SECRET_ACCESS_KEY'),
            endpoint_url=current_app.config.get('S3_ENDPOINT_URL')
        )
    else:
        return LocalStorageBackend(
            root_path=current_app.config['STORAGE_LOCAL_ROOT']
        )
