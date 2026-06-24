# Dockerfile for Personal Finance Management System
# ==============================================

# Use Python 3.11 as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=expensetracker.settings_prod

# Set work directory
WORKDIR /app

# Install system dependencies (pure-python PyMySQL does not require client dev headers)
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Run gunicorn dynamically binding to the port provided by Railway
CMD ["sh", "-c", "gunicorn expensetracker.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --timeout 120"]
