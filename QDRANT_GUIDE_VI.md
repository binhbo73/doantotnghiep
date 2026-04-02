# 🔍 Hướng Dẫn Sử Dụng Qdrant (Vector Database)

## 📋 Qdrant là gì?

**Qdrant** là một vector database production-ready dùng để lưu trữ và tìm kiếm embeddings (vector). So với ChromaDB:

| Tiêu Chí | ChromaDB | Qdrant |
|---------|----------|--------|
| **Production-Ready** | ⚠️ Phát triển | ✅ Production Ready |
| **Hiệu Năng** | Trung bình | ⭐ Cao |
| **Scalability** | Giới hạn | ✅ Rất tốt |
| **API** | REST chỉ | REST + gRPC |
| **UI Dashboard** | ❌ Không có | ✅ Có sẵn |
| **Backup/Snapshots** | Cơ bản | ✅ Advanced |

---

## 🚀 Khởi Động Qdrant

### Cách 1: Chạy toàn bộ stack (PostgreSQL + Qdrant + Django)

```bash
cd d:\RAG\doantotnghiep
docker-compose up -d
```

**Output sẽ hiển thị:**
```
Creating rag_postgres  ... done
Creating rag_qdrant    ... done
Creating rag_backend   ... done
```

### Cách 2: Chỉ chạy Qdrant (nếu các service khác đã chạy)

```bash
docker-compose up -d qdrant
```

### Kiểm tra trạng thái:

```bash
docker-compose ps
```

**Kết quả mong đợi:**
```
NAME            COMMAND                  SERVICE      STATUS              PORTS
rag_postgres    postgres                 postgres     Up 2 minutes (healthy)  5433/tcp
rag_qdrant      ./qdrant --http-port 6333 qdrant     Up 1 minute         0.0.0.0:6333->6333/tcp
rag_backend     gunicorn config.wsgi     backend      Up 1 minute (healthy)  0.0.0.0:8000->8000/tcp
```

---

## 🎯 Truy Cập Qdrant UI (Dashboard)

### 📍 URL Qdrant Web UI
```
http://localhost:6333/dashboard
```

### 🖥️ Màn Hình Dashboard Hiển Thị:
- ✅ Danh sách Collections (tương tự "database")
- ✅ Số lượng vectors trong mỗi collection
- ✅ Kích thước bộ nhớ
- ✅ Thống kê tìm kiếm
- ✅ Cài đặt & trạng thái server

### 📸 Giao Diện Qdrant:
```
┌─────────────────────────────────────────┐
│         QDRANT VECTOR SEARCH            │
├─────────────────────────────────────────┤
│ Collections:                             │
│ · documents_embeddings (1,234 vectors)  │
│ · queries_cache (456 vectors)           │
│ · user_preferences (789 vectors)        │
│                                          │
│ Server Health: ✅ OK                     │
│ Memory Usage: 234 MB / 2 GB              │
└─────────────────────────────────────────┘
```

---

## 🔌 API Qdrant (REST)

### 1️⃣ Health Check
```bash
curl http://localhost:6333/health
```

**Response:**
```json
{
  "title": "Qdrant",
  "version": "v1.x.x"
}
```

### 2️⃣ Liệt Kê Các Collections
```bash
curl http://localhost:6333/collections
```

**Response:**
```json
{
  "collections": [
    {
      "name": "documents",
      "vectors_count": 1234,
      "points_count": 1234
    }
  ]
}
```

### 3️⃣ Tạo Collection Mới
```bash
curl -X PUT http://localhost:6333/collections/my_documents \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'
```

### 4️⃣ Thêm Vector (Embedding)
```bash
curl -X PUT http://localhost:6333/collections/my_documents/points \
  -H "Content-Type: application/json" \
  -d '{
    "points": [
      {
        "id": 1,
        "vector": [0.1, 0.2, 0.3, ...],
        "payload": {
          "document_id": "doc_123",
          "text": "Sample text",
          "metadata": {}
        }
      }
    ]
  }'
```

### 5️⃣ Tìm Kiếm Tương Tự (Similarity Search)
```bash
curl -X POST http://localhost:6333/collections/my_documents/points/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.1, 0.2, 0.3, ...],
    "limit": 10,
    "score_threshold": 0.7
  }'
```

**Response:**
```json
{
  "result": [
    {
      "id": 1,
      "score": 0.95,
      "payload": {
        "document_id": "doc_123",
        "text": "Most similar document"
      }
    }
  ]
}
```

