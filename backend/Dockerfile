# Multi-stage build để giảm kích thước image
FROM python:3.11-slim as builder

WORKDIR /app

# Cài đặt dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Ensure CUDA-enabled PyTorch is compatible with the host driver and with FlagEmbedding's
# torch.load safety requirement (torch >= 2.6 for this code path).
RUN pip install --user --no-cache-dir --upgrade --force-reinstall \
    torch==2.6.0+cu124 \
    --index-url https://download.pytorch.org/whl/cu124


# Final stage
FROM python:3.11-slim

WORKDIR /app

# Cài đặt các package hệ thống cần thiết cho docling/opencv + OCR + image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    default-jre-headless \
    libreoffice-writer \
    tesseract-ocr \
    tesseract-ocr-vie \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libjpeg62-turbo \
    libpng16-16 \
    libtiff6 \
    libwebp7 \
    libopenjp2-7 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages từ builder
COPY --from=builder /root/.local /root/.local

# Set PATH để dùng packages từ /root/.local
ENV PATH=/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY . .

# Tạo thư mục logs, uploads, static files, media, models
RUN mkdir -p logs uploads chroma_data staticfiles media media/document_assets

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Run Django with ASGI server for Channels support
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--ws", "websockets", "--log-level", "info"]
