# 🐳 RAG System - Docker Setup Guide (Microservices Optimized)

Hệ thống RAG doanh nghiệp đã được tối ưu hóa theo kiến trúc Microservices, sử dụng MongoDB Atlas và ChromaDB.

---

## 📋 Yêu Cầu Hệ Thống

1. **Docker Desktop**: Để chạy các Service nội bộ (Backend, ChromaDB).
2. **MongoDB Atlas Account**: Hệ thống đã được cấu hình mặc định để kết nối với Cloud Atlas nhằm tối ưu hiệu năng.
3. **Python 3.11+**: Nếu bạn muốn chạy script trực tiếp không qua Docker.

---

## 🚀 Khởi Động Nhanh

### 1. Chuẩn Bị File Cấu Hình
Hệ thống sử dụng file `.env.docker.local` để quản lý các biến môi trường cho Docker.

### 2. Khởi Động Services

```powershell
# Di chuyển vào thư mục project
cd D:\RAG\doantotnghiep

# Khởi động Backend và ChromaDB
docker-compose --env-file .env.docker.local up -d --build
```

---

## 📍 Service URLs

Sau khi khởi động thành công:

| Service | URL | Mô Tả |
|---------|-----|-------|
| **Backend API** | http://localhost:8000 | FastAPI Server chính |
| **Swagger UI** | http://localhost:8000/docs | Tài liệu API tương tác |
| **ChromaDB** | http://localhost:8001 | Vector Database |
| **MongoDB Atlas** | [Cloud Dashboard](https://cloud.mongodb.com) | Database Cloud |

---

## 🏗️ Kiến Trúc Microservices

Hệ thống được thiết kế để có thể scale độc lập:
- **IAM Service**: Quản lý định danh và phân quyền.
- **Ingestion Service**: Xử lý và băm nhỏ tài liệu.
- **Vector Search Service**: Tìm kiếm ngữ nghĩa.
- **Chat Service**: Giao tiếp AI.

---

## 🛠️ Lệnh Thường Dùng

### Xem Logs
```powershell
docker-compose --env-file .env.docker.local logs -f backend
```

### Dừng Hệ Thống
```powershell
docker-compose --env-file .env.docker.local down
```

### Reset Vector Database
```powershell
# Xóa container và volume dữ liệu ChromaDB
docker-compose --env-file .env.docker.local down -v
```

---

## 🧪 Kiểm Tra Sức Khỏe (Health Check)

Kiểm tra trạng thái backend:
```powershell
curl http://localhost:8000/health
```

---

**Lưu ý:** Hệ thống đã loại bỏ Neo4j để tối ưu độ gọn nhẹ. Toàn bộ logic phân tầng đã được chuyển sang cấu trúc Summary-Detail trên MongoDB và ChromaDB.
