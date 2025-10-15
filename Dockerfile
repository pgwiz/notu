FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p storage/local

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Create startup script
RUN echo '#!/bin/bash\n\
echo "🚀 Starting Notu application..."\n\
echo "⏳ Waiting for MySQL..."\n\
python -c "import time; import pymysql; [time.sleep(1) for _ in range(30) if not any([pymysql.connect(host=\"mysql\", user=\"notu\", password=\"notu123\", database=\"notu\", charset=\"utf8mb4\") for _ in [1]])]" 2>/dev/null || true\n\
echo "🔧 Setting up database..."\n\
python setup_mysql.py\n\
python migrate_db.py\n\
python seed.py\n\
echo "✅ Setup completed!"\n\
echo "🌐 Starting application..."\n\
gunicorn -w 4 -b 0.0.0.0:5000 run:app' > /app/start.sh && chmod +x /app/start.sh

# Use startup script
CMD ["/app/start.sh"]
