# 🗺️ API DEVELOPMENT ROADMAP — BẢN ĐẦY ĐỦ NHẤT (MASTER REFERENCE)

> **Mục đích:** Tài liệu này là "bản đồ chiến tranh" trước khi viết code backend. Mỗi API đều có đầy đủ: Endpoint, Method, Bảng DB liên quan, Logic xử lý, Lưu ý khi code và các Tình huống đặc biệt cần xử lý.

---

## 📐 SƠ ĐỒ LIÊN KẾT BẢNG (DB RELATIONSHIP MAP)

```
Account (AbstractUser)
  ├── AccountRole (M2M) ────────────── Role
  │                                      └── RolePermission (M2M) ─── Permission
  └── UserProfile (1:1)
        └── Department (N:1)               Department (Tree - tự tham chiếu)
              └── Folder (N:1)               Folder (Tree - tự tham chiếu)
                    ├── FolderPermission (1:N)  [subject: role | account]
                    └── Document (N:1)
                          ├── DocumentPermission (1:N) [subject: role | account]
                          ├── DocumentChunk (1:N) ──── [vector_id -> Qdrant]
                          └── UserDocumentCache (1:N)

Conversation (N:1 Account)
  ├── Message (1:N)
  │     └── HumanFeedback (1:N)
  ├── ConversationAttachedDocument (M2M) ─── Document
  └── ConversationAttachedFolder (M2M) ────── Folder

AuditLog (N:1 Account)
AsyncTask (N:1 Document, N:1 DocumentChunk)
```

---

## 📜 QUY TẮC PHÂN QUYỀN (GOLDEN RULES - ĐỌC TRƯỚC KHI CODE)

### Quy tắc 1: Thứ tự ưu tiên phân quyền cho Document
Khi kiểm tra quyền của User X trên Document D:

```
Bước 1: Tra bảng DocumentPermission WHERE document_id=D AND subject_id=X AND subject_type='account'
  → Nếu tìm thấy với precedence='deny'   → TỪ CHỐI (kết thúc)
  → Nếu tìm thấy với precedence='override' → CHẤP NHẬN (kết thúc)

Bước 2: Tra bảng DocumentPermission WHERE document_id=D AND subject_id IN (roles của X) AND subject_type='role'
  → Nếu tìm thấy deny cho bất kỳ role nào → TỪ CHỐI (kết thúc)
  → Nếu tìm thấy override cho bất kỳ role → CHẤP NHẬN (kết thúc)

Bước 3: Document.access_scope == 'inherit' → Kiểm tra FolderPermission của Folder cha
  3a. FolderPermission WHERE folder_id=Folder AND subject_id=X AND subject_type='account'
  3b. FolderPermission WHERE folder_id=Folder AND subject_id IN (roles của X) AND subject_type='role'

Bước 4: Tra bảng UserDocumentCache (nếu cache chưa hết hạn) → Lấy max_permission

Bước 5: Tra bảng RolePermission (Role-based Feature Permission) - ví dụ: DOCUMENT_DELETE
  → Nếu user có permission code 'DOCUMENT_DELETE' → CHẤP NHẬN

Mặc định (không có gì khớp): TỪ CHỐI
```

### Quy tắc 2: Các bảng phải có `is_deleted=False` trong ALL Queryset mặc định
Trong `BaseRepository`:
```python
def get_queryset(self):
    return super().get_queryset().filter(is_deleted=False)
```

### Quy tắc 3: Mọi thao tác DELETE phải là Soft Delete
```python
obj.is_deleted = True
obj.deleted_at = timezone.now()
obj.save()
```

### Quy tắc 4: Mọi thao tác cần ghi AuditLog
Các action phải log: `LOGIN, LOGOUT, UPLOAD, DELETE, DOWNLOAD, SHARE, CHANGE_ROLE, GRANT_ACL, REVOKE_ACL`

---

## 🚀 CHI TIẾT TỪNG API THEO PHASE

---

## PHASE 0: AUTHENTICATION (Day 1–2)

> **Viết trước tiên vì:** Tất cả API khác đều cần `request.user` đã xác thực.

---

### API-01: `POST /api/v1/auth/login`
**Chức năng:** Đăng nhập hệ thống.

**Bảng DB liên quan:**
- `accounts` (Account model – read)
- `account_roles` (AccountRole – read)
- `role_permissions` (RolePermission – read)
- `permissions` (Permission – read)

**Luồng xử lý:**
1. Nhận `username` + `password` từ request body.
2. Xác thực với `Account.objects.get(username=...)`.
3. Check `account.status == 'active'` và `account.is_deleted == False`.
4. Dùng `authenticate()` của Django để check password.
5. Tạo JWT `access_token` (15 phút) + `refresh_token` (7 ngày).
6. Query tổng hợp **tất cả permission_codes** của user: `Account → AccountRole → Role → RolePermission → Permission.code`.
7. Lấy `department_id` từ `UserProfile.department_id`.
8. Trả về response.

