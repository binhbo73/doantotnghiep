# 📊 TẤT CẢ CÁC TRƯỜNG HỢP UPLOAD - KẾT HỢP DOCUMENT & FOLDER

**Ngày**: 06/05/2026  
**Phạm vi**: Liệt kê tất cả tổ hợp Folder + Document  
**Mục tiêu**: Giải thích rõ các trường hợp hợp lệ, không hợp lệ, và các case dễ gây nhầm lẫn

---

## 🎯 GIỚI THIỆU

**Thuộc tính của Folder**:
- `access_scope`: `company` / `department` / `personal`
- `department_id`: `NULL` hoặc UUID
- `parent_id`: Có hoặc không, dùng để xác định folder cha

**Thuộc tính của Document**:
- `folder_id`: `NULL` hoặc UUID của folder
- `access_scope`: `company` / `department` / `personal`
- `department_id`: `NULL` hoặc UUID

---

## 📱 PHẦN 0.5: SO SÁNH VỚI GOOGLE DRIVE & ONEDRIVE

### Câu hỏi chính

**Folder có `access_scope = company` hoặc `personal` nhưng vẫn có `department_id` thì có chuẩn không?**

### Kết luận

**Không chuẩn** và **không nên dùng**. Đây là một anti-pattern.

---

### GOOGLE DRIVE

#### Cấu trúc
```text
Google Drive:
├── My Drive (cá nhân - chỉ tôi)
├── Shared Drive (tổ chức - toàn công ty)
└── Shared with me (tài liệu người khác chia sẻ)

Google Drive không có khái niệm "department" riêng.
Chia sẻ là explicit: File/Folder + User/Group + Permission.
```

#### Mô hình chia sẻ
```text
File/Folder có thể chia sẻ với:
  ✅ Người dùng cụ thể
  ✅ Nhóm (group, nhưng không phải department implicit)
  ✅ Toàn tổ chức
  ✅ Công khai internet

  ❌ Không có: ràng buộc department ngầm
  ❌ Không có: scope của folder + danh sách user riêng kiểu ẩn
```

#### Metadata
```text
File:
  - owner: user_id
  - shared_with: [user1, user2, group1, ...]
  - access_level: READER, COMMENTER, EDITOR, OWNER

Folder:
  - owner: user_id hoặc team_id
  - shared_with: [...]
  - Không có field riêng tên là department_id
```

**Nhận xét**: Google Drive không dùng `department_id` như một metadata truy cập. Quyền truy cập là danh sách quyền explicit, không phải scope phòng ban ngầm.

---

### ONEDRIVE / SHAREPOINT

#### Cấu trúc
```text
OneDrive:
├── My Files (cá nhân)
├── Shared (chia sẻ explicit)
└── Organization Sites (qua SharePoint)

SharePoint:
├── Teams (Microsoft Teams)
├── Sites (tổ chức)
└── Lists/Libraries

Có khái niệm Team nhưng không đồng nghĩa với Department.
```

#### Mô hình permission
```text
Item (File/Folder) → Permission:
  - Owner
  - Can Edit
  - Can View

Đối tượng được cấp quyền:
  - User cụ thể
  - SharePoint Group (explicit)
  - Organization (everyone)

  ❌ Không có: department scope ngầm
  ❌ Không có: folder scope + department_id riêng biệt
```

#### Khác biệt chính
```text
OneDrive: Sharing = ACL rõ ràng
  → Permission được lưu trực tiếp trên item
  → Không có kế thừa department ngầm

Hệ thống của bạn:
  → access_scope + department_id
  → Có thể tạo ra mâu thuẫn khi kế thừa
```

**Nhận xét**: OneDrive/SharePoint dùng explicit sharing, không dùng department scope ngầm.

---

### Vì sao `company/personal + department_id` không chuẩn

#### Vấn đề 1: Mâu thuẫn ngữ nghĩa
```text
Google Drive: Không mâu thuẫn
  - Scope = "chia sẻ cho mọi người" → không cần department_id
  - Scope = "riêng tư" → không cần department_id

Hệ thống của bạn: ❌ Mâu thuẫn
  - access_scope="company" (mọi người)
    + department_id="finance" (chỉ Finance?)
    = Không rõ cái nào thắng
```

