# Notu - Notes Upload App

A modern Flask application for uploading, organizing, and sharing course notes and documents with a beautiful green/black theme and dual storage backend support.

## Features

- **Course Management**: Admin-defined courses with prefix-based organization
- **Document Categories**: Three categories (notes, cats, others) with path-based routing
- **Dual Storage**: Local filesystem and S3-compatible storage with one-click sync
- **Privacy Controls**: Public/private document visibility
- **Role-Based Access**: Admin and user roles with appropriate permissions
- **Modern UI**: Bootstrap + Tailwind CSS with green/black theme
- **Theme System**: Configurable themes with CSS variables
- **File Validation**: Secure file uploads with MIME type validation
- **Audit Logging**: Comprehensive activity tracking
- **Responsive Design**: Mobile-friendly interface

## Quick Start

### Prerequisites

- Python 3.8+
- pip (Python package installer)
- MySQL 8.0+ (or use Docker Compose)
- Docker and Docker Compose (optional, for easy MySQL setup)

### Installation

#### Option 1: Using Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd notu
   ```

2. **Start MySQL with Docker Compose**
   ```bash
   docker-compose up -d mysql
   ```

3. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up the database**
   ```bash
   python setup_mysql.py
   python seed.py
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

#### Option 2: Using Local MySQL

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd notu
   ```

2. **Install and configure MySQL**
   - Install MySQL 8.0+ on your system
   - Create a database named `notu`
   - Create a user `notu` with password `notu123`
   - Grant all privileges on `notu` database to `notu` user

3. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables**
   ```bash
   cp env.example .env
   # Edit .env file with your MySQL credentials
   ```

6. **Set up the database**
   ```bash
   python setup_mysql.py
   python seed.py
   ```

7. **Run the application**
   ```bash
   python run.py
   ```

#### Access the Application

- Open your browser to `http://localhost:5000`
- Login with `admin@notu.local` / `admin123` (admin)
- Or login with `user@notu.local` / `user123` (user)

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=mysql+pymysql://notu:notu123@localhost:3306/notu

# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=notu
MYSQL_PASSWORD=notu123
MYSQL_DATABASE=notu
MYSQL_ROOT_USER=root
MYSQL_ROOT_PASSWORD=rootpassword

# S3 Configuration (optional)
S3_BUCKET_NAME=your-bucket-name
S3_REGION=us-east-1
S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud  # For Scaleway
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# File Upload Settings
MAX_CONTENT_LENGTH=104857600  # 100MB
ALLOWED_EXTENSIONS=pdf,doc,docx,txt,jpg,jpeg,png,gif
```

### Storage Backends

The application supports two storage backends:

1. **Local Storage**: Files stored in `storage/local/` directory
2. **S3 Storage**: Files stored in AWS S3, Scaleway Object Storage, or other S3-compatible services

Switch between backends in the admin panel or set `ACTIVE_STORAGE_BACKEND` in your configuration.

#### Scaleway Object Storage Configuration

To use Scaleway Object Storage instead of AWS S3:

```env
S3_BUCKET_NAME=your-scaleway-bucket
S3_REGION=fr-par
S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud
AWS_ACCESS_KEY_ID=your-scaleway-access-key
AWS_SECRET_ACCESS_KEY=your-scaleway-secret-key
ACTIVE_STORAGE_BACKEND=s3
```

Replace `your-scaleway-bucket` with your actual Scaleway bucket name and provide your Scaleway access credentials.

## Project Structure

```
notu/
├── app/                    # Flask application factory
├── blueprints/            # Flask blueprints
│   ├── auth.py           # Authentication routes
│   ├── public.py         # Public pages
│   ├── user.py           # User dashboard
│   ├── admin.py          # Admin dashboard
│   └── api.py            # API endpoints
├── config.py             # Configuration classes
├── models.py             # SQLAlchemy models
├── services/             # Business logic
│   ├── storage.py        # Storage backends
│   ├── security.py       # File validation
│   ├── auth.py           # Authentication utilities
│   └── sync.py           # Storage synchronization
├── templates/            # Jinja2 templates
├── static/               # Static assets
│   ├── css/             # Stylesheets
│   └── js/              # JavaScript
├── requirements.txt      # Python dependencies
├── run.py               # Application entry point
├── seed.py              # Database seeding script
└── README.md            # This file
```

## Usage

### Admin Features

- **Course Management**: Create, edit, and delete courses
- **User Management**: Manage user accounts and roles
- **Storage Management**: Switch between storage backends
- **Sync Operations**: Synchronize files between storage backends
- **Theme Management**: Create and manage UI themes
- **Audit Logs**: View system activity logs

### User Features

- **Document Upload**: Upload PDFs, documents, and images
- **Privacy Control**: Set documents as public or private
- **Document Management**: Edit, delete, and organize documents
- **Statistics**: View upload statistics and storage usage
- **Search**: Search through public documents

### Public Features

- **Course Browsing**: Browse available courses and categories
- **Document Viewing**: View public documents inline
- **Document Download**: Download public documents
- **Search**: Search through public documents
- **Theme Selection**: Choose from available themes

## API Endpoints

The application provides a REST API for frontend interactions:

- `GET /api/documents/<id>/toggle-privacy` - Toggle document privacy
- `DELETE /api/documents/<id>/delete` - Delete document
- `GET /api/courses/<id>/documents` - Get course documents
- `GET /api/themes` - Get available themes
- `GET /api/search` - Search documents
- `GET /api/user/stats` - Get user statistics
- `GET /api/admin/stats` - Get admin statistics

## Security Features

- **File Validation**: MIME type checking and file size limits
- **Secure Filenames**: Using `secure_filename` for uploads
- **CSRF Protection**: Form protection with Flask-WTF
- **Role-Based Access**: Admin and user permission levels
- **Audit Logging**: Comprehensive activity tracking
- **Session Security**: Secure session management

## Customization

### Themes

Create custom themes by adding entries to the `Theme` model:

```python
theme = Theme(
    name='custom-theme',
    display_name='Custom Theme',
    variables_json='{"--bg-primary": "#000", "--accent": "#fff"}',
    font_family='Arial, sans-serif',
    icon_pack='fontawesome',
    is_default=False
)
```

### Storage Backends

Implement custom storage backends by extending the `IStorageBackend` interface:

```python
class CustomStorageBackend(IStorageBackend):
    def put(self, file, key):
        # Implementation
        pass
    
    def get_url(self, key, public=False, expires_in=3600):
        # Implementation
        pass
    
    # ... other methods
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Database Migrations

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Building Assets

```bash
# Install Tailwind CSS CLI
npm install -g tailwindcss

# Build Tailwind CSS
tailwindcss -i static/css/input.css -o static/css/tailwind.css --watch
```

## Deployment

### Production Setup

1. **Set environment variables**
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY=your-production-secret-key
   export DATABASE_URL=mysql+pymysql://user:pass@localhost/notu
   ```

2. **Install production dependencies**
   ```bash
   pip install gunicorn pymysql cryptography
   ```

3. **Run with Gunicorn**
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 run:app
   ```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python seed.py

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue on the GitHub repository.
