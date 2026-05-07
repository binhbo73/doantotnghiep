# Multi-stage build để giảm kích thước image
FROM python:3.11-slim as builder

WORKDIR /app

# Cài đặt dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


# Final stage
FROM python:3.11-slim

WORKDIR /app

# Cài đặt các package hệ thống cần thiết cho docling/opencv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    default-jre-headless \
    libreoffice-writer \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages từ builder
COPY --from=builder /root/.local /root/.local

# Set PATH để dùng packages từ /root/.local
ENV PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY . .

# Tạo thư mục logs, uploads, static files
RUN mkdir -p logs uploads chroma_data staticfiles media

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Run Django with ASGI server for Channels support
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--ws", "websockets", "--log-level", "info"]
