# FOLDER & DOCUMENT CREATION LOGIC ANALYSIS

## 0. Quick Summary - All Cases With Concrete Examples

### Folder Creation

| Case | Input | Kết quả |
|------|-------|---------|
| F1 | `name="Company Policies"`, `access_scope="company"`, không có `parent_id` | Tạo root folder công ty: `department_id=NULL`, `access_scope=company` |
| F2 | `name="Finance Documents"`, `access_scope="department"`, `department_id="uuid-finance"` | Tạo root folder phòng ban: `department_id=uuid-finance`, `access_scope=department` |
| F3 | `parent_id="company-root"`, parent có `department_id=NULL` | Sub-folder bị ép về `access_scope=company`, `department_id=NULL` |
| F4 | `parent_id="finance-root"`, parent có `department_id="uuid-finance"` | Sub-folder kế thừa `access_scope=department`, `department_id=uuid-finance` |
| F5 | `name="My Private Documents"`, `access_scope="personal"` | Tạo folder cá nhân: chỉ creator thấy được |
| F6 | `access_scope="department"` nhưng không truyền `department_id` | Lấy `department_id` từ `UserProfile`; nếu không có thì lỗi |

### Document Upload

| Case | Input | Kết quả |
|------|-------|---------|
| D1 | `folder_id="finance-folder"`, folder có `department_id="uuid-finance"` | Document kế thừa `folder_id`, `department_id=uuid-finance`, `access_scope=department` |
| D2 | `folder_id="company-folder"`, folder không có department | Document thành company doc: `department_id=NULL`, `access_scope=company` |
| D3 | Không có `folder_id`, có `department_id="uuid-sales"`, `access_scope="department"` | Document thuộc phòng ban Sales, không nằm trong folder |
| D4 | Không có `folder_id`, không có `department_id` | Document company-wide: `department_id=NULL`, `access_scope=company` |
| D5 | Không có `folder_id`, `access_scope="personal"` | Document cá nhân: chỉ uploader xem được |
| D6 | `folder_id` trỏ tới personal folder nhưng truyền `access_scope="company"` | Bị chặn, lỗi validation vì personal folder bắt buộc personal scope |

### Ví dụ thật ngắn

1. **Folder company root**
    ```json
    {
      "name": "Company Policies",
      "access_scope": "company"
    }
    ```
    Kết quả: folder công ty, không gắn phòng ban.

2. **Folder department root**
    ```json
    {
      "name": "Finance Docs",
      "access_scope": "department",
      "department_id": "uuid-finance"
    }
    ```
    Kết quả: folder thuộc phòng ban Finance.

3. **Sub-folder dưới folder phòng ban**
    ```json
    {
      "name": "Q1 Budget",
      "parent_id": "finance-root",
      "access_scope": "personal"
    }
    ```
    Kết quả: vẫn là folder department, vì parent ép scope.

4. **Document upload vào folder phòng ban**
    ```http
    file=report.pdf
    folder_id=finance-folder
    ```
    Kết quả: document tự lấy `department_id` của folder.

5. **Document upload theo phòng ban, không folder**
    ```http
    file=memo.txt
    department_id=uuid-sales
    access_scope=department
    ```
    Kết quả: document thuộc Sales, nằm ở root-level.

6. **Document cá nhân**
    ```http
    file=draft.md
    access_scope=personal
    ```
    Kết quả: chỉ người upload xem được.

## 1. FOLDER CREATION - Detailed Cases

### Request Structure
```http
POST /api/v1/folders

Request Body:
{
    "name": "string" (required, max 100 chars),
    "description": "string" (optional),
    "parent_id": "uuid" (optional),
    "access_scope": "personal|department|company" (optional, default='company'),
    "department_id": "uuid" (optional)
}
```

### Folder Creation Logic by Case

#### **CASE 1: Creating Root Folder (No parent_id) with access_scope='company'**

**Request:**
```json
{
    "name": "Company Policies",
    "access_scope": "company",
    "description": "Central company documents"
}
```

**Logic Flow (folder_service.py, lines 257-350):**
1. Validate name: Required, max 100 chars ✓
2. Validate access_scope: Must be one of ['personal', 'department', 'company'] ✓
3. No parent_id provided → go to CASE C/D
4. access_scope = 'company' → Keep it as is
5. department_id = None (not provided)

**Result Database State:**
```
folders table:
{
    id: UUID,
    name: "Company Policies",
    parent_id: NULL,
    department_id: NULL,
    access_scope: "company",
    created_by_id: user_id,
    created_at: now(),
    is_deleted: FALSE
}
```

**Permissions:**
- Creator (user_id) → Full access (admin)
- All other users → Can see and read (if they check folder tree)

---

#### **CASE 2: Creating Root Folder with access_scope='department'**

**Request:**
```json
{
    "name": "Finance Documents",
    "access_scope": "department",
    "department_id": "uuid-finance-dept"
}
```

**Logic Flow:**
1. Validate name ✓
2. Validate access_scope ✓
3. No parent_id → go to CASE C/D
4. access_scope = 'department' → Requires department_id
5. department_id provided → Use it as is
6. Create folder with access_scope='department' AND department_id='uuid-finance-dept'

**Result Database State:**
```
folders table:
{
    id: UUID,
    name: "Finance Documents",
    parent_id: NULL,
    department_id: "uuid-finance-dept",
    access_scope: "department",
    created_by_id: user_id
}
```

**Permissions:**
- Only users with department_id = 'uuid-finance-dept' can access
- Cannot be accessed by users from other departments

---

#### **CASE 3: Creating Sub-folder Under Company Folder (CASE A - parent has no department)**

**Scenario:**
- Parent folder: id='parent-uuid', access_scope='company', department_id=NULL
- Creating: Sub-folder under this parent

**Request:**
```json
{
    "name": "Q1 Reports",
    "parent_id": "parent-uuid",
    "access_scope": "company"  // Will be overridden
}
```

**Logic Flow:**
1. Validate name ✓
2. Validate access_scope ✓
3. parent_id provided → Get parent folder
4. **parent.department_id is NULL** → Go to CASE B
5. Force: access_scope = 'company' (inherited from parent)
6. Force: department_id = NULL

**Result Database State:**
```
folders table:
{
    id: UUID,
    name: "Q1 Reports",
    parent_id: "parent-uuid",
    department_id: NULL,  // Force NULL (parent is company-wide)
    access_scope: "company",
    created_by_id: user_id
}
```

**Key Behavior:**
- Even if user requested different scope, parent's company scope is enforced
- Subfolder inherits parent's company-wide accessibility

---

#### **CASE 4: Creating Sub-folder Under Department Folder (CASE A - parent has department)**

**Scenario:**
- Parent folder: id='finance-parent-uuid', access_scope='department', department_id='uuid-finance-dept'
- Creating: Sub-folder under this parent

**Request:**
```json
{
    "name": "2024 Budget",
    "parent_id": "finance-parent-uuid",
    "access_scope": "personal"  // Will be overridden
}
```