**Lưu ý khi code:**
- ⚠️ Phải kiểm tra `account.status != 'blocked'` trước khi trả token.
- ⚠️ Phải ghi `AuditLog(action='LOGIN', account=account, ip_address=...)`.
- ⚠️ Phải trả về `permission_codes: []` để Frontend ẩn/hiển thị menu mà không cần gọi thêm API.
- ⚠️ Không trả về `password` hash trong response.

**Response mẫu:**
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "user": {
    "id": 1, "username": "admin",
    "full_name": "Nguyen Van A",
    "department_id": "uuid-...",
    "roles": ["Manager", "Staff"],
    "permission_codes": ["DOCUMENT_READ", "DOCUMENT_UPLOAD", "USER_VIEW"]
  }
}
```

---

### API-02: `POST /api/v1/auth/refresh`
**Chức năng:** Làm mới access token.

**Bảng DB liên quan:**
- `accounts` (check is_deleted, status)

**Lưu ý khi code:**
- ⚠️ Khi refresh, phải kiểm tra lại `account.is_deleted` và `account.status`. Nếu User bị block sau khi login thì không cấp token mới.
- ⚠️ Cân nhắc dùng **Token Rotation** (mỗi lần refresh thì invalidate refresh token cũ, cấp cái mới) để tránh chiếm đoạt token.

---

### API-03: `POST /api/v1/auth/logout`
**Chức năng:** Đăng xuất.

**Lưu ý khi code:**
- ⚠️ Ghi `AuditLog(action='LOGOUT')`.
- ⚠️ Nếu dùng stateless JWT thuần: cần có cơ chế blacklist token (lưu jti vào Redis với TTL bằng thời gian expire còn lại của token).

---

### API-04: `GET /api/v1/auth/me`
**Chức năng:** Lấy thông tin đầy đủ của User đang đăng nhập.

**Bảng DB liên quan:**
- `accounts`, `users` (UserProfile), `departments`, `account_roles`, `roles`, `role_permissions`, `permissions`

**Lưu ý khi code:**
- Trả về đầy đủ `roles`, `permission_codes`, thông tin profile.
- Dùng `select_related` để tối ưu query, tránh N+1 problem.

---

## PHASE 1: IAM — ROLE & PERMISSION (Day 3–4)

> **Viết thứ hai vì:** Cần có Role/Permission để viết middleware phân quyền cho toàn bộ API còn lại.

---

### API-05: `GET /api/v1/iam/permissions`
**Chức năng:** Liệt kê toàn bộ permission codes trong hệ thống.

**Bảng DB liên quan:**
- `permissions`

**Lưu ý khi code:**
- ⚠️ Chỉ Admin (người có quyền `IAM_VIEW`) mới được gọi API này.
- Đây thường là dữ liệu **seed cứng** (được ghi vào DB lúc khởi tạo), không thay đổi thường xuyên.
- Trả về groupped by `module` (documents, users, iam, operations) để FE hiển thị checkbox phân nhóm.

---

### API-06: `GET /api/v1/iam/roles`
**Chức năng:** Liệt kê tất cả Roles.

**Bảng DB liên quan:**
- `roles`, `role_permissions`, `permissions` (JOIN để đếm số quyền)

**Lưu ý khi code:**
- Trả về kèm `permission_count` và danh sách `permission_codes` cho mỗi Role.
- ⚠️ Yêu cầu quyền `IAM_VIEW`.

---

### API-07: `POST /api/v1/iam/roles`
**Chức năng:** Tạo Role mới.

**Bảng DB liên quan:**
- `roles` (insert)

**Lưu ý khi code:**
- ⚠️ Yêu cầu quyền `IAM_MANAGE`.
- `is_custom=True` khi tạo từ API (phân biệt với System Roles).
- Validate: `role_name` không được trùng.
- Ghi `AuditLog(action='CREATE_ROLE')`.

---

### API-08: `PUT /api/v1/iam/roles/{role_id}`
**Chức năng:** Cập nhật thông tin Role.

**Lưu ý khi code:**
- ⚠️ KHÔNG được sửa/xóa các Role hệ thống (ví dụ Role có `is_custom=False`).
- Validate: `role_name` unique (bỏ qua chính nó).

---

### API-09: `DELETE /api/v1/iam/roles/{role_id}`
**Chức năng:** Xóa Role.

**Bảng DB liên quan (IMPACT):**
- `roles` → `account_roles` → `folder_permissions` → `document_permissions`

**Lưu ý khi code (PHỨC TẠP):**
- ⚠️ Tuyệt đối KHÔNG xóa Role `Admin`.
- ⚠️ Trước khi xóa, kiểm tra xem Role này có đang được gán cho User nào không (`AccountRole.objects.filter(role_id=...).exists()`). Nếu có → Trả lỗi 409 kèm danh sách User, yêu cầu Admin gán lại Role cho những User đó trước.
- ⚠️ Sau khi đảm bảo không còn User dùng Role này: Xóa các bản ghi `FolderPermission` và `DocumentPermission` đang dùng `subject_type='role'` và `subject_id=role_id` này để tránh dữ liệu mồ côi.
- Dùng **transaction** để đảm bảo thao tác là atomic (tất cả thành công hoặc rollback hết).

---

### API-10: `POST /api/v1/iam/roles/{role_id}/permissions`
**Chức năng:** Gán danh sách Permission cho Role (bulk update).

**Bảng DB liên quan:**
- `role_permissions` (delete old + insert new)

**Lưu ý khi code:**
- ⚠️ Dùng cơ chế "Replace All": Nhận vào một danh sách `permission_ids[]` mới → Xóa tất cả  `RolePermission` cũ của Role → Insert lại mới. Tránh insert từng cái một (tốn query).
- ⚠️ Sau khi cập nhật xong, phải **invalide cache** của tất cả User đang thuộc Role này (xóa toàn bộ bản ghi `UserDocumentCache` của những User đó).
- Ghi `AuditLog(action='CHANGE_ROLE')`.

---

## PHASE 2: USERS & DEPARTMENTS (Day 5–7)

---

### API-11: `GET /api/v1/users`
**Chức năng:** Danh sách toàn bộ User (có phân trang, tìm kiếm, lọc).

**Bảng DB liên quan:**
- `accounts` JOIN `users` (UserProfile) JOIN `departments` JOIN `account_roles` JOIN `roles`

**Lưu ý khi code:**
- ⚠️ Yêu cầu quyền `USER_VIEW`.
- Filter theo: `department_id`, `role_id`, `status`, `search` (full_name, email, username).
- Dùng `select_related('user_profile__department')` và `prefetch_related('account_roles__role')` để tránh N+1.
- Phân trang bắt buộc (không trả all, có thể có vạn User).

---

### API-12: `POST /api/v1/users`
**Chức năng:** Tạo User mới (Admin tạo, không phải tự đăng ký).

**Bảng DB liên quan (WRITE):**
- `accounts` (insert)
- `users` (UserProfile - insert)
- `account_roles` (insert ít nhất 1 Role)

**Lưu ý khi code:**
- ⚠️ Yêu cầu quyền `USER_CREATE`.
- Phải tạo cả `Account` và `UserProfile` trong **cùng 1 database transaction** (`atomic()`).
- Validate: `username`, `email` unique.
- Bắt buộc gán ít nhất 1 `Role` và 1 `Department` cho User mới.
- Ghi `AuditLog(action='CREATE_USER')`.

---

### API-13: `GET /api/v1/users/{user_id}`
**Chức năng:** Chi tiết một User.

**Bảng DB liên quan:**
- `accounts`, `users`, `departments`, `account_roles` → `roles` → `role_permissions` → `permissions`

**Lưu ý khi code:**
- ⚠️ User có thể xem profile của **chính mình**. Admin mới xem được người khác.
- Trả về đầy đủ danh sách Roles và danh sách Permission Codes tổng hợp.

---

### API-14: `PUT /api/v1/users/{user_id}`
**Chức năng:** Cập nhật thông tin User.

**Bảng DB liên quan (WRITE):**
- `users` (UserProfile - update)
- `accounts` (update status nếu cần)

**Lưu ý khi code:**
- ⚠️ Chỉ Admin hoặc chính User đó mới được sửa.
- Admin mới được sửa `status` (active/blocked/inactive).
- Nếu cập nhật `department_id`, phải cân nhắc có ảnh hưởng tới việc truy cập Folder của User đó không.

---

### API-15: `DELETE /api/v1/users/{user_id}`
**Chức năng:** Vô hiệu hóa User (Soft Delete).

**Bảng DB liên quan (IMPACT):**
- `accounts` – set `is_deleted=True`, `status='inactive'`
- `account_roles` – set `is_active=False` cho tất cả AccountRole của User
- `conversations` – KHÔNG xóa, giữ nguyên lịch sử

**Lưu ý khi code:**
- ⚠️ KHÔNG bao giờ hard delete User. Set `is_deleted=True`.
- ⚠️ Nếu User là Manager của một Department, phải xử lý (xóa manager hoặc gán người khác).
- ⚠️ Vô hiệu hóa tất cả `AccountRole` nhưng KHÔNG xóa để còn lịch sử audit.
- Ghi `AuditLog(action='DELETE_USER')`.

---

### API-16 & 17: `POST/DELETE /api/v1/users/{user_id}/roles`
**Chức năng:** Gán thêm hoặc xóa Role của User.

**Bảng DB liên quan:**
- `account_roles`

**Lưu ý khi code:**
- ⚠️ Khi gán Role mới: insert vào `AccountRole`. Kiểm tra unique constraint `(account, role)`.
- ⚠️ Khi xóa Role: Set `is_active=False` hoặc xóa hard (tùy thiết kế).
- ⚠️ **QUAN TRỌNG:** Sau khi thay đổi Role, phải xóa toàn bộ bản ghi `UserDocumentCache` của User này để hệ thống tính lại quyền.
- Ghi `AuditLog(action='CHANGE_ROLE')`.

---

### API-18: `GET /api/v1/departments`
**Chức năng:** Lấy cây thư mục phòng ban (Tree structure).

**Bảng DB liên quan:**
- `departments` (self-join, hierarchical)

**Lưu ý khi code:**
- ⚠️ Phải xử lý cấu trúc cây đệ quy (`parent` → `sub_departments`). Dùng thuật toán DFS hoặc Library `django-treebeard` / `django-mptt`.
- Trả về dạng Nested JSON (cây lồng nhau) để FE hiển thị Sidebar tree.
- Filter `is_deleted=False` trong toàn bộ câu query.

---

### API-19: `POST /api/v1/departments`
**Chức năng:** Tạo phòng ban mới.

**Lưu ý khi code:**
- Nếu `parent_id` được cung cấp, phải validate `parent` tồn tại và không phải là chính phòng ban này (circular reference).
- Gán `manager` nếu cần (phải là Account đang active).

---

### API-20: `DELETE /api/v1/departments/{dept_id}`
**Chức năng:** Xóa phòng ban.

**Bảng DB liên quan (IMPACT CỰC MẠNH):**
- `users` (UserProfile) – `department_id` sẽ bị ảnh hưởng
- `folders` – `department_id` sẽ bị ảnh hưởng
- `departments` con (sub-departments)

**Lưu ý khi code (NGUY HIỂM NHẤT TRONG PHASE NÀY):**
- ⚠️ **Bước 1:** Kiểm tra có `UserProfile` nào đang thuộc phòng ban này không. Nếu có → Trả lỗi 409, yêu cầu di chuyển User trước.
- ⚠️ **Bước 2:** Kiểm tra có `Department` con nào không. Nếu có → Hỏi user: "Xóa luôn phòng ban con?" hoặc "Di chuyển phòng ban con lên cha trước?".
- ⚠️ **Bước 3:** Xử lý Folder: Set `department_id=NULL` hoặc xóa soft toàn bộ Folder thuộc phòng ban đó.
- Tất cả trong 1 `transaction`.

---

## PHASE 3: FOLDER & FOLDER PERMISSION (Day 8–10)

> **Đây là tầng quan trọng nhất của ACL. Viết cẩn thận nhất.**

---

### API-21: `GET /api/v1/folders`
**Chức năng:** Lấy cây thư mục mà User được phép xem.

**Bảng DB liên quan:**
- `folders`, `folder_permissions`, `account_roles`, `users` (UserProfile.department_id)

**Logic phức tạp:** Một User thấy Folder khi THỎA MÃN ít nhất 1 điều kiện:
1. `folder.department_id == user.department_id` (cùng phòng ban) VÀ `folder.access_scope == 'department'`
2. `folder.access_scope == 'company'` (toàn công ty)
3. Có bản ghi `FolderPermission(subject_type='account', subject_id=user_id)`
4. Có bản ghi `FolderPermission(subject_type='role', subject_id IN user_roles)`

**Lưu ý khi code:**
- ⚠️ KHÔNG bao giờ trả về tất cả Folder rồi filter ở tầng Python. Phải filter ngay trong SQL query.
- ⚠️ Dùng `UNION` hoặc `OR` trong Django ORM với `Q()` object.
- Trả về dạng cây (Tree) nested JSON.
- Kèm theo `user_permission` (read/write/delete) cho mỗi Folder để FE biết nên hiển thị nút gì.

**Query mẫu (tham khảo):**
```python
from django.db.models import Q
user_roles = [ar.role_id for ar in user.account_roles.filter(is_active=True)]