#### Vấn đề 2: Không rõ cách resolve quyền
```text
Google Drive: Rõ ràng
  File.shared_with = ["user1", "user2", "group1"]
  → Danh sách quyền explicit
  → Không phải đoán

Hệ thống của bạn: ❌ Mơ hồ
  Folder:
    access_scope = "company"
    department_id = "finance"

  Câu hỏi:
  - Document kế thừa access_scope hay department_id?
  - Nếu xung đột thì cái nào thắng?
  - Nếu user không thuộc Finance nhưng là owner thì sao?
  - Đây là lỗi hay chủ ý?
```

#### Vấn đề 3: Tình huống thực tế
```text
Google Drive:
  Folder "Company Handbook"
  ├── shared_with = ["everyone@company.com"]
  ├── permission = VIEWER

  Folder "Finance Reports"
  ├── shared_with = ["finance-team@company.com"]
  ├── permission = EDITOR

  ✅ Rõ ràng, không mơ hồ

Hệ thống của bạn:
  Folder "Company Handbook"
    access_scope = "company"
    department_id = "finance"

  Câu hỏi:
  - Ai xem được? Toàn công ty hay chỉ Finance?
  - `department_id` là lỗi hay chỉ là metadata?
```

#### Vấn đề 4: Kế thừa gây nhầm lẫn
```text
Google Drive: Không phải lo kế thừa kiểu này
  - Mỗi file có permission explicit
  - Folder permission không ép cứng file con

Hệ thống của bạn: ❌ Dễ nhầm
  Folder(access_scope="company", dept_id="sales")
    ├─ Doc1(access_scope="company", dept_id="sales")
    ├─ Doc2(access_scope="department", dept_id="finance")
    └─ Doc3(access_scope="personal", dept_id="sales")

  Câu hỏi:
  - Người dùng cố ý đặt tất cả `dept_id` này hay không?
  - Hay là tự kế thừa không nhất quán?
  - Nếu folder đổi phòng ban thì tài liệu con có đổi theo không?
```

---

### Chuẩn kiểu Google Drive / OneDrive

#### Mẫu 1: Folder company rõ ràng
```yaml
❌ Sai (hệ thống hiện tại):
  Folder:
    name: "Company Handbook"
    access_scope: "company"
    department_id: "finance"  # Gây nhầm lẫn

✅ Đúng (kiểu Google Drive):
  Folder:
    name: "Company Handbook"
    shared_with: ["everyone@company.com"]
    ownership: "company"

  Hoặc nếu giữ hệ thống hiện tại thì nên sửa:
  Folder:
    name: "Company Handbook"
    access_scope: "company"
    department_id: NULL  # Phải là NULL
```

#### Mẫu 2: Folder phòng ban rõ ràng
```yaml
❌ Sai:
  Folder:
    name: "Finance Docs"
    access_scope: "company"  # Nói là toàn công ty
    department_id: "finance"  # Nhưng lại giới hạn Finance

✅ Đúng (kiểu Google Drive):
  Folder:
    name: "Finance Docs"
    shared_with: ["finance-team@company.com"]

  Hoặc nếu giữ hệ thống hiện tại thì nên sửa:
  Folder:
    name: "Finance Docs"
    access_scope: "department"
    department_id: "finance"
```

#### Mẫu 3: Folder cá nhân rõ ràng
```yaml
❌ Sai:
  Folder:
    name: "My Docs"
    access_scope: "personal"
    department_id: "marketing"  # Cá nhân nhưng lại có phòng ban?

✅ Đúng (kiểu Google Drive):
  Folder:
    name: "My Docs"
    owner: "john@company.com"
    shared_with: []  # Chỉ owner

  Hoặc nếu giữ hệ thống hiện tại thì nên sửa:
  Folder:
    name: "My Docs"
    access_scope: "personal"
    department_id: NULL  # Phải là NULL
```

---

### Bảng so sánh

