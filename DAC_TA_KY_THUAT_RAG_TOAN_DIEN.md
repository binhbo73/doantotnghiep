# ĐẶC TẢ KỸ THUẬT VÀ KỊCH BẢN VẬN HÀNH: HỆ THỐNG RAG DOANH NGHIỆP

**Vị trí**: Kỹ sư trưởng (Senior Software Engineer)
**Đề tài**: Hệ thống Quản trị Tri thức thông minh Đa doanh nghiệp dựa trên cấu trúc RAG phân tầng (Enterprise Hierarchical RAG).

---

## 1. MÔ TẢ TỔNG QUAN HỆ THỐNG (SYSTEM OVERVIEW)

Hệ thống **Enterprise Hierarchical RAG** là một nền tảng quản trị tri thức thông minh, được xây dựng để giải quyết bài toán "quá tải thông tin" và "bảo mật dữ liệu" trong các tổ chức lớn. Khác với các hệ thống AI thông thường, nền tảng này đóng vai trò như một **Trợ lý ảo chuyên sâu**, có khả năng đọc hiểu, phân loại và truy xuất thông tin từ hàng chục ngàn tài liệu nội bộ với độ chính xác và tính bảo mật ở mức cao nhất.

### 1.1. Kiến trúc Đa thuê bao (Multi-tenancy Architecture)
Hệ thống được thiết kế theo mô hình SaaS (Software as a Service), cho phép nhiều doanh nghiệp cùng hoạt động trên một hạ tầng nhưng dữ liệu hoàn toàn cô lập. Mỗi doanh nghiệp sẽ có một "không gian tri thức" riêng, một hệ thống phân quyền riêng và các bộ lọc AI riêng biệt.

### 1.2. Trí tuệ nhân tạo phân tầng (Hierarchical Intelligence)
Điểm cốt lõi của hệ thống là công nghệ **Hierarchical RAG**. Thay vì xử lý văn bản như một chuỗi ký tự dài, hệ thuật toán của chúng tôi phân tích tài liệu theo cấu trúc hình cây (Chương -> Mục -> Trang -> Đoạn văn). Điều này giúp AI nắm bắt được "Bức tranh lớn" (Big Picture) trước khi đi sâu vào chi tiết, giúp câu trả lời luôn đúng ngữ cảnh và có chiều sâu chuyên môn.

### 1.3. Tính an toàn và Tuân thủ (Security & Compliance)
Hệ thống tích hợp chặt chẽ với cơ cấu tổ chức (Phòng ban/Chức vụ). AI sẽ tự động học các quy tắc bảo mật: "Nếu một nhân viên không có quyền đọc tài liệu về Tài chính, AI sẽ tuyệt đối không sử dụng thông tin từ tài liệu đó để trả lời câu hỏi của nhân viên đó". Mọi tương tác với AI đều được lưu vết (Audit Log) để đảm bảo tính minh bạch.

---

## 2. TẦM NHÌN VÀ GIÁ TRỊ CỐT LÕI

Hệ thống này được thiết kế không chỉ là một Chatbot thông thường, mà là một **Hệ điều hành Tri thức Doanh nghiệp** tập trung vào 3 giá trị:
- **Bảo mật tuyệt đối (Multi-tenancy)**: Dữ liệu giữa các công ty được cô lập hoàn toàn ở mức vật lý và logic.
- **Phân quyền năng động (Dynamic RBAC)**: Cho phép mỗi doanh nghiệp tự xây dựng bộ quy tắc bảo mật riêng.
- **Trí tuệ chính xác (Hierarchical Intelligence)**: Loại bỏ hiện tượng AI "nói xạo" bằng cách hiểu cấu trúc tài liệu (Chương/Mục).

---

## 2. PHÂN TÍCH CHỨC NĂNG THEO VAI TRÒ (ROLES)

### A. Quản trị hệ thống (System Admin)
- **Cấp phát Tenant**: Khởi tạo không gian cho các tập đoàn mới.
- **Giám sát toàn cục**: Theo dõi tài nguyên, log hệ thống và đảm bảo tính tuân thủ bảo mật.
- **Quản lý quyền hạt nhân**: Định nghĩa danh mục các "hành động" (Permissions) mà hệ thống hỗ trợ.

### B. Quản trị doanh nghiệp (Company Admin)
- **Kỹ thuật số hóa tổ chức**: Xây dựng sơ đồ phòng ban (Departments).
- **Thiết lập vai trò động**: Tạo các chức danh riêng (vđ: "Trình dược viên", "Kỹ sư hiện trường") và gán quyền hạn tương ứng.
- **Quản lý nhân sự**: Quản lý vòng đời nhân viên (thêm, sửa, khóa tài khoản).

### C. Trưởng phòng ban (Department Lead)
- **Kho tri thức chuyên biệt**: Quản lý các thư mục tài liệu dành riêng cho đội nhóm.
- **Phân quyền Folder (ACL)**: Cấp quyền xem tài liệu nhạy cảm cho đúng người, đúng việc.
- **Kiểm soát quy trình**: Phê duyệt các tài liệu trước khi đưa vào bộ não AI của phòng.

### D. Nhân viên (Staff / End-User)
- **Hỏi đáp tri thức**: Chat với AI dựa trên kho dữ liệu "được phép xem".
- **Trích dẫn nguồn cấp**: AI tự động chỉ ra thông tin nằm ở trang nào, file nào.
- **Không gian cá nhân**: Quản lý tài liệu riêng tư để phục trợ công việc cá nhân.

---

## 3. KỊCH BẢN VẬN HÀNH CHI TIẾT (LIFECYLCES)

## 3. KỊCH BẢN VẬN HÀNH CHI TIẾT (LIFECYCLES)

---

### 📝 KỊCH BẢN 1️⃣: ĐĂNG KÝ CÔNG TY & KHỞI TẠO (Onboarding Scenario)

#### **Nhân vật:** Nguyễn Văn Tâm - Giám đốc Công ty ABC Corp (Công ty bất động sản, 150 nhân viên)
#### **Mục tiêu:** Đăng ký sử dụng hệ thống RAG để quản lý tài liệu nội bộ (Nội quy, hợp đồng, guide kỹ thuật)
#### **Tình huống:** Hôm nay, Tâm được bộ phận IT giới thiệu hệ thống mới, anh muốn dùng thử

---

##### **BƯỚC 1: Giám đốc Tâm truy cập Website & Điền Thông tin Công ty (5 phút)**

```
Timeline: 9:00 AM - Tâm mở trình duyệt Chrome

Frontend:
  URL: https://rag-system.com/register
  
  ┌─────────────────────────────────────────┐
  │     ĐĂNG KÝ DOANH NGHIỆP                │
  ├─────────────────────────────────────────┤
  │ Tên công ty: ABC Corp                   │
  │ Slug/URL: abc-corp                      │
  │ Domain: abc-corp.com                    │
  │ Email liên hệ: toan@abc-corp.com        │
  │ Điện thoại: 0987654331                  │
  │ Địa chỉ: 123 Nguyễn Hữu Cảnh, TP.HCM   │
  │ Ngành: Bất động sản                      │
  │ Số nhân viên: 150                       │
  │ Gói dịch vụ: Pro (100-1000 users)       │
  │                                          │
  │ [ĐĂNG KÝ NGAY]                         │
  └─────────────────────────────────────────┘
```

**Backend xử lý (Tất cả trong 1 transaction):**

