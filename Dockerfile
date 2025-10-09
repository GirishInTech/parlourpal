# Use official Python image
FROM python:3.11-slim

# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Collect static files (for Django)
RUN python manage.py collectstatic --noinput || true

# Expose Django default port
EXPOSE 8000

# Start server (local test mode)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
