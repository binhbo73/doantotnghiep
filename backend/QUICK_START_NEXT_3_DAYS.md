# 🚀 QUICK START - API Implementation in Next 3 Days

**TL;DR**: Code 3 Phase liên tiếp, không conflict, follow Django best practices

---

## 📊 Quick Status

```
✅ Already Done (23 endpoints):
   - Phase 0: Auth (login, register, refresh, logout)
   - Phase 1: Password reset
   - Phase 2: User profile (self + admin)
   - Phase 2c (partial): Role assignment via Account

❌ Next 3 Priorities (24 endpoints):
   🔴 Phase 3: IAM Endpoints (5) → 4-6h
   🔴 Phase 4A: Folder CRUD (8) → 8-10h
   🔴 Phase 4B: Document Upload + CRUD (10) → 10-12h

🟡 Then (4 weeks):
   - Infrastructure: Qdrant + Ollama (1 week)
   - Phase 5: Department (3 endpoints)
   - Phase 6: Chat (4 endpoints + streaming)
   - Phase 7-8: Tags + Admin (6 endpoints)
```

---

## 🎯 Day 1: Phase 3 - IAM Endpoints (4-6 hours)

### What to Code

**File**: `backend/api/views/iam_views.py`

5 View Classes:
1. `PermissionListView` - GET `/api/v1/iam/permissions`
2. `RoleListView` - GET `/api/v1/iam/roles`
3. `RoleCreateView` - POST `/api/v1/iam/roles`
4. `RoleUpdateView` - PUT `/api/v1/iam/roles/{role_id}`
5. `RoleDeleteView` - DELETE `/api/v1/iam/roles/{role_id}`

### Template Structure

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsAdmin
from repositories.permission_repository import PermissionRepository
from repositories.role_repository import RoleRepository

class PermissionListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        # 1. Query repository
        repo = PermissionRepository()
        perms = repo.get_all()
        
        # 2. Serialize
        data = [{'id': p.id, 'code': p.code, 'name': p.name} for p in perms]
        
        # 3. Return standardized response
        return Response({
            'success': True,
            'status_code': 200,
            'data': data
        })
```

### Steps

1. **Create file** `backend/api/views/iam_views.py` with 5 classes
2. **Check serializers** in `backend/api/serializers/` (role_serializers, permission_serializers must exist)
3. **Add URLs** to `backend/api/urls.py` - register 5 new routes
4. **Test in terminal**:
   ```bash
   curl -X GET http://localhost:8000/api/v1/iam/permissions/ \
     -H "Authorization: Bearer <token>"
   ```

### Checklist

- [ ] Create iam_views.py with 5 classes
- [ ] Import repositories correctly
- [ ] Use permission_classes = [IsAuthenticated, IsAdmin]
- [ ] Return standard response format
- [ ] Add URLs (5 routes)
- [ ] Test all 5 endpoints
- [ ] Verify non-admin gets 403

---

## 🎯 Day 2: Phase 4A - Folder Endpoints (8-10 hours)

### What to Code

**Files**: 
- `backend/api/views/folder_views.py` (8 view classes)
- `backend/services/folder_service.py` (new)
- Check/create serializers

### 8 Endpoints

1. `GET /api/v1/folders` - Tree structure
2. `POST /api/v1/folders` - Create
3. `PUT /api/v1/folders/{id}` - Update
4. `DELETE /api/v1/folders/{id}` - Delete (recursive)
5. `PATCH /api/v1/folders/{id}/move` - Move to another parent
6. `GET /api/v1/folders/{id}/permissions` - View ACL
7. `POST /api/v1/folders/{id}/permissions` - Grant ACL
8. `DELETE /api/v1/folders/{id}/permissions/{perm_id}` - Revoke ACL

### Key Points

⚠️ **Permission Hierarchy**:
```
Check User permission before:
1. View folder (access_scope + department + FolderPermission)
2. Edit folder (write permission required)
3. Delete folder (delete permission + check users inside)
```

⚠️ **Folder Tree**:
```
- Folder has parent_id (self-referential FK)
- GET /folders returns nested tree structure
- Need to handle recursion
```

⚠️ **Delete is Complex**:
```
- Delete folder
- Also delete all sub-folders (DFS)
- Also delete all documents inside
- Sync Qdrant to remove vectors
- Invalidate UserDocumentCache
- Use transaction.atomic()
```

### Steps

1. Verify `Folder` model exists in `apps/documents/models.py`
2. Create `services/folder_service.py`
3. Create `api/views/folder_views.py` with 8 classes
4. Check serializers exist
5. Add 8 URL routes
6. Test each endpoint

### Checklist

- [ ] Verify Folder model exists
- [ ] Create folder_service.py
- [ ] Create folder_views.py (8 classes)
- [ ] Add URLs
- [ ] Test GET /folders (returns tree)
- [ ] Test POST /folders (create)
- [ ] Test PUT /folders/{id}
- [ ] Test DELETE /folders/{id} (proper cascade)
- [ ] Test permission checks (non-owner gets 403)
- [ ] Verify all responses use standard format

---

## 🎯 Day 3: Phase 4B - Document Endpoints (10-12 hours)

### What to Code

**Files**:
- `backend/api/views/document_views.py` (10 classes)
- `backend/services/document_service.py` completion

### 10 Endpoints + **File Upload**

1. `GET /api/v1/documents` - List (with permission filters)
2. **`POST /api/v1/documents/upload`** - Upload file ⭐ COMPLEX
3. `GET /api/v1/documents/{id}` - Detail
4. `PUT /api/v1/documents/{id}` - Update metadata
5. `DELETE /api/v1/documents/{id}` - Soft delete
6. `GET /api/v1/documents/{id}/download` - Download file
7. `GET /api/v1/documents/{id}/permissions` - View ACL
8. `POST /api/v1/documents/{id}/permissions` - Grant ACL
9. `GET /api/v1/documents/{id}/status` - Check processing (pending/completed/failed)
10. `POST /api/v1/documents/{id}/reprocess` - Re-index

### Key: File Upload Handler

```python
# The tricky one!

