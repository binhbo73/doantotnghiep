# Cấu Trúc Backend - Django + FastAPI Hybrid

## 📁 Cấu Trúc Thư Mục

```
backend/
├── config/                    # 🔧 Cấu hình Django chính
│   ├── settings.py           # Cài đặt Django (sẵn sàng production)
│   ├── urls.py               # Định tuyến URL
│   ├── asgi.py               # Cấu hình ASGI (async)
│   └── wsgi.py               # Cấu hình WSGI (sync - Gunicorn dùng cái này)
│
├── apps/                      # 📦 Ứng dụng Django (chia theo chức năng)
│   ├── users/                # Quản lý tài khoản & phân quyền
│   │   ├── models.py         # Model: Account, Role, Permission
│   │   └── migrations/       # Lịch sử thay đổi Database
│   ├── documents/            # Quản lý tài liệu
│   │   ├── models.py
│   │   └── migrations/
│   └── operations/           # Quản lý tác vụ & quy trình
│       ├── models.py
│       └── migrations/
│
├── api/                       # 🌐 REST API (Django REST Framework - DRF)
│   ├── serializers/          # Serializer: xác thực & chuyển đổi dữ liệu
│   │   ├── user_serializer.py
│   │   └── document_serializer.py
│   ├── views/                # ViewSet: xử lý API requests
│   │   ├── user_viewset.py
│   │   └── document_viewset.py
│   └── routers/              # Router: đăng ký URL endpoints
│       └── __init__.py       # Cấu hình router chính
│
├── core/                      # ⚙️ Core utilities & trợ giúp
│   ├── exceptions/           # Exception tùy chỉnh
│   │   └── __init__.py       # AppException, ValidationError, NotFoundError...
│   ├── constants/            # Hằng số ứng dụng
│   │   └── __init__.py       # APP_NAME, VERSION, DEFAULTS, etc.
│   ├── middleware/           # Middleware Django (auth, CORS, logging)
│   ├── permissions/          # Custom permission cho DRF
│   ├── utils/                # Hàm trợ giúp chung
│   │   └── __init__.py       # sanitize_input, paginate_queryset, etc.
│   └── decorators/           # Decorator tùy chỉnh
│
├── repositories/             # 🗄️ Data access layer (Repository pattern)
│   └── __init__.py           # BaseRepository, các repository cụ thể
│
├── services/                 # 💼 Business logic layer (logic kinh doanh)
│   └── __init__.py           # BaseService, auth_service, document_service...
│
├── scripts/                  # 📜 Script quản lý & tiện ích
│   ├── seed_data.py          # Nhập dữ liệu ban đầu vào database
│   ├── fixtures/             # Test data (dữ liệu test)
│   └── management_commands/  # Custom Django management commands
│
├── tests/                    # 🧪 Test suite (kiểm thử)
│   ├── conftest.py           # Cấu hình Pytest
│   ├── test_auth.py          # Test xác thực
│   └── test_api.py           # Test API endpoints
│
├── logs/                     # 📋 Nhật ký ứng dụng
├── uploads/                  # 📤 File người dùng tải lên
├── staticfiles/              # 🎨 Static files (CSS, JS, images)
├── media/                    # 📸 Media files (nội dung người dùng)
├── qdrant_data/              # 🔍 Dữ liệu Qdrant (vector DB)
│
├── manage.py                 # Django CLI tool
├── Dockerfile                # Cấu hình Docker
├── requirements.txt          # Dependencies Python
├── .env.local                # Biến môi trường local (không commit)
└── .env.local.example        # Template .env
```

## 🏗️ Các Lớp Kiến Trúc

### 1. **Presentation Layer (API) - Tầng Giao Diện**
- `api/views/` - ViewSet xử lý HTTP request từ client
- `api/serializers/` - Validate & chuyển đổi dữ liệu JSON ↔ Python object
- `api/routers/` - Đăng ký URL endpoints (ví dụ: /api/users/, /api/documents/)

### 2. **Business Logic Layer - Tầng Logic Kinh Doanh**
- `services/` - Xử lý logic chính: auth, document processing, embeddings...
- `repositories/` - Truy cập data từ database (Repository pattern)