```text
┌──────────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ TIÊU CHÍ             │ GOOGLE DRIVE     │ ONEDRIVE/SP      │ HỆ THỐNG CỦA BẠN │
├──────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Khái niệm scope      │ shared_with list  │ permission ACL   │ access_scope +   │
│                      │                  │                  │ department_id    │
│ Personal folder      │ Không dept_id     │ Không dept_id    │ ❌ Cho phép dept │
│ metadata             │                  │                  │ id (SAI)         │
│ Company scope        │ Không dept meta   │ Không dept meta  │ ❌ Cho phép dept │
│ metadata             │                  │                  │ id (SAI)         │
│ Team/Department      │ Group explicit    │ Group explicit   │ ✅ Có nhưng      │
│ handling             │ (không implicit)  │ (không implicit) │ còn mơ hồ        │
│ Kế thừa              │ Không ép cứng     │ Có thể kế thừa   │ ❌ Dễ gây nhầm    │
│                      │ (explicit perms)  │ nhưng explicit   │                  │
│                      │                  │ override          │                  │
│ Mâu thuẫn            │ ✅ Không có       │ ✅ Không có      │ ❌ Có thể xảy ra │
└──────────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

---

### Khuyến nghị

#### Không nên
- Company/Personal folder + `department_id`
- Vì nó gây mâu thuẫn ngữ nghĩa
- Không giống cách Google Drive/OneDrive làm
- Làm code khó bảo trì và người dùng khó hiểu

#### Nên làm

**Option 1: Validation nghiêm ngặt**
```python
class Folder(BaseModel):
    def clean(self):
        if self.access_scope == 'company' and self.department_id:
            raise ValidationError(
                "Folder company không được có department_id. "
                "Nếu muốn giới hạn theo phòng ban thì hãy dùng scope 'department'."
            )

        if self.access_scope == 'personal' and self.department_id:
            raise ValidationError(
                "Folder personal không được có department_id. "
                "Folder personal chỉ dành cho từng người dùng."
            )

        if self.access_scope == 'department' and not self.department_id:
            raise ValidationError(
                "Folder department phải có department_id."
            )
```

**Option 2: Tự sửa + cảnh báo tạm thời**
```python
class Folder(BaseModel):
    def save(self, *args, **kwargs):
        if self.access_scope != 'department' and self.department_id:
            logger.warning(
                f"Folder '{self.name}': xóa department_id vì không khớp với scope '{self.access_scope}'"
            )
            self.department_id = None

        super().save(*args, **kwargs)
```

**Option 3: Danh sách permission explicit**
```python
# Tương lai: giống Google Drive hơn

class FolderPermission(BaseModel):
    """Danh sách quyền explicit, tương tự shared_with của Google Drive"""
    folder = ForeignKey(Folder)
    granted_to = ForeignKey('users.Account')  # hoặc Department
    permission_type = ('VIEWER', 'EDITOR', 'OWNER')

class Folder(BaseModel):
    name = CharField(max_length=100)
    owner = ForeignKey(Account)
    # Không còn access_scope, không còn department_id
    # Quyền được quản lý qua bảng FolderPermission
