# RAG System Backend API

Backend API sử dụng Django (Python) cho hệ thống RAG (Retrieval-Augmented Generation) với PostgreSQL.

## Cấu trúc thư mục

```
backend/
├── apps/                    # Các module ứng dụng (Domain-Driven Design)
│   ├── users/               # Quản lý người dùng, Role, Permission
│   ├── documents/           # Quản lý tài liệu và Chunks
│   └── operations/          # Tiến trình xử lý (Jobs), Chat, Logs
├── config/                  # Cấu hình project Django
├── chroma_data/             # Vector Database (Local ChromaDB)
├── .env                     # File biến môi trường (chứa mật khẩu DB)
├── manage.py                # Command-line utility của Django
└── requirements.txt         # Các thư viện Python cần thiết
```

## Cài đặt và Chạy thử nghiệm Local

### 1. Cài đặt Python Dependencies

Bạn cần kích hoạt môi trường ảo (virtual environment) và chạy lệnh cài đặt:
```bash
python -m pip install -r requirements.txt
```

### 2. Cấu hình thông tin PostgreSQL

Tạo database có tên `rag_system` trong pgAdmin.
Kiểm tra nội dung file `.env` đã trỏ đúng vào CSDL mới chưa:

```env
POSTGRES_DB=rag_system
POSTGRES_USER=postgres
POSTGRES_PASSWORD=mat_khau_cua_ban
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
```

### 3. Migrations (Khởi tạo Database)

Đưa các bảng dữ liệu của Django vào trong PostgreSQL:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Chạy Server

```bash
python manage.py runserver
```

Server sẽ khởi chạy tại URL nội bộ: `http://localhost:8000`