```python
# 1. Tạo Company document
db.companies.insertOne({
  "_id": ObjectId("company_abc123"),
  "name": "ABC Corp",
  "slug": "abc-corp",
  "domain": "abc-corp.com",
  "contact_email": "toan@abc-corp.com",
  "phone": "0987654331",
  "address": "123 Nguyễn Hữu Cảnh, TP.HCM",
  "status": "active",
  "subscription_plan": "pro",
  "max_users": 1000,
  "is_deleted": False,
  "created_at": ISODate("2026-03-07T09:00:00Z")
})

# 2. Tạo User Admin (Tâm)
db.users.insertOne({
  "_id": ObjectId("user_tam123"),
  "company_id": ObjectId("company_abc123"),
  "email": "toan@abc-corp.com",
  "password_hash": bcrypt.hash("SecurePassword123"),
  "username": "toan",
  "avatar_url": "https://...",
  "status": "active",
  "is_deleted": False,
  "created_at": ISODate("2026-03-07T09:00:00Z")
})

# 3. Tạo Role "Company Admin" (mặc định)
db.roles.insertOne({
  "_id": ObjectId("role_admin123"),
  "company_id": ObjectId("company_abc123"),
  "name": "Company Admin",
  "description": "Quản trị viên công ty - Quyền truy cập tối đa",
  "level": 100,  # Cao nhất
  "is_custom": False,
  "is_deleted": False,
  "created_at": ISODate("2026-03-07T09:00:00Z")
})

# 4. Tạo Role "Member" (mặc định)
db.roles.insertOne({
  "_id": ObjectId("role_member123"),
  "company_id": ObjectId("company_abc123"),
  "name": "Member",
  "description": "Nhân viên thường - Quyền truy cập cơ bản",
  "level": 10,
  "is_custom": False,
  "is_deleted": False,
  "created_at": ISODate("2026-03-07T09:00:00Z")
})

# 5. Gán User Tâm vào Role Admin
db.user_roles.insertOne({
  "_id": ObjectId(),
  "user_id": ObjectId("user_tam123"),
  "role_id": ObjectId("role_admin123"),
  "company_id": ObjectId("company_abc123"),
  "assigned_at": ISODate("2026-03-07T09:00:00Z"),
  "assigned_by": ObjectId("system_admin"),  # System Admin
  "is_active": True,
  "is_deleted": False
})

# 6. Tạo Permissions mặc định cho company này
permissions = [
  "DOCUMENT_CREATE", "DOCUMENT_VIEW", "DOCUMENT_EDIT", "DOCUMENT_DELETE",
  "FOLDER_CREATE", "FOLDER_MANAGE", "CHAT_ACCESS", "ADMIN_ACCESS"
]

for perm_code in permissions:
  db.permissions.insertOne({
    "_id": ObjectId(),
    "company_id": ObjectId("company_abc123"),
    "code": perm_code,
    "name": perm_code.replace("_", " "),
    "is_deleted": False,
    "created_at": ISODate("2026-03-07T09:00:00Z")
  })

# 7. Gán tất cả Permissions cho Admin Role
admin_perms = db.permissions.find({"company_id": ObjectId("company_abc123")})
for perm in admin_perms:
  db.role_permissions.insertOne({
    "_id": ObjectId(),
    "role_id": ObjectId("role_admin123"),
    "permission_id": perm["_id"],
    "company_id": ObjectId("company_abc123"),
    "is_active": True,
    "is_deleted": False,
    "created_at": ISODate("2026-03-07T09:00:00Z")
  })

# 8. Gán một số permissions cho Member Role
member_perms = ["DOCUMENT_VIEW", "FOLDER_VIEW", "CHAT_ACCESS"]
for perm_code in member_perms:
  perm = db.permissions.findOne({"code": perm_code, "company_id": ObjectId("company_abc123")})
  db.role_permissions.insertOne({
    "_id": ObjectId(),
    "role_id": ObjectId("role_member123"),
    "permission_id": perm["_id"],
    "company_id": ObjectId("company_abc123"),
    "is_active": True,
    "is_deleted": False
  })

# 9. Lưu audit log
db.audit_logs.insertOne({
  "_id": ObjectId(),
  "company_id": ObjectId("company_abc123"),
  "user_id": ObjectId("system_admin"),
  "action": "COMPANY_ONBOARDED",
  "details": {
    "company_name": "ABC Corp",
    "admin_user": "toan@abc-corp.com",
    "plan": "pro"
  },
  "timestamp": ISODate("2026-03-07T09:00:00Z"),
  "is_deleted": False
})
```

**Kết quả:**
```
✅ Company ABC Corp created
✅ Admin user (toan@abc-corp.com) created
✅ Default roles (Admin, Member) created
✅ Default permissions (8) created
✅ Role-Permission mappings created
✅ Audit log recorded

Email gửi tới toan@abc-corp.com:
  "Chào Nguyễn Văn Tâm,
   Công ty ABC Corp đã được đăng ký thành công!
   
   Thông tin đăng nhập:
   - Email: toan@abc-corp.com
   - Password: (tạo tại quá trình đăng ký)
   - Vai trò: Company Admin
   
   Bước tiếp theo: Vào dashboard để thiết lập phòng ban và mời nhân viên."
```

---

##### **BƯỚC 2: Admin Tâm Đăng nhập & Vào Dashboard (2 phút)**

```
Frontend:
  POST /auth/login
  {
    "email": "toan@abc-corp.com",
    "password": "SecurePassword123"
  }

Backend:
  1. Find user by email
     db.users.findOne({email: "toan@abc-corp.com"})
     ├─ Index: email_1 ✅ (5ms)
     ├─ Result: ObjectId("user_tam123"), company_id: ObjectId("company_abc123")
  
  2. Verify password
     bcrypt.compare(password, password_hash) ✅ MATCH
  
  3. Load user roles
     db.user_roles.find({user_id: ObjectId("user_tam123")})
     ├─ Result: role_id = ObjectId("role_admin123")
  
  4. Load permissions for role
     db.role_permissions.find({role_id: ObjectId("role_admin123")})
     ├─ Result: [DOCUMENT_CREATE, DOCUMENT_VIEW, ..., ADMIN_ACCESS]
  
  5. Create JWT token
     JWT payload: {
       user_id: ObjectId("user_tam123"),
       company_id: ObjectId("company_abc123"),
       role: "Company Admin",
       permissions: ["DOCUMENT_CREATE", "DOCUMENT_VIEW", ...]
     }
  
  6. Return token + user info

Response:
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user_tam123",
    "email": "toan@abc-corp.com",
    "company": "ABC Corp",
    "role": "Company Admin"
  }
}

Time: ⏱️ 500ms
```

**Frontend Dashboard:**
```
┌────────────────────────────────────────────────────┐
│  🏢 DASHBOARD - CÔNG TY ABC CORP                   │
├────────────────────────────────────────────────────┤
│                                                    │
│  👤 Xin chào, Nguyễn Văn Tâm (Company Admin)      │
│                                                    │
│  📊 THỐNG KÊ NHANH:                               │
│  ├─ Nhân viên: 0/1000 (chưa có)                   │
│  ├─ Phòng ban: 0                                  │
│  ├─ Tài liệu: 0                                   │
│  └─ Chunks (tri thức): 0                          │
│                                                    │
│  🔧 QUẢN LÝ ADMIN:                                │
│  ├─ [➕ Thêm phòng ban]                           │
│  ├─ [➕ Mời nhân viên]                            │
│  ├─ [⚙️ Quản lý vai trò & quyền]                  │
│  ├─ [📂 Quản lý tài liệu]                         │
│  ├─ [💬 Chat với AI]                              │
│  └─ [📊 Xem báo cáo]                              │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

##### **BƯỚC 3: Admin Tâm Tạo Cơ cấu Phòng ban (10 phút)**

```
Admin click: [➕ Thêm phòng ban]

Form nhập liệu:
┌────────────────────────────────────────────┐
│  THÊM PHÒNG BAN MỚI                        │
├────────────────────────────────────────────┤
│ Tên phòng ban: Nhân sự                     │
│ Mô tả: Phòng quản lý nhân lực              │
│ Trưởng phòng: [Dropdown - chọn sau]        │
│ Ngân sách: 1,000,000,000 VND               │
│ [TẠO]                                      │
└────────────────────────────────────────────┘

Backend:
  POST /api/v1/departments
  {
    "company_id": "company_abc123",
    "parent_id": null,  # Phòng cấp top
    "name": "Nhân sự",
    "description": "Phòng quản lý nhân lực",
    "level": 0,
    "budget": 1000000000
  }

  db.departments.insertOne({
    "_id": ObjectId("dept_hr"),
    "company_id": ObjectId("company_abc123"),
    "parent_id": null,
    "name": "Nhân sự",
    "description": "Phòng quản lý nhân lực",
    "level": 0,
    "budget": 1000000000,
    "manager_id": null,  # Chưa có
    "is_deleted": False,
    "created_at": ISODate("2026-03-07T09:30:00Z")
  })
  └─ Index: company_id_1_parent_id_1 ✅ (5ms)

