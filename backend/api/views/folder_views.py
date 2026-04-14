"""
Folder Views - API Endpoints cho Folder Management
Phase 4A - 8 endpoints

Endpoints:
1. GET    /api/v1/folders              - Tree structure
2. POST   /api/v1/folders              - Create
3. PUT    /api/v1/folders/{id}         - Update
4. DELETE /api/v1/folders/{id}         - Delete (recursive)
5. PATCH  /api/v1/folders/{id}/move    - Move to parent
6. GET    /api/v1/folders/{id}/permissions - View ACL (TODO)
7. POST   /api/v1/folders/{id}/permissions - Grant ACL (TODO)
8. DELETE /api/v1/folders/{id}/permissions/{perm_id} - Revoke ACL (TODO)

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
from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.views import APIView
from django.db import transaction
import logging

from core.permissions.drf_permissions import IsAuthenticatedUser
from core.utils.response_builder import ResponseBuilder
from core.exceptions import (
    ValidationError,
    NotFoundError,
    BusinessLogicError,
    PermissionDeniedError,
)
from services.folder_service import FolderService
from api.serializers.folder_serializers import (
    FolderTreeSerializer,
    FolderDetailSerializer,
    FolderCreateSerializer,
    FolderUpdateSerializer,
    FolderMoveSerializer,
    FolderListSerializer,
    FolderPermissionSerializer,
)

logger = logging.getLogger(__name__)


# ============================================================
# 1. Folder List (GET) + Create (POST)
# ============================================================

class FolderListCreateView(APIView):
    """
    API Endpoint: GET|POST /api/v1/folders
    
    GET: Get all accessible folders in tree structure
    POST: Create new folder
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request):
        """
        GET /api/v1/folders
        
        Get folder tree structure.
        User only sees folders they're allowed to access (based on access_scope).
        
        Query Parameters (optional):
        - format: 'tree' (default) or 'flat'
        
        Response:
        {
            "success": true,
            "data": [
                {
                    "id": "uuid-1",
                    "name": "Projects",
                    "access_scope": "company",
                    "sub_folders": [...]
                    ...
                }
            ]
        }
        """
        try:
            service = FolderService()
            
            # Get folder tree
            folder_tree = service.get_folder_tree(
                user_id=str(request.user.id),
                include_deleted=False
            )
            
            logger.info(f"User {request.user.id} retrieved folder tree ({len(folder_tree)} root folders)")
            
            return Response(
                ResponseBuilder.success(
                    data=folder_tree,
                    message="Folder tree retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except BusinessLogicError as e:
            logger.warning(f"Business logic error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error retrieving folder tree: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve folder tree", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def post(self, request):
        """
        POST /api/v1/folders
        
        Create new folder.
        
        Request Body:
        {
            "name": "My Project",
            "description": "Project description",
            "parent_id": "uuid-parent" (optional),
            "access_scope": "company" (optional, default='company'),
            "department_id": "uuid-dept" (optional)
        }
        
        Response:
        {
            "success": true,
            "status_code": 201,
            "message": "Folder created successfully",
            "data": {
                "id": "uuid-new",
                "name": "My Project",
                ...
            }
        }
        """
        try:
            # Validate input
            serializer = FolderCreateSerializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"Invalid folder creation request: {serializer.errors}")
                return Response(
                    ResponseBuilder.error(
                        f"Validation failed: {serializer.errors}",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call service
            service = FolderService()
            folder = service.create_folder(
                name=serializer.validated_data.get('name'),
                user_id=str(request.user.id),
                parent_id=serializer.validated_data.get('parent_id'),
                description=serializer.validated_data.get('description'),
                access_scope=serializer.validated_data.get('access_scope', 'company'),
                department_id=serializer.validated_data.get('department_id'),
            )
            
            # Serialize response
            response_serializer = FolderDetailSerializer(folder)
            
            logger.info(f"Folder created by {request.user.id}: {folder.name}")
            
            return Response(
                ResponseBuilder.success(
                    data=response_serializer.data,
                    message="Folder created successfully",
                    status_code=201
                ),
                status=status.HTTP_201_CREATED
            )
        
        except ValidationError as e:
            logger.warning(f"Validation error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except NotFoundError as e:
            logger.warning(f"Not found error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except BusinessLogicError as e:
            logger.warning(f"Business logic error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating folder: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to create folder", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 2. Folder Detail (GET) + Update (PUT) + Delete (DELETE)
# ============================================================

class FolderDetailView(APIView):
    """
    API Endpoint: GET|PUT|DELETE /api/v1/folders/{folder_id}
    
    GET: Get folder details
    PUT: Update folder info
    DELETE: Delete folder (recursive soft delete)
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request, folder_id):
        """
        GET /api/v1/folders/{folder_id}
        
        Get detailed folder information.
        
        Response:
        {
            "success": true,
            "data": {
                "id": "uuid",
                "name": "Project X",
                "subfolder_count": 3,
                "document_count": 15,
                ...
            }
        }
        """
        try:
            service = FolderService()
            repo = service.repository
            
            folder = repo.get_by_id(folder_id)
            if not folder:
                return Response(
                    ResponseBuilder.error(f"Folder {folder_id} not found", status_code=404),
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # TODO: Check user has read permission on folder
            # For now: assume all authenticated users can view
            
            serializer = FolderDetailSerializer(folder)
            
            logger.info(f"User {request.user.id} retrieved folder {folder_id}")
            
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message="Folder details retrieved"
                ),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving folder: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve folder", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def put(self, request, folder_id):
        """
        PUT /api/v1/folders/{folder_id}
        
        Update folder information.
        
        Request Body:
        {
            "name": "New Name",
            "description": "New Description",
            "access_scope": "department",
            "department_id": "uuid-dept"
        }
        """
        try:
            # Validate input
            serializer = FolderUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                logger.warning(f"Invalid folder update request: {serializer.errors}")
                return Response(
                    ResponseBuilder.error(
                        f"Validation failed: {serializer.errors}",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call service
            service = FolderService()
            folder = service.update_folder(
                folder_id=folder_id,
                user_id=str(request.user.id),
                **serializer.validated_data
            )
            
            # Serialize response
            response_serializer = FolderDetailSerializer(folder)
            
            logger.info(f"Folder updated by {request.user.id}: {folder_id}")
            
            return Response(
                ResponseBuilder.success(
                    data=response_serializer.data,
                    message="Folder updated successfully"
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
        except BusinessLogicError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error updating folder: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to update folder", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def delete(self, request, folder_id):
        """
        DELETE /api/v1/folders/{folder_id}
        
        Delete folder (soft delete - recursive).
        This will also soft-delete all sub-folders and documents inside.
        
        Response:
        {
            "success": true,
            "status_code": 204
        }
        """
        try:
            service = FolderService()
            
            # Delete folder (with cascade)
            service.delete_folder_recursive(
                folder_id=folder_id,
                user_id=str(request.user.id),
            )
            
            logger.info(f"Folder deleted by {request.user.id}: {folder_id}")
            
            return Response(
                ResponseBuilder.success(
                    data=None,
                    message="Folder deleted successfully"
                ),
                status=status.HTTP_204_NO_CONTENT
            )
        
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDeniedError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=403),
                status=status.HTTP_403_FORBIDDEN
            )
        except BusinessLogicError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error deleting folder: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to delete folder", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 3. Move Folder (PATCH)
# ============================================================

class FolderMoveView(APIView):
    """
    API Endpoint: PATCH /api/v1/folders/{folder_id}/move
    
    Move folder to different parent (or root if new_parent_id=null)
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    @transaction.atomic
    def patch(self, request, folder_id):
        """
        PATCH /api/v1/folders/{folder_id}/move
        
        Move folder to different parent.
        
        Request Body:
        {
            "new_parent_id": "uuid-parent" (or null to make root)
        }
        
        Response:
        {
            "success": true,
            "data": {
                "id": "uuid",
                "parent_id": "uuid-parent",
                ...
            }
        }
        """
        try:
            # Validate input
            serializer = FolderMoveSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    ResponseBuilder.error(
                        f"Validation failed: {serializer.errors}",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call service
            service = FolderService()
            folder = service.move_folder(
                folder_id=folder_id,
                new_parent_id=serializer.validated_data.get('new_parent_id'),
                user_id=str(request.user.id),
            )
            
            # Serialize response
            response_serializer = FolderDetailSerializer(folder)
            
            logger.info(f"Folder moved by {request.user.id}: {folder_id}")
            
            return Response(
                ResponseBuilder.success(
                    data=response_serializer.data,
                    message="Folder moved successfully"
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
        except BusinessLogicError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error moving folder: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to move folder", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================
# 4. Folder Permissions (GET/POST/DELETE)
# ============================================================

class FolderPermissionsView(APIView):
    """
    API Endpoint: GET|POST|DELETE /api/v1/folders/{folder_id}/permissions
    
    Manage folder ACL (access control lists)
    
    NOTE: These are placeholder implementations.
    Full ACL system will be implemented when integrating with
    FolderPermission model.
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request, folder_id):
        """
        GET /api/v1/folders/{folder_id}/permissions
        
        View all permissions (ACL) for a folder.
        
        Response:
        {
            "success": true,
            "data": {
                "folder_id": "uuid",
                "folder_name": "My Folder",
                "access_scope": "company",
                "permissions": [
                    {
                        "id": "perm-uuid",
                        "subject_type": "account",
                        "subject_id": "user-uuid",
                        "subject_name": "john.doe",
                        "permission": "read",
                        "is_active": true,
                        "created_at": "2026-04-14T..."
                    },
                    {
                        "id": "perm-uuid-2",
                        "subject_type": "role",
                        "subject_id": "role-uuid",
                        "subject_name": "Editor",
                        "permission": "write",
                        "is_active": true,
                        "created_at": "2026-04-14T..."
                    }
                ],
                "total_permissions": 2
            }
        }
        """
        try:
            service = FolderService()
            
            # Get folder permissions
            data = service.get_folder_permissions(folder_id)
            
            logger.info(f"User {request.user.id} viewed permissions for folder {folder_id}")
            
            return Response(
                ResponseBuilder.success(
                    data=data,
                    message="Folder permissions retrieved"
                ),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving folder permissions: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve permissions", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def post(self, request, folder_id):
        """
        POST /api/v1/folders/{folder_id}/permissions
        
        Grant access to folder for account or role.
        
        Request Body:
        {
            "subject_type": "account" | "role",
            "subject_id": "uuid",
            "permission": "read" | "write" | "delete"
        }
        
        Response: Permission granted
        {
            "success": true,
            "data": {
                "id": "perm-uuid",
                "folder_id": "folder-uuid",
                "subject_type": "account",
                "subject_id": "user-uuid",
                "subject_name": "john.doe",
                "permission": "read",
                "is_active": true,
                "created": true,
                "created_at": "2026-04-14T..."
            }
        }
        """
        try:
            # Validate input
            serializer = FolderPermissionSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    ResponseBuilder.error(
                        "Invalid permission data",
                        errors=serializer.errors,
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call service to grant permission
            service = FolderService()
            result = service.grant_permission(
                user_id=str(request.user.id),
                folder_id=folder_id,
                subject_type=serializer.validated_data['subject_type'],
                subject_id=serializer.validated_data['subject_id'],
                permission=serializer.validated_data['permission']
            )
            
            logger.info(
                f"User {request.user.id} granted {serializer.validated_data['permission']} "
                f"permission to {serializer.validated_data['subject_type']}:"
                f"{serializer.validated_data['subject_id']} on folder {folder_id}"
            )
            
            return Response(
                ResponseBuilder.success(
                    data=result,
                    message="Permission granted successfully"
                ),
                status=status.HTTP_201_CREATED
            )
        
        except UnsupportedMediaType as e:
            return Response(
                ResponseBuilder.error(
                    "Invalid Content-Type header. Must be 'application/json'",
                    status_code=415
                ),
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
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
        except BusinessLogicError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error granting folder permission: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to grant permission", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FolderPermissionDetailView(APIView):
    """
    Handle individual folder permission operations.
    
    DELETE: Revoke access to folder (identified by subject_type, subject_id, permission level)
    """
    
    @transaction.atomic
    def delete(self, request, folder_id, subject_type, subject_id, permission):
        """
        DELETE /api/v1/folders/{folder_id}/permissions/{subject_type}/{subject_id}/{permission}
        
        Revoke access to folder for a specific subject.
        
        Path Parameters:
        - folder_id: Target folder UUID
        - subject_type: "account" or "role"
        - subject_id: UUID of account or role ID
        - permission: "read", "write", or "delete"
        
        Response: 204 No Content (successful deletion)
        
        Example:
        DELETE /api/v1/folders/d7cf3758-e1b3-49aa-9ae0-783dd4426177/permissions/account/0176c136-0d10-4c85-84ea-31fc7b9379d2/read
        
        This deletes the FolderPermission record where:
        - folder_id = d7cf3758-e1b3-49aa-9ae0-783dd4426177
        - subject_type = "account"
        - subject_id = 0176c136-0d10-4c85-84ea-31fc7b9379d2
        - permission = "read"
        """
        try:
            # Validate inputs
            if subject_type not in ['account', 'role']:
                return Response(
                    ResponseBuilder.error(
                        f"Invalid subject_type: '{subject_type}'. Must be 'account' or 'role'",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if permission not in ['read', 'write', 'delete']:
                return Response(
                    ResponseBuilder.error(
                        f"Invalid permission: '{permission}'. Must be 'read', 'write', or 'delete'",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call service to revoke permission
            service = FolderService()
            service.revoke_permission_by_subject(
                user_id=str(request.user.id),
                folder_id=folder_id,
                subject_type=subject_type,
                subject_id=subject_id,
                permission=permission
            )
            
            logger.info(
                f"User {request.user.id} revoked {permission} permission "
                f"from {subject_type}:{subject_id} on folder {folder_id}"
            )
            
            return Response(
                ResponseBuilder.success(
                    message="Permission revoked successfully"
                ),
                status=status.HTTP_204_NO_CONTENT
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
        except BusinessLogicError as e:
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error revoking folder permission: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to revoke permission", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