---

## 🐍 Sử Dụng Qdrant trong Django Backend

### 1. Cài đặt Qdrant Python Client

```bash
# Trong backend container
docker-compose exec backend pip install qdrant-client
```

Hoặc thêm vào `backend/requirements.txt`:
```
qdrant-client==2.7.0
```

### 2. Tạo Service Qdrant trong Django

**File: `backend/services/vector_db_service.py`**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class QdrantService:
    def __init__(self, host="qdrant", port=6333, api_key="qdrant"):
        self.client = QdrantClient(
            host=host,
            port=port,
            api_key=api_key
        )

    def create_collection(self, collection_name: str, vector_size: int = 1024):
        """Tạo collection cho embeddings"""
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
            return {"status": "success", "message": f"Collection '{collection_name}' created"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def add_vector(self, collection_name: str, vector_id: int, vector: list, payload: dict):
        """Thêm vector vào collection"""
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=vector_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def search_similar(self, collection_name: str, vector: list, limit: int = 10, threshold: float = 0.7):
        """Tìm vectors tương tự"""
        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=vector,
                limit=limit,
                score_threshold=threshold
            )
            return {"status": "success", "results": results}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_vector(self, collection_name: str, vector_id: int):
        """Xóa vector"""
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=[vector_id]
            )
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
```

### 3. Sử Dụng trong ViewSet

**File: `backend/api/views/document_viewset.py`**
```python
from rest_framework import viewsets
from services.vector_db_service import QdrantService

class DocumentViewSet(viewsets.ModelViewSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qdrant_service = QdrantService()

    def create(self, request, *args, **kwargs):
        # Lưu document vào PostgreSQL
        response = super().create(request, *args, **kwargs)
        
        # Tạo embedding từ text
        text = request.data.get('text')
        embedding = generate_embedding(text)  # Từ Ollama/OpenAI
        
        # Lưu vào Qdrant
        self.qdrant_service.add_vector(
            collection_name="documents",
            vector_id=response.data['id'],
            vector=embedding,
            payload={
                "document_id": response.data['id'],
                "text": text
            }
        )
        
        return response
```

---

## 📊 Biến Môi Trường Qdrant

Các biến trong `.env`:

```env
# Qdrant Configuration
QDRANT_HOST=qdrant           # Docker service name
QDRANT_PORT=6333             # Default port
QDRANT_API_KEY=qdrant        # API key cho auth
QDRANT_PERSIST_DIRECTORY=./qdrant_data  # Data persistence
```

---

## 🔧 Các Command Docker Hữu Ích

### Xem logs Qdrant:
```bash
docker-compose logs qdrant -f
```

### Vào container Qdrant:
```bash
docker-compose exec qdrant bash
```

### Xóa toàn bộ dữ liệu Qdrant (cảnh báo!):
```bash
docker-compose down
docker volume rm doantotnghiep_qdrant_data
docker-compose up -d
```

### Backup dữ liệu Qdrant:
```bash
docker-compose exec qdrant qdrant-snapshot create
```

---

## 📱 Ports & Endpoints Tóm Tắt

| Dịch Vụ | Port | URL | Mục Đích |
|--------|------|-----|---------|
| Qdrant HTTP | 6333 | `http://localhost:6333` | REST API |
| Qdrant gRPC | 6334 | `grpc://localhost:6334` | High-performance API |
| Qdrant UI | 6333 | `http://localhost:6333/dashboard` | Web Dashboard |
| PostgreSQL | 5433 | `postgres://localhost:5433` | Relational DB |
| Django Backend | 8000 | `http://localhost:8000` | API Server |

---

## ✅ Checklist Sau Khi Migrate từ ChromaDB

- [ ] ✅ Cấu hình docker-compose.yml (đã sử dụng Qdrant)
- [ ] ✅ Cập nhật .env/.env.example (QDRANT_* variables)
- [ ] ✅ Cài đặt `qdrant-client` trong requirements.txt
- [ ] ✅ Tạo QdrantService class
- [ ] ✅ Cập nhật ViewSets sử dụng QdrantService
- [ ] ✅ Tạo collections ban đầu (seed_data.py)
- [ ] ✅ Test API search endpoints
- [ ] ✅ Xóa ChromaDB references từ code cũ

---

**🎯 Trạng Thái:** Qdrant đã được cấu hình thay ChromaDB
**📚 PDF Tham Khảo:** https://qdrant.tech/documentation/