```

---

## ⚠️ PHẦN 0: QUY TẮC NHẤT QUÁN - VALIDATION CHO FOLDER

### Câu hỏi

Có được folder với `access_scope="company"` nhưng `department_id` khác NULL không?

### Câu trả lời

**Được về mặt model hiện tại, nhưng không nên dùng.**

### Ví dụ không nên
```json
{
  "id": "folder-xyz",
  "name": "Company Policies",
  "access_scope": "company",
  "department_id": "dept-finance-uuid"
}
```

### Vì sao không nên?
1. `company` nghĩa là toàn công ty, nhưng lại gắn thêm phòng ban riêng
2. Backend hiện nay chỉ xét `folder.department_id` có NULL hay không:
   ```python
   if folder.department_id:
       # Xử lý như folder phòng ban
       return {..., department_id: str(folder.department_id), ...}
   else:
       # Xử lý như folder công ty
       return {..., department_id: None, access_scope: 'company'}
   ```
3. Validation hiện chưa chặn đủ:
   - Chưa chặn company folder phải có `department_id = NULL`
   - Chưa chặn personal folder phải có `department_id = NULL`

### Khuyến cáo
- `access_scope="company"` → `department_id` phải là NULL
- `access_scope="department"` → `department_id` phải có giá trị
- `access_scope="personal"` → `department_id` phải là NULL

---

### Nên fix trong backend

Thêm vào model Folder:
```python
class Folder(BaseModel):
    ...

    def clean(self):
        """Kiểm tra tính nhất quán của access_scope."""
        if self.access_scope == 'company' and self.department_id:
            raise ValidationError(
                "Folder company không được có department_id. "
                "Hãy đổi sang scope 'department' hoặc xóa department."
            )

        if self.access_scope == 'personal' and self.department_id:
            raise ValidationError(
                "Folder personal không được có department_id."
            )

        if self.access_scope == 'department' and not self.department_id:
            raise ValidationError(
                "Folder scope department phải có department_id."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
```

---

## ✅ PHẦN 1: CÁC LOẠI FOLDER ĐÚNG

### Folder type 1: Root company-wide
```json
{
  "id": "folder-company-root",
  "name": "Company Policies",
  "parent_id": null,
  "access_scope": "company",
  "department_id": null,
  "created_by_id": 1
}
```

### Folder type 2: Root department - Finance
```json
{
  "id": "folder-finance-root",
  "name": "Finance Department",
  "parent_id": null,
  "access_scope": "department",
  "department_id": "dept-finance-uuid",
  "created_by_id": 1
}
```

### Folder type 3: Root department - Sales
```json
{
  "id": "folder-sales-root",
  "name": "Sales Department",
  "parent_id": null,
  "access_scope": "department",
  "department_id": "dept-sales-uuid",
  "created_by_id": 1
}
```

### Folder type 4: Root cá nhân
```json
{
  "id": "folder-personal-root",
  "name": "My Private Documents",
  "parent_id": null,
  "access_scope": "personal",
  "department_id": null,
  "created_by_id": 123
}
```

---

## 📋 PHẦN 2: VÍ DỤ SUBFOLDER

### Subfolder 2a: Finance > 2024
```json
{
  "id": "folder-finance-2024",
  "name": "2024",
  "parent_id": "folder-finance-root",
  "access_scope": "department",
  "department_id": "dept-finance-uuid",
  "created_by_id": 5
}
```

### Subfolder 2b: Finance > 2024 > Q1
```json
{
  "id": "folder-finance-2024-q1",
  "name": "Q1",
  "parent_id": "folder-finance-2024",
  "access_scope": "department",
  "department_id": "dept-finance-uuid",
  "created_by_id": 5
}
```

### Subfolder 3a: Sales > 2024
```json
{
  "id": "folder-sales-2024",
  "name": "2024",
  "parent_id": "folder-sales-root",
  "access_scope": "department",
  "department_id": "dept-sales-uuid",
  "created_by_id": 10
}
```

### Subfolder 1a: Company > Reports
```json
{
  "id": "folder-company-reports",
  "name": "Reports",
  "parent_id": "folder-company-root",
  "access_scope": "company",
  "department_id": null,
  "created_by_id": 1
}
```

---

## 📋 PHẦN 3: TẤT CẢ CÁC TRƯỜNG HỢP UPLOAD

### Trường hợp bất thường: cấu hình folder không nhất quán

Những case này có thể tồn tại trong database nhưng **không nên**.

#### Bất thường 1: Company folder + `department_id`
```yaml
FOLDER CONFIG (SAI):
  id: "folder-company-root"
  name: "Company Policies"
  access_scope: "company"
  department_id: "dept-finance-uuid"

KẾT QUẢ:
  Backend thấy folder.department_id != NULL → coi như folder phòng ban

UPLOAD DOCUMENT:
  _resolve_scope() trả về:
    access_scope="company"
    department_id="dept-finance-uuid"

HẬU QUẢ:
  - UI hiển thị tên company
  - Nhưng document lại bị giới hạn theo Finance
  - Không phải ai cũng xem được

KHUYẾN NGHỊ:
  - Không dùng cấu hình này
  - Nếu muốn theo Finance thì phải đổi access_scope sang "department"
```

#### Bất thường 2: Personal folder + `department_id`
```yaml
FOLDER CONFIG (SAI):
  id: "folder-personal-root"
  name: "My Private Docs"
  access_scope: "personal"
  department_id: "dept-sales-uuid"

KẾT QUẢ:
  Validation sẽ chặn nếu document không phải personal

LÝ DO:
  Personal folder phải chỉ chứa tài liệu cá nhân
  `department_id` không có ý nghĩa ở đây

KHUYẾN NGHỊ:
  - Không tạo personal folder có department_id
  - Hoặc dùng department scope đúng nghĩa
```

---

### Nhóm A: Upload vào folder công ty gốc (4 case)

#### A1: Company folder + document company
```yaml
FOLDER:
  id: "folder-company-root"
  access_scope: "company"
  department_id: null

UPLOAD REQUEST:
  folder_id: "folder-company-root"
  access_scope: "company"
  department_id: null

KẾT QUẢ:
  Document được tạo:
    folder_id: "folder-company-root"
    access_scope: "company"    ✅ Khớp
    department_id: null         ✅ Khớp
  Quyền xem: Mọi người trong công ty

VÍ DỤ:
  File: "Company_Handbook.pdf"
  → Folder: "Company Policies"
  → Scope: Company-wide
  → Ai xem: Everyone
```

#### A2: Company folder + document department nhưng thiếu `department_id`
```yaml
FOLDER:
  id: "folder-company-root"
  access_scope: "company"
  department_id: null

UPLOAD REQUEST:
  folder_id: "folder-company-root"
  access_scope: "department"
  department_id: null

KẾT QUẢ:
  Lỗi vì scope department bắt buộc có department_id

GIẢI PHÁP:
  Người dùng phải chọn department_id
```

#### A3: Company folder + document department có `department_id`
```yaml
FOLDER:
  id: "folder-company-root"
  access_scope: "company"
  department_id: null

UPLOAD REQUEST:
  folder_id: "folder-company-root"
  access_scope: "department"
  department_id: "dept-finance-uuid"

KẾT QUẢ:
  Document được tạo:
    folder_id: "folder-company-root"
    access_scope: "company"    ⚠️ Kế thừa từ folder
    department_id: null         ⚠️ Kế thừa từ folder

  Scope thực tế: COMPANY
  Ai xem: Everyone
```

#### A4: Company folder + document personal
```yaml
FOLDER:
  id: "folder-company-root"
  access_scope: "company"
  department_id: null

UPLOAD REQUEST:
  folder_id: "folder-company-root"
  access_scope: "personal"
  department_id: null

KẾT QUẢ:
  Document được tạo:
    folder_id: "folder-company-root"
    access_scope: "company"    ⚠️ Kế thừa từ folder
    department_id: null

  Scope thực tế: COMPANY
  Ai xem: Everyone
```

---

### Nhóm B: Upload vào folder phòng ban Finance

#### B1: Finance folder + document company
```yaml
FOLDER:
  id: "folder-finance-root"
  name: "Finance Department"
  access_scope: "department"
  department_id: "dept-finance-uuid"

UPLOAD REQUEST:
  folder_id: "folder-finance-root"
  access_scope: "company"
  department_id: null

KẾT QUẢ:
  Lỗi

LÝ DO:
  Không được upload tài liệu company-wide vào folder phòng ban
```

#### B2: Finance folder + document department đúng phòng ban
```yaml
FOLDER:
  id: "folder-finance-root"
  name: "Finance Department"
  access_scope: "department"
  department_id: "dept-finance-uuid"

UPLOAD REQUEST:
  folder_id: "folder-finance-root"
  access_scope: "department"
  department_id: "dept-finance-uuid"

KẾT QUẢ:
  Document được tạo với scope department Finance
```

#### B3: Finance folder + document department khác phòng ban
```yaml
FOLDER:
  id: "folder-finance-root"
  name: "Finance Department"
  access_scope: "department"
  department_id: "dept-finance-uuid"

UPLOAD REQUEST:
  folder_id: "folder-finance-root"
  access_scope: "department"
  department_id: "dept-sales-uuid"

KẾT QUẢ:
  Document vẫn bị ép theo department của folder (Finance)
```

#### B4: Finance folder + document personal
```yaml
FOLDER:
  id: "folder-finance-root"
  name: "Finance Department"
  access_scope: "department"
  department_id: "dept-finance-uuid"

UPLOAD REQUEST:
  folder_id: "folder-finance-root"
  access_scope: "personal"
  department_id: null

KẾT QUẢ:
  Document vẫn theo scope của folder: department Finance
```

#### B5-B8: Các subfolder của Finance
```text
B5: Finance > 2024 > Q1 + Company → Lỗi
B6: Finance > 2024 > Q1 + Department (Finance) → OK
B7: Finance > 2024 > Q1 + Department (Sales) → Bị ép về Finance
B8: Finance > 2024 > Q1 + Personal → Bị ép về department
```

#### B9-B12: Upload không chọn folder nhưng thuộc Finance
```yaml
B9: folder = NULL, scope = department, dept = Finance → OK
B10: folder = NULL, scope = company, dept = Finance → department_id bị bỏ qua
B11: folder = NULL, scope = personal, dept = Finance → department_id bị bỏ qua
B12: folder = NULL, scope = department, dept = NULL → Lỗi hoặc auto-detect
```

---

### Nhóm C: Upload vào folder phòng ban Sales

Tương tự nhóm B, chỉ thay `Finance` bằng `Sales` và `dept-finance-uuid` bằng `dept-sales-uuid`.

---

### Nhóm D: Upload vào folder cá nhân

#### D1: Personal folder + document company
```yaml
KẾT QUẢ: Lỗi
LÝ DO: Tài liệu trong personal folder phải là personal
```

#### D2: Personal folder + document department
```yaml
KẾT QUẢ: Lỗi
LÝ DO: Personal folder không được chứa document department
```

#### D3: Personal folder + document personal
```yaml
KẾT QUẢ: OK
Ai xem: Chỉ người upload
```

#### D4-D12
```text
D4: Personal + Company → Lỗi
D5: Personal + Department → Lỗi
D6: Personal + Personal → OK
D7-D12: Các biến thể khác hoặc không chọn folder
```

---

### Nhóm E: Không chọn folder

#### E1: Không chọn folder + company
```yaml
KẾT QUẢ: Document ở root, scope company
Ai xem: Everyone
```

#### E2: Không chọn folder + department có `department_id`
```yaml
KẾT QUẢ: Document ở root, scope department
Ai xem: Phòng ban được chọn
```

#### E3: Không chọn folder + department nhưng thiếu `department_id`
```yaml
KẾT QUẢ: Lỗi hoặc tự lấy phòng ban của user
```

#### E4: Không chọn folder + personal
```yaml
KẾT QUẢ: Document ở root, scope personal
Ai xem: Chỉ uploader
```

#### E5-E8: Biến thể khác
```text
E5: No folder + company nhưng có dept_id → dept_id bị bỏ qua
E6: No folder + department với Sales → OK
E7: No folder + personal nhưng có dept_id → dept_id bị bỏ qua
E8: No folder + auto-detect → Dùng scope mặc định của user
```

---

## 📊 PHẦN 4: BẢNG TÓM LƯỢT

```text
┌──────────────────────────────┬─────────────┬──────────────┬──────────────┬─────────┐
│ TRƯỜNG HỢP                   │ Folder Type │ Yêu cầu doc  │ Kết quả      │ Trạng thái │
├──────────────────────────────┼─────────────┼──────────────┼──────────────┼─────────┤
│ A1: Company + Company        │ company     │ company      │ company      │ ✅ OK   │
│ A2: Company + Dept (thiếu id) │ company     │ department   │ Lỗi          │ ❌ ERR  │
│ A3: Company + Dept (có id)    │ company     │ department   │ COMPANY      │ ⚠️ WARN │
│ A4: Company + Personal        │ company     │ personal     │ COMPANY      │ ⚠️ WARN │
│                              │             │              │              │         │
│ B1: Finance + Company         │ department  │ company      │ Lỗi          │ ❌ ERR  │
│ B2: Finance + Dept đúng       │ department  │ department   │ DEPARTMENT   │ ✅ OK   │
│ B3: Finance + Dept khác       │ department  │ department   │ FINANCE      │ ⚠️ WARN │
│ B4: Finance + Personal        │ department  │ personal     │ DEPARTMENT   │ ⚠️ WARN │
│                              │             │              │              │         │
│ D1: Personal + Company        │ personal    │ company      │ Lỗi          │ ❌ ERR  │
│ D2: Personal + Department     │ personal    │ department   │ Lỗi          │ ❌ ERR  │
│ D3: Personal + Personal       │ personal    │ personal     │ PERSONAL     │ ✅ OK   │
│                              │             │              │              │         │
│ E1: No folder + Company       │ NULL        │ company      │ COMPANY      │ ✅ OK   │
│ E2: No folder + Dept có id    │ NULL        │ department   │ DEPARTMENT   │ ✅ OK   │
│ E3: No folder + Dept thiếu id │ NULL        │ department   │ Lỗi          │ ❌ ERR  │
│ E4: No folder + Personal      │ NULL        │ personal     │ PERSONAL     │ ✅ OK   │
├──────────────────────────────┼─────────────┼──────────────┼──────────────┼─────────┤
│ BẤT THƯỜNG: Company + dept_id │ company +   │ kế thừa      │ Bị coi là    │ ⚠️ BAD  │
│                              │ dept_id     │              │ DEPARTMENT   │ CONFIG  │
│ BẤT THƯỜNG: Personal + dept_id│ personal +  │ bất kỳ       │ Bị chặn      │ ⚠️ BAD  │
│                              │ dept_id     │              │ nghiêm ngặt  │ CONFIG  │
│ BẤT THƯỜNG: Department + thiếu │ department  │ kế thừa      │ NULL/Lỗi     │ ⚠️ BAD  │
│ dept_id                      │ no dept_id  │              │              │ CONFIG  │
└──────────────────────────────┴─────────────┴──────────────┴──────────────┴─────────┘
```

---

## 🔑 QUY TẮC NHẤT QUÁN

### Cấu hình folder hợp lệ

#### Company folder
```yaml
access_scope: "company"
department_id: NULL
created_by_id: 1

Có thể chứa:
  - Document company
  - Document department của bất kỳ phòng ban nào
  - Document personal
```

#### Department folder
```yaml
access_scope: "department"
department_id: "dept-xyz"
created_by_id: 5

Có thể chứa:
  - Document department cùng phòng ban hoặc phòng ban khác
  - Document personal

Không được chứa:
  - Document company
```

#### Personal folder
```yaml
access_scope: "personal"
department_id: NULL
created_by_id: 123

Chỉ có thể chứa:
  - Document personal

Không được chứa:
  - Document company
  - Document department
```

### Cấu hình folder không hợp lệ

#### Company + department_id
```yaml
access_scope: "company"
department_id: "dept-xyz"

Vấn đề:
  - UI nói là company nhưng lại có ràng buộc department
  - Backend dễ hiểu nhầm thành folder phòng ban
```

#### Personal + department_id
```yaml
access_scope: "personal"
department_id: "dept-xyz"

Vấn đề:
  - Personal là của một người
  - department_id là của cả phòng ban
  - Hai khái niệm này xung đột
```

#### Department + thiếu department_id
```yaml
access_scope: "department"
department_id: NULL

Vấn đề:
  - Nói là department nhưng không chỉ rõ phòng ban nào
```

---

## 🎯 BẢNG QUYẾT ĐỊNH

### 1. Upload tài liệu toàn công ty
```text
✅ Tốt nhất: Không chọn folder, access_scope="company"
✅ Ổn: Chọn folder company, access_scope="company"
❌ Tránh: Folder phòng ban hoặc cá nhân
```

### 2. Upload báo cáo của phòng Finance
```text
✅ Tốt nhất: Folder Finance, access_scope="department"
✅ Ổn: Không chọn folder, access_scope="department", dept=Finance
❌ Tránh: Folder company rồi cố chọn department
```

### 3. Upload bản nháp cá nhân
```text
✅ Tốt nhất: Folder personal, access_scope="personal"
✅ Ổn: Không chọn folder, access_scope="personal"
❌ Tránh: Folder company/phòng ban rồi cố chọn personal
```

### 4. Upload báo cáo chỉ phòng Sales xem
```text
✅ Tốt nhất: Folder Sales, access_scope="department"
✅ Ổn: Không chọn folder, access_scope="department", dept=Sales
❌ Tránh: Folder Finance rồi chọn Sales
```

---

## 💡 NHẬN XÉT CHÍNH

### Quy tắc 1: Scope của folder là giới hạn tối đa
```text
Nếu folder = company → document có thể ở bất kỳ scope nào
Nếu folder = department → document chỉ nên là department hoặc personal
Nếu folder = personal → document bắt buộc là personal
```

### Quy tắc 2: `department_id` phải được kế thừa rõ ràng
```text
Nếu upload vào folder có department_id:
  → Document phải kế thừa department_id từ folder
  → Giá trị department_id do user nhập khác đi sẽ bị bỏ qua
```

### Quy tắc 3: Personal folder phải nghiêm ngặt
```text
Document trong personal folder:
  → Bắt buộc personal
  → Không được company hoặc department
  → Chỉ người tạo xem được
```

### Quy tắc 4: Company folder linh hoạt nhất
```text
Document trong company folder:
  → Có thể là company, department hoặc personal
  → Là loại permissive nhất
```

---

## Script: Sửa folder không nhất quán

```python
# File: backend/scripts/fix_folder_consistency.py
from apps.documents.models import Folder
from django.db import transaction

@transaction.atomic
def fix_folder_consistency():
    """Sửa các folder có access_scope và department_id không nhất quán."""

    fixes = {
        'company_with_dept': 0,
        'personal_with_dept': 0,
        'department_without_dept': 0,
    }

    # Fix 1: Company folder + department_id → xóa department_id
    bad_company = Folder.objects.filter(
        access_scope='company',
        department_id__isnull=False,
        is_deleted=False,
    )
    for folder in bad_company:
        print(f"Đang sửa: {folder.name} - xóa department_id")
        folder.department_id = None
        folder.save()
        fixes['company_with_dept'] += 1

    # Fix 2: Personal folder + department_id → xóa department_id
    bad_personal = Folder.objects.filter(
        access_scope='personal',
        department_id__isnull=False,
        is_deleted=False,
    )
    for folder in bad_personal:
        print(f"Đang sửa: {folder.name} - xóa department_id")
        folder.department_id = None
        folder.save()
        fixes['personal_with_dept'] += 1

    # Fix 3: Department folder nhưng thiếu department_id → đổi sang company
    bad_dept = Folder.objects.filter(
        access_scope='department',
        department_id__isnull=True,
        is_deleted=False,
    )
    for folder in bad_dept:
        print(f"Đang sửa: {folder.name} - đổi scope sang company")
        folder.access_scope = 'company'
        folder.save()
        fixes['department_without_dept'] += 1

    return fixes

# Chạy:
# python manage.py shell
# >>> from scripts.fix_folder_consistency import fix_folder_consistency
# >>> results = fix_folder_consistency()
# >>> print(results)
```

---

## 🧪 CÂU HỎI KIỂM TRA NHANH

### Test 1: Có upload báo cáo Finance vào folder company với scope Finance được không?
```text
Câu hỏi: folder="Company Policies" + scope="department" + dept="Finance"
Trả lời: Được, nhưng document sẽ trở thành COMPANY-WIDE
Kết quả: Ai cũng xem được, không chỉ Finance
```

### Test 2: Có upload policy công ty vào folder Finance không?
```text
Câu hỏi: folder="Finance" + scope="company"
Trả lời: Không
Lỗi: Không được để tài liệu company-wide trong folder phòng ban
```

### Test 3: Có upload bản nháp cá nhân vào folder personal không?
```text
Câu hỏi: folder="My Docs" + scope="personal"
Trả lời: Có
Kết quả: Chỉ bạn xem được
```

### Test 4: Không chọn folder nhưng chọn department scope được không?
```text
Câu hỏi: folder=NULL + scope="department" + dept="Sales"
Trả lời: Được
Kết quả: Document nằm ở root level, chỉ phòng Sales xem
```

### Test 5: Upload document của phòng khác vào folder Finance được không?
```text
Câu hỏi: folder="Finance" + scope="department" + dept="Sales"
Trả lời: Được, nhưng department_id sẽ bị ép về Finance
Kết quả: Document nhận department_id của folder
```