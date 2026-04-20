"""
IAM Views - Role & Permission Management
Phase 3 API Implementation (9 endpoints)

Flow: View → Service → Repository → ORM

All views follow strict enterprise Django pattern:
1. Permission check (via permission_classes)
2. Input validation (via Serializer)
3. Call Service (business logic)
4. Service calls Repository (ORM)
5. Return response via ResponseBuilder
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.permissions.drf_permissions import IsAdmin
from core.utils.response_builder import ResponseBuilder
from core.exceptions import (
    ValidationError,
    NotFoundError,
    PermissionDeniedError,
    BusinessLogicError,
)
from services.role_service import RoleService
from services.permission_service import PermissionService
from api.serializers.role_serializers import (
    PermissionDetailSerializer,
    PermissionSerializer,
    PermissionUpdateSerializer,
    PermissionCreateSerializer,
    RoleDetailSerializer,
    RoleCreateUpdateSerializer,
)
import logging

logger = logging.getLogger(__name__)


class PermissionListView(APIView):
    """
    API: GET|POST|PUT|DELETE /api/v1/iam/permissions
    
    Endpoints:
    - GET /api/v1/iam/permissions - List all permissions (paginated)
    - POST /api/v1/iam/permissions - Create new permission
    - PUT /api/v1/iam/permissions/{permission_id} - Update permission
    - DELETE /api/v1/iam/permissions/{permission_id} - Delete permission (soft delete)
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, permission_id=None):
        """
        GET /api/v1/iam/permissions - List all permissions with pagination
        GET /api/v1/iam/permissions/{permission_id} - Get single permission details
        """
        try:
            # Get single permission
            if permission_id:
                permission_service = PermissionService()
                result = permission_service.get_permission(permission_id)
                return Response(ResponseBuilder.success(data=result), status=status.HTTP_200_OK)
            
            # List permissions with pagination
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            search = request.query_params.get('search', '').strip() or None
            
            if page < 1 or page_size < 1 or page_size > 100:
                return Response(
                    ResponseBuilder.error("Invalid pagination (page >= 1, 1 <= page_size <= 100)", status_code=400),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            permission_service = PermissionService()
            result = permission_service.list_permissions(page=page, page_size=page_size, search=search)
            
            return Response(
                ResponseBuilder.paginated(
                    items=result['permissions'],
                    page=result['pagination']['page'],
                    page_size=result['pagination']['page_size'],
                    total_items=result['pagination']['total']
                ),
                status=status.HTTP_200_OK
            )
        except NotFoundError as e:
            return Response(ResponseBuilder.error(str(e), status_code=404), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting permissions: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve permissions", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, permission_id=None):
        """
        POST /api/v1/iam/permissions - Create new permission
        
        Request body:
            {
                "code": "document_approve",
                "name": "Approve Document",
                "description": "Can approve documents",
                "resource": "document",
                "action": "approve"
            }
        
        Returns:
            {
                "success": true,
                "status_code": 201,
                "message": "Permission created successfully",
                "data": {
                    "id": "...",
                    "code": "document_approve",
                    "name": "Approve Document",
                    "description": "Can approve documents",
                    "resource": "document",
                    "action": "approve",
                    "created_at": "...",
                    "updated_at": "..."
                }
            }
        """
        try:
            # Validate input data
            serializer = PermissionCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    ResponseBuilder.error("Validation failed", status_code=400, data=serializer.errors),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call service to create
            permission_service = PermissionService()
            result = permission_service.create_permission(
                data=serializer.validated_data,
                requested_by_user_id=request.user.id if hasattr(request, 'user') else None
            )
            
            return Response(
                ResponseBuilder.created(data=result, resource_type="Permission"),
                status=status.HTTP_201_CREATED
            )
        
        except ValidationError as e:
            return Response(ResponseBuilder.error(str(e), status_code=400), status=status.HTTP_400_BAD_REQUEST)
        except BusinessLogicError as e:
            return Response(ResponseBuilder.error(str(e), status_code=400), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating permission: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to create permission", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, permission_id=None):
        """
        PUT /api/v1/iam/permissions/{permission_id} - Update permission details
        
        Request body:
            {
                "name": "New Permission Name",
                "description": "New description",
                "code": "document_write",  // optional, must be unique
                "resource": "document",    // optional
                "action": "write"          // optional
            }
        
        Returns:
            {
                "success": true,
                "data": {
                    "id": "...",
                    "code": "document_write",
                    "name": "New Permission Name",
                    "description": "New description",
                    "resource": "document",
                    "action": "write",
                    "created_at": "...",
                    "updated_at": "..."
                },
                "message": "Permission updated successfully"
            }
        """
        if not permission_id:
            return Response(
                ResponseBuilder.error("permission_id required in URL path", status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validate input data
            serializer = PermissionUpdateSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(
                    ResponseBuilder.error("Validation failed", status_code=400, data=serializer.errors),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call service to update
            permission_service = PermissionService()
            result = permission_service.update_permission(
                permission_id=permission_id,
                data=serializer.validated_data,
                requested_by_user_id=request.user.id if hasattr(request, 'user') else None
            )
            
            return Response(
                ResponseBuilder.success(data=result, message="Permission updated successfully"),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            return Response(ResponseBuilder.error(str(e), status_code=404), status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(ResponseBuilder.error(str(e), status_code=400), status=status.HTTP_400_BAD_REQUEST)
        except BusinessLogicError as e:
            return Response(ResponseBuilder.error(str(e), status_code=400), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating permission: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to update permission", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, permission_id=None):
        """
        DELETE /api/v1/iam/permissions/{permission_id} - Delete permission (soft delete)
        
        Returns:
            {
                "success": true,
                "message": "Permission deleted successfully"
            }
        """
        if not permission_id:
            return Response(
                ResponseBuilder.error("permission_id required in URL path", status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            permission_service = PermissionService()
            permission_service.delete_permission(
                permission_id=permission_id,
                requested_by_user_id=request.user.id if hasattr(request, 'user') else None
            )
            
            return Response(
                ResponseBuilder.success(message="Permission deleted successfully"),
                status=status.HTTP_204_NO_CONTENT
            )
        
        except NotFoundError as e:
            return Response(ResponseBuilder.error(str(e), status_code=404), status=status.HTTP_404_NOT_FOUND)
        except BusinessLogicError as e:
            return Response(ResponseBuilder.error(str(e), status_code=400), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error deleting permission: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to delete permission", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RoleManagementView(APIView):
    """API-06/07/08/09: GET|POST|PUT|DELETE /api/v1/iam/roles"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, role_id=None):
        try:
            if role_id:
                role_service = RoleService()
                result = role_service.get_role_details(role_id)
                return Response(ResponseBuilder.success(data=result), status=status.HTTP_200_OK)
            else:
                page = int(request.query_params.get('page', 1))
                page_size = int(request.query_params.get('page_size', 20))
                search = request.query_params.get('search', '').strip() or None
                
                if page < 1 or page_size < 1 or page_size > 100:
                    return Response(ResponseBuilder.error("Invalid pagination", status_code=400), status=status.HTTP_400_BAD_REQUEST)
                
                role_service = RoleService()
                result = role_service.list_roles(page=page, page_size=page_size, search=search)
                
                return Response(ResponseBuilder.paginated(items=result['roles'], page=result['pagination']['page'], page_size=result['pagination']['page_size'], total_items=result['pagination']['total']), status=status.HTTP_200_OK)
        except NotFoundError as e:
            return Response(ResponseBuilder.error(str(e), status_code=404), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in get roles: {e}", exc_info=True)
            return Response(ResponseBuilder.error("Failed to retrieve roles", status_code=500), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, role_id=None):
        try:
            serializer = RoleCreateUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(ResponseBuilder.error("Validation failed", status_code=400, data=serializer.errors), status=status.HTTP_400_BAD_REQUEST)
            
            role_service = RoleService()
            result = role_service.create_role(data=serializer.validated_data, requested_by_user_id=request.user.id if hasattr(request, 'user') else None)
            
            return Response(ResponseBuilder.success(data=result, message="Role created successfully"), status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating role: {e}", exc_info=True)
            return Response(ResponseBuilder.error("Failed to create role", status_code=500), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, role_id=None):
        if not role_id:
            return Response(ResponseBuilder.error("role_id required", status_code=400), status=status.HTTP_400_BAD_REQUEST)
        
        try:
            serializer = RoleCreateUpdateSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(ResponseBuilder.error("Validation failed", status_code=400, data=serializer.errors), status=status.HTTP_400_BAD_REQUEST)
            
            role_service = RoleService()
            result = role_service.update_role(role_id=role_id, data=serializer.validated_data, requested_by_user_id=request.user.id if hasattr(request, 'user') else None)
            
            return Response(ResponseBuilder.success(data=result, message="Role updated successfully"), status=status.HTTP_200_OK)
        except NotFoundError as e:
            return Response(ResponseBuilder.error(str(e), status_code=404), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating role: {e}", exc_info=True)
            return Response(ResponseBuilder.error("Failed to update role", status_code=500), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, role_id=None):
        if not role_id:
            return Response(ResponseBuilder.error("role_id required", status_code=400), status=status.HTTP_400_BAD_REQUEST)
        
        try:
            role_service = RoleService()
            role_service.delete_role(role_id=role_id, requested_by_user_id=request.user.id if hasattr(request, 'user') else None)
            
            return Response(ResponseBuilder.success(message="Role deleted successfully"), status=status.HTTP_204_NO_CONTENT)
        except NotFoundError as e:
            return Response(ResponseBuilder.error(str(e), status_code=404), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting role: {e}", exc_info=True)
            return Response(ResponseBuilder.error("Failed to delete role", status_code=500), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RolePermissionsView(APIView):
    """API-10/11/12: GET|POST|DELETE /api/v1/iam/roles/{role_id}/permissions"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, role_id=None, permission_id=None):
        if not role_id:
            return Response(ResponseBuilder.error("role_id required", status_code=400), status=status.HTTP_400_BAD_REQUEST)
        
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            search = request.query_params.get('search', '').strip() or None
            
            role_service = RoleService()
            result = role_service.get_role_permissions(role_id=role_id, page=page, page_size=page_size, search=search)
            
            return Response(ResponseBuilder.paginated(items=result['permissions'], page=result['pagination']['page'], page_size=result['pagination']['page_size'], total_items=result['pagination']['total']), status=status.HTTP_200_OK)
        except NotFoundError as e:
            return Response(ResponseBuilder.error(str(e), status_code=404), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving role permissions: {e}", exc_info=True)
            return Response(ResponseBuilder.error("Failed to retrieve permissions", status_code=500), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, role_id=None, permission_id=None):
        if not role_id:
            return Response(ResponseBuilder.error("role_id required", status_code=400), status=status.HTTP_400_BAD_REQUEST)
        
        try:
            perm_id = request.data.get('permission_id')
            if not perm_id:
                return Response(ResponseBuilder.error("permission_id required", status_code=400), status=status.HTTP_400_BAD_REQUEST)
            
            role_service = RoleService()
            result = role_service.add_permission_to_role(role_id=role_id, permission_id=perm_id, requested_by_user_id=request.user.id if hasattr(request, 'user') else None)
            
            return Response(ResponseBuilder.success(data=result, message="Permission added to role"), status=status.HTTP_200_OK)
        except (NotFoundError, ValidationError) as e:
            return Response(ResponseBuilder.error(str(e), status_code=404), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error adding permission: {e}", exc_info=True)
            return Response(ResponseBuilder.error("Failed to add permission", status_code=500), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, role_id=None, permission_id=None):
        if not role_id or not permission_id:
            return Response(ResponseBuilder.error("role_id and permission_id required", status_code=400), status=status.HTTP_400_BAD_REQUEST)
        
        try:
            role_service = RoleService()
            role_service.remove_permission_from_role(role_id=role_id, permission_id=permission_id, requested_by_user_id=request.user.id if hasattr(request, 'user') else None)
            
            return Response(ResponseBuilder.success(message="Permission removed from role"), status=status.HTTP_204_NO_CONTENT)
        except (NotFoundError, ValidationError) as e:
            return Response(ResponseBuilder.error(str(e), status_code=404), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error removing permission: {e}", exc_info=True)
            return Response(ResponseBuilder.error("Failed to remove permission", status_code=500), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckUserPermissionView(APIView):
    """API-13: POST /api/v1/iam/users/{user_id}/check-permission"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request, user_id):
        try:
            permission_code = request.data.get('permission_code')
            if not permission_code:
                return Response(ResponseBuilder.error("permission_code is required", status_code=400), status=status.HTTP_400_BAD_REQUEST)
            
            role_service = RoleService()
            result = role_service.check_user_permission(user_id=user_id, permission_code=permission_code)
            
            return Response(ResponseBuilder.success(data=result, message=result.get('message', 'Permission check completed')), status=status.HTTP_200_OK)
        except (ValidationError, NotFoundError) as e:
            return Response(ResponseBuilder.error(str(e), status_code=404), status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error checking user permission: {e}", exc_info=True)
            return Response(ResponseBuilder.error("Failed to check permission", status_code=500), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