Audit log:
  db.audit_logs.insertOne({
    action: "DEPARTMENT_CREATED",
    details: {name: "Nhân sự"},
    ...
  })
```

**Lặp lại 2-3 lần để tạo các phòng ban khác:**

```
Phòng ban được tạo:
1. Nhân sự (HR)
   ├─ Chi phí: 1B VND
   └─ Trưởng phòng: [chưa gán]

2. Kỹ thuật (Engineering)
   ├─ Chi phí: 2B VND
   └─ Trưởng phòng: [chưa gán]

3. Tài chính (Finance)
   ├─ Chi phí: 0.5B VND
   └─ Trưởng phòng: [chưa gán]

4. Bán hàng (Sales)
   ├─ Chi phí: 1.5B VND
   └─ Trưởng phòng: [chưa gán]

Thời gian: ⏱️ 2 phút
```

---

##### **BƯỚC 4: Admin Tâm Mời Nhân viên (5 phút)**

```
Admin click: [➕ Mời nhân viên]

Form:
┌────────────────────────────────────────────┐
│  MỜI NHÂN VIÊN                             │
├────────────────────────────────────────────┤
│ Email(s): (CSV hoặc từng email)            │
│   - ngoc@abc-corp.com (Phòng HR)           │
│   - minh@abc-corp.com (Phòng IT)           │
│   - duc@abc-corp.com (Phòng IT)            │
│   - anh@abc-corp.com (Phòng Sales)         │
│                                            │
│ Phòng ban gán mặc định: HR                 │
│ Vai trò gán mặc định: Member               │
│                                            │
│ [GỬI MỜI]                                 │
└────────────────────────────────────────────┘

Backend:
  POST /api/v1/invite/bulk
  {
    "company_id": "company_abc123",
    "invites": [
      {email: "ngoc@abc-corp.com", dept_id: "dept_hr", role: "member"},
      {email: "minh@abc-corp.com", dept_id: "dept_it", role: "member"},
      ...
    ]
  }

  For each email:
    1. db.users.insertOne({
         email: "ngoc@abc-corp.com",
         company_id: ObjectId("company_abc123"),
         dept_id: ObjectId("dept_hr"),
         status: "pending",  # Chưa nhấn confirm
         password_hash: null,  # Chưa đặt
         created_at: now
       })
    
    2. db.user_roles.insertOne({
         user_id: ObjectId("ngoc_user"),
         role_id: ObjectId("role_member123"),
         company_id: ObjectId("company_abc123")
       })
    
    3. Send email:
       "Bạn được mời tham gia ABC Corp!
        Link xác nhận: https://rag-system.com/accept-invite?token=..."

Kết quả:
  ✅ 4 emails sent
  ✅ 4 users created with status "pending"
  ✅ All assigned to role "Member"
  ⏳ Chờ nhân viên confirm email

Thời gian: ⏱️ 2 phút
```

---

##### **BƯỚC 5: Admin Tâm Quản lý Roles & Permissions cho phòng ban (10 phút)**

```
Admin click: [⚙️ Quản lý vai trò & quyền]

Admin muốn tạo custom roles cho từng phòng ban:
┌─────────────────────────────────────────────┐
│  QUẢN LÝ VÀI TRÒ (ROLES)                    │
├─────────────────────────────────────────────┤
│                                             │
│ 📋 VAI TRÒ HIỆN TẠI:                       │
│ ├─ Company Admin (100)       [Edit] [Delete]│
│ ├─ Member (10)               [Edit] [Delete]│
│ ├─ HR Manager (30)           [Edit] [Delete]│
│ ├─ IT Lead (40)              [Edit] [Delete]│
│ └─ Sales Manager (35)        [Edit] [Delete]│
│                                             │
│ [➕ TẠO VÀI TRÒ MỚI]                      │
│                                             │
└─────────────────────────────────────────────┘

Admin tạo: "HR Manager"
  - Tên: HR Manager
  - Mô tả: Trưởng phòng Nhân sự
  - Mức quyền: 30
  - Quyền cấp phát: [
      ☑ DOCUMENT_CREATE
      ☑ DOCUMENT_VIEW
      ☑ DOCUMENT_EDIT
      ☑ FOLDER_MANAGE
      ☑ CHAT_ACCESS
      ☑ EMPLOYEE_MANAGE
      ☐ ADMIN_ACCESS (không cho)
    ]

Backend:
  1. db.roles.insertOne({
       "_id": ObjectId("role_hr_manager"),
       "company_id": ObjectId("company_abc123"),
       "name": "HR Manager",
       "description": "Trưởng phòng Nhân sự",
       "level": 30,
       "is_custom": True,
       "is_deleted": False,
       "created_at": now
     })

  2. For each selected permission:
     db.role_permissions.insertOne({
       "role_id": ObjectId("role_hr_manager"),
       "permission_id": ObjectId("perm_xxx"),
       "company_id": ObjectId("company_abc123"),
       "is_active": True,
       "is_deleted": False
     })

  3. Audit log recorded
     action: "ROLE_CREATED"
```

---

##### **BƯỚC 6: Admin Tâm Gán Nhân viên vào Vai trò (5 phút)**

```
Admin click: [Quản lý nhân viên]

Dashboard:
┌──────────────────────────────────────────────┐
│  DANH SÁCH NHÂN VIÊN                         │
├──────────────────────────────────────────────┤
│ # | Email              | Phòng  | Vai trò    │
│─────────────────────────────────────────────│
│ 1 | ngoc@abc-corp.com  | HR    | Member   ✓  │
│ 2 | minh@abc-corp.com  | IT    | Member   ✓  │
│ 3 | duc@abc-corp.com   | IT    | IT Lead ✓   │
│ 4 | anh@abc-corp.com   | Sales | Member   ✓  │
│                                              │
│ ⚠️ Action: Click "IT Lead" để gán duc      │
└──────────────────────────────────────────────┘

Admin click trên "duc@abc-corp.com" → Edit:
  
┌──────────────────────────────────────────────┐
│  SỬA NHÂN VIÊN: duc@abc-corp.com             │
├──────────────────────────────────────────────┤
│ Email: duc@abc-corp.com                      │
│ Tên: Trần Văn Đức                            │
│ Phòng: IT [không thay đổi]                   │
│ Vai trò: [Dropdown]                          │
│   ☐ Company Admin                            │
│   ☐ Member                                   │
│   ☑ IT Lead  ← Chọn                         │
│                                              │
│ [LƯU]                                        │
└──────────────────────────────────────────────┘

Backend:
  1. db.user_roles.updateOne(
       {user_id: ObjectId("duc_user"), company_id: ObjectId("company_abc123")},
       {$set: {role_id: ObjectId("role_it_lead")}}
     )
  
  2. db.audit_logs.insertOne({
       action: "USER_ROLE_UPDATED",
       details: {user_email: "duc@abc-corp.com", new_role: "IT Lead"},
       ...
     })

Thời gian: ⏱️ 5 phút
```

**Kết quả sau Bước 1-6:**
```
✅ Company ABC Corp đã thiết lập xong cơ cấp tổ chức:

Phòng ban:
├─ HR (Nhân sự)
│  └─ Trưởng phòng: [chưa gán]
├─ IT (Kỹ thuật)
│  └─ Trưởng phòng: Trần Văn Đức
├─ Finance (Tài chính)
│  └─ Trưởng phòng: [chưa gán]
└─ Sales (Bán hàng)
   └─ Trưởng phòng: [chưa gán]

Nhân viên:
├─ ngoc@abc-corp.com (HR, Member)
├─ minh@abc-corp.com (IT, Member)
├─ duc@abc-corp.com (IT, IT Lead) 🔑
└─ anh@abc-corp.com (Sales, Member)

Roles:
├─ Company Admin (100)
├─ Member (10)
├─ HR Manager (30)
├─ IT Lead (40)
└─ Sales Manager (35)

TOTAL TIME: ⏱️ ~35 phút (nhưng chỉ làm 1 lần duy nhất)
```

---

### 📤 KỊCH BẢN 2️⃣: NẠP TRI THỨC PHÂN TẦNG (Hierarchical Ingestion)

#### **Nhân vật:** Nguyễn Thị Ngoại - HR Manager tại ABC Corp
#### **Mục tiêu:** Upload bộ sổ tay nhân viên (200 trang) vào hệ thống RAG
#### **Tình huống:** Ngày thứ 2, Ngoại được giao nhiệm vụ đưa tài liệu nội bộ vào hệ thống

---

##### **BƯỚC 1: Ngoại Truy cập Chat & Click Upload Document (2 phút)**

```
Timeline: 10:00 AM - Ngoại vào hệ thống

