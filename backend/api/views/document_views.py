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
from django.db import transaction
import logging

from core.permissions.drf_permissions import IsAuthenticatedUser
from core.utils.response_builder import ResponseBuilder
from core.exceptions import (
    ValidationError,
    NotFoundError,
    BusinessLogicError,
    PermissionDeniedError,
    FileSizeExceededError,
)
from services.document_service import DocumentService
from services.folder_service import FolderService
from api.serializers.document_serializers import (
    DocumentSerializer,
    DocumentCreateSerializer,
    DocumentChunkSerializer,
)
from api.serializers.folder_serializers import FolderPermissionSerializer

logger = logging.getLogger(__name__)


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
            sort_by = request.query_params.get('sort', 'created_at')
            
            # Call service to get accessible documents
            service = DocumentService()
            result = service.list_accessible_documents(
                user_id=request.user.id,
                page=page,
                page_size=page_size,
                folder_id=folder_id,
                status=doc_status,
                search=search_query,
                sort_by=sort_by,
            )
            
            # Serialize response
            serializer = DocumentSerializer(result['documents'], many=True)
            
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


# ============================================================
# 2. Document Upload (POST /api/v1/documents/upload)
# ============================================================

class DocumentUploadView(APIView):
    """
    API Endpoint: POST /api/v1/documents/upload
    
    Upload file and trigger async indexing.
    
    CRITICAL ENDPOINT - Complex business logic:
    1. Validate file type & size
    2. Check folder permission (write)
    3. Save file to uploads/ directory
    4. Create Document record (status='pending')
    5. Auto-create DocumentPermission for uploader
    6. Submit AsyncTask for INDEX_DOCUMENT
    7. Write AuditLog
    8. Return doc_id + status='pending'
    """
    
    permission_classes = [IsAuthenticatedUser]
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        """
        POST /api/v1/documents/upload
        
        Upload file with metadata.
        
        Request:
        - file (required): File to upload
        - folder_id (optional): Target folder
        - tags (optional): Comma-separated tags
        - description (optional): Document description
        
        Response:
        {
            "success": true,
            "status_code": 201,
            "message": "Document uploaded successfully",
            "data": {
                "id": "uuid",
                "original_name": "report.pdf",
                "status": "pending",
                "processing_status": "pending"
            }
        }
        """
        try:
            # 1. Validate file provided
            if 'file' not in request.FILES:
                return Response(
                    ResponseBuilder.error("File is required", status_code=400),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file = request.FILES['file']
            
            # 2. Get optional parameters
            folder_id = request.POST.get('folder_id', '').strip() or None
            tags = request.POST.get('tags', '').split(',') if request.POST.get('tags') else []
            description = request.POST.get('description', '').strip() or None
            
            # 3. Validate via serializer
            serializer = DocumentCreateSerializer(data={
                'original_name': file.name,
                'file': file,
                'folder_id': folder_id,
                'description': description,
                'tags': tags,
            })
            
            if not serializer.is_valid():
                logger.warning(f"Invalid document upload: {serializer.errors}")
                return Response(
                    ResponseBuilder.error(
                        f"Validation failed: {serializer.errors}",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 4. Check folder permission if folder_id provided
            if folder_id:
                folder_service = FolderService()
                try:
                    # Check user has write permission on folder
                    has_permission = folder_service.check_folder_permission(
                        folder_id=folder_id,
                        user_id=request.user.id,
                        permission_required='write'
                    )
                    if not has_permission:
                        logger.warning(f"User {request.user.id} lacks write permission on folder {folder_id}")
                        return Response(
                            ResponseBuilder.error(
                                f"You don't have write permission on this folder",
                                status_code=403
                            ),
                            status=status.HTTP_403_FORBIDDEN
                        )
                except NotFoundError as e:
                    return Response(
                        ResponseBuilder.error(str(e), status_code=404),
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # 5. Call service with transaction
            service = DocumentService()
            
            with transaction.atomic():
                document = service.upload_document(
                    file=file,
                    user_id=request.user.id,
                    folder_id=folder_id,
                    description=description,
                    tags=tags,
                )
                
                # 6. Log upload action
                from services.audit_service import AuditService
                audit_service = AuditService()
                audit_service.log(
                    action='DOCUMENT_UPLOAD',
                    account=request.user,
                    resource_id=str(document.id),
                    resource_type='Document',
                    metadata={
                        'file_name': document.original_name,
                        'file_size': document.file_size,
                        'folder_id': str(folder_id) if folder_id else None,
                    }
                )
            
            # 7. Serialize response
            response_data = {
                'id': str(document.id),
                'original_name': document.original_name,
                'status': document.status,
                'file_size': document.file_size,
            }
            
            logger.info(f"Document uploaded by {request.user.id}: {document.id}")
            
            return Response(
                ResponseBuilder.success(
                    data=response_data,
                    message="Document uploaded successfully and queued for processing",
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
        except Exception as e:
            logger.error(f"Error uploading document: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to upload document", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            service = DocumentService()
            
            # Get document with permission check
            document = service.get_document_detail(
                doc_id=doc_id,
                user_id=request.user.id,
                permission_required='read'
            )
            
            serializer = DocumentSerializer(document)
            
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
            
            response_serializer = DocumentSerializer(document)
            
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
            
            # Return file response
            response = Response(
                file_data['content'],
                status=status.HTTP_200_OK
            )
            response['Content-Type'] = file_data.get('mime_type', 'application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{file_data["filename"]}"'
            
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
# 7. Document Permissions (GET|POST)
# ============================================================

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
            service = DocumentService()
            
            permissions = service.get_document_permissions(
                doc_id=doc_id,
                user_id=request.user.id,
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