accessible_folders = Folder.objects.filter(
    is_deleted=False
).filter(
    Q(access_scope='company') |
    Q(access_scope='department', department_id=user.user_profile.department_id) |
    Q(permissions__subject_type='account', permissions__subject_id=str(user.id)) |
    Q(permissions__subject_type='role', permissions__subject_id__in=[str(r) for r in user_roles])
).distinct()
```

---

### API-22: `POST /api/v1/folders`
**Chức năng:** Tạo thư mục mới.

**Bảng DB liên quan:**
- `folders` (insert)
- `folder_permissions` (insert bản ghi mặc định cho owner)

**Lưu ý khi code:**
- ⚠️ Yêu cầu quyền `FOLDER_CREATE`.
- ⚠️ Nếu có `parent_id`: Check User có quyền `write` trên Folder cha không.
- ⚠️ Sau khi tạo, tự động tạo `FolderPermission` gán quyền `write/delete` cho User tạo.
- `department_id` nên lấy mặc định từ Department của User tạo (nếu không cung cấp).

---

### API-23: `PUT /api/v1/folders/{folder_id}`
**Chức năng:** Sửa thông tin Folder (tên, mô tả, scope).

**Lưu ý khi code:**
- ⚠️ Kiểm tra quyền `write` trên Folder này.
- ⚠️ Nếu thay đổi `access_scope` từ 'company' → 'department': Các User không thuộc Department đó sẽ mất quyền truy cập. Phải invalide `UserDocumentCache` của tất cả Document trong Folder này.

---

### API-24: `DELETE /api/v1/folders/{folder_id}`
**Chức năng:** Xóa thư mục (Recursive Soft Delete - Xóa đệ quy).

**Bảng DB liên quan (IMPACT TOÀN HỆ THỐNG):**
- `folders` – set is_deleted=True cho cả cây con
- `documents` – set is_deleted=True cho tất cả file bên trong
- `document_chunks` – ảnh hưởng gián tiếp (sẽ không được search vì document đã bị xóa)
- `user_document_cache` – phải xóa cache của tất cả User

**Lưu ý khi code:**
- ⚠️ Kiểm tra quyền `delete` trên Folder.
- ⚠️ Dùng hàm đệ quy hoặc `WITH RECURSIVE` SQL để lấy toàn bộ subfolder IDs.
- ⚠️ Lấy toàn bộ `document_ids` trong tất cả Folder vừa tìm được.
- ⚠️ Set `is_deleted=True` cho tất cả Folder con + Document con trong 1 **transaction**.
- ⚠️ Gọi service để xóa/vô hiệu hóa vector trong Qdrant cho tất cả Document bị ảnh hưởng (async task).
- ⚠️ Xóa `UserDocumentCache` của tất cả Document bị ảnh hưởng để hệ thống tính lại quyền.

---

### API-25: `PATCH /api/v1/folders/{folder_id}/move`
**Chức năng:** Di chuyển Folder sang Folder cha khác.

**Lưu ý khi code:**
- ⚠️ Kiểm tra quyền `write` ở cả Folder đang di chuyển VÀ Folder cha đích.
- ⚠️ Cập nhật `parent_id` của Folder.
- ⚠️ `department_id` có thể thay đổi theo Folder cha mới.
- ⚠️ Invalide cache `UserDocumentCache` của tất cả Document bên trong Folder này vì quyền thừa kế có thể đã thay đổi.

---

### API-26: `GET /api/v1/folders/{folder_id}/permissions`
**Chức năng:** Xem danh sách ACL của Folder.

**Bảng DB liên quan:**
- `folder_permissions` JOIN `roles`/`accounts`

**Lưu ý khi code:**
- ⚠️ Chỉ Admin hoặc người có quyền `write` trên Folder mới được xem.
- Trả về dạng hiển thị rõ ràng: `{ subject_type: 'role', subject_name: 'Manager', permission: 'read' }`.

---

### API-27: `POST /api/v1/folders/{folder_id}/permissions`
**Chức năng:** Gán quyền ACL cho Folder (cho User hoặc Role cụ thể).

**Bảng DB liên quan:**
- `folder_permissions` (insert hoặc update)

**Lưu ý khi code (QUAN TRỌNG):**
- ⚠️ Phân biệt `subject_type`: 'role' thì `subject_id` là UUID của Role, 'account' thì là ID số nguyên của Account.
- ⚠️ Dùng `update_or_create(folder=..., subject_type=..., subject_id=...)` để tránh duplicate.
- ⚠️ **Sau khi gán quyền**, phải invalide `UserDocumentCache` của tất cả Document trong Folder này. Vì lần sau khi User query, cache cũ có thể sai.
- ⚠️ Ghi `AuditLog(action='GRANT_ACL', resource_id=folder_id)`.

---

### API-28: `DELETE /api/v1/folders/{folder_id}/permissions/{perm_id}`
**Chức năng:** Thu hồi quyền ACL trên Folder.

**Lưu ý khi code:**
- ⚠️ Sau khi thu hồi quyền, invalide `UserDocumentCache`.
- ⚠️ Ghi `AuditLog(action='REVOKE_ACL')`.

---

## PHASE 4: DOCUMENT MANAGEMENT (Day 11–14)

---

### API-29: `GET /api/v1/documents`
**Chức năng:** Danh sách tài liệu mà User được phép xem.

**Bảng DB liên quan:**
- `documents`, `document_permissions`, `folder_permissions`, `account_roles`, `user_document_cache`

**Logic quyền truy cập (theo thứ tự này):**
1. Check `UserDocumentCache` – nếu cache còn hạn thì trả về ngay (nhanh nhất).
2. Nếu không có cache: Tính toán qua các bước:
   - Lấy tất cả `is_deleted=False` Documents.
   - Loại trừ những Document có `DocumentPermission(subject_id=user, precedence='deny')`.
   - Giữ lại Document có bất kỳ điều kiện nào sau đây đúng:
     - `DocumentPermission(subject_id=user|role, precedence='override')`.
     - `FolderPermission` của Folder cha cho phép user/role.
     - `Document.access_scope == 'company'`.
     - `Document.department_id == user.department_id` và `scope == 'department'`.

**Lưu ý khi code:**
- ⚠️ Đây là query phức tạp nhất. Phải test kỹ với nhiều case.
- ⚠️ Sau khi tính xong, lưu kết quả vào `UserDocumentCache` với `expires_at = now() + 10 phút`.
- Hỗ trợ filter: `folder_id`, `tag`, `status`, `file_type`, `search` (tên file).

---

### API-30: `POST /api/v1/documents/upload`
**Chức năng:** Tải lên tài liệu và kích hoạt pipeline xử lý AI.

**Bảng DB liên quan (WRITE):**
- `documents` (insert với `status='pending'`)
- `document_permissions` (insert quyền `write/delete` cho uploader)
- `async_tasks` (insert task `INDEX_DOCUMENT`)
- `audit_logs` (insert `UPLOAD`)

**Lưu ý khi code:**
- ⚠️ Yêu cầu quyền `DOCUMENT_UPLOAD`.
- ⚠️ Phải kiểm tra User có quyền `write` tại Folder đích không (nếu cung cấp `folder_id`).
- ⚠️ Validate file: loại file (pdf, docx, txt, md), kích thước tối đa (MAX_FILE_SIZE từ settings).
- ⚠️ Lưu file vật lý vào `uploads/` với tên được hash (tránh trùng).
- ⚠️ Tự động điền `department_id` từ `folder.department_id` (nếu không có Folder, lấy từ UserProfile).
- ⚠️ Tự động insert `DocumentPermission` cho uploader với `subject_type='account'`, `permission='write'`, `precedence='override'`.
- ⚠️ Insert `AsyncTask(task_type='INDEX_DOCUMENT', document=doc, priority='high')`.
- ⚠️ Ghi `AuditLog(action='UPLOAD', resource_id=doc.id)`.

---

### API-31: `GET /api/v1/documents/{doc_id}`
**Chức năng:** Lấy metadata chi tiết của tài liệu.

**Lưu ý khi code:**
- ⚠️ Kiểm tra User có quyền `read` trên Document này không (dùng hàm `check_document_permission`).
- Trả về kèm `processing_status` (pending/processing/completed/failed) và `has_chunks`.

---

### API-32: `PUT /api/v1/documents/{doc_id}`
**Chức năng:** Cập nhật metadata tài liệu (tên, tags, scope, folder).

**Bảng DB liên quan:**
- `documents` (update)
- `user_document_cache` (cần invalide nếu thay đổi scope)

**Lưu ý khi code:**
- ⚠️ Kiểm tra quyền `write` trên Document.
- ⚠️ Nếu thay đổi `folder_id` (di chuyển file): Invalide `UserDocumentCache` của document này.
- ⚠️ Nếu thay đổi `access_scope`: Invalide toàn bộ cache liên quan.
- Nếu thay đổi nội dung file thực sự (thay thế file mới): Phải tạo lại toàn bộ Chunk và Vector (tăng `version` lên).

---

### API-33: `DELETE /api/v1/documents/{doc_id}`
**Chức năng:** Xóa tài liệu (Soft Delete + Qdrant Sync).

**Bảng DB liên quan (IMPACT):**
- `documents` – set `is_deleted=True`
- `document_chunks` – set `is_deleted=True`
- `user_document_cache` – xóa cache của document này

**Lưu ý khi code:**
- ⚠️ Kiểm tra quyền `delete` trên Document.
- ⚠️ Set `is_deleted=True` cho Document.
- ⚠️ **Đồng bộ Qdrant:** Lấy tất cả `DocumentChunk.vector_id` của document này, gọi `qdrant_client.delete(collection_name=..., points_selector=vector_ids)`.
- ⚠️ Xóa `UserDocumentCache` của document này.
- ⚠️ Ghi `AuditLog(action='DELETE', resource_id=doc.id)`.

---

### API-34: `GET /api/v1/documents/{doc_id}/download`
**Chức năng:** Tải file gốc.

**Lưu ý khi code:**
- ⚠️ Kiểm tra quyền `read`.
- ⚠️ Ghi `AuditLog(action='DOWNLOAD', resource_id=doc.id)`.
- Dùng Django `FileResponse` hoặc redirect tới presigned URL (nếu dùng S3).

---

### API-35: `GET /api/v1/documents/{doc_id}/permissions`
**Chức năng:** Xem danh sách ACL của tài liệu.

**Lưu ý khi code:**
- ⚠️ Chỉ Admin hoặc người có quyền `write` mới xem được.
- Trả về cả quyền inherit từ Folder cha (để Admin hiểu rõ nguồn gốc quyền).

---

### API-36: `POST /api/v1/documents/{doc_id}/permissions`
**Chức năng:** Gán ACL chi tiết cho Document.

**Bảng DB liên quan:**
- `document_permissions` (insert/update)
- `user_document_cache` (invalide)

**Logic Precedence (CỰC KỲ QUAN TRỌNG):**
- `precedence='deny'` → User/Role đó bị chặn hoàn toàn, dù Folder cha có mở.
- `precedence='override'` → Ghi đè lên quyền của Folder cha (có thể cho thêm hoặc bớt quyền).
- `precedence='inherit'` → Tự động theo quyền Folder cha (giá trị mặc định).

**Lưu ý khi code:**
- ⚠️ Phân biệt rõ `subject_type`: 'role' hoặc 'account'.
- ⚠️ Dùng `update_or_create` theo unique_together `(document, subject_type, subject_id)`.
- ⚠️ Invalide `UserDocumentCache` sau khi lưu.
- ⚠️ Ghi `AuditLog(action='GRANT_ACL', resource_id=doc_id)`.

---

### API-37: `GET /api/v1/documents/{doc_id}/status`
**Chức năng:** Kiểm tra trạng thái xử lý AI của document.

**Bảng DB liên quan:**
- `documents` (status field)
- `async_tasks` (task status)

**Lưu ý khi code:**
- Polling endpoint (FE sẽ gọi mỗi 3-5 giây sau khi upload).
- Trả về `status`, `chunk_count`, `error_message` nếu thất bại.

---

### API-38: `POST /api/v1/documents/{doc_id}/reprocess`
**Chức năng:** Xử lý lại AI pipeline cho document.

**Lưu ý khi code:**
- ⚠️ Kiểm tra quyền `write`.
- ⚠️ Trước khi reprocess, phải **xóa các Chunk cũ** trong PostgreSQL và **xóa các Vector cũ** trong Qdrant.
- Insert `AsyncTask` mới với `task_type='INDEX_DOCUMENT'`.

---

## PHASE 5: TAGS (Day 15)

---

### API-39: `GET/POST/DELETE /api/v1/tags`
**Chức năng:** Quản lý Tags để phân loại tài liệu.

**Lưu ý khi code:**
- Tags được gán vào Document qua M2M `Document.tags`.
- Khi xóa Tag: Postgres tự động xóa liên kết qua M2M (`documents.tags.remove(tag)`).
- Khi xóa Tag, KHÔNG cần invalide Vector vì Tag không được lưu trong Qdrant payload.

---

## PHASE 6: RAG CHAT (Day 16–20)

> **Đây là phần quan trọng nhất của đồ án. Cần chú ý security nhất.**

---

### API-40: `GET /api/v1/conversations`
**Chức năng:** Danh sách hội thoại của User hiện tại.

**Lưu ý khi code:**
- ⚠️ Chỉ trả về Conversation của `request.user` (tuyệt đối không trả của người khác).
- Filter `is_deleted=False`, sắp xếp theo `updated_at DESC`.
- Phân trang.

---

### API-41: `POST /api/v1/conversations`
**Chức năng:** Tạo cuộc hội thoại mới.

**Bảng DB liên quan:**
- `conversations` (insert)
- `conversations_attached_documents` (nếu kèm file specific)
- `conversations_attached_folders` (nếu kèm folder specific)

**Lưu ý khi code:**
- ⚠️ Nếu user đính kèm Document cụ thể: Phải check quyền `read` trên từng Document đó.
- ⚠️ Nếu user đính kèm Folder cụ thể: Check quyền `read` trên Folder.
- `title` ban đầu có thể để trống, sẽ được auto-generate sau câu hỏi đầu tiên.

---

### API-42: `POST /api/v1/conversations/{conv_id}/messages`
**Chức năng:** Gửi câu hỏi và nhận câu trả lời từ AI (STREAMING).

**Bảng DB liên quan:**
- `messages` (insert 2 bản ghi: user message + AI response)
- `user_document_cache` (read để lấy accessible doc_ids)
- `document_chunks` (read để lấy chunk content sau search)
- `conversations` (update `updated_at`)
- `audit_logs` (insert QUERY)

**LUỒNG XỬ LÝ (CỰC KỲ QUAN TRỌNG):**
```
1. Nhận user message text
2. Save Message(role='user', content=text) vào DB
3. Tính toán accessible doc_ids:
   a. Check UserDocumentCache còn hạn → Lấy list doc_ids
   b. Nếu không có cache → Tính toán quyền, lưu cache