Frontend:
  URL: https://rag-system.com/knowledge-base
  
  ┌────────────────────────────────────────────────┐
  │ 📚 KHOANG TRI THỨC                            │
  ├────────────────────────────────────────────────┤
  │                                                │
  │ Phòng ban: [HR ▼]                             │
  │                                                │
  │ Các tài liệu hiện tại:                        │
  │ (Trống - Chưa có tài liệu)                    │
  │                                                │
  │ [➕ UPLOAD TÀI LIỆU MỚI]                      │
  │                                                │
  └────────────────────────────────────────────────┘

Ngoại click: [➕ UPLOAD TÀI LIỆU MỚI]

Form upload:
  ┌────────────────────────────────────────────────┐
  │  UPLOAD TÀI LIỆU                              │
  ├────────────────────────────────────────────────┤
  │ Tên tài liệu: Sổ tay nhân viên 2026           │
  │ Mô tả: Nội quy, chính sách, quy định nội bộ  │
  │ Phòng ban: HR                                 │
  │ Truy cập: [Department ▼] (chỉ HR xem được)   │
  │ File: [📎 Chọn file]                         │
  │ Tags: #nội-quy #chính-sách #hr               │
  │                                                │
  │ [UPLOAD]                                       │
  └────────────────────────────────────────────────┘

Ngoại chọn file: nhan_vien_handbook_200trang.pdf (50MB)
```

---

##### **BƯỚC 2: Backend Nhận File & Tạo Metadata (1 phút)**

```
Backend:
  POST /api/v1/documents/upload
  
  Payload:
  {
    "company_id": "company_abc123",
    "folder_id": null,  # Root level
    "dept_id": "dept_hr",
    "name": "Sổ tay nhân viên 2026",
    "description": "Nội quy, chính sách, quy định nội bộ",
    "access_scope": "department",  # Chỉ phòng HR
    "file": <binary 50MB>
  }

Step 1: Tạo Document record
  db.documents.insertOne({
    "_id": ObjectId("doc_handbook_001"),
    "company_id": ObjectId("company_abc123"),
    "folder_id": null,
    "name": "Sổ tay nhân viên 2026",
    "description": "Nội quy, chính sách, quy định nội bộ",
    "file_name": "nhan_vien_handbook_200trang.pdf",
    "file_path": "s3://rag-bucket/company_abc123/doc_handbook_001.pdf",
    "file_size": 50000000,  # 50MB
    "uploader_id": ObjectId("ngoc_user"),
    "dept_id": ObjectId("dept_hr"),
    "status": "pending",  # Chưa xử lý
    "chunk_count": 0,  # Chưa tính
    "tags": ["nội-quy", "chính-sách", "hr"],
    "access_scope": "department",
    "is_deleted": False,
    "created_at": ISODate("2026-03-07T10:00:00Z")
  })
  └─ Index: company_id_1_status_1 ✅ (5ms)

Step 2: Upload file to S3
  s3_client.put_object(
    Bucket='rag-bucket',
    Key='company_abc123/doc_handbook_001.pdf',
    Body=<50MB file>,
    ContentType='application/pdf'
  )
  Time: ⏱️ 10-15 giây (network)

Step 3: Tạo Processing Job
  db.processing_jobs.insertOne({
    "_id": ObjectId("job_001"),
    "company_id": ObjectId("company_abc123"),
    "document_id": ObjectId("doc_handbook_001"),
    "job_type": "hierarchical_chunking",
    "status": "queued",
    "priority": "high",
    "created_at": ISODate("2026-03-07T10:00:00Z")
  })

Step 4: Trả về response
  Response:
  {
    "success": true,
    "document_id": "doc_handbook_001",
    "status": "processing",
    "message": "Tài liệu đang được xử lý, thời gian ước tính: 2-5 phút"
  }

Thời gian: ⏱️ 15 giây
```

**Frontend hiển thị:**
```
┌────────────────────────────────────────────────┐
│ ✅ UPLOAD THÀNH CÔNG                          │
│                                                │
│ Tài liệu: Sổ tay nhân viên 2026              │
│ Kích thước: 50 MB                             │
│ Trạng thái: ⏳ ĐANG XỬ LÝ (2-5 phút)         │
│                                                │
│ 🔄 Tiến độ:                                   │
│ ├─ ✅ Upload file thành công                  │
│ ├─ ⏳ Phân tích cấu trúc PDF                  │
│ ├─ ⏳ Tạo Summary nodes                       │
│ ├─ ⏳ Tạo Detail nodes                        │
│ ├─ ⏳ Nhúng vectors                           │
│ └─ ⏳ Lưu ChromaDB                            │
│                                                │
│ [Đóng]                                        │
└────────────────────────────────────────────────┘
```

---

##### **BƯỚC 3: Backend Xử lý Hierarchical Chunking (Background Job - 5 phút)**

```
Worker process nhận job từ queue:

=== PHASE 1: Phân tích PDF ===
Time: ⏱️ 1 phút

1. Download file from S3
   s3_client.get_object(Bucket='rag-bucket', Key='...pdf')
   Size: 50MB
   
2. Phân tích structure PDF
   pypdf.PdfReader('...pdf')
   ├─ Total pages: 200
   ├─ Detect headings/chapters
   ├─ Result:
   │  Chapter 1: Lương & Phúc lợi (Pages 1-30)
   │  Chapter 2: Nghỉ phép & Nghỉ lễ (Pages 31-60)
   │  Chapter 3: Quy tắc hành động (Pages 61-100)
   │  Chapter 4: Kỷ luật & Kết thúc hợp đồng (Pages 101-150)
   │  Chapter 5: Thủ tục & Tùy chọn khác (Pages 151-200)
   
3. Tạo mapping: Heading → Page ranges

=== PHASE 2: Tạo Summary Nodes ===
Time: ⏱️ 1.5 phút

For each Chapter:
  1. Trích xuất nội dung chương (30 trang)
  2. Tóm tắt bằng LLM:
     
     Prompt: "Tóm tắt nội dung các trang 1-30 về Lương & Phúc lợi 
              trong không quá 500 từ. Giữ lại các con số, chính sách cụ thể."
     
     Response: "Chương 1 - Lương & Phúc lợi:
                - Lương cơ bản theo vị trí (Level 1-5)
                - Thưởng hiệu suất 10-20% theo KPI
                - Bảo hiểm: BHXH, BHYT, BHTN theo quy định
                - Phụ cấp: gia đình, trẻ em, nơi cách xa
                - Lương 13 tháng theo pháp luật"
     
     Time: 30 giây/chương
  
  3. Lưu vào document_chunks:
     db.document_chunks.insertOne({
       "_id": ObjectId("chunk_summary_001"),
       "doc_id": ObjectId("doc_handbook_001"),
       "company_id": ObjectId("company_abc123"),
       "content": "Chương 1 - Lương & Phúc lợi: [30 trang tóm tắt]...",
       "node_type": "summary",
       "parent_node_id": null,
       "chapter_title": "Lương & Phúc lợi",
       "page_numbers": [1, 30],
       "page_range": "1-30",
       "relevance_score": 0,  # Chưa tính
       "char_count": 2500,
       "is_deleted": False,
       "created_at": ISODate("2026-03-07T10:03:00Z")
     })
     └─ Index: doc_id_1_node_type_1 ✅ (5ms per chunk)
  
  Summary nodes tạo: 5 (1 per chapter)

=== PHASE 3: Tạo Detail Nodes ===
Time: ⏱️ 2 phút