### 3. **Core Layer - Tầng Core Tiện Ích**
- `core/exceptions/` - Exception tùy chỉnh (ValidationError, NotFoundError...)
- `core/constants/` - Hằng số toàn app (VERSION, DEFAULTS, TIMEOUTS...)
- `core/middleware/` - Middleware: xác thực token, CORS, logging request
- `core/permissions/` - Custom permission DRF (check user.role, access control)
- `core/utils/` - Helper function: sanitize, paginate, format...
- `core/decorators/` - Decorator: @login_required, @permission_required...

### 4. **Data Layer - Tầng Dữ Liệu**
- `apps/*/models.py` - Django ORM models (Account, Document, Operation...)
- `apps/*/migrations/` - Lịch sử thay đổi schema database
- **PostgreSQL database** - Được quản lý qua Django ORM

### 5. **Vector DB Layer - Tầng Vector Database**
- **ChromaDB** - Lưu embeddings & thực hiện semantic search cho RAG

## 📝 Cách Sử Dụng Thường Gặp

### ✅ Thêm API endpoint mới
```bash
# 1. Tạo model trong apps/[domain]/models.py
#    (ví dụ: class Company(models.Model): ...)

# 2. Tạo migration (lịch sử database)
python manage.py makemigrations

# 3. Tạo Serializer trong api/serializers/
#    (ví dụ: class CompanySerializer(serializers.ModelSerializer): ...)

# 4. Tạo ViewSet trong api/views/
#    (ví dụ: class CompanyViewSet(viewsets.ModelViewSet): ...)

# 5. Đăng ký trong api/routers/__init__.py
#    (ví dụ: router.register(r'companies', CompanyViewSet))
```

### ✅ Thêm business logic
```bash
# 1. Tạo Repository trong repositories/__init__.py
#    (ví dụ: class CompanyRepository(BaseRepository): ...)

# 2. Tạo Service trong services/__init__.py
#    (ví dụ: class CompanyService(BaseService): ...)

# 3. Sử dụng Service trong ViewSet
#    (ví dụ: service.get_by_id(id) trong view)
```
File Chính Cần Chỉnh Sửa

| File | Mục Đích |
|------|---------|
| `config/settings.py` | Cài đặt Django (DATABASE, INSTALLED_APPS, MIDDLEWARE...) |
| `config/urls.py` | Định tuyến URL chính (/admin/, /api/...) |
| `api/routers/__init__.py` | Đăng ký các endpoint API mới |
| `apps/*/models.py` | Định nghĩa các model database |
| `services/__init__.py` | Thêm business logic |
| `core/exceptions/__init__.py` | Thêm custom exception |
| `scripts/seed_data.py` | Nhập dữ liệu test vào database |

## 🚀 Checklist Deploy Production

- [ ] ✅ `.env.local` được ignore trong `.gitignore` (không commit secret)
- [ ] ✅ `SECRET_KEY` lấy từ environment variable (không hardcode)
- [ ] ✅ `DEBUG = False` trong production
- [ ] ✅ `ALLOWED_HOSTS` được cấu hình (domain sản xuất)
- [ ] ✅ Database migration: `python manage.py migrate`
- [ ] ✅ Collect static files: `python manage.py collectstatic`
- [ ] ✅ Gunicorn cấu hình (đã có trong Dockerfile)
- [ ] ✅ Error logging cấu hình
- [ ] ✅ CORS cấu hình (cho frontend domain)

---

**🎯 Trạng Thái:** Production-ready Django backend với DRF API
**📅 Cập Nhật Lần Cuối:** 2026-03-28
**📍 URL Chính:**
- Admin: http://localhost:8000/admin/
- Health: http://localhost:8000/health/
- API: http://localhost:8000/api/

- [ ] All `.env.local` files git-ignored
- [ ] SECRET_KEY pulled from environment
- [ ] DEBUG set to False in production
- [ ] ALLOWED_HOSTS configured
- [ ] Database migrations applied
- [ ] Static files collected: `python manage.py collectstatic`
- [ ] Gunicorn configured (currently in Dockerfile)
- [ ] Error logging configured
- [ ] CORS configured for frontend domain

---

**Status:** Production-ready Django backend with DRF API
**Last Updated:** 2026-03-28