4. Nếu conversation có AttachedDocuments → Lọc: chỉ search trong doc_ids của AttachedDocuments ∩ accessible_doc_ids
5. Embed user question → gọi Ollama embedding model
6. Search Qdrant với payload filter: { 'document_id': { '$in': accessible_doc_ids } }
7. Lấy top-k chunks, kèm document metadata
8. Build RAG prompt: [System Prompt] + [Context từ chunks] + [User question]
9. Gọi Ollama LLM, STREAM response về FE (SSE)
10. Sau khi stream xong → Save Message(role='assistant', content=full_response, citations=[...])
11. Ghi AuditLog(action='QUERY', query_text=user_message)
12. (Optional) Auto-generate Conversation title từ câu hỏi đầu tiên
```

**Lưu ý khi code (BẮT BUỘC):**
- ⚠️ **TUYỆT ĐỐI:** Bước 6 phải có payload filter, KHÔNG bao giờ search toàn bộ Qdrant rồi filter sau.
- ⚠️ `citations` lưu mảng object: `[{ "chunk_id": "...", "doc_id": "...", "doc_name": "...", "page": 3, "snippet": "..." }]`.
- ⚠️ Dùng `StreamingHttpResponse` hoặc SSE (Server-Sent Events) để stream.
- ⚠️ Phải có timeout cho việc gọi Ollama.
- ⚠️ Nếu Ollama lỗi → Trả về error message, NOT crash server.

---

### API-43: `POST /api/v1/search`
**Chức năng:** Tìm kiếm ngữ nghĩa (Semantic Search) không cần chat.

**Luồng xử lý:**
1. Tính `accessible_doc_ids` (giống API-42).
2. Embed query.
3. Search Qdrant với filter `document_id IN accessible_doc_ids`.
4. Trả về danh sách chunks, kèm document metadata, score.
5. Ghi `AuditLog(action='QUERY')`.

**Lưu ý khi code:**
- ⚠️ Hỗ trợ filter thêm: `folder_id`, `tag`, `date_range` (thêm vào Qdrant payload filter).
- ⚠️ Phải trả về nguồn trích dẫn để User có thể click vào xem file gốc.

---

### API-44: `POST /api/v1/messages/{msg_id}/feedback`
**Chức năng:** User đánh giá câu trả lời AI (thumbs up/down).

**Bảng DB liên quan:**
- `human_feedback`

**Lưu ý khi code:**
- Unique constraint `(message, account)` → Dùng `update_or_create`.
- Ghi `AuditLog(action='FEEDBACK')`.

---

## PHASE 7: AUDIT & ADMIN (Day 21–23)

---

### API-45: `GET /api/v1/admin/audit-logs`
**Chức năng:** Xem nhật ký hành động hệ thống.

**Lưu ý khi code:**
- ⚠️ Yêu cầu quyền `ADMIN` hoặc `AUDIT_VIEW`.
- Hỗ trợ filter mạnh: `action`, `account_id`, `resource_id`, `date_range`.
- ⚠️ Phân trang bắt buộc (log có thể lên đến hàng triệu dòng).
- Chỉ đọc, KHÔNG cho phép sửa/xóa audit log.

---

### API-46: `GET /api/v1/admin/stats`
**Chức năng:** Thống kê tổng quát hệ thống.

**Lưu ý khi code:**
- Tính: Tổng User, Tổng Document, Tổng Query hôm nay, Dung lượng lưu trữ.
- Dùng `COUNT()` và `SUM()` trực tiếp trong DB, không load toàn bộ objects ra Python.

---

### API-47: `GET /api/v1/admin/async-tasks`
**Chức năng:** Xem trạng thái các tác vụ xử lý AI.

**Lưu ý khi code:**
- Filter theo `status`, `document_id`, `task_type`.
- Hỗ trợ restart task đang bị stuck (`status='failed'` → Reset về `pending`).

---

## ⚡ HELPER FUNCTIONS BẮT BUỘC PHẢI VIẾT TRƯỚC (core/permissions/)

```python
# 1. Hàm quan trọng nhất - dùng ở ~80% API
def get_user_accessible_doc_ids(user_id: int, permission='read') -> list[str]:
    """Trả về list UUID của Document mà user có quyền truy cập."""
    # Check cache trước
    # Nếu không có cache → tính toán và lưu cache