For each Chapter → For each Sub-section:
  
  Example: Chapter 1 → Sub-section 1.1 "Lương cơ bản"
  
  1. Trích xuất nội dung (3-5 trang)
  2. Chia thành 1-2 chunks (mỗi ~4K tokens)
  3. Lưu với parent_id = Summary node
  
  db.document_chunks.insertOne({
    "_id": ObjectId("chunk_detail_001_1"),
    "doc_id": ObjectId("doc_handbook_001"),
    "company_id": ObjectId("company_abc123"),
    "content": "1.1 Lương cơ bản:\n- Level 1 (Intern): 5M VND/tháng\n...",
    "node_type": "detail",
    "parent_node_id": ObjectId("chunk_summary_001"),  # ← LIÊN KẾT
    "section_title": "Lương cơ bản",
    "page_numbers": [1, 5],
    "relevance_score": 0,
    "char_count": 2000,
    "is_deleted": False,
    "created_at": ISODate("2026-03-07T10:03:30Z")
  })

Total Detail nodes: ~50-100 (tùy cấu trúc)

=== PHASE 4: Nhúng Vectors (Embedding) ===
Time: ⏱️ 1-2 phút (tùy LLM)

For each chunk (55-105 nodes):
  
  1. Get OpenAI embedding for content
     POST https://api.openai.com/v1/embeddings
     {
       "model": "text-embedding-3-large",
       "input": "Chương 1 - Lương & Phúc lợi:..."
     }
     
     Response:
     {
       "embedding": [0.0234, -0.0145, 0.0891, ..., 0.0023],
       # 1536 dimensions
     }
     
     Time: 200ms per chunk
  
  2. Update chunk with vector_id
     db.document_chunks.updateOne(
       {_id: ObjectId("chunk_summary_001")},
       {
         $set: {
           vector_id: "v_abc123def456",
           embedded_at: ISODate(...)
         }
       }
     )
  
  3. Insert vào ChromaDB
     chroma_collection.add(
       ids=["v_abc123def456"],
       embeddings=[[0.0234, -0.0145, ...]],
       metadatas=[{
         "doc_id": "doc_handbook_001",
         "company_id": "company_abc123",
         "node_type": "summary",
         "chapter": "Lương & Phúc lợi"
       }],
       documents=["Chương 1 - Lương & Phúc lợi:..."]
     )
     Time: 50ms per chunk

Total time: 100-150 chunks × 200ms = 20-30 phút
Nhưng tối ưu: Parallel processing = 2 phút (batch embedding)

=== PHASE 5: Cập nhật Document Status ===
Time: ⏱️ 30 giây

db.documents.updateOne(
  {_id: ObjectId("doc_handbook_001")},
  {
    $set: {
      status: "completed",
      chunk_count: 105,
      processed_at: ISODate("2026-03-07T10:05:30Z")
    }
  }
)

=== PHASE 6: Lưu Audit Log ===

db.audit_logs.insertOne({
  "_id": ObjectId(),
  "company_id": ObjectId("company_abc123"),
  "user_id": ObjectId("ngoc_user"),
  "action": "DOCUMENT_UPLOADED",
  "details": {
    "doc_id": "doc_handbook_001",
    "doc_name": "Sổ tay nhân viên 2026",
    "total_pages": 200,
    "chunks_created": 105,
    "vectors_created": 105,
    "processing_time_seconds": 330  # 5.5 phút
  },
  "timestamp": ISODate("2026-03-07T10:05:30Z"),
  "is_deleted": False
})

=== KẾT THÚC ===
✅ Document status: completed
✅ 105 chunks created (5 summary + 100 detail)
✅ 105 vectors embedded
✅ ChromaDB indexed
✅ Ready for RAG queries!

TỔNG THỜI GIAN: ⏱️ 5-6 phút
```

**Frontend cập nhật:**
```
┌────────────────────────────────────────────────┐
│ ✅ HOÀN THÀNH XỬ LÝ                          │
│                                                │
│ Tài liệu: Sổ tay nhân viên 2026              │
│ Trạng thái: ✅ READY (Sẵn sàng)               │
│                                                │
│ 📊 THỐNG KÊ:                                  │
│ ├─ Trang: 200                                 │
│ ├─ Chunks: 105 (5 summary + 100 detail)      │
│ ├─ Vectors: 105 ✅                            │
│ └─ Thời gian: 5 phút 30 giây                 │
│                                                │
│ 📁 Cấu trúc:                                  │
│ ├─ Chapter 1: Lương & Phúc lợi (30 trang)    │
│ ├─ Chapter 2: Nghỉ phép & Nghỉ lễ (30 trang)│
│ ├─ Chapter 3: Quy tắc hành động (40 trang)   │
│ ├─ Chapter 4: Kỷ luật & Kết thúc (50 trang)  │
│ └─ Chapter 5: Thủ tục & Tùy chọn (50 trang)  │
│                                                │
│ [Xem chi tiết] [Chia sẻ] [Xóa]               │
└────────────────────────────────────────────────┘
```

---

### 🤖 KỊCH BẢN 3️⃣: TRUY VẤN THÔNG MINH (Intelligent Query)

#### **Nhân vật:** Lê Thị Linh - Nhân viên mới tại ABC Corp (Phòng HR)
#### **Mục tiêu:** Hỏi AI về chính sách nghỉ thai sản
#### **Tình huống:** Linh vừa nhận tin cô đang mang thai, cần tìm hiểu quy định nghỉ phép

---

##### **BƯỚC 1: Linh Truy cập Chat & Gõ Query (1 phút)**

```
Timeline: 14:00 (Chiều)

Frontend:
  Linh truy cập: https://rag-system.com/chat
  
  ┌──────────────────────────────────────────────────┐
  │ 💬 CHAT VỚI AI                                  │
  ├──────────────────────────────────────────────────┤
  │                                                  │
  │ [Bước vào từ ai...]                            │
  │                                                  │
  │ User Linh:                                      │
  │ ┌────────────────────────────────────────────┐ │
  │ │ "Em vừa biết cô đang mang thai đã.       │ │
  │ │ Em muốn hỏi chính sách nghỉ thai sản      │ │
  │ │ của công ty là gì? Thời gian nghỉ được   │ │
  │ │ bao lâu? Cách làm thủ tục thế nào?"      │ │
  │ └────────────────────────────────────────────┘ │
  │                                                  │
  │ [SEND] 🎤                                      │
  └──────────────────────────────────────────────────┘
```

---

##### **BƯỚC 2: Frontend Gửi Query tới Backend (Instant)**

```
POST /api/v1/chat
{
  "conversation_id": "conv_linh_001",  # New conversation
  "user_id": ObjectId("linh_user"),
  "company_id": ObjectId("company_abc123"),
  "dept_id": ObjectId("dept_hr"),
  "query": "Chính sách nghỉ thai sản của công ty là gì? 
           Thời gian nghỉ được bao lâu? Cách làm thủ tục?"
}
```

---

##### **BƯỚC 3: Backend Xác thực & Phân quyền (100-200ms)**

```
Backend:
  1. Verify JWT token ✅
  2. Extract: user_id, company_id, dept_id, permissions
  3. Check: user has CHAT permission?
     db.permissions.findOne({code: "CHAT_ACCESS", company_id: "company_abc123"})
     └─ Result: ✅ YES
  4. Check: Linh có quyền chat? ✅ YES (Member role có permission)
  5. Load permission list từ user's role
     └─ Result: [DOCUMENT_VIEW, CHAT_ACCESS, FOLDER_VIEW]

Time: ⏱️ 100-200ms
```

---

##### **BƯỚC 4: Query Embedding & ChromaDB Search (2-3 giây)**

```
Backend:

Step 1: Embedding query
  OpenAI API:
  POST /v1/embeddings
  {
    "model": "text-embedding-3-large",
    "input": "Chính sách nghỉ thai sản... Thời gian... Thủ tục?"
  }
  
  Response:
  {
    "embedding": [0.0542, -0.0231, 0.0789, ..., 0.0156],
    "tokens": 22
  }
  
  Time: ⏱️ 1500-2000ms

Step 2: ChromaDB similarity search
  collection.query(
    query_embeddings=[[0.0542, -0.0231, ...]],
    n_results=20,  # Lấy top-20
    where={
      "$and": [
        {"company_id": "company_abc123"},
        {"is_deleted": False}
      ]
    }
  )
  
  Cosine similarity tính toán:
  similarity = (query_vector · chunk_vector) / (|query| * |chunk|)
  
  Top results:
  ✅ chunk_summary_002 (similarity: 0.96) 
     "Chapter 2 - Nghỉ phép & Nghỉ lễ: Quy định chung về nghỉ phép..."
  
  ✅ chunk_detail_002_1 (similarity: 0.94)
     "2.1 Nghỉ thai sản: Phụ nữ có quyền nghỉ 4 tháng..."
  
  ✅ chunk_detail_002_2 (similarity: 0.91)
     "2.2 Quy trình: Thông báo cho HR trước 1 tháng, nộp hóa đơn khám thai..."
  
  ✅ chunk_detail_002_3 (similarity: 0.88)
     "2.3 Lương trong kỳ nghỉ thai sản: 60% lương cơ bản..."
  
  ... (16 kết quả khác)
  
  Time: ⏱️ 150-200ms
