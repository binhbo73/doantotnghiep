# RAG Enterprise System - Quy mô Đa doanh nghiệp (Multi-tenancy)

Hệ thống RAG (Retrieval-Augmented Generation) phân tầng dành cho doanh nghiệp, hỗ trợ quản lý đa tổ chức, phân quyền chi tiết và tổ chức tri thức theo chủ đề.

---

## ✅ TỔNG QUAN KIẾN TRÚC
- **MongoDB** (Database chính - Phân tầng & Metadata): 17 collections
- **ChromaDB** (Vector Database - Search thông minh): 1 collection
- **Kiến trúc Microservices**: IAM Service, Ingestion Service, Vector Search Service, Chat Service.

---

## 🔵 NHÓM 1 — IAM (Identity & Access Management)
👉 Quản lý đa doanh nghiệp, phòng ban, user, role linh hoạt.
👉 **7 collections**

1. **companies**: Thông tin pháp nhân doanh nghiệp (Tên, mã số thuế, domain...).
2. **departments**: Phân cấp phòng ban (Cấu trúc cây - Tree structure).
3. **users**: Tài khoản người dùng (gắn chặt với Company & Department).
4. **roles**: Danh sách vai trò (Hệ thống dùng chung & DN tự định nghĩa).
5. **permissions**: Các hành động cụ thể (vđ: `DOC_READ`, `USER_CREATE`).
6. **user_roles**: Bảng nối một người dùng với nhiều vai trò.
7. **role_permissions**: Bảng nối một vai trò với nhiều quyền hạn.

---

## 🟢 NHÓM 2 — KNOWLEDGE BASE (RAG Core)
👉 Quản lý tri thức, cây thư mục và cấu trúc RAG phân tầng (Hierarchical RAG).
👉 **5 collections**

8. **folders**: Cây thư mục/Chủ đề (Hỗ trợ parent_id vô hạn cấp).
9. **documents**: Thông tin file tài liệu gốc đã tải lên.
10. **document_chunks**: Các đoạn văn bản đã băm nhỏ (Cấu trúc Summary -> Detail).
11. **document_permissions**: Phân quyền ngoại lệ (Gán quyền cho cá nhân trên từng file).
12. **tags**: Nhãn dán phân loại và lọc tài liệu nhanh.

---

## 🟠 NHÓM 3 — AI OPERATIONS & CHAT
👉 Hội thoại AI và giám sát vận hành toàn bộ hệ thống.
👉 **5 collections**

13. **conversations**: Quản lý các phiên chat của từng người dùng.
14. **messages**: Nội dung tin nhắn kèm trích dẫn (citations) từ tài liệu.
15. **ai_feedback**: Lưu đánh giá Like/Dislike để tối ưu chất lượng AI.
16. **processing_jobs**: Trạng thái xử lý tài liệu (OCR, Embedding, Indexing).
17. **audit_logs**: Nhật ký hoạt động chi tiết (Ai, làm gì, lúc nào) - Phục vụ bảo mật.

---

## 🚀 ĐIỂM MẠNH CỦA HỆ THỐNG
1. **Kiến trúc Microservices**: Sẵn sàng mở rộng (Scale-out) khi số lượng người dùng tăng cao.
2. **Bảo mật Đa tầng**: Dữ liệu giữa các công ty được cô lập hoàn toàn.
3. **Hierarchical RAG**: Trả lời cực chính xác nhờ việc hiểu cấu trúc Tài liệu (Chương -> Mục -> Nội dung chi tiết).
4. **Không Neo4j**: Tối ưu hiệu năng, giảm sự phức tạp nhưng vẫn giữ được logic phân cấp nhờ MongoDB.
5. **Sẵn sàng Sản xuất**: Hỗ trợ Soft-delete, Indexing tối ưu và Audit Logs đầy đủ.

---

👉 **Tài liệu hướng dẫn chi tiết:** [system_logic_and_schema.md](./system_logic_and_schema.md)