# 2. Check quyền cụ thể trên 1 Document
def check_document_permission(user_id: int, doc_id: str, action: str) -> bool:
    """Kiểm tra user có quyền action trên document không. action: read|write|delete"""

# 3. Check quyền cụ thể trên 1 Folder
def check_folder_permission(user_id: int, folder_id: str, action: str) -> bool:
    """Kiểm tra user có quyền action trên folder không."""

# 4. Invalide cache sau mọi thay đổi quyền
def invalidate_user_document_cache(doc_id: str = None, user_id: int = None):
    """Xóa cache liên quan. Dùng khi: upload, xóa, đổi quyền, đổi role."""
```

---

## 🚨 CHECKLIST 10 ĐIỀU TRÁNH LỖI

| # | Kiểm tra | Lý do |
|:--|:--|:--|
| 1 | Không hard-delete bất kỳ Object nào | Luôn dùng Soft Delete |
| 2 | Luôn có `is_deleted=False` trong get_queryset | Tránh trả về dữ liệu đã xóa |
| 3 | Invalide `UserDocumentCache` sau mọi thay đổi quyền | Tránh cache stale |
| 4 | Dùng `select_related` + `prefetch_related` | Tránh N+1 query |
| 5 | Dùng `transaction.atomic()` khi write nhiều bảng | Tránh dữ liệu không nhất quán |
| 6 | Filter Qdrant bằng doc_ids trước khi search | Security - tránh rò rỉ kiến thức |
| 7 | Ghi AuditLog cho mọi thao tác quan trọng | Compliance & Debug |
| 8 | Kiểm tra Account.status trước mọi action | Account bị block không được dùng |
| 9 | Validate quyền ở tầng Service, không phải View | Centralized permission check |
| 10 | Sync Qdrant bất kỳ khi nào Document bị xóa/reprocess | Tránh AI trả lời dựa trên file đã xóa |