```

---

##### **BƯỚC 5: Lấy Chi tiết Chunks từ MongoDB (300-500ms)**

```
Backend:

Query IDs: [chunk_summary_002, chunk_detail_002_1, chunk_detail_002_2, chunk_detail_002_3, ...]

db.document_chunks.find({
  _id: {$in: [chunk_summary_002, chunk_detail_002_1, ...]},
  company_id: ObjectId("company_abc123"),
  is_deleted: False
})
.sort({relevance_score: -1})
.limit(5)
└─ Index: company_id_1_is_deleted_1 ✅ (10ms)

Results:
[
  {
    "_id": ObjectId("chunk_summary_002"),
    "content": "Chương 2 - Nghỉ phép & Nghỉ lễ:\nCông ty ABC Corp tuân thủ đầy đủ ...",
    "node_type": "summary",
    "parent_node_id": null,
    "page_numbers": [31, 60],
    "relevance_score": 0.96,
    "doc_id": ObjectId("doc_handbook_001")
  },
  {
    "_id": ObjectId("chunk_detail_002_1"),
    "content": "2.1 Nghỉ thai sản:\nPhụ nữ công nhân viên có quyền nghỉ 4 tháng...",
    "node_type": "detail",
    "parent_node_id": ObjectId("chunk_summary_002"),  # ← Liên kết
    "page_numbers": [33, 35],
    "relevance_score": 0.94,
    "doc_id": ObjectId("doc_handbook_001")
  },
  ...
]

Time: ⏱️ 300-500ms
```

---

##### **BƯỚC 6: Kiểm tra Quyền xem từng Chunk (100-200ms)**

```
Backend:

For chunk in results:
  Check: Linh có quyền xem doc_handbook_001 không?
  
  Query:
  db.document_permissions.findOne({
    document_id: ObjectId("doc_handbook_001"),
    company_id: ObjectId("company_abc123"),
    $or: [
      {user_id: ObjectId("linh_user")},           # Cá nhân
      {department_id: ObjectId("dept_hr")},       # Phòng
      {role_id: ObjectId("role_member123")}       # Vai trò
    ],
    access_type: {$in: ["VIEW", "EDIT"]},
    is_deleted: False
  })
  └─ Index: document_id_1_company_id_1 ✅ (5ms)
  
  Result: {access_type: "VIEW"} ✅ HAS PERMISSION

✅ All chunks permitted

Time: ⏱️ 50-100ms
```

---

##### **BƯỚC 7: Chuẩn bị Context cho LLM (200-300ms)**

```
Backend:

Combine chunks + metadata:

CONTEXT = """
=== NGUỒN: Sổ tay nhân viên 2026 (Phòng HR) ===

[SUMMARY - CHAPTER 2]
Chương 2 - Nghỉ phép & Nghỉ lễ:
Công ty ABC Corp tuân thủ đầy đủ các quy định của pháp luật 
về nghỉ phép, nghỉ lễ, nghỉ thai sản cho nhân viên nữ...

[DETAIL - SECTION 2.1]
2.1 Nghỉ thai sản:
Phụ nữ công nhân viên có quyền nghỉ 4 tháng (kể từ ngày sinh con):
- 2 tháng trước dự kiến ngày sinh
- 2 tháng sau sinh

[DETAIL - SECTION 2.2]
2.2 Quy trình:
1. Thông báo cho phòng HR trước 1 tháng dự kiến ngày sinh
2. Nộp hóa đơn khám thai từ bệnh viện
3. Điền form xin nghỉ thai sản
4. Trưởng phòng ký phê duyệt
5. Gửi lên HR cuối cùng

[DETAIL - SECTION 2.3]
2.3 Lương trong kỳ nghỉ thai sản:
- 60% lương cơ bản được thanh toán hàng tháng
- Bảo hiểm BHXH, BHYT, BHTN vẫn duy trì
- Thưởng hiệu suất tạm dừng

[DETAIL - SECTION 2.4]
2.4 Sau khi hết kỳ nghỉ:
- Trở lại công việc cũ hoặc tương đương
- Không bị giảm lương
- Quyền đi làm bán thời gian trong 3 tháng đầu (nếu muốn)
"""

Token count: ~450 tokens
Time: ⏱️ 200-300ms
```

---

##### **BƯỚC 8: Gửi tới LLM tạo Câu trả lời (1-2 giây)**

```
Backend:

OpenAI API:
POST /chat/completions

{
  "model": "gpt-4-turbo",
  "messages": [
    {
      "role": "system",
      "content": """Bạn là trợ lý HR thông minh của ABC Corp.
                    Trả lời câu hỏi của nhân viên dựa CHÍNH XÁC 
                    trên tài liệu được cung cấp.
                    
                    LUẬT VÀNG:
                    1. Nếu không tìm thấy thông tin → Nói rõ "Tôi không tìm thấy"
                    2. Luôn trích dẫn nguồn (Section + Page)
                    3. Trả lời bằng Tiếng Việt, thân thiện, chuyên nghiệp
                    4. Nếu cần, đề xuất liên hệ HR để làm rõ"""
    },
    {
      "role": "user",
      "content": """Chị em vừa biết đang mang thai. 
                    Chị em muốn hỏi chính sách nghỉ thai sản 
                    của công ty là gì? 
                    Thời gian nghỉ được bao lâu? 
                    Cách làm thủ tục thế nào?
                    
                    [CONTEXT]
                    ${CONTEXT_ABOVE}"""
    }
  ],
  "temperature": 0.3,  # Thấp = Accurate, không hallucination
  "max_tokens": 600
}

LLM Processing:
  1. Parse context
  2. Identify key information about maternity leave
  3. Generate response
  4. Review for accuracy & citations

Response:
{
  "choices": [
    {
      "message": {
        "content": """Chúc mừng tin vui! 🎉

Dưới đây là thông tin chính sách nghỉ thai sản tại ABC Corp:

**1. Thời gian nghỉ phép:**
- Tổng cộng: **4 tháng** (theo Sổ tay nhân viên 2026, Mục 2.1)
  - 2 tháng trước dự kiến ngày sinh
  - 2 tháng sau sinh

**2. Quy trình làm thủ tục (Mục 2.2):**
Bạn cần thực hiện các bước sau:
1. Thông báo cho phòng HR **trước 1 tháng** dự kiến ngày sinh
2. Nộp hóa đơn khám thai từ bệnh viện để xác nhận
3. Điền form xin nghỉ thai sản
4. Trưởng phòng ký phê duyệt
5. Gửi lên phòng HR để hoàn tất

**3. Lương & Bảo hiểm (Mục 2.3):**
- Lương: **60% lương cơ bản** được thanh toán hàng tháng
- Bảo hiểm: BHXH, BHYT, BHTN vẫn duy trì bình thường
- Thưởng hiệu suất: Tạm dừng trong kỳ nghỉ

**4. Sau khi hết kỳ nghỉ (Mục 2.4):**
- Quay lại công việc cũ hoặc tương đương
- Không bị giảm lương
- Có thể làm bán thời gian trong 3 tháng đầu (nếu muốn)

**Hãy liên hệ phòng HR** (ngoc@abc-corp.com) để thực hiện thủ tục.
Đội HR sẽ hỗ trợ bạn từng bước!

📞 Điện thoại HR: ext. 1234
📧 Email: ngoc@abc-corp.com"""
      }
    }
  ],
  "usage": {
    "prompt_tokens": 520,
    "completion_tokens": 340,
    "total_tokens": 860
  }
}

Time: ⏱️ 1500-2000ms
```

---

##### **BƯỚC 9: Trích xuất Citations & Lưu Message (200-300ms)**

```
Backend:

