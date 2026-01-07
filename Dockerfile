# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    poppler-utils \
    tesseract-ocr \
    libreoffice-writer \
    libreoffice-calc \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p tmp/mospi_uploads/images tmp/mospi_uploads/Outputs

# Set proper permissions
RUN chmod -R 755 tmp/

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "demo:app", "--host", "0.0.0.0", "--port", "8000"]


# # Use Python 3.11 slim image as base
# FROM python:3.11-slim

# # # Set environment variables
# # ENV PYTHONDONTWRITEBYTECODE=1 \
# #     PYTHONUNBUFFERED=1 \
# #     DEBIAN_FRONTEND=noninteractive

# # Set work directory
# WORKDIR /app

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     curl \
#     software-properties-common \
#     git \
#     poppler-utils \
#     tesseract-ocr \
#     libreoffice \
#     pandoc \
#     && rm -rf /var/lib/apt/lists/*

# # Copy requirements file first for better caching
# COPY requirements.txt .

# # Install Python dependencies
# RUN pip install --no-cache-dir --upgrade pip && \
#     pip install --no-cache-dir -r requirements.txt

# # Copy application code
# COPY . .

# # Create necessary directories
# RUN mkdir -p tmp/mospi_uploads/images tmp/mospi_uploads/Outputs

# # Set proper permissions
# RUN chmod -R 755 tmp/

# # # Create non-root user for security
# # RUN groupadd -r appuser && useradd -r -g appuser appuser
# # RUN chown -R appuser:appuser /app
# # USER appuser

# # Expose the port
# EXPOSE 8000

# # # Health check
# # HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
# #     CMD curl -f http://localhost:8000/docs || exit 1

# # Run the application
# CMD ["uvicorn", "demo:app", "--host", "0.0.0.0", "--port", "8000"]
