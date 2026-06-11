"""
Document Views - API Endpoints cho Document Management
Phase 4B - 10 endpoints

Endpoints:
1. GET    /api/v1/documents              - List accessible documents (with filters)
2. POST   /api/v1/documents/upload       - Upload file (CRITICAL - file + AsyncTask)
3. GET    /api/v1/documents/{id}         - Document detail
4. PUT    /api/v1/documents/{id}         - Update metadata
5. DELETE /api/v1/documents/{id}         - Soft delete + Qdrant sync
6. GET    /api/v1/documents/{id}/download - Download file
7. GET|POST /api/v1/documents/{id}/permissions - View/Grant ACL
8. DELETE /api/v1/documents/{id}/permissions/{type}/{id}/{perm} - Revoke ACL
9. GET    /api/v1/documents/{id}/status  - Processing status
10. POST  /api/v1/documents/{id}/reprocess - Re-index

Flow: View → Service → Repository → ORM

Each view:
1. Permission check (IsAuthenticatedUser)
2. Input validation (Serializer)
3. Call Service (business logic)
4. Serialize response
5. Return standard response
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ParseError, UnsupportedMediaType
from django.http import FileResponse
from django.db import transaction
import logging
import io
import asyncio

from core.permissions.drf_permissions import IsAuthenticatedUser, user_has_any_permission, user_has_permission
from core.constants import PermissionCodes
from core.utils.response_builder import ResponseBuilder
from core.exceptions import (
    ValidationError,
    NotFoundError,
    BusinessLogicError,
    PermissionDeniedError,
    FileSizeExceededError,
    DocumentProcessingError,
)
from services.document_service import DocumentService
from services.document_upload_service import DocumentUploadService
from services.folder_service import FolderService
from api.serializers.document_serializers import (
    DocumentSerializer,
    DocumentCreateSerializer,
    DocumentChunkSerializer,
    DocumentUploadSerializer,
    DocumentVersionUploadSerializer,
    DocumentPermissionListSerializer,
    SharedFolderWithDocumentsSerializer,
)
from api.serializers.folder_serializers import FolderPermissionSerializer

logger = logging.getLogger(__name__)


async def _async_file_chunks(file_object, chunk_size=64 * 1024):
    """Read file content without blocking the ASGI event loop."""
    while True:
        chunk = await asyncio.to_thread(file_object.read, chunk_size)
        if not chunk:
            break
        yield chunk


def _asgi_file_response(file_object, **kwargs):
    """Build a FileResponse backed by an asynchronous iterator under ASGI."""
    response = FileResponse(file_object, **kwargs)
    response.streaming_content = _async_file_chunks(file_object)
    return response


def _forbidden(message="You don't have the required document permission"):
    return Response(
        ResponseBuilder.error(message, status_code=403),
        status=status.HTTP_403_FORBIDDEN,
    )


DOCUMENT_MANAGE_PERMISSIONS = [
    PermissionCodes.DOCUMENT_SHARE,
    PermissionCodes.DOCUMENT_UPDATE,
    PermissionCodes.DOCUMENT_DELETE,
]


# ============================================================
# 1. Document List (GET) + Upload (POST)
# ============================================================

class DocumentListView(APIView):
    """
    API Endpoint: GET|POST /api/v1/documents
    
    GET: Get all accessible documents with pagination
    POST: Upload new document (handled by DocumentUploadView)
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request):
        """
        GET /api/v1/documents
        
        List all documents user can access (permission-filtered).
        
        Query Parameters:
        - page (int): Page number (default: 1)
        - page_size (int): Items per page (default: 20, max: 100)
        - folder_id (uuid): Filter by folder
        - status (str): Filter by status (pending, processing, completed, failed)
        - search (str): Search in original_name
        - sort (str): Sort field (default: created_at)
        
        Response:
        {
            "success": true,
            "status_code": 200,
            "data": [
                {
                    "id": "uuid",
                    "original_name": "report.pdf",
                    "file_type": "pdf",
                    "file_size": 1024,
                    "status": "completed",
                    "uploader_id": "uuid",
                    "folder_id": "uuid",
                    "created_at": "2024-04-14T10:30:00Z"
                }
            ],
            "pagination": {
                "page": 1,
                "page_size": 20,
                "total_items": 50,
                "total_pages": 3
            }
        }
        """
        try:
            if not user_has_permission(request.user, PermissionCodes.DOCUMENT_READ):
                return _forbidden("You need document_read permission to view documents")

            # Validate pagination params
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            if page < 1 or page_size < 1 or page_size > 100:
                return Response(
                    ResponseBuilder.error(
                        "Invalid pagination (page >= 1, 1 <= page_size <= 100)",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get filter params
            folder_id = request.query_params.get('folder_id', '').strip() or None
            doc_status = request.query_params.get('status', '').strip() or None
            search_query = request.query_params.get('search', '').strip() or None
            access_scope = request.query_params.get('access_scope', '').strip() or None
            sort_by = request.query_params.get('sort', 'created_at')
            include_versions = (
                request.query_params.get('include_versions', '').strip().lower()
                in {'1', 'true', 'yes'}
            )

            if access_scope and access_scope not in ['personal', 'department', 'company']:
                return Response(
                    ResponseBuilder.error(
                        "Invalid access_scope. Must be one of: personal, department, company",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Call service to get accessible documents
            service = DocumentService()
            result = service.list_accessible_documents(
                user_id=request.user.id,
                page=page,
                page_size=page_size,
                folder_id=folder_id,
                status=doc_status,
                search=search_query,
                access_scope=access_scope,
                sort_by=sort_by,
                include_versions=include_versions,
            )
            
            # Serialize response
            serializer = DocumentSerializer(result['documents'], many=True, context={'request': request})
            
            logger.info(f"User {request.user.id} listed {len(result['documents'])} documents")
            
            return Response(
                ResponseBuilder.paginated(
                    items=serializer.data,
                    page=result['pagination']['page'],
                    page_size=result['pagination']['page_size'],
                    total_items=result['pagination']['total']
                ),
                status=status.HTTP_200_OK
            )
        
        except ValueError as e:
            logger.warning(f"Invalid parameter: {e}")
            return Response(
                ResponseBuilder.error(f"Invalid parameter: {str(e)}", status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error listing documents: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to list documents", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SharedWithMeDocumentsView(APIView):
    """
    API Endpoint: GET /api/v1/documents/shared-with-me

    Return folders and documents explicitly shared to current user.

    Rules:
    - FolderPermission overrides access_scope for folder visibility.
    - If a folder is shared, documents inside that folder are also shared.
    - DocumentPermission shares only that specific document.
    - Explicit document deny still takes precedence.
    """

    permission_classes = [IsAuthenticatedUser]

    def get(self, request):
        try:
            if not user_has_permission(request.user, PermissionCodes.DOCUMENT_READ):
                return _forbidden("You need document_read permission to view shared documents")

            service = DocumentService()
            shared_data = service.get_shared_with_me_documents(user_id=str(request.user.id))

            folders_payload = SharedFolderWithDocumentsSerializer(
                shared_data['folders'],
                many=True,
                context={
                    'request': request,
                    'folder_documents_map': shared_data['folder_documents_map'],
                },
            ).data

            unfoldered_payload = DocumentSerializer(
                shared_data['unfoldered_documents'],
                many=True,
                context={'request': request},
            ).data

            result = {
                'folders': folders_payload,
                'unfoldered_documents': unfoldered_payload,
            }

            return Response(
                ResponseBuilder.success(
                    data=result,
                    message='Shared folders and documents retrieved successfully'
                ),
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error retrieving shared-with-me documents: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve shared-with-me documents", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 2. Document Upload (POST /api/v1/documents/upload)
# ============================================================

class DocumentUploadView(APIView):
    """
    API Endpoint: POST /api/v1/documents/upload

    Upload tài liệu nội bộ (multipart/form-data).

    Logic scoping tự động:
      - folder_id + folder.department  → doc thuộc folder + phòng ban đó  (Case A)
      - folder_id + folder không dept  → doc thuộc folder công ty           (Case B)
      - department_id (không folder)   → doc thuộc phòng ban, không folder  (Case C)
      - không folder, không dept       → tài liệu toàn công ty              (Case D)

    Pipeline sau khi lưu file:
      1. Parse text (PDF/DOCX/TXT/MD)
      2. Chunk văn bản
      3. Embed từng chunk → Qdrant + DocumentEmbedding
      4. Cập nhật Document.status = 'completed' | 'failed'
    """

    permission_classes = [IsAuthenticatedUser]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        """
        POST /api/v1/documents/upload

        Request (multipart/form-data):
          - file          : File cần upload (bắt buộc)
          - folder_id     : UUID folder đích (optional)
          - department_id : UUID phòng ban (optional, dùng khi không có folder)
          - access_scope  : 'personal'|'department'|'company' (optional)
          - description   : Mô tả tài liệu (optional)
          - tags          : Tags phân cách bằng dấu phẩy, vd 'hợp đồng,2024' (optional)

        Response 201:
        {
            "success": true,
            "data": {
                "id": "uuid",
                "original_name": "bao_cao_q1.pdf",
                "status": "completed",
                "access_scope": "department",
                "department": "uuid-dept",
                "folder": null,
                "chunk_count": 18
            }
        }
        """
        try:
            if not user_has_permission(request.user, PermissionCodes.DOCUMENT_CREATE):
                return _forbidden("You need document_create permission to upload documents")

            # ── Validate input ────────────────────────────────────────────────
            serializer = DocumentUploadSerializer(data={
                **request.POST.dict(),
                'file': request.FILES.get('file'),
            })
            if not serializer.is_valid():
                return Response(
                    ResponseBuilder.error(
                        f"Validation failed: {serializer.errors}",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )

            validated = serializer.validated_data
            file = validated['file']
            folder_id = str(validated['folder_id']) if validated.get('folder_id') else None
            department_id = str(validated['department_id']) if validated.get('department_id') else None
            access_scope = validated.get('access_scope')   # có thể None → auto-detect
            description = validated.get('description') or None
            tags = validated.get('tags')                    # đã được convert sang list trong serializer

            # ── Lấy department của user ───────────────────────────────────────
            user_department = None
            if hasattr(request.user, 'user_profile') and request.user.user_profile:
                user_department = request.user.user_profile.department

            # ── Auto-set access_scope cho user ───────────────────────────────
            if not folder_id and access_scope is None:
                # User upload không chỉ định folder và access_scope → mặc định department scope
                access_scope = 'department'
                if user_department:
                    department_id = str(user_department.id)
                else:
                    # User không có department → fallback to personal
                    access_scope = 'personal'
                    department_id = None

            # ── Kiểm tra quyền ghi trên folder (nếu có) ──────────────────────
            if folder_id:
                folder_service = FolderService()
                try:
                    is_admin = user_has_permission(request.user, PermissionCodes.SYSTEM_ADMIN)

                    has_perm = folder_service.check_folder_permission(
                        folder_id=folder_id,
                        user_id=request.user.id,
                        permission='write',
                    )
                    if not has_perm:
                        return Response(
                            ResponseBuilder.error(
                                "Bạn không có quyền ghi vào folder này",
                                status_code=403
                            ),
                            status=status.HTTP_403_FORBIDDEN
                        )
                    
                        # ── Validation: chỉ giới hạn user thường theo đúng department ──
                        # Admin đã được check_folder_permission() cho phép full quyền.
                        if not is_admin:
                            folder = folder_service.repository.get_by_id(folder_id)
                            if folder and folder.access_scope == 'department':
                                if not user_department or str(folder.department_id) != str(user_department.id):
                                    return Response(
                                        ResponseBuilder.error(
                                            "Bạn chỉ được upload tài liệu vào folder của phòng ban mình",
                                            status_code=403
                                        ),
                                        status=status.HTTP_403_FORBIDDEN
                                    )
                            
                except NotFoundError as e:
                    return Response(
                        ResponseBuilder.error(str(e), status_code=404),
                        status=status.HTTP_404_NOT_FOUND
                    )

            # ── Gọi DocumentUploadService ─────────────────────────────────────
            upload_service = DocumentUploadService()
            document = upload_service.upload(
                file=file,
                user_id=request.user.id,
                folder_id=folder_id,
                department_id=department_id,
                access_scope=access_scope,
                description=description,
                tags=tags,
                run_processing=True,   # parse + chunk + embed ngay
            )

            # ── Audit log ─────────────────────────────────────────────────────
            try:
                from services.audit_service import AuditService
                AuditService().log(
                    action='DOCUMENT_UPLOAD',
                    account=request.user,
                    resource_id=str(document.id),
                    resource_type='Document',
                    metadata={
                        'file_name': document.original_name,
                        'file_size': document.file_size,
                        'folder_id': folder_id,
                        'department_id': department_id,
                        'access_scope': document.access_scope,
                        'status': document.status,
                    }
                )
            except Exception as audit_err:
                logger.warning(f"Audit log failed (non-critical): {audit_err}")

            # ── Response ──────────────────────────────────────────────────────
            response_data = {
                'id': str(document.id),
                'original_name': document.original_name,
                'status': document.status,
                'file_size': document.file_size,
                'access_scope': document.access_scope,
                'department': str(document.department_id) if document.department_id and document.access_scope != 'personal' else None,
                'folder': str(document.folder_id) if document.folder_id else None,
                'chunk_count': document.chunks.filter(is_deleted=False).count(),
                'metadata': document.metadata,
            }

            logger.info(
                f"[Upload] User {request.user.id} uploaded '{document.original_name}' "
                f"→ {document.status} (scope={document.access_scope})"
            )

            return Response(
                ResponseBuilder.success(
                    data=response_data,
                    message=f"Tài liệu đã được upload và xử lý ({document.status})",
                    status_code=201
                ),
                status=status.HTTP_201_CREATED
            )

        except FileSizeExceededError as e:
            logger.warning(f"File size exceeded: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=413),
                status=status.HTTP_413_PAYLOAD_TOO_LARGE
            )
        except ValidationError as e:
            logger.warning(f"Validation error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except (ParseError, UnsupportedMediaType) as e:
            logger.warning(f"Invalid upload request payload: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error uploading document: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error(f"Upload thất bại: {str(e)}", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DocumentVersionListCreateView(APIView):
    """List document history or upload a new immutable version."""

    permission_classes = [IsAuthenticatedUser]
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request, doc_id):
        try:
            DocumentService().get_document_detail(
                doc_id,
                request.user.id,
                permission_required='read',
            )
            from services.document_version_service import DocumentVersionService

            versions = DocumentVersionService().list_versions(str(doc_id))
            payload = DocumentSerializer(
                versions,
                many=True,
                context={'request': request},
            ).data
            return Response(
                ResponseBuilder.success(data=payload),
                status=status.HTTP_200_OK,
            )
        except NotFoundError as exc:
            return Response(ResponseBuilder.error(str(exc), status_code=404), status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as exc:
            return Response(ResponseBuilder.error(str(exc), status_code=403), status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            logger.error("Error listing document versions: %s", exc, exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to list document versions", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request, doc_id):
        try:
            serializer = DocumentVersionUploadSerializer(data={
                **request.POST.dict(),
                'file': request.FILES.get('file'),
            })
            if not serializer.is_valid():
                return Response(
                    ResponseBuilder.error(
                        f"Validation failed: {serializer.errors}",
                        status_code=400,
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            from services.document_version_service import DocumentVersionService

            document = DocumentVersionService().create_version(
                base_document_id=str(doc_id),
                file=serializer.validated_data['file'],
                user_id=request.user.id,
                expected_version_lock=serializer.validated_data.get('version_lock'),
                change_summary=serializer.validated_data.get('change_summary') or '',
                update_mode=serializer.validated_data.get('update_mode') or 'auto',
            )
            payload = DocumentSerializer(document, context={'request': request}).data
            return Response(
                ResponseBuilder.success(
                    data=payload,
                    message="New document version queued for processing",
                    status_code=202,
                ),
                status=status.HTTP_202_ACCEPTED,
            )
        except (ValidationError, FileSizeExceededError) as exc:
            return Response(ResponseBuilder.error(str(exc), status_code=400), status=status.HTTP_400_BAD_REQUEST)
        except BusinessLogicError as exc:
            return Response(ResponseBuilder.error(str(exc), status_code=409), status=status.HTTP_409_CONFLICT)
        except NotFoundError as exc:
            return Response(ResponseBuilder.error(str(exc), status_code=404), status=status.HTTP_404_NOT_FOUND)
        except PermissionDeniedError as exc:
            return Response(ResponseBuilder.error(str(exc), status_code=403), status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            logger.error("Error creating document version: %s", exc, exc_info=True)
            return Response(
                ResponseBuilder.error(f"Version upload failed: {exc}", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================
# 3. Document Detail (GET)
# ============================================================

class DocumentDetailView(APIView):
    """
    API Endpoint: GET|PUT|DELETE /api/v1/documents/{doc_id}
    
    GET: Get document metadata
    PUT: Update document metadata
    DELETE: Soft delete document
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request, doc_id):
        """
        GET /api/v1/documents/{doc_id}
        
        Get document details.
        
        Permission Check: User must have READ permission on document.
        
        Response:
        {
            "success": true,
            "data": {
                "id": "uuid",
                "original_name": "report.pdf",
                "file_type": "pdf",
                "file_size": 1024,
                "status": "completed",
                "uploader_id": "uuid",
                "folder_id": "uuid",
                "chunk_count": 5,
                "created_at": "2024-04-14T10:30:00Z"
            }
        }
        """
        try:
            if not user_has_permission(request.user, PermissionCodes.DOCUMENT_READ):
                return _forbidden("You need document_read permission to view documents")

            service = DocumentService()
            
            # Get document with permission check
            document = service.get_document_detail(
                doc_id=doc_id,
                user_id=request.user.id,
                permission_required='read'
            )
            
            serializer = DocumentSerializer(document, context={'request': request})
            
            logger.info(f"User {request.user.id} retrieved document {doc_id}")
            
            return Response(
                ResponseBuilder.success(data=serializer.data),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error retrieving document: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve document", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 4. Document Update (PUT)
# ============================================================

class DocumentUpdateView(APIView):
    """
    API Endpoint: PUT /api/v1/documents/{doc_id}
    
    Update document metadata.
    
    Permission Check: User must have WRITE permission on document.
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def put(self, request, doc_id):
        """
        PUT /api/v1/documents/{doc_id}
        
        Update document metadata.
        
        Request:
        {
            "description": "New description",
            "tags": ["tag1", "tag2"],
            "access_scope": "department"
        }
        """
        try:
            if not user_has_any_permission(
                request.user,
                [PermissionCodes.DOCUMENT_UPDATE, PermissionCodes.DOCUMENT_WRITE],
            ):
                return _forbidden("You need document_update permission to update documents")

            # Validate input
            serializer = DocumentCreateSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                logger.warning(f"Invalid document update: {serializer.errors}")
                return Response(
                    ResponseBuilder.error(
                        f"Validation failed: {serializer.errors}",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            service = DocumentService()
            
            # Update with transaction
            with transaction.atomic():
                document = service.update_document(
                    doc_id=doc_id,
                    user_id=request.user.id,
                    **serializer.validated_data
                )
            
            response_serializer = DocumentSerializer(document, context={'request': request})
            
            logger.info(f"Document updated by {request.user.id}: {doc_id}")
            
            return Response(
                ResponseBuilder.success(
                    data=response_serializer.data,
                    message="Document updated successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error updating document: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to update document", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 4B. Document Move (PATCH)
# ============================================================

class DocumentMoveView(APIView):
    """
    API Endpoint: PATCH /api/v1/documents/{doc_id}/move
    
    Move document to a different folder (or root if new_folder_id=None).
    When moved, document inherits access_scope and department from target folder.
    
    Permission Check: User must have WRITE permission on document.
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def patch(self, request, doc_id):
        """
        PATCH /api/v1/documents/{doc_id}/move
        
        Move document to target folder.
        
        Request:
        {
            "folder_id": "uuid-folder" (optional, null to move to root)
        }
        
        Response:
        {
            "success": true,
            "data": {
                "id": "uuid-doc",
                "folder_id": "uuid-folder",
                "access_scope": "department",  // ← inherited from folder
                "department_id": "uuid-dept",   // ← inherited from folder
                ...
            }
        }
        """
        try:
            if not user_has_any_permission(
                request.user,
                [PermissionCodes.DOCUMENT_UPDATE, PermissionCodes.DOCUMENT_WRITE],
            ):
                return _forbidden("You need document_update permission to move documents")

            # Get folder_id from request (can be null to move to root)
            new_folder_id = request.data.get('folder_id', None)
            
            service = DocumentService()
            
            # Move with transaction
            with transaction.atomic():
                document = service.move_document(
                    doc_id=doc_id,
                    user_id=request.user.id,
                    new_folder_id=new_folder_id
                )
            
            response_serializer = DocumentSerializer(document, context={'request': request})
            
            logger.info(f"Document moved by {request.user.id}: {doc_id} to folder {new_folder_id or 'root'}")
            
            return Response(
                ResponseBuilder.success(
                    data=response_serializer.data,
                    message="Document moved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error moving document: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to move document", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 5. Document Delete (DELETE)
# ============================================================

class DocumentDeleteView(APIView):
    """
    API Endpoint: DELETE /api/v1/documents/{doc_id}
    
    Soft delete document and sync with Qdrant.
    
    Permission Check: User must have DELETE permission on document.
    
    Side Effects:
    - Sets document.is_deleted = True
    - Sets document.chunks[].is_deleted = True
    - Removes vectors from Qdrant
    - Invalidates permission cache
    - Audit log
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def delete(self, request, doc_id):
        """
        DELETE /api/v1/documents/{doc_id}
        
        Soft delete document (mark as deleted, don't remove from DB).
        """
        try:
            service = DocumentService()
            
            # Delete with transaction
            with transaction.atomic():
                service.delete_document(
                    document_id=doc_id,
                    user_id=request.user.id,
                )
            
            logger.info(f"Document deleted by {request.user.id}: {doc_id}")
            
            return Response(
                ResponseBuilder.success(
                    message="Document deleted successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error deleting document: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to delete document", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 6. Document Download (GET)
# ============================================================

class DocumentDownloadView(APIView):
    """
    API Endpoint: GET /api/v1/documents/{doc_id}/download
    
    Download original file.
    
    Permission Check: User must have READ permission on document.
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request, doc_id):
        """
        GET /api/v1/documents/{doc_id}/download
        
        Download file.
        
        Returns:
        - Binary file data with proper Content-Type headers
        """
        try:
            if not user_has_permission(request.user, PermissionCodes.DOCUMENT_DOWNLOAD):
                return _forbidden("You need document_download permission to download documents")

            service = DocumentService()
            
            # Get document with permission check
            file_data = service.get_document_download(
                doc_id=doc_id,
                user_id=request.user.id,
            )
            
            # Log download action
            from services.audit_service import AuditService
            audit_service = AuditService()
            audit_service.log(
                action='DOCUMENT_DOWNLOAD',
                account=request.user,
                resource_id=doc_id,
                resource_type='Document',
            )
            
            logger.info(f"User {request.user.id} downloaded document {doc_id}")
            
            # Return file response using FileResponse to avoid JSON encoding binary data
            file_stream = io.BytesIO(file_data['content'])
            response = _asgi_file_response(
                file_stream,
                as_attachment=True,
                filename=file_data['filename'],
                content_type=file_data.get('mime_type', 'application/octet-stream')
            )
            return response
        
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error downloading document: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to download document", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 6b. Document Preview (GET)
# ============================================================

class DocumentPreviewView(APIView):
    """
    API Endpoint: GET /api/v1/documents/{doc_id}/preview

    Return a browser-previewable file.
    Word documents are served as cached PDF preview for page-accurate citations.
    """
    permission_classes = [IsAuthenticatedUser]

    def get(self, request, doc_id):
        try:
            if not user_has_permission(request.user, PermissionCodes.DOCUMENT_READ):
                return _forbidden("You need document_read permission to preview documents")

            service = DocumentService()

            if request.query_params.get('format') == 'html':
                html = service.get_document_preview_html(
                    doc_id=doc_id,
                    user_id=request.user.id,
                )

                return Response(
                    ResponseBuilder.success(
                        data={'html': html},
                        message='Preview HTML generated successfully',
                        status_code=200
                    ),
                    status=status.HTTP_200_OK
                )

            file_ref = service.get_document_preview_file_reference(
                doc_id=doc_id,
                user_id=request.user.id,
            )

            response = _asgi_file_response(
                open(file_ref['path'], 'rb'),
                as_attachment=False,
                filename=file_ref['filename'],
                content_type=file_ref.get('mime_type', 'application/octet-stream'),
            )
            response['X-Document-Preview-Mode'] = file_ref.get('preview_mode', 'original')
            return response

        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except DocumentProcessingError as e:
            logger.error(f"Error generating preview: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error(str(e), status_code=422),
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except Exception as e:
            logger.error(f"Error generating document preview: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to generate document preview", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DocumentChunkSourceView(APIView):
    """
    API Endpoint: GET /api/v1/documents/{doc_id}/chunks/{chunk_id}

    Return the exact stored chunk behind a citation so the viewer can anchor
    by document/chunk/page metadata before falling back to visual text matching.
    """
    permission_classes = [IsAuthenticatedUser]

    def get(self, request, doc_id, chunk_id):
        try:
            if not user_has_permission(request.user, PermissionCodes.DOCUMENT_READ):
                return _forbidden("You need document_read permission to view document chunks")

            service = DocumentService()
            chunk = service.get_document_chunk_source(
                doc_id=doc_id,
                chunk_id=chunk_id,
                user_id=request.user.id,
            )

            return Response(
                ResponseBuilder.success(
                    data=chunk,
                    message='Document chunk loaded successfully',
                    status_code=200
                ),
                status=status.HTTP_200_OK
            )

        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error loading document chunk source: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to load document chunk", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 7. Document Permissions (GET|POST)
# ============================================================


class DocumentPermissionsListView(APIView):
    """
    API Endpoint: GET /api/v1/documents/permissions

    Return a paginated list of documents with their ACL entries.
    """

    permission_classes = [IsAuthenticatedUser]

    def get(self, request):
        try:
            if not user_has_any_permission(request.user, DOCUMENT_MANAGE_PERMISSIONS):
                return _forbidden("You need document management permission to view document permissions")

            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            search = request.query_params.get('search')
            granted_by_id = request.query_params.get('granted_by_id')

            if page < 1 or page_size < 1 or page_size > 100:
                return Response(
                    ResponseBuilder.error(
                        "Invalid pagination (page >= 1, 1 <= page_size <= 100)",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            service = DocumentService()
            result = service.list_document_permissions(
                user_id=request.user.id,
                page=page,
                page_size=page_size,
                search=search,
                granted_by_id=granted_by_id,
            )

            serialized_items = DocumentPermissionListSerializer(result['items'], many=True).data

            return Response(
                ResponseBuilder.paginated(
                    items=serialized_items,
                    page=page,
                    page_size=page_size,
                    total_items=result['pagination']['total_items'],
                    message="Document permissions retrieved",
                ),
                status=status.HTTP_200_OK,
            )

        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error retrieving document permissions list: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve document permissions", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class DocumentPermissionsView(APIView):
    """
    API Endpoint: GET|POST /api/v1/documents/{doc_id}/permissions
    
    GET: List document ACL (permissions)
    POST: Grant document permission to account/role
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request, doc_id):
        """
        GET /api/v1/documents/{doc_id}/permissions
        
        List all permissions on document.
        
        Permission Check: Admin or document owner only.
        
        Response:
        {
            "success": true,
            "data": [
                {
                    "id": "uuid",
                    "subject_type": "role",
                    "subject_id": "uuid",
                    "subject_name": "Manager",
                    "permission": "read",
                    "precedence": "inherit"
                }
            ]
        }
        """
        try:
            if not user_has_any_permission(request.user, DOCUMENT_MANAGE_PERMISSIONS):
                return _forbidden("You need document management permission to view document permissions")

            service = DocumentService()
            granted_by_id = request.query_params.get('granted_by_id')
            
            permissions = service.get_document_permissions(
                doc_id=doc_id,
                user_id=request.user.id,
                granted_by_id=granted_by_id,
            )
            
            serializer = FolderPermissionSerializer(permissions, many=True)
            
            logger.info(f"User {request.user.id} listed permissions for document {doc_id}")
            
            return Response(
                ResponseBuilder.success(data=serializer.data),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error listing permissions: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to list permissions", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, doc_id):
        """
        POST /api/v1/documents/{doc_id}/permissions
        
        Grant permission on document.
        
        Request:
        {
            "subject_type": "account",  # "account" or "role"
            "subject_id": "uuid",       # UUID or ID for account/role
            "permission": "read",       # "read", "write", "delete"
            "precedence": "inherit"     # "inherit", "override", "deny"
        }
        """
        try:
            if not user_has_permission(request.user, PermissionCodes.DOCUMENT_SHARE):
                return _forbidden("You need document_share permission to grant document permissions")

            # Validate input
            serializer = FolderPermissionSerializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"Invalid permission grant: {serializer.errors}")
                return Response(
                    ResponseBuilder.error(
                        f"Validation failed: {serializer.errors}",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            service = DocumentService()
            
            # Grant permission with transaction
            with transaction.atomic():
                permission = service.grant_document_permission(
                    doc_id=doc_id,
                    user_id=request.user.id,
                    subject_type=serializer.validated_data['subject_type'],
                    subject_id=serializer.validated_data['subject_id'],
                    permission=serializer.validated_data['permission'],
                    precedence=serializer.validated_data.get('precedence', 'inherit'),
                )
            
            response_serializer = FolderPermissionSerializer(permission)
            
            logger.info(f"Permission granted by {request.user.id} on document {doc_id}")
            
            return Response(
                ResponseBuilder.success(
                    data=response_serializer.data,
                    message="Permission granted successfully",
                    status_code=201
                ),
                status=status.HTTP_201_CREATED
            )
        
        except ValidationError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error granting permission: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to grant permission", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 8. Document Permission Detail (DELETE)
# ============================================================

class DocumentPermissionDetailView(APIView):
    """
    API Endpoint: DELETE /api/v1/documents/{doc_id}/permissions/{subject_type}/{subject_id}/{permission}
    
    Revoke specific permission from document.
    
    Example:
    DELETE /api/v1/documents/uuid/permissions/role/uuid-role/read
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def delete(self, request, doc_id, subject_type, subject_id, permission):
        """
        DELETE /api/v1/documents/{doc_id}/permissions/{subject_type}/{subject_id}/{permission}
        
        Revoke permission.
        
        Parameters:
        - subject_type: "account" or "role"
        - subject_id: UUID or ID of account/role
        - permission: "read", "write", or "delete"
        """
        try:
            if not user_has_permission(request.user, PermissionCodes.DOCUMENT_SHARE):
                return _forbidden("You need document_share permission to revoke document permissions")

            service = DocumentService()
            
            # Revoke permission with transaction
            with transaction.atomic():
                service.revoke_document_permission(
                    doc_id=doc_id,
                    user_id=request.user.id,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    permission=permission,
                )
            
            logger.info(f"Permission revoked by {request.user.id} on document {doc_id}")
            
            return Response(
                ResponseBuilder.success(
                    message="Permission revoked successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error revoking permission: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to revoke permission", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 9. Document Status (GET)
# ============================================================

class DocumentStatusView(APIView):
    """
    API Endpoint: GET /api/v1/documents/{doc_id}/status
    
    Get document processing status.
    
    Permission Check: User must have READ permission on document.
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request, doc_id):
        """
        GET /api/v1/documents/{doc_id}/status
        
        Get document and chunks processing status.
        
        Response:
        {
            "success": true,
            "data": {
                "document_id": "uuid",
                "document_status": "completed",
                "document_error": null,
                "chunk_processing_status": {
                    "total_chunks": 5,
                    "completed_chunks": 5,
                    "failed_chunks": 0,
                    "pending_chunks": 0
                },
                "estimated_completion": "2024-04-14T10:30:00Z"
            }
        }
        """
        try:
            if not user_has_permission(request.user, PermissionCodes.DOCUMENT_READ):
                return _forbidden("You need document_read permission to view document status")

            service = DocumentService()
            
            status_info = service.get_document_processing_status(
                doc_id=doc_id,
                user_id=request.user.id,
            )
            
            logger.info(f"User {request.user.id} checked status for document {doc_id}")
            
            return Response(
                ResponseBuilder.success(data=status_info),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error getting status: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to get status", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 10. Document Reprocess (POST)
# ============================================================

class DocumentReprocessView(APIView):
    """
    API Endpoint: POST /api/v1/documents/{doc_id}/reprocess
    
    Re-index document (submit new INDEX_DOCUMENT AsyncTask).
    
    Permission Check: User must have WRITE permission on document.
    
    Use Case:
    - Re-index after manual edits
    - Fix failed processing
    - Change embedding model
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def post(self, request, doc_id):
        """
        POST /api/v1/documents/{doc_id}/reprocess
        
        Reprocess document chunks and embeddings.
        
        Request (optional):
        {
            "chunking_strategy": "recursive_character_1000_200",
            "embedding_model": "mistral-embed"
        }
        
        Response:
        {
            "success": true,
            "message": "Document reprocessing queued",
            "data": {
                "document_id": "uuid",
                "status": "processing"
            }
        }
        """
        try:
            if not user_has_any_permission(
                request.user,
                [PermissionCodes.DOCUMENT_UPDATE, PermissionCodes.DOCUMENT_WRITE],
            ):
                return _forbidden("You need document_update permission to reprocess documents")
            if not user_has_permission(request.user, PermissionCodes.EMBEDDING_GENERATE):
                return _forbidden("You need embedding_generate permission to reprocess documents")

            # Get optional parameters
            chunking_strategy = request.data.get('chunking_strategy')
            embedding_model = request.data.get('embedding_model')
            
            service = DocumentService()
            
            # Reprocess with transaction
            with transaction.atomic():
                document = service.reprocess_document(
                    doc_id=doc_id,
                    user_id=request.user.id,
                    chunking_strategy=chunking_strategy,
                    embedding_model=embedding_model,
                )
            
            logger.info(f"Document reprocessing started by {request.user.id}: {doc_id}")
            
            return Response(
                ResponseBuilder.success(
                    data={
                        'document_id': str(document.id),
                        'status': document.status,
                    },
                    message="Document reprocessing queued successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except ValidationError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            logger.warning(f"Permission denied for user {request.user.id}: {str(e)}")
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Error reprocessing document: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to reprocess document", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