**Logic Flow:**
1. Validate name ✓
2. Validate access_scope ✓
3. parent_id provided → Get parent folder
4. **parent.department_id is NOT NULL** → Go to CASE A
5. Force: access_scope = parent.access_scope = 'department'
6. Force: department_id = parent.department_id = 'uuid-finance-dept'

**Result Database State:**
```
folders table:
{
    id: UUID,
    name: "2024 Budget",
    parent_id: "finance-parent-uuid",
    department_id: "uuid-finance-dept",  // Force inherited from parent
    access_scope: "department",  // Force inherited from parent
    created_by_id: user_id
}
```

**Key Behavior:**
- Subfolder MUST inherit parent's department and scope
- Cannot have different department than parent
- Maintains department hierarchy consistency

---

#### **CASE 5: Creating Personal Folder (Root)**

**Request:**
```json
{
    "name": "My Private Documents",
    "access_scope": "personal"
}
```

**Logic Flow:**
1. Validate name ✓
2. Validate access_scope ✓
3. No parent_id
4. access_scope = 'personal' → Scope is set
5. department_id = None (personal folders don't have department association)

**Result Database State:**
```
folders table:
{
    id: UUID,
    name: "My Private Documents",
    parent_id: NULL,
    department_id: NULL,
    access_scope: "personal",
    created_by_id: user_id
}
```

**Permissions:**
- Only creator (user_id) can access
- Completely private to the user

---

#### **CASE 6: Department Folder Without Explicit department_id**

**Request:**
```json
{
    "name": "My Department Files",
    "access_scope": "department"
    // No department_id provided
}
```

**Logic Flow:**
1. Validate name ✓
2. Validate access_scope ✓
3. No parent_id
4. access_scope = 'department' → Requires department_id
5. department_id not provided → Fallback to user's department from UserProfile
6. If user has department_id in UserProfile → Use it
7. If user has NO department → Raise ValidationError

**Result Database State (if user belongs to a department):**
```
folders table:
{
    id: UUID,
    name: "My Department Files",
    parent_id: NULL,
    department_id: "uuid-user-dept",  // Inherited from user's profile
    access_scope: "department",
    created_by_id: user_id
}
```

**Error Case:**
```json
{
    "success": false,
    "error": "Department folder must have department_id"
}
```

---

### Folder Creation Summary Table

| Case | parent_id | Provided access_scope | Result access_scope | Result department_id | Notes |
|------|-----------|----------------------|---------------------|----------------------|-------|
| 1 | NULL | company | company | NULL | Standard company folder |
| 2 | NULL | department | department | provided_dept_id | Department folder |
| 3 | root_company | any | company | NULL | Inherits parent company scope |
| 4 | dept_folder | any | department | parent_dept_id | Inherits parent department |
| 5 | NULL | personal | personal | NULL | Private folder |
| 6 | NULL | department | department | user_dept_id | Auto-fallback to user dept |

---

---

## 2. DOCUMENT CREATION (UPLOAD) - Detailed Cases

### Request Structure
```http
POST /api/v1/documents/upload

Content-Type: multipart/form-data

Fields:
- file: File (required, max 100MB)
- folder_id: UUID (optional)
- department_id: UUID (optional)
- access_scope: personal|department|company (optional)
- description: string (optional)
- tags: string (comma-separated, optional)
```

### Document Upload Logic by Case

#### **CASE A: Upload to Folder with Department Association**

**Scenario:**
- Folder exists: id='folder-uuid', department_id='uuid-finance-dept', access_scope='department'
- User uploads file to this folder

**Request:**
```http
file: report.pdf
folder_id: folder-uuid
access_scope: company  // Will be overridden
```

**Logic Flow (document_upload_service.py, lines 242-280):**
1. Validate file: size < 100MB ✓, MIME type allowed ✓
2. _resolve_scope() called with folder_id='folder-uuid', department_id=None, access_scope='company'
3. Fetch folder from DB → folder.department_id is NOT NULL
4. Resolve result returned:

**Result Database State:**
```
documents table:
{
    id: UUID,
    original_name: "report.pdf",
    filename: "abc123def.pdf",  // Hashed name
    folder_id: "folder-uuid",
    department_id: "uuid-finance-dept",  // Force inherited from folder
    access_scope: "department",  // Force inherited from folder
    uploader_id: user_id,
    status: "pending" → "completed" (after processing),
    created_at: now()
}
```

**Python Code Logic:**
```python
def _resolve_scope(folder_id='folder-uuid', department_id=None, access_scope='company'):
    if folder_id:
        folder = Folder.objects.get(pk=folder_id)  # Has department_id
        
        if folder.department_id:  # CASE A
            return {
                'folder_id': str(folder.id),
                'department_id': str(folder.department_id),  # Force inherit
                'access_scope': folder.access_scope,  # Force inherit
            }
```

**Validation Rules (document_upload_service.py):**
- If folder.access_scope = 'personal' → Document MUST be 'personal' (strict)
- If folder.access_scope = 'department' → Document can be 'department' or 'personal'
- If folder.access_scope = 'company' → Document can be any scope

---

#### **CASE B: Upload to Company-Wide Folder (Folder without Department)**

**Scenario:**
- Folder exists: id='company-folder-uuid', department_id=NULL, access_scope='company'
- User uploads file to this folder

**Request:**
```http
file: policy.docx
folder_id: company-folder-uuid
department_id: uuid-sales-dept  // Provided but ignored
```

**Logic Flow:**
1. Validate file ✓
2. _resolve_scope() called with folder_id='company-folder-uuid', department_id='uuid-sales-dept'
3. Fetch folder → folder.department_id IS NULL
4. Go to CASE B logic

**Result Database State:**
```
documents table:
{
    id: UUID,
    original_name: "policy.docx",
    folder_id: "company-folder-uuid",
    department_id: NULL,  // Force NULL (folder is company-wide)
    access_scope: "company",  // Force company scope
    uploader_id: user_id,
    status: "pending" → "completed"
}
```

**Python Code Logic:**
```python
def _resolve_scope(folder_id='company-folder-uuid', department_id='uuid-sales-dept', access_scope=None):
    if folder_id:
        folder = Folder.objects.get(pk=folder_id)  # No department_id
        
        if not folder.department_id:  # CASE B
            return {
                'folder_id': str(folder.id),
                'department_id': None,  # Ignore provided department_id
                'access_scope': 'company',  # Force company scope
            }
```

**Key Behavior:**
- Any department_id or access_scope provided by user is ignored
- Documents uploaded to company folders MUST be company-wide

---

#### **CASE C: Upload to Department (No Folder)**

**Scenario:**
- No folder_id provided
- User specifies department_id and wants document to be department-scoped

**Request:**
```http
file: memo.txt
department_id: uuid-sales-dept
access_scope: department  // Or can be omitted, defaults to 'department'
```

**Logic Flow:**
1. Validate file ✓
2. _resolve_scope() called with folder_id=None, department_id='uuid-sales-dept', access_scope='department'
3. No folder → go to CASE C logic

**Result Database State:**
```
documents table:
{
    id: UUID,
    original_name: "memo.txt",
    folder_id: NULL,  // No folder
    department_id: "uuid-sales-dept",
    access_scope: "department",  // Explicitly set
    uploader_id: user_id,
    status: "pending" → "completed"
}
```

**Python Code Logic:**
```python
def _resolve_scope(folder_id=None, department_id='uuid-sales-dept', access_scope='department'):
    if not folder_id and department_id:  # CASE C
        return {
            'folder_id': None,
            'department_id': str(department_id),
            'access_scope': access_scope or 'department',  # Default to 'department'
        }
```

**Permissions:**
- Only users with department_id = 'uuid-sales-dept' can access

---

#### **CASE D: Upload to Company (No Folder, No Department)**

**Scenario:**
- Simple company-wide document
- No specific department association

**Request:**
```http
file: announcement.pdf
// No folder_id, no department_id
```

**Logic Flow:**
1. Validate file ✓
2. _resolve_scope() called with folder_id=None, department_id=None, access_scope=None
3. No folder, no department → go to CASE D

**Result Database State:**
```
documents table:
{
    id: UUID,
    original_name: "announcement.pdf",
    folder_id: NULL,
    department_id: NULL,
    access_scope: "company",  // Default
    uploader_id: user_id,
    status: "pending" → "completed"
}
```

**Python Code Logic:**
```python
def _resolve_scope(folder_id=None, department_id=None, access_scope=None):
    if not folder_id and not department_id:  # CASE D
        return {
            'folder_id': None,
            'department_id': None,
            'access_scope': access_scope or 'company',  # Default to 'company'
        }
```

**Permissions:**
- All company users can access

---

#### **CASE E: Upload as Personal Document (No Folder)**

**Request:**
```http
file: personal_notes.md
access_scope: personal  // Explicitly mark as personal
```

**Logic Flow:**
1. Validate file ✓
2. _resolve_scope() called with folder_id=None, department_id=None, access_scope='personal'
3. No folder → go to CASE C/D
4. access_scope='personal' → Use it

**Result Database State:**
```
documents table:
{
    id: UUID,
    original_name: "personal_notes.md",
    folder_id: NULL,
    department_id: NULL,
    access_scope: "personal",
    uploader_id: user_id,
    status: "completed"
}
```

**Permissions:**
- Only uploader (user_id) can access

---

#### **CASE F: Upload to Personal Folder**

**Scenario:**
- Personal folder: id='personal-folder-uuid', access_scope='personal', department_id=NULL

**Request:**
```http
file: draft.txt
folder_id: personal-folder-uuid
access_scope: company  // Will be rejected
```

**Logic Flow:**
1. Validate file ✓
2. _resolve_scope() called with folder_id='personal-folder-uuid', access_scope='company'
3. Fetch folder → folder.access_scope='personal'
4. **Validation check:** Document in personal folder MUST be 'personal'
5. User requested 'company' → **Raise ValidationError**

**Error Response:**
```json
{
    "success": false,
    "error": "Document in personal folder phải có access_scope='personal', không được 'company'"
}
```

**What IS allowed:**
```json
{
    "success": true,
    "data": {
        "id": "uuid",
        "folder_id": "personal-folder-uuid",
        "access_scope": "personal",
        "department_id": null
    }
}
```

---

### Document Upload Complete Logic Matrix

| Case | folder_id | folder.dept | folder.scope | input dept | input scope | Result folder_id | Result dept_id | Result scope | Notes |
|------|-----------|-------------|--------------|------------|-------------|------------------|---|---|-------|
| A | has_id | ≠NULL | dept | any | any | folder_id | folder.dept | folder.scope | Force inherit from folder |
| B | has_id | NULL | company | any | any | folder_id | NULL | company | Force company scope |
| C | NULL | - | - | ≠NULL | any | NULL | dept_id | dept or default | Department-only document |
| D | NULL | - | - | NULL | NULL/company | NULL | NULL | company | Company-wide document |
| E | NULL | - | - | NULL | personal | NULL | NULL | personal | Personal document |
| F | personal | - | personal | - | ≠personal | ERROR | - | - | Validation error |

---

---

## 3. Permission Model After Creation

### After Folder is Created

**FolderPermission table** is NOT automatically created. Access is determined by:

1. **Creator Bypass** (lines 220-221 in folder_service.py)
   - Creator always has admin access
   
2. **Access Scope Check**
   - `access_scope='company'` → All users can read
   - `access_scope='department'` → Only users with same department_id can read
   - `access_scope='personal'` → Only creator can read

3. **Explicit FolderPermission Entries** (optional, for fine-grained control)
   - subject_type: 'account' | 'role'
   - subject_id: UUID
   - permission: 'read' | 'write' | 'delete'

---

### After Document is Created

**DocumentPermission table** IS automatically created:

```
document_permissions table:
{
    id: UUID,
    document_id: "uuid-doc",
    subject_type: "account",
    subject_id: user_id,  // The uploader
    permission: "write",  // Creator can write
    precedence: "override",
    is_active: TRUE,
    is_deleted: FALSE
}
```

**Access Rules:**

1. **By Scope** (Primary check)
   - `access_scope='company'` → All authenticated users can read
   - `access_scope='department'` → Users in same department can read
   - `access_scope='personal'` → Only uploader can read

2. **By Explicit Permission** (Overrides scope)
   - Checked via subject_type='account' or 'role'
   - Higher precedence level overrides default access

---

---

## 4. API Validation Sequence

### For Folder Creation

**Serializer (FolderCreateSerializer):**
```python
name = CharField(max_length=100, required=True, trim_whitespace=True)
description = CharField(max_length=1000, required=False, allow_null=True)
parent_id = UUIDField(required=False, allow_null=True)
access_scope = ChoiceField(choices=['personal', 'department', 'company'], required=False)
department_id = UUIDField(required=False, allow_null=True)
```

**Service Validation (create_folder):**
1. Name validation ✓
2. access_scope validation ✓
3. Parent folder existence check ✓
4. Parent permission check ✓
5. Department requirement check (if access_scope='department') ✓

---

### For Document Upload

**Serializer (DocumentUploadSerializer):**
```python
file = FileField(required=True)
folder_id = UUIDField(required=False, allow_null=True)
department_id = UUIDField(required=False, allow_null=True)
access_scope = ChoiceField(choices=['personal', 'department', 'company'], required=False)
description = CharField(max_length=2000, required=False)
tags = CharField(required=False)  # Converted to list in serializer
```

**View Validation (DocumentUploadView):**
1. File received ✓
2. Folder write permission check (if folder_id provided) ✓

**Service Validation (DocumentUploadService):**
1. File size check (< 100MB) ✓
2. MIME type validation ✓
3. Folder existence check ✓
4. Scope-to-folder compatibility check ✓
5. Personal folder personal scope enforcement ✓

---

---

## 5. Database State After Creation Examples

### Example 1: Company-wide Document in Company Folder

```python
# CREATE REQUEST
POST /api/v1/documents/upload
{
    file: "Q1_Report.pdf",
    folder_id: "d1a2b3c4-e5f6-4a7b-8c9d-e0f1a2b3c4d5",
    // No department_id, no access_scope
}

# RESULT IN DATABASE
documents:
{
    id: "u1u2u3u4-v5v6-7w7x-y8y9-z0z1z2z3z4z5",
    original_name: "Q1_Report.pdf",
    filename: "5d41402abc4b2a76b9719d911017c592.pdf",
    storage_path: "uploads/123/5d41402abc4b2a76b9719d911017c592.pdf",
    file_type: "pdf",
    file_size: 2048000,
    uploader_id: 123,
    folder_id: "d1a2b3c4-e5f6-4a7b-8c9d-e0f1a2b3c4d5",
    department_id: NULL,
    access_scope: "company",
    status: "completed",
    created_at: "2024-05-05T10:30:00Z"
}

document_permissions:
{
    id: "p1p2p3p4-q5q6-7r7s-t8t9-u0u1u2u3u4u5",
    document_id: "u1u2u3u4-v5v6-7w7x-y8y9-z0z1z2z3z4z5",
    subject_type: "account",
    subject_id: 123,
    permission: "write",
    precedence: "override",
    is_active: TRUE
}
```

---

### Example 2: Department Document without Folder

```python
# CREATE REQUEST
POST /api/v1/documents/upload
{
    file: "Sales_Strategy.docx",
    department_id: "a7a8a9aa-b0b1-4a7b-8c9d-e0f1a2b3c4d5",
    access_scope: "department"
}

# RESULT IN DATABASE
documents:
{
    id: "x1x2x3x4-y5y6-7z7z-z8z9-a0a1a2a3a4a5",
    original_name: "Sales_Strategy.docx",
    filename: "c4ca4238a0b923820dcc509a6f75849b.docx",
    storage_path: "uploads/456/c4ca4238a0b923820dcc509a6f75849b.docx",
    file_type: "docx",
    uploader_id: 456,
    folder_id: NULL,  // No folder
    department_id: "a7a8a9aa-b0b1-4a7b-8c9d-e0f1a2b3c4d5",
    access_scope: "department",
    status: "completed"
}

# Access Rules:
# - Only users with UserProfile.department_id = "a7a8a9aa-b0b1-4a7b-8c9d-e0f1a2b3c4d5" can read
# - Other users cannot access
```

---

### Example 3: Personal Document in Personal Folder

```python
# CREATE REQUEST
POST /api/v1/documents/upload
{
    file: "Draft_Notes.txt",
    folder_id: "m1m2m3m4-n5n6-7o7o-p8p9-q0q1q2q3q4q5"
    // Personal folder, so document automatically personal
}

# RESULT IN DATABASE
documents:
{
    id: "d1d2d3d4-e5e6-7f7f-g8g9-h0h1h2h3h4h5",
    original_name: "Draft_Notes.txt",
    filename: "37b51d194a7513e45b56f6524f2d51f2.txt",
    storage_path: "uploads/789/37b51d194a7513e45b56f6524f2d51f2.txt",
    file_type: "txt",
    uploader_id: 789,
    folder_id: "m1m2m3m4-n5n6-7o7o-p8p9-q0q1q2q3q4q5",
    department_id: NULL,
    access_scope: "personal",  // Inherited from personal folder
    status: "completed"
}

# Access:
# - Only user 789 (uploader) can access
```

---

---

## 6. Error Cases & Validation Failures

### Folder Creation Errors

| Error | Trigger | Response Code |
|-------|---------|---|
| Name required or > 100 chars | `name=""` or `name` > 100 chars | 400 |
| Invalid access_scope | `access_scope="invalid"` | 400 |
| Parent not found | `parent_id="non-existent-uuid"` | 404 |
| No write permission on parent | User lacks write on parent folder | 403 |
| No department for dept folder | `access_scope="department"` without dept_id and user has no dept | 400 |

---

### Document Upload Errors

| Error | Trigger | Response Code |
|-------|---------|---|
| File too large | File size > 100MB | 413 |
| Invalid MIME type | `.exe`, `.zip` files | 400 |
| Folder not found | `folder_id="non-existent"` | 404 |
| No write permission on folder | User lacks write on folder | 403 |
| Personal scope mismatch | Upload as 'company' to personal folder | 400 |
| File required | No file in request | 400 |

---

---

## 7. File Processing Pipeline (Post-Upload)

After document is created with `status='pending'`:

```
1. Thread started → _process_document()
   │
   ├─→ Parse file (PDF/DOCX/TXT/MD)
   │   └─→ Extract text content
   │
   ├─→ Split into chunks
   │   └─→ Create DocumentChunk entries (status='pending')
   │
   ├─→ Embed each chunk
   │   ├─→ Generate embedding vector
   │   ├─→ Save to Qdrant (vector DB)
   │   └─→ Create DocumentEmbedding entries
   │
   └─→ Update Document.status = 'completed' or 'failed'
       └─→ Log AuditLog if processing failed
```

**During this pipeline:**
- Document remains accessible (with `status='pending'`)
- Users can see document exists but cannot query chunks yet
- Once `status='completed'` → Ready for RAG queries

---

## 8. Summary: Key Business Rules

### Folder Rules
1. **Root folders** can be: company, department, or personal
2. **Sub-folders** inherit parent's scope and department (strict inheritance)
3. **Department folders** require a department_id
4. **Personal folders** are isolated to creator

### Document Rules
1. **With folder** → Inherits folder's scope AND department
2. **Department scope** (no folder) → Requires department_id OR user's department
3. **Company scope** (default) → No department restriction
4. **Personal scope** → Only uploader can access
5. **Personal folder documents** → MUST be personal scope (enforced)

### Access Determination
1. Creator always has full access
2. Access scope determines default visibility
3. Explicit permissions can override defaults
4. Department_id filters who can see department-scoped items

---

---

## 10. TWO-LAYER PERMISSION ARCHITECTURE - RBAC ⟷ ACL Integration

### Overview: Hai Tầng Quyền Hạn

```
┌──────────────────────────────────────────────────────────────────────┐
│                     PERMISSION SYSTEM (2 LAYERS)                     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  LAYER 1: RBAC (Role-Based Access Control)                           │
│  ──────────────────────────────────────────────────────────────────  │
│  Account → Role → Permission → API Action                            │
│                                                                        │
│  Quyết định: "User XYZ CÓ QUYỀN làm ACTION gì?"                      │
│  (Xác định quyền GLOBAL trên hệ thống)                               │
│                                                                        │
│  Example:                                                             │
│    Account(id=1) ──has_role──> Role(admin) ──has_perm──>             │
│    Permissions: [document_read, document_write, document_share]     │
│                                                                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  LAYER 2: ACL (Access Control List - Object Level)                   │
│  ──────────────────────────────────────────────────────────────────  │
│  Document/Folder → FolderPermission/DocumentPermission               │
│  → Explicit allow/deny on specific resource                          │
│                                                                        │
│  Quyết định: "User XYZ CÓ QUYỀN truy cập DOCUMENT/FOLDER cụ thể?"   │
│  (Xác định quyền trên TÀI NGUYÊN cụ thể)                            │
│                                                                        │
│  Mechanism:                                                           │
│    - access_scope: company / department / personal (default boundary)│
│    - FolderPermission: Explicit grant/deny on folders                │
│    - DocumentPermission: Explicit grant/deny + precedence control    │
│                                                                        │
└──────────────────────────────────────────────────────────────────────┘
```

---

### Permission Decision Flow - Lưu Đồ Quyết Định

```
                    REQUEST ARRIVES
                    │
                    ▼
      ┌─────────────────────────────────┐
      │ API Permission Class Check      │ ← LAYER 1 Entry Point
      │ (drf_permissions.py)            │
      │ Has user's ROLE got permission? │
      │ e.g., HasDocumentPermission     │
      └──────────┬──────────────────────┘
                 │
            ┌────▼────┐
            │  RBAC   │
            │  Check  │
            └────┬────┘
                 │
         ┌───────▼────────┐
         │  User has Role │
         │  + Permission? │
         └───────┬────────┘
                 │
            NO   │   YES
         ┌───────┴────────┐
         │                │
         ▼                ▼
      DENY        Continue to Layer 2
                         │
                  ┌──────▼──────────┐
                  │ ACL/Object-Level│ ← LAYER 2 Entry Point
                  │ Permission Check│
                  │ (permission_    │
                  │  manager.py)    │
                  └──────┬──────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
      Level 1         Level 2         Level 3
   Explicit DENY   Explicit ALLOW    Role-based
   on Object       on Object         on Document
         │               │               │
         │ YES            │ YES            │ YES
         │                │                │
         ▼                ▼                ▼
      DENY            ALLOW            Check Level 4
                                            │
         ┌─────────────────────────────────┘
         │
         ▼
      Level 4: Inherit from Folder
      ├─ Parent folder has permission?
      ├─ YES: Check permission level
      └─ NO: Go to Level 5
         
         ▼
      Level 5: access_scope boundary
      ├─ 'company': All users allowed
      ├─ 'department': Only dept users allowed
      └─ 'personal': Only creator allowed
         
         ▼
      Level 6: Default DENY
      └─ No permission found = DENIED

      ┌─────────────────────────────────┐
      │         FINAL DECISION          │
      │         ALLOW or DENY           │
      └─────────────────────────────────┘
```

---

### Permission Hierarchy Matrix - Ma Trận Quyết Định

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6-LEVEL PERMISSION HIERARCHY (High to Low Priority)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ Level  │ Check Type            │ Example                                     │
│────────┼───────────────────────┼──────────────────────────────────────────  │
│ 1      │ EXPLICIT DENY         │ DocumentPermission(permission='deny')       │
│        │ (Highest Priority)    │ → STOP: Access Denied                      │
│                                                                               │
│ 2      │ EXPLICIT ALLOW        │ DocumentPermission(permission='write')      │
│        │ (Document-level)      │ → Check if permission level ≥ required      │
│                                                                               │
│ 3      │ ROLE-BASED (RBAC)     │ Role(name='manager') has Permission(code=   │
│        │ (Global permission)   │ 'document_write') → Allow                   │
│                                                                               │
│ 4      │ FOLDER INHERITANCE    │ Document.folder → Check folder permissions  │
│        │                       │ If folder has write → document allow write  │
│                                                                               │
│ 5      │ ACCESS SCOPE          │ Document.access_scope='department' &        │
│        │ (Default Boundary)    │ user.department=same → Allow read           │
│                                                                               │
│ 6      │ DEFAULT DENY          │ No permission found → DENY (most restrictive)
│        │ (Lowest Priority)     │                                             │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Real-World Example 1: Simple Company Document

```
SCENARIO: 
  User "Alice" (ID: user-001, Role: editor) tries to READ a company-scoped document
  
DOCUMENT DETAILS:
  {
    id: "doc-001",
    name: "Company Policy 2024",
    access_scope: "company",        ← Everyone can read
    uploader_id: "user-admin",
    folder_id: NULL
  }

REQUEST:
  GET /api/v1/documents/doc-001/

─────────────────────────────────────────────────────────────────────────────

PERMISSION CHECK FLOW:

┌─ STEP 1: RBAC LAYER (API Guard)
│  Question: Does Alice's role include 'document_read' permission?
│
│  Database Query:
│    Account.id = user-001
│    ├─ AccountRole.role_id → Role(id=role-editor)
│    └─ Role.permissions → has Permission(code='document_read')?
│
│  Result: ✅ YES (editor role has document_read)
│  Status: RBAC Check PASS → Continue to Layer 2
│
├─ STEP 2: ACL LAYER (permission_manager.py)
│  Question: Can Alice access THIS specific document?
│
│  Check Hierarchy:
│
│  Level 1 - Explicit DENY?
│    DocumentPermission.document_id=doc-001 & permission='deny'
│    Result: ❌ NO (not found)
│
│  Level 2 - Explicit ALLOW?
│    DocumentPermission.document_id=doc-001 & 
│    subject_id=user-001 & permission='write'
│    Result: ❌ NO (not found)
│
│  Level 3 - Role-based?
│    Account(user-001).roles → check Role(editor)
│    Role has 'document_read'? ✅ YES
│    Status: ALLOW via RBAC
│
│  Final: ✅ ALLOW (Level 3 matched)
│
└─ STEP 3: Response
   HTTP 200 OK
   {
     "id": "doc-001",
     "name": "Company Policy 2024",
     "content": "...",
     "access_granted": true,
     "granted_via": "RBAC role-based permission"
   }

SUMMARY:
  Layer 1 (RBAC): ✅ PASS (Alice's role has document_read)
  Layer 2 (ACL):  ✅ PASS (Role-based permission applies)
  FINAL RESULT:   ✅ ALLOW
```

---

### Real-World Example 2: Department Document - Cross-Department Access Denied

```
SCENARIO:
  User "Bob" (ID: user-bob, Dept: sales, Role: user) tries to READ 
  a department-scoped document from the Finance department
  
DOCUMENT DETAILS:
  {
    id: "doc-finance-001",
    name: "Finance Q1 Budget",
    access_scope: "department",           ← Only same dept
    department_id: "dept-finance",        ← Finance department
    folder_id: "folder-finance",
    uploader_id: "user-finance-mgr"
  }

REQUEST:
  GET /api/v1/documents/doc-finance-001/
  Headers: Authorization: Bearer token_bob

─────────────────────────────────────────────────────────────────────────────

PERMISSION CHECK FLOW:

┌─ STEP 1: RBAC LAYER
│  Question: Does Bob's role include 'document_read'?
│
│  Database Query:
│    Account.id = user-bob
│    ├─ AccountRole → Role(id=role-user)
│    └─ Role.permissions → has Permission(code='document_read')?
│
│  Result: ✅ YES (user role has document_read)
│  Status: RBAC Check PASS → Continue to Layer 2
│
├─ STEP 2: ACL LAYER (permission_manager.py)
│  Question: Can Bob access THIS specific Finance document?
│  
│  Context:
│    Bob's department: dept-sales
│    Document's department: dept-finance
│
│  Check Hierarchy:
│
│  Level 1 - Explicit DENY?
│    DocumentPermission.document_id=doc-finance-001 & permission='deny'
│    Result: ❌ NO
│
│  Level 2 - Explicit ALLOW?
│    DocumentPermission where:
│      document_id=doc-finance-001 & 
│      subject_id=user-bob & 
│      permission='read'
│    Result: ❌ NO (Bob not explicitly granted)
│
│  Level 3 - Role-based?
│    Bob's role = 'user' (generic role)
│    Can 'user' role read Finance documents? 
│    No specific role permission on Finance docs
│    Result: ❌ NO
│
│  Level 4 - Inherit from folder?
│    Document.folder_id = folder-finance
│    FolderPermission where:
│      folder_id=folder-finance & 
│      subject_id=user-bob
│    Result: ❌ NO
│
│  Level 5 - access_scope boundary?
│    document.access_scope = 'department'
│    document.department = dept-finance
│    bob.department = dept-sales
│    _check_department_hierarchy(dept-sales, dept-finance)
│    → Bob's dept ≠ Finance dept → ❌ FAIL
│
│  Level 6 - Default DENY
│    No permission found → Default: DENY
│
│  Final: ❌ DENY (at Level 5)
│
└─ STEP 3: Response
   HTTP 403 Forbidden
   {
     "error": "Permission denied",
     "message": "You do not have access to this document",
     "reason": "Document belongs to Finance department, your access is limited to Sales department"
   }

SUMMARY:
  Layer 1 (RBAC):  ✅ PASS (Bob has document_read permission)
  Layer 2 (ACL):   ❌ FAIL (Department scope check failed at Level 5)
  FINAL RESULT:    ❌ DENY

KEY INSIGHT:
  Even though Bob has global 'document_read' permission (RBAC),
  the ACL layer blocks access because the document is department-scoped
  and Bob is from a different department.
  This is "fail-secure" design: permission must pass BOTH layers.
```

---

### Real-World Example 3: Role Permission Override vs Document ACL

```
SCENARIO:
  User "Charlie" (ID: user-charlie, Dept: sales, Role: manager) 
  tries to WRITE a document that he doesn't own
  
  - Charlie has 'manager' role (can write company documents)
  - The document is in a shared folder
  - No explicit DocumentPermission for Charlie
  
DOCUMENT DETAILS:
  {
    id: "doc-shared-001",
    name: "Sales Strategy 2024",
    access_scope: "department",
    department_id: "dept-sales",
    folder_id: "folder-sales-shared",
    uploader_id: "user-alex"  ← Different from Charlie
  }

REQUEST:
  PATCH /api/v1/documents/doc-shared-001/
  Body: { name: "Sales Strategy 2024 - Updated" }

─────────────────────────────────────────────────────────────────────────────

PERMISSION CHECK FLOW:

┌─ STEP 1: RBAC LAYER
│  Question: Does Charlie's role include 'document_write'?
│
│  Database Query:
│    Account.id = user-charlie
│    ├─ AccountRole → Role(id=role-manager)
│    └─ Role.permissions → has Permission(code='document_write')?
│
│  Result: ✅ YES (manager role has document_write)
│  Status: RBAC Check PASS → Continue to Layer 2
│
├─ STEP 2: ACL LAYER (permission_manager.py)
│  Question: Can Charlie WRITE THIS specific document?
│
│  Context:
│    Action: 'write'
│    Charlie's department: dept-sales
│    Document's department: dept-sales (SAME)
│
│  Check Hierarchy:
│
│  Level 1 - Explicit DENY?
│    DocumentPermission where:
│      document_id=doc-shared-001 & 
│      subject_id=user-charlie & 
│      permission='deny'
│    Result: ❌ NO
│
│  Level 2 - Explicit ALLOW?
│    DocumentPermission where:
│      document_id=doc-shared-001 & 
│      subject_id=user-charlie & 
│      permission='write'
│    Result: ❌ NO (no explicit permission record)
│
│  Level 3 - Role-based (RBAC)?
│    Charlie's role = 'manager'
│    required_permission_code = 'document_write'
│    check_user_has_permission(user-charlie, 'document_write')
│    Result: ✅ YES (manager has document_write)
│    → ALLOW (permission granted via RBAC)
│
│  Final: ✅ ALLOW (Level 3 matched)
│
└─ STEP 3: Response
   HTTP 200 OK
   {
     "id": "doc-shared-001",
     "name": "Sales Strategy 2024 - Updated",
     "modified_by": "user-charlie",
     "modified_at": "2024-05-05T15:30:00Z",
     "message": "Document updated successfully"
   }

SUMMARY:
  Layer 1 (RBAC):  ✅ PASS (Charlie has document_write permission)
  Layer 2 (ACL):   ✅ PASS (Role-based check at Level 3)
  FINAL RESULT:    ✅ ALLOW

KEY INSIGHT:
  Charlie doesn't have an explicit DocumentPermission record,
  but can still write because his ROLE (manager) grants 'document_write'.
  This is role-based access control at work.
```

---

### Real-World Example 4: Explicit Document Permission Override - Shared Document

```
SCENARIO:
  User "Diana" (ID: user-diana, Dept: hr, Role: user) 
  tries to READ a Finance department document that was explicitly shared with her
  
  Normal rule: Diana (HR) cannot access Finance docs
  But: The Finance manager explicitly shared it → FolderPermission with 'read'
  
DOCUMENT & FOLDER DETAILS:
  Folder:
  {
    id: "folder-finance-secret",
    name: "Finance Confidential",
    access_scope: "department",
    department_id: "dept-finance"
  }
  
  Document:
  {
    id: "doc-finance-secret",
    name: "Confidential Audit Report",
    access_scope: "department",
    department_id: "dept-finance",
    folder_id: "folder-finance-secret",
    uploader_id: "user-finance-controller"
  }
  
  FolderPermission:
  {
    id: "folperm-001",
    folder_id: "folder-finance-secret",
    subject_type: "account",
    subject_id: "user-diana",
    permission: "read",
    is_active: TRUE
  }

REQUEST:
  GET /api/v1/documents/doc-finance-secret/
  User: Diana (HR)

─────────────────────────────────────────────────────────────────────────────

PERMISSION CHECK FLOW:

┌─ STEP 1: RBAC LAYER
│  Question: Does Diana's role include 'document_read'?
│
│  Database Query:
│    Account.id = user-diana
│    ├─ AccountRole → Role(id=role-user)
│    └─ Role.permissions → has Permission(code='document_read')?
│
│  Result: ✅ YES (user role has document_read)
│  Status: RBAC Check PASS → Continue to Layer 2
│
├─ STEP 2: ACL LAYER (permission_manager.py)
│  Question: Can Diana READ THIS specific Finance document?
│
│  Context:
│    Diana's department: dept-hr
│    Document's department: dept-finance (DIFFERENT)
│
│  Check Hierarchy:
│
│  Level 1 - Explicit DENY?
│    DocumentPermission where:
│      document_id=doc-finance-secret & 
│      subject_id=user-diana & 
│      permission='deny'
│    Result: ❌ NO
│
│  Level 2 - Explicit ALLOW on Document?
│    DocumentPermission where:
│      document_id=doc-finance-secret & 
│      subject_id=user-diana & 
│      permission='read'
│    Result: ❌ NO (no explicit document-level permission)
│
│  Level 3 - Role-based?
│    Diana's role = 'user' (has document_read globally)
│    But this requires Level 5 scope check to pass first
│    Scope check would fail at department boundary
│    Result: ⚠️  Cannot use (scope mismatch)
│
│  Level 4 - Inherit from folder?
│    Document.folder_id = "folder-finance-secret"
│    Query FolderPermission:
│      folder_id = "folder-finance-secret"
│      subject_type = "account"
│      subject_id = "user-diana"
│      permission = "read"
│    Result: ✅ YES (explicit folder permission found!)
│    → ALLOW (Diana can read folder → can read documents in it)
│
│  Final: ✅ ALLOW (Level 4 matched via folder inheritance)
│
└─ STEP 3: Response
   HTTP 200 OK
   {
     "id": "doc-finance-secret",
     "name": "Confidential Audit Report",
     "content": "...",
     "access_granted_via": "Explicit folder permission granted by Finance department",
     "shared_by": "user-finance-controller",
     "access_scope": "department"
   }

SUMMARY:
  Layer 1 (RBAC):        ✅ PASS (Diana has document_read permission)
  Layer 2 (ACL Level 4): ✅ PASS (Explicit folder permission override)
  FINAL RESULT:          ✅ ALLOW

KEY INSIGHT:
  Even though Diana is from a different department (HR vs Finance),
  the Finance manager can grant her access by adding a FolderPermission.
  This demonstrates fine-grained access control via the ACL layer.
  The folder-level permission (Level 4) overrides the department scope (Level 5).
```

---

### Real-World Example 5: Permission Precedence - Deny Override

```
SCENARIO:
  User "Eve" (ID: user-eve, Dept: sales, Role: manager)
  has manager role (can write documents)
  BUT the document owner explicitly DENIED her access
  
DOCUMENT DETAILS:
  {
    id: "doc-denied",
    name: "Sensitive Sales Data",
    access_scope: "department",
    department_id: "dept-sales",
    uploader_id: "user-frank"
  }
  
  DocumentPermission (DENY):
  {
    id: "docperm-deny-001",
    document_id: "doc-denied",
    subject_type: "account",
    subject_id: "user-eve",
    permission: "deny",
    precedence: "override",
    is_active: TRUE
  }

REQUEST:
  PATCH /api/v1/documents/doc-denied/
  User: Eve (manager, can normally write)

─────────────────────────────────────────────────────────────────────────────

PERMISSION CHECK FLOW:

┌─ STEP 1: RBAC LAYER
│  Question: Does Eve's role include 'document_write'?
│
│  Database Query:
│    Account.id = user-eve
│    ├─ AccountRole → Role(id=role-manager)
│    └─ Role.permissions → has Permission(code='document_write')?
│
│  Result: ✅ YES (manager role has document_write)
│  Status: RBAC Check PASS → Continue to Layer 2
│
├─ STEP 2: ACL LAYER (permission_manager.py)
│  Question: Can Eve WRITE THIS specific document?
│
│  Check Hierarchy:
│
│  Level 1 - Explicit DENY?
│    DocumentPermission where:
│      document_id=doc-denied & 
│      subject_id=user-eve & 
│      permission='deny'
│    Result: ✅ YES (FOUND!)
│    → STOP HERE: DENY TAKES PRECEDENCE
│
│  Final: ❌ DENY (Level 1 matched - explicit deny)
│         (Levels 2-6 are not even checked)
│
└─ STEP 3: Response
   HTTP 403 Forbidden
   {
     "error": "Access denied",
     "message": "You do not have permission to modify this document",
     "reason": "Document owner has explicitly denied your access"
   }

SUMMARY:
  Layer 1 (RBAC):  ✅ PASS (Eve has document_write permission)
  Layer 2 (ACL):   ❌ FAIL (Explicit DENY at Level 1 - highest priority)
  FINAL RESULT:    ❌ DENY

KEY INSIGHT:
  This is the most important rule: EXPLICIT DENY has HIGHEST PRIORITY.
  Even though Eve's manager role grants write permission at the RBAC layer,
  the ACL layer's explicit deny (Level 1) overrides it completely.
  No amount of role permissions can override a direct deny.
  This implements the "principle of least privilege" - deny is fail-safe.
```

---

### Permission Decision Matrix - All Combinations

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ COMPLETE PERMISSION MATRIX - RBAC × ACL Combinations                            │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│ RBAC    │ ACL Level 1  │ ACL Level 2  │ ACL Level 5  │ Final Result │ Reason     │
│ Result  │ Explicit Deny│ Explicit Allow│ Scope Check │             │            │
│─────────┼──────────────┼──────────────┼─────────────┼─────────────┼────────────│
│         │              │              │             │             │            │
│ ✅ YES  │ ✅ YES (DENY)│      -       │      -      │  ❌ DENY    │ Deny > All │
│         │              │              │             │             │            │
│ ✅ YES  │ ❌ NO        │ ✅ YES (ALLOW)│     -      │  ✅ ALLOW   │ Explicit   │
│         │              │              │             │             │ Allow      │
│         │              │              │             │             │            │
│ ✅ YES  │ ❌ NO        │ ❌ NO        │ ✅ PASS    │  ✅ ALLOW   │ Scope-based│
│         │              │              │             │             │ allow      │
│         │              │              │             │             │            │
│ ✅ YES  │ ❌ NO        │ ❌ NO        │ ❌ FAIL    │  ❌ DENY    │ Scope      │
│         │              │              │             │             │ blocked    │
│         │              │              │             │             │            │
│ ❌ NO   │      -       │      -       │      -      │  ❌ DENY    │ No RBAC    │
│         │              │              │             │             │ permission │
│         │              │              │             │             │            │
└─────────┴──────────────┴──────────────┴─────────────┴─────────────┴────────────┘

LOGIC RULES:
  1. If RBAC = NO          → IMMEDIATE DENY (don't check ACL)
  2. If RBAC = YES & Level 1 Deny = YES  → DENY (deny highest priority)
  3. If RBAC = YES & Level 2 Allow = YES → ALLOW
  4. If RBAC = YES & Level 3 Role Perm = YES & Scope = YES → ALLOW
  5. If RBAC = YES & Level 4 Folder = YES → ALLOW
  6. If RBAC = YES & Levels 1-4 = NO → Check Level 5 (access_scope)
  7. If all levels fail → DEFAULT DENY

CONCLUSION:
  ✅ ALLOW = (RBAC = YES) AND (Any ACL Level matches AND Scope allows)
  ❌ DENY  = (RBAC = NO) OR (All ACL Levels fail) OR (Explicit Deny present)
```

---

### Implementation in Code - How Layers are Orchestrated

```python
# File: backend/core/permissions/drf_permissions.py (API Guard)
class HasDocumentPermission(permissions.BasePermission):
    """LAYER 1: RBAC Check at API entry point"""
    
    def has_permission(self, request, view):
        # RBAC: Check user has global 'document_read' permission
        if request.method == 'GET':
            return request.user.has_permission('document_read')
        elif request.method in ['PUT', 'PATCH']:
            return request.user.has_permission('document_write')
        return False
    
    def has_object_permission(self, request, view, obj):
        # LAYER 2: Call permission manager for ACL check
        perm_manager = PermissionManager()
        action = 'read' if request.method == 'GET' else 'write'
        return perm_manager.check_document_access(
            request.user.id,
            obj.id,
            action
        )

# File: backend/core/permissions/permission_manager.py (ACL Orchestration)
class PermissionManager:
    """LAYER 2: ACL Check with 6-level hierarchy"""
    
    def check_document_access(self, user_id, doc_id, action):
        """Main ACL decision point"""
        user = Account.objects.get(id=user_id)
        doc = Document.objects.get(id=doc_id)
        
        return self._check_document_permission_hierarchy(
            user=user,
            document=doc,
            action=action
        )
    
    def _check_document_permission_hierarchy(self, user, document, action):
        """Implementation of 6-level hierarchy"""
        
        # Level 1: Explicit DENY
        if self.perm_mgr_repo.get_document_deny_permission(doc.id, user.id):
            return False  # ← STOP HERE
        
        # Level 2: Explicit ALLOW
        if self.perm_mgr_repo.get_document_allow_permission(doc.id, user.id):
            return True   # ← ALLOW
        
        # Level 3: Role-based RBAC
        if self.permission_repo.check_user_has_permission(user.id, 'document_write'):
            return True   # ← ALLOW
        
        # Level 4: Folder inheritance
        if document.folder and self._check_folder_inheritance(user, document.folder):
            return True   # ← ALLOW
        
        # Level 5: access_scope boundary
        if document.access_scope == 'company':
            return True   # ← ALLOW (company-wide)
        elif document.access_scope == 'department':
            if self._check_department_hierarchy(user.dept, document.dept):
                return True  # ← ALLOW (same department)
        elif document.access_scope == 'personal':
            if document.uploader_id == user.id:
                return True  # ← ALLOW (own document)
        
        # Level 6: Default DENY
        return False  # ← DENY
```

---

### Layer Interaction Diagram - Complete Flow

```
                      HTTP REQUEST
                      (user wants action on resource)
                             │
                             ▼
              ┌──────────────────────────────┐
              │  URL Routing                 │
              │  /api/v1/documents/{id}/    │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  ViewSet.get/put/patch()     │
              │  (e.g., DocumentViewSet)     │
              └──────────────┬───────────────┘
                             │
                   ┌─────────▼─────────┐
                   │  permission_      │
                   │  classes = [       │
                   │    IsAuthenticated,│
                   │    HasDocument    │
                   │    Permission     │ ← LAYER 1 ENTRY
                   │  ]                │
                   └─────────┬─────────┘
                             │
         ┌───────────────────▼───────────────────┐
         │         LAYER 1: RBAC Check           │
         │  (drf_permissions.py)                │
         │                                       │
         │  Q: Does user's ROLE have the        │
         │     global permission?                │
         │                                       │
         │  Checks:                             │
         │  - Account.has_permission('doc_read')│
         │  - Via AccountRole → Role.permissions │
         │                                       │
         └─────────────────┬─────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  RBAC Result │
                    └──────┬──────┘
                           │
                     ┌─────┴──────┐
                     │            │
                    FAIL          PASS
                     │            │
                     ▼            ▼
                  403 Forbidden  (Continue)
                                 │
                    ┌────────────▼────────────┐
                    │  LAYER 2: ACL Check    │
                    │ (permission_manager.py)│
                    │                        │
                    │  Q: Can user access    │
                    │     THIS specific      │
                    │     resource?          │
                    │                        │
                    │  Checks (6-levels):    │
                    │  1. Explicit DENY      │
                    │  2. Explicit ALLOW     │
                    │  3. Role-based RBAC    │
                    │  4. Folder inherit     │
                    │  5. access_scope       │
                    │  6. Default DENY       │
                    │                        │
                    └────────────┬───────────┘
                                 │
                          ┌──────▼──────┐
                          │  ACL Result  │
                          └──────┬──────┘
                                 │
                           ┌─────┴──────┐
                           │            │
                          FAIL          PASS
                           │            │
                           ▼            ▼
                        403 Forbidden  200 OK
                                      + Data


KEY FLOWS:
  ✅ ALLOW:
    1. RBAC Check = PASS
    2. ACL Level 1-4 match OR Level 5 scope allows
    
  ❌ DENY:
    1. RBAC Check = FAIL (early exit)
    2. ACL Level 1 = Explicit DENY (highest priority)
    3. All ACL Levels fail (default principle of least privilege)
    4. Scope check fails (department/personal boundary)
```

---

### Summary Table: When to Use Which Layer

```
┌─────────────────────────────────────────────────────────────────┐
│ WHEN TO CONFIGURE PERMISSIONS                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ RBAC (Layer 1) - Role-Based Access Control                       │
│ Use for: Global capability restrictions                          │
│ Example: "Only editors can write documents"                      │
│ Config:  Role → Permission mapping                              │
│ Where:   admin/roles/permissions settings                       │
│                                                                   │
│ ─────────────────────────────────────────────────────────────   │
│                                                                   │
│ ACL (Layer 2) - Object-Level Access Control                      │
│ Use for: Fine-grained resource sharing                           │
│ Example: "Share Finance budget with specific HR people"          │
│ Config:  FolderPermission / DocumentPermission records           │
│ Where:   Document/Folder sharing UI                             │
│                                                                   │
│ ─────────────────────────────────────────────────────────────   │
│                                                                   │
│ access_scope - Default Boundary                                  │
│ Use for: Organize by company / department / personal             │
│ Example: "All staff documents go to company scope"               │
│ Config:  Set on folder/document creation                        │
│ Where:   Automatic via service layer logic                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. File References in Backend

**Key Implementation Files:**
- [backend/services/folder_service.py](backend/services/folder_service.py#L257) - `create_folder()` method
- [backend/services/document_upload_service.py](backend/services/document_upload_service.py#L76) - `upload()` and `_resolve_scope()` methods
- [backend/api/views/folder_views.py](backend/api/views/folder_views.py#L130) - FolderListCreateView POST handler
- [backend/api/views/document_views.py](backend/api/views/document_views.py#L180) - DocumentUploadView POST handler
- [backend/api/serializers/folder_serializers.py](backend/api/serializers/folder_serializers.py#L150) - FolderCreateSerializer
- [backend/api/serializers/document_serializers.py](backend/api/serializers/document_serializers.py#L100) - DocumentUploadSerializer
- [backend/core/permissions/permission_manager.py](backend/core/permissions/permission_manager.py#L250) - Permission hierarchy implementation
- [backend/core/permissions/drf_permissions.py](backend/core/permissions/drf_permissions.py#L81) - RBAC guard classes
