#!/usr/bin/env python3
"""
Basic tests for Notu application
"""
import unittest
import os
import tempfile
from app import create_app, db
from models import User, Course, Document, Theme, AuditLog
from services.storage import LocalStorageBackend
from services.security import FileValidator
from services.auth import authenticate_user, create_user

class NotuTestCase(unittest.TestCase):
    """Test case for Notu application"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Create test database
        db.create_all()
        
        # Create test data
        self.create_test_data()
    
    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def create_test_data(self):
        """Create test data"""
        # Create test user
        self.test_user = User(
            email='test@example.com',
            role='user',
            is_active=True
        )
        self.test_user.set_password('test123')
        db.session.add(self.test_user)
        
        # Create test admin
        self.test_admin = User(
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.test_admin.set_password('admin123')
        db.session.add(self.test_admin)
        
        # Create test course
        self.test_course = Course(
            name='Test Course',
            prefix='test',
            description='Test course description',
            is_active=True
        )
        db.session.add(self.test_course)
        
        # Create test theme
        self.test_theme = Theme(
            name='test-theme',
            display_name='Test Theme',
            variables_json='{"--bg-primary": "#000", "--accent": "#fff"}',
            font_family='Arial, sans-serif',
            icon_pack='heroicons',
            is_default=True,
            is_active=True
        )
        db.session.add(self.test_theme)
        
        db.session.commit()
    
    def test_app_creation(self):
        """Test app creation"""
        self.assertIsNotNone(self.app)
        self.assertEqual(self.app.config['TESTING'], True)
    
    def test_user_creation(self):
        """Test user creation and authentication"""
        # Test user creation
        user = User.query.filter_by(email='test@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.role, 'user')
        self.assertTrue(user.is_active)
        
        # Test password checking
        self.assertTrue(user.check_password('test123'))
        self.assertFalse(user.check_password('wrongpassword'))
        
        # Test admin user
        admin = User.query.filter_by(email='admin@example.com').first()
        self.assertIsNotNone(admin)
        self.assertEqual(admin.role, 'admin')
        self.assertTrue(admin.is_admin())
    
    def test_course_creation(self):
        """Test course creation"""
        course = Course.query.filter_by(prefix='test').first()
        self.assertIsNotNone(course)
        self.assertEqual(course.name, 'Test Course')
        self.assertEqual(course.prefix, 'test')
        self.assertTrue(course.is_active)
    
    def test_theme_creation(self):
        """Test theme creation"""
        theme = Theme.query.filter_by(name='test-theme').first()
        self.assertIsNotNone(theme)
        self.assertEqual(theme.display_name, 'Test Theme')
        self.assertTrue(theme.is_default)
        
        # Test theme variables
        variables = theme.get_variables()
        self.assertEqual(variables['--bg-primary'], '#000')
        self.assertEqual(variables['--accent'], '#fff')
    
    def test_file_validator(self):
        """Test file validation"""
        validator = FileValidator()
        
        # Test allowed extensions
        self.assertTrue(validator.is_allowed_extension('test.pdf'))
        self.assertTrue(validator.is_allowed_extension('test.docx'))
        self.assertTrue(validator.is_allowed_extension('test.jpg'))
        self.assertFalse(validator.is_allowed_extension('test.exe'))
        self.assertFalse(validator.is_allowed_extension('test.php'))
        
        # Test double extension detection
        self.assertTrue(validator._has_double_extension('test.txt.exe'))
        self.assertFalse(validator._has_double_extension('test.txt'))
    
    def test_local_storage(self):
        """Test local storage backend"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalStorageBackend(temp_dir)
            
            # Test file operations
            test_key = 'test/file.txt'
            test_content = b'Hello, World!'
            
            # Create a mock file object
            from io import BytesIO
            from werkzeug.datastructures import FileStorage
            
            file_obj = FileStorage(
                stream=BytesIO(test_content),
                filename='test.txt',
                content_type='text/plain'
            )
            
            # Test file storage
            self.assertTrue(storage.put(file_obj, test_key))
            self.assertTrue(storage.exists(test_key))
            
            # Test file retrieval
            stream = storage.stream(test_key)
            self.assertIsNotNone(stream)
            content = b''.join(stream)
            self.assertEqual(content, test_content)
            
            # Test file deletion
            self.assertTrue(storage.delete(test_key))
            self.assertFalse(storage.exists(test_key))
    
    def test_authentication_service(self):
        """Test authentication service"""
        # Test user authentication
        user = authenticate_user('test@example.com', 'test123')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'test@example.com')
        
        # Test failed authentication
        user = authenticate_user('test@example.com', 'wrongpassword')
        self.assertIsNone(user)
        
        # Test non-existent user
        user = authenticate_user('nonexistent@example.com', 'password')
        self.assertIsNone(user)
    
    def test_home_page(self):
        """Test home page access"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Notu', response.data)
    
    def test_login_page(self):
        """Test login page access"""
        response = self.client.get('/auth/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
    
    def test_courses_page(self):
        """Test courses page access"""
        response = self.client.get('/courses')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Courses', response.data)
    
    def test_admin_dashboard_protection(self):
        """Test admin dashboard protection"""
        # Test unauthenticated access
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test user access (should be forbidden)
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.test_user.id)
            sess['_fresh'] = True
        
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_user_dashboard_protection(self):
        """Test user dashboard protection"""
        # Test unauthenticated access
        response = self.client.get('/user/dashboard')
        self.assertEqual(response.status_code, 302)  # Redirect to login

def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)

if __name__ == '__main__':
    run_tests()
