FROM python:3.12-slim

# Prevent Python from writing .pyc files & buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Collect static files for WhiteNoise serving
RUN python manage.py collectstatic --noinput || true

# Security: Create non-root user and grant group 0 access for OpenShift (Rahti) arbitrary UID execution
RUN useradd -m -u 1000 djangouser && \
    chown -R djangouser:djangouser /app && \
    chgrp -R 0 /app && \
    chmod -R g=u /app

USER 1000

EXPOSE 8000

# Default CMD - run production WSGI via Gunicorn
CMD ["gunicorn", "ExcellStudy.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120"]
