# MySQL Setup Guide for Notu

This guide will help you set up Notu with MySQL database support.

## Quick Start with Docker Compose (Recommended)

The easiest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone <repository-url>
cd notu

# Start MySQL and the application
docker-compose up -d

# The application will be available at http://localhost:5000
```

## Manual MySQL Setup

### 1. Install MySQL

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install mysql-server mysql-client
sudo mysql_secure_installation
```

#### macOS (with Homebrew):
```bash
brew install mysql
brew services start mysql
```

#### Windows:
Download and install MySQL from [mysql.com](https://dev.mysql.com/downloads/mysql/)

### 2. Create Database and User

Connect to MySQL as root:
```bash
mysql -u root -p
```

Run the following SQL commands:
```sql
-- Create database
CREATE DATABASE notu CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER 'notu'@'localhost' IDENTIFIED BY 'notu123';

-- Grant privileges
GRANT ALL PRIVILEGES ON notu.* TO 'notu'@'localhost';
FLUSH PRIVILEGES;

-- Exit MySQL
EXIT;
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:
```bash
cp env.example .env
```

Edit the `.env` file with your MySQL credentials:
```env
# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=notu
MYSQL_PASSWORD=notu123
MYSQL_DATABASE=notu
MYSQL_ROOT_USER=root
MYSQL_ROOT_PASSWORD=your_root_password
```

### 4. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Set Up Database

```bash
# Run MySQL setup script
python setup_mysql.py

# Run database migrations
python migrate_db.py

# Seed the database
python seed.py
```

### 6. Start the Application

```bash
# Start the application
python run.py
```

## Docker Setup (Alternative)

If you prefer to use Docker for the entire setup:

### 1. Build and Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f app

# Stop services
docker-compose down
```

### 2. Build Docker Image Manually

```bash
# Build the image
docker build -t notu .

# Run with MySQL
docker run -d --name notu-mysql \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=notu \
  -e MYSQL_USER=notu \
  -e MYSQL_PASSWORD=notu123 \
  -p 3306:3306 \
  mysql:8.0

# Wait for MySQL to start
sleep 30

# Run the application
docker run -d --name notu-app \
  --link notu-mysql:mysql \
  -e MYSQL_HOST=mysql \
  -e MYSQL_USER=notu \
  -e MYSQL_PASSWORD=notu123 \
  -e MYSQL_DATABASE=notu \
  -p 5000:5000 \
  notu
```

## Troubleshooting

### Common Issues

#### 1. MySQL Connection Refused
```bash
# Check if MySQL is running
sudo systemctl status mysql  # Linux
brew services list | grep mysql  # macOS

# Start MySQL if not running
sudo systemctl start mysql  # Linux
brew services start mysql  # macOS
```

#### 2. Authentication Plugin Error
If you get an authentication plugin error, update the MySQL user:
```sql
ALTER USER 'notu'@'localhost' IDENTIFIED WITH mysql_native_password BY 'notu123';
FLUSH PRIVILEGES;
```

#### 3. Permission Denied
Make sure the MySQL user has the correct privileges:
```sql
GRANT ALL PRIVILEGES ON notu.* TO 'notu'@'localhost';
FLUSH PRIVILEGES;
```

#### 4. Database Not Found
Create the database:
```sql
CREATE DATABASE notu CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Testing Connection

Test your MySQL connection:
```bash
python setup_mysql.py test
```

### Reset Database

To reset the database:
```bash
# Drop and recreate database
mysql -u root -p -e "DROP DATABASE IF EXISTS notu; CREATE DATABASE notu CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Re-run setup
python setup_mysql.py
python migrate_db.py
python seed.py
```

## Production Considerations

### 1. Security
- Change default passwords
- Use strong passwords
- Restrict MySQL user privileges
- Enable SSL connections
- Use environment variables for sensitive data

### 2. Performance
- Configure MySQL for production use
- Set appropriate buffer sizes
- Enable query caching
- Use connection pooling

### 3. Backup
- Set up regular database backups
- Test backup restoration
- Consider replication for high availability

### 4. Monitoring
- Monitor database performance
- Set up alerts for issues
- Log database operations

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `MYSQL_HOST` | MySQL server host | `localhost` |
| `MYSQL_PORT` | MySQL server port | `3306` |
| `MYSQL_USER` | MySQL username | `notu` |
| `MYSQL_PASSWORD` | MySQL password | `notu123` |
| `MYSQL_DATABASE` | Database name | `notu` |
| `MYSQL_ROOT_USER` | MySQL root username | `root` |
| `MYSQL_ROOT_PASSWORD` | MySQL root password | `` |

## Support

If you encounter issues with MySQL setup:

1. Check the logs: `docker-compose logs mysql`
2. Test connection: `python setup_mysql.py test`
3. Verify environment variables
4. Check MySQL server status
5. Review the troubleshooting section above

For additional help, please open an issue on the GitHub repository.