class DocumentUploadView(APIView):
    def post(self, request):
        # 1. Get file from request.FILES['file']
        # 2. Validate: file type, size
        # 3. Check user permission on folder_id
        # 4. Save with hashed name to uploads/
        # 5. Create Document record (status='pending')
        # 6. Create DocumentPermission for uploader
        # 7. Submit AsyncTask for processing (INDEX_DOCUMENT)
        # 8. Write AuditLog
        # 9. Return doc_id + status: 'pending'
```

### Key Complexity: Permission Checks

```
User can see document if:
1. DocumentPermission(account=user, document=doc) exists
   OR
2. DocumentPermission(role IN user.roles, document=doc) exists
   OR
3. Inherit from Folder parent permissions

Make sure to:
- Check UserDocumentCache first (cache!)
- Fallback to DB query if cache miss
- Invalidate cache on permission changes
```

### Steps

1. Verify Document model exists
2. Create document_service.py methods
3. Create document_views.py with 10 classes
4. **File upload**: Save to `uploads/` directory
5. AsyncTask: Submit INDEX_DOCUMENT task
6. Test all 10 endpoints
7. Test permission cascade from folder

### Checklist

- [ ] Verify Document model
- [ ] Create document_service.py
- [ ] Create document_views.py (10 classes)
- [ ] Implement file upload handler
- [ ] Verify file saved to uploads/
- [ ] Test permission checks
- [ ] Test all 10 endpoints
- [ ] Test cascade delete (folder delete → document delete)
- [ ] Test Qdrant sync on delete
- [ ] Test async task submission

---

## ⚠️ AVOID CONFLICTS - 5 Rules

### Rule 1: Always Use Service Layer
```python
# ❌ BAD - Query directly from View
doc = Document.objects.get(id=doc_id)

# ✅ GOOD - Use Service
service = DocumentService()
doc = service.get_document(doc_id)
```

### Rule 2: Always Use Repository in Service
```python
# ❌ BAD - Query directly from Service
user = Account.objects.filter(username=...).first()

# ✅ GOOD - Use Repository
repo = UserRepository()
user = repo.get_by_username(...)
```

### Rule 3: Always Soft Delete
```python
# ❌ BAD
obj.delete()

# ✅ GOOD
obj.is_deleted = True
obj.save()
```

### Rule 4: Always Write AuditLog for Important Actions
```python
audit_service.log(
    action='CREATE_DOCUMENT',
    account=request.user,
    resource_id=str(doc.id),
    metadata={'file_size': doc.size}
)
```

### Rule 5: Use Transactions for Multi-Table Operations
```python
from django.db import transaction

@transaction.atomic()
def delete_folder_recursive(folder_id):
    # All or nothing - if something fails, rollback all
    pass
```

---

## 🧪 Testing Quick Commands

```bash
# 1. Get admin token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123"}' | jq -r '.access_token')

# 2. Test IAM permission list
curl -X GET http://localhost:8000/api/v1/iam/permissions/ \
  -H "Authorization: Bearer $TOKEN"

# 3. Test folder create
curl -X POST http://localhost:8000/api/v1/folders/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"My Folder"}'

# 4. Test document upload
curl -X POST http://localhost:8000/api/v1/documents/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@myfile.pdf" \
  -F "folder_id=uuid-here"
```

---

## 📊 Progress Tracking

After 3 days, you should have:
- ✅ Phase 3: 5/5 endpoints (100%)
- ✅ Phase 4A: 8/8 endpoints (100%)
- ✅ Phase 4B: 10/10 endpoints (100%)

**Total**: 23 + 23 = 46/47 endpoints (98%)

---

## 🎯 Next Week

After Day 3:
- Week 2: Fix bugs, add tests, optimize queries
- Week 3: Qdrant + Ollama integration (background)
- Week 4: Phase 6 Chat endpoints (with streaming)
- Week 5: Polish + deployment

---

## ✅ Checklist Before Starting

- [ ] Read NEXT_PHASE_IMPLEMENTATION_ROADMAP.md (full details)
- [ ] Review existing Phase 0-2 code structure
- [ ] Verify all model relationships
- [ ] Make sure you have database migrations
- [ ] Docker backend running: `docker compose up -d`
- [ ] Can login and get token

---

## 🚀 START NOW!

**Day 1 Goal**: Complete Phase 3 IAM (5 endpoints)

Go to `backend/api/views/` and create `iam_views.py` 🎯

Good luck! 💪