Step 1: Parse response để tìm citations
  Citations identified:
  ✅ "Sổ tay nhân viên 2026, Mục 2.1"
  ✅ "Mục 2.2"
  ✅ "Mục 2.3"
  ✅ "Mục 2.4"
  
  Matching chunks:
  - chunk_detail_002_1 (2.1)
  - chunk_detail_002_2 (2.2)
  - chunk_detail_002_3 (2.3)
  - chunk_detail_002_4 (2.4)

Step 2: Tạo conversation (nếu chưa có)
  db.conversations.insertOne({
    "_id": ObjectId("conv_linh_001"),
    "company_id": ObjectId("company_abc123"),
    "user_id": ObjectId("linh_user"),
    "dept_id": ObjectId("dept_hr"),
    "title": "Chính sách nghỉ thai sản",
    "message_count": 0,
    "created_at": ISODate("2026-03-07T14:00:00Z"),
    "updated_at": ISODate("2026-03-07T14:00:00Z"),
    "is_deleted": False
  })

Step 3: Lưu user's message
  db.messages.insertOne({
    "_id": ObjectId("msg_linh_001"),
    "conversation_id": ObjectId("conv_linh_001"),
    "company_id": ObjectId("company_abc123"),
    "user_id": ObjectId("linh_user"),
    "role": "user",
    "content": "Chính sách nghỉ thai sản...?",
    "created_at": ISODate("2026-03-07T14:00:30Z"),
    "is_deleted": False
  })
  └─ Index: conversation_id_1 ✅ (5ms)

Step 4: Lưu AI response
  db.messages.insertOne({
    "_id": ObjectId("msg_ai_001"),
    "conversation_id": ObjectId("conv_linh_001"),
    "company_id": ObjectId("company_abc123"),
    "user_id": null,  # AI assistant
    "role": "assistant",
    "content": "Chúc mừng tin vui! 🎉\n\nDưới đây là thông...",
    "citations": [
      ObjectId("chunk_detail_002_1"),
      ObjectId("chunk_detail_002_2"),
      ObjectId("chunk_detail_002_3"),
      ObjectId("chunk_detail_002_4")
    ],
    "model": "gpt-4-turbo",
    "tokens_used": 860,
    "created_at": ISODate("2026-03-07T14:00:34Z"),
    "is_deleted": False
  })
  └─ Index: conversation_id_1 ✅ (5ms)

Step 5: Cập nhật conversation
  db.conversations.updateOne(
    {_id: ObjectId("conv_linh_001")},
    {
      $set: {updated_at: ISODate("2026-03-07T14:00:34Z")},
      $inc: {message_count: 2}
    }
  )

Step 6: Lưu audit log
  db.audit_logs.insertOne({
    "_id": ObjectId(),
    "company_id": ObjectId("company_abc123"),
    "user_id": ObjectId("linh_user"),
    "action": "CHAT_QUERY",
    "details": {
      "query_topic": "Maternity leave policy",
      "response_length": 340,
      "chunks_used": 4,
      "citations": ["section 2.1", "section 2.2", "section 2.3", "section 2.4"]
    },
    "timestamp": ISODate("2026-03-07T14:00:34Z"),
    "is_deleted": False
  })
  └─ Index: company_id_1_action_1_timestamp_-1 ✅ (8ms)

Time: ⏱️ 200-300ms
```

---

##### **BƯỚC 10: Trả về Response cho Frontend (50-100ms)**

```
API Response:
{
  "success": true,
  "data": {
    "message_id": ObjectId("msg_ai_001"),
    "response": "Chúc mừng tin vui! 🎉\n\nDưới đây...",
    "citations": [
      {
        "chunk_id": ObjectId("chunk_detail_002_1"),
        "section": "2.1 Nghỉ thai sản",
        "page_range": "33-35",
        "preview": "Phụ nữ công nhân viên có quyền nghỉ 4 tháng...",
        "document": "Sổ tay nhân viên 2026"
      },
      {
        "chunk_id": ObjectId("chunk_detail_002_2"),
        "section": "2.2 Quy trình",
        "page_range": "35-37",
        "preview": "1. Thông báo cho phòng HR trước 1 tháng...",
        "document": "Sổ tay nhân viên 2026"
      },
      ...
    ],
    "sources": [
      {
        "doc_id": ObjectId("doc_handbook_001"),
        "name": "Sổ tay nhân viên 2026",
        "upload_date": "2026-03-07",
        "relevance": 0.96
      }
    ]
  },
  "time_ms": 5500
}
```

---

##### **BƯỚC 11: Hiển thị trên Frontend**

```
┌─────────────────────────────────────────────────────┐
│ 💬 CHAT - HỎI ĐÁP TRI THỨC                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│ USER (Linh) - 14:00:30                             │
│ ┌───────────────────────────────────────────────┐ │
│ │ Chị em vừa biết đang mang thai.             │ │
│ │ Chị em muốn hỏi chính sách nghỉ thai sản    │ │
│ │ của công ty là gì?...                        │ │
│ └───────────────────────────────────────────────┘ │
│                                                     │
│ ASSISTANT (AI) - 14:00:34 ✅ 4 giây               │
│ ┌───────────────────────────────────────────────┐ │
│ │ Chúc mừng tin vui! 🎉                        │ │
│ │                                               │ │
│ │ 1. Thời gian nghỉ phép:                      │ │
│ │ - Tổng cộng: **4 tháng**                     │ │
│ │   - 2 tháng trước sinh                       │ │
│ │   - 2 tháng sau sinh                         │ │
│ │                                               │ │
│ │ 2. Quy trình làm thủ tục:                    │ │
│ │ 1. Thông báo HR trước 1 tháng                │ │
│ │ 2. Nộp hóa đơn khám thai                     │ │
│ │ 3. Điền form xin nghỉ                        │ │
│ │ 4. Trưởng phòng ký phê duyệt                 │ │
│ │ 5. HR xác nhận                               │ │
│ │                                               │ │
│ │ 3. Lương & Bảo hiểm:                         │ │
│ │ - Lương: 60% lương cơ bản                    │ │
│ │ - Bảo hiểm: Duy trì bình thường             │ │
│ │ - Thưởng: Tạm dừng                          │ │
│ │                                               │ │
│ │ 4. Sau khi hết kỳ nghỉ:                      │ │
│ │ - Quay lại công việc cũ                      │ │
│ │ - Không giảm lương                           │ │
│ │ - Có thể làm bán thời gian 3 tháng          │ │
│ │                                               │ │
│ │ Liên hệ HR: ngoc@abc-corp.com                │ │
│ └───────────────────────────────────────────────┘ │
│                                                     │
│ 📚 NGUỒN THAM KHẢO:                               │
│ ✅ Sổ tay nhân viên 2026 (Chương 2, Trang 33-45)  │
│    - Mục 2.1: Nghỉ thai sản                       │
│    - Mục 2.2: Quy trình                           │
│    - Mục 2.3: Lương & Bảo hiểm                    │
│    - Mục 2.4: Sau kỳ nghỉ                         │
│                                                     │
│ 🔗 [Xem tài liệu gốc] [Tải PDF] [Chia sẻ]        │
│                                                     │
│ ┌───────────────────────────────────────────────┐ │
│ │ Linh: "Cảm ơn! Em có câu hỏi thêm..."         │ │
│ │       [SEND] 🎤                               │ │
│ └───────────────────────────────────────────────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

##### **⏱️ TÓNG HỢP THỜI GIAN END-TO-END:**

| Bước | Thời gian | Accumulative |
|------|----------|------------|
| 1. Frontend input | 0.1s | 0.1s |
| 2. Auth + Permission | 0.2s | 0.3s |
| 3. Query embedding | 1.8s | 2.1s |
| 4. ChromaDB search | 0.2s | 2.3s |
| 5. Fetch chunks | 0.4s | 2.7s |
| 6. Permission check | 0.1s | 2.8s |
| 7. Context prep | 0.3s | 3.1s |
| 8. LLM response | 1.8s | 4.9s |
| 9. Save data | 0.3s | 5.2s |
| 10. Return API | 0.1s | 5.3s |
| 11. Display | 0.2s | 5.5s |
| **TOTAL** | | **~5.5 giây** |

**Kết luận:** Nhân viên Linh nhận được câu trả lời chi tiết, chính xác, có trích dẫn nguồn trong vòng **dưới 6 giây** từ khi gõ query!

---

---

## 4. THIẾT KẾ CƠ SỞ DỮ LIỆU (17 BẢNG)

| Nhóm | Các bảng (Collections) | Chức năng |
| :--- | :--- | :--- |
| **IAM** | `companies`, `departments`, `users`, `roles`, `permissions`, `user_roles`, `role_permissions` | Quản lý định danh, phân quyền động và đa thuê bao. |
| **Knowledge** | `folders`, `documents`, `document_chunks`, `document_permissions`, `tags` | Quản lý cây thư mục và cấu trúc tri thức phân tầng (Summary-Detail). |
| **AI Ops** | `conversations`, `messages`, `ai_feedback` | Lưu vết hội thoại, nguồn trích dẫn và thu thập phản hồi người dùng. |
| **Audit/Jobs**| `audit_logs`, `processing_jobs` | Nhật ký bảo mật và giám sát tiến độ xử lý file nặng. |

---

## 5. CÔNG NGHỆ VÀ CHIẾN LƯỢC MICROSERVICES

- **FastAPI**: Backend hiệu năng cao, xử lý bất đồng bộ.
- **MongoDB Atlas**: Lưu trữ metadata và cấu trúc phân tầng linh hoạt.
- **ChromaDB**: Lưu trữ vector để tìm kiếm ngữ nghĩa nhanh chóng.
- **JWT**: Xác thực không trạng thái (Stateless), an toàn tuyệt đối.
- **Chia Service (Logic)**:
    - **IAM Service**: Quản lý "Ai là ai".
    - **Ingestion Service**: Quản lý "Dữ liệu là gì".
    - **Search Service**: Quản lý "Tìm ở đâu".
    - **Chat Service**: Quản lý "Trả lời thế nào".

---

## 6. LỘ TRÌNH THỰC HIỆN (ROADMAP)

1. **Giai đoạn 1**: Xây dựng nền tảng Bảo mật & Phân quyền (IAM/RBAC).
2. **Giai đoạn 2**: Phát triển "Nhà máy" xử lý tài liệu (OCR & Chunking).
3. **Giai đoạn 3**: Tích hợp AI (LLM) và thuật toán tìm kiếm phân tầng.
4. **Giai đoạn 4**: Hoàn thiện giao diện và hệ thống giám sát.

---

## 7. ĐIỂM NHẤN CÔNG NGHỆ THUYẾT PHỤC (TECHNICAL HIGHLIGHTS)

Để một đồ án tốt nghiệp về RAG được đánh giá cao, hệ thống không chỉ dừng lại ở hiệu ứng "wow" khi chat, mà phải giải quyết được các bài toán "vùng xám" của AI:

### 7.1. Hybrid Search (Tìm kiếm lai)
Hệ thống không chỉ dùng Vector Search (tìm theo ý nghĩa) mà kết hợp với **Keyword Search (BM25)**. Điều này đảm bảo khi người dùng tìm chính xác một mã sản phẩm, một thuật ngữ chuyên môn hoặc tên riêng, AI vẫn truy xuất được chính xác 100%, thay vì chỉ tìm các nội dung "gần giống".

### 7.2. Xử lý OCR và Dữ liệu thô (Advanced Ingestion)
Đồ án tập trung vào việc xử lý các file PDF "khó": 
- PDF dạng ảnh quét (Scan).
- PDF có bảng biểu phức tạp (Tables).
- PDF có sơ đồ.
Hệ thống sử dụng các thư viện chuyên sâu để chuyển đổi bảng biểu thành Markdown/JSON trước khi đưa vào AI, giúp AI "đọc" được bảng số liệu một cách chính xác.

### 7.3. Cơ chế Prompt Engineering & Reranking
Sau khi tìm được các đoạn văn bản liên quan, chúng tôi sử dụng thêm một lớp **Reranker** (ví dụ: Cohere hoặc BGE-Reranker) để chọn ra 3-5 đoạn thực sự liên quan nhất trong số 100 đoạn tìm được. Điều này giúp giảm nhiễu thông tin đầu vào cho LLM.

---

## 8. CÁC KỊCH BẢN SỬ DỤNG THỰC TẾ TRONG DOANH NGHIỆP

Để giáo viên thấy được tính thực tiễn, hệ thống sẽ demo qua 3 kịch bản điển hình:

1.  **Bộ phận Nhân sự (HR)**: Nhân viên hỏi về "Quy định làm thêm giờ ngày lễ". AI tìm trong sổ tay nhân viên, trích dẫn đúng trang và công thức tính lương.
2.  **Bộ phận Kỹ thuật/Sản xuất**: Kỹ sư hiện trường hỏi về "Cách xử lý lỗi E04 trên máy CNC". AI truy xuất từ sách hướng dẫn kỹ thuật dày 500 trang và đưa ra các bước hướng dẫn xử lý ngay tại chỗ.
3.  **Bộ phận Pháp chế/Tuân thủ**: Kiểm tra sự phù hợp của một hợp đồng mới so với các quy định pháp luật đã lưu trong kho tri thức của công ty.

---

## 9. HỆ THỐNG ĐO LƯỜNG VÀ ĐÁNH GIÁ (EVALUATION FRAMEWORK)

Đây là phần quan trọng nhất để thuyết phục giáo viên về tính khoa học của đồ án. Chúng tôi sử dụng bộ chỉ số **RAGAS** để đánh giá:
-   **Faithfulness (Tính trung thực)**: Câu trả lời có thực sự trích dẫn đúng từ tài liệu không? (Chống ảo giác).
-   **Answer Relevance (Tính liên quan)**: Câu trả lời có đúng trọng tâm câu hỏi không?
-   **Context Precision (Độ chính xác ngữ cảnh)**: Các đoạn văn bản tìm được có thực sự chứa câu trả lời không?

---

## 10. PHÂN TÍCH TỔNG QUAN CHI TIẾT (BỔ SUNG)

### 10.1. Bối cảnh và Thách thức cốt lõi
Trong kỷ nguyên số, việc khai thác tri thức từ hàng ngàn tài liệu nội bộ (PDF, Word, Wiki) là một thách thức lớn. Các hệ thống RAG thông thường băm nhỏ tài liệu một cách mù quáng (naive chunking) dẫn đến mất ngữ cảnh. Hệ thống này giải quyết điều đó bằng kiến trúc **Enterprise Hierarchical RAG**.

### 10.2. Mục tiêu hệ thống
- **Độ chính xác (Accuracy)**: Giảm thiểu 99% lỗi "nói xạo" của AI bằng cách sử dụng kiến trúc Summary-Detail.
- **Tính bảo mật (Security)**: Cách ly dữ liệu ở mức vật lý (Collection riêng) và logic (Middleware kiểm tra quyền).
- **Khả năng mở rộng (Scalability)**: Kiến trúc Microservices cho phép xử lý hàng triệu tài liệu cùng lúc.

### 10.3. Quy trình Ingestion Phân tầng (Knowledge Pipeline)
1. **Phân tích cấu trúc**: Nhận diện tiêu đề, chương, mục của tài liệu.
2. **Summary Nodes**: Tạo ra các đoạn tóm tắt cho từng chương/mục lớn.
3. **Detail Nodes**: Giữ lại nội dung chi tiết, được liên kết với Summary Node cha.
4. **Truy vấn Recursive**: Tìm trong Summary trước để xác định vùng kiến thức, sau đó mới đi sâu vào Detail.

### 10.4. Chiến lược bảo mật đa thuê bao
- **Cách ly ở tầng Vector**: Mỗi Công ty có một `collection_name` riêng trong ChromaDB.
- **Middleware RBAC**: Mọi yêu cầu truy xuất đều đi qua bước kiểm tra: `user -> roles -> permissions -> folder access`.

---

## 11. KẾT LUẬN

Bản đặc tả này đại diện cho sự kết hợp giữa **Kỹ thuật phần mềm hiện đại** và **Trí tuệ nhân tạo**, đảm bảo tính khả thi và điểm số xuất sắc cho đồ án tốt nghiệp. Hệ thống không chỉ giải quyết bài toán trả lời câu hỏi, mà còn là một công cụ quản trị tri thức tối ưu cho doanh nghiệp.
