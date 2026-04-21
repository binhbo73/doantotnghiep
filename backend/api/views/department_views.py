"""
Department Views - CRUD API Endpoints
======================================

Endpoints:
- GET    /api/v1/departments           - List all departments in tree structure  
- POST   /api/v1/departments           - Create new department
- PUT    /api/v1/departments/{id}      - Update department info
- DELETE /api/v1/departments/{id}      - Soft delete department

Flow: View → Service → Repository → ORM
Each view:
1. Permission check (IsAdmin)
2. Input validation (Serializer)
3. Call Service (business logic)
4. Serialize response
5. Return standard response
"""

from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.utils import timezone
import logging

from core.permissions.drf_permissions import IsAdmin, IsAuthenticatedUser
from core.utils.response_builder import ResponseBuilder
from core.exceptions import (
    ValidationError,
    NotFoundError,
    DepartmentNotFoundError,
    BusinessLogicError,
    ConflictError,
)
from apps.users.models import Department
from services.department_service import DepartmentService
from api.serializers.department_serializers import (
    DepartmentTreeSerializer,
    DepartmentDetailSerializer,
    DepartmentCreateUpdateSerializer,
    DepartmentListSerializer,
    DepartmentDetailWithCountsSerializer,
    DepartmentExpandedSerializer,
)

logger = logging.getLogger(__name__)


# ============================================================
# CUSTOM PAGINATION
# ============================================================

class DepartmentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class DepartmentListTreeView(APIView):
    """
    API - Department List & Create
    
    GET  /api/v1/departments       - Get all departments with pagination (authenticated users)
    POST /api/v1/departments       - Create new department (admin only)
    
    Query Parameters (GET):
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    
    Response (GET):
    {
        "success": true,
        "data": {
            "items": [
                {
                    "id": "uuid-1",
                    "name": "Sales",
                    "parent_id": null,
                    "manager": {...},
                    "sub_departments": [...]
                }
            ],
            "pagination": {
                "page": 1,
                "page_size": 20,
                "total_items": 50,
                "total_pages": 3,
                "has_next": true,
                "has_previous": false
            }
        },
        "message": "Department list retrieved successfully"
    }
    """
    
    # GET requires authenticated user, POST requires admin
    permission_classes = [IsAuthenticatedUser]
    pagination_class = DepartmentPagination
    
    def get(self, request):
        """GET: Get all departments with pagination"""
        try:
            # Get all non-deleted departments from ORM (not tree structure for pagination)
            departments = Department.objects.filter(is_deleted=False).order_by('name')
            
            # Apply pagination
            paginator = self.pagination_class()
            paginated_queryset = paginator.paginate_queryset(departments, request)
            
            # Serialize with detail serializer
            serializer = DepartmentDetailSerializer(paginated_queryset, many=True)
            
            page_size = paginator.page_size
            total_count = paginator.page.paginator.count
            
            logger.info(f"User {request.user.username} retrieved department list - page {paginator.page.number}")
            
            return Response(
                ResponseBuilder.paginated(
                    items=serializer.data,
                    page=paginator.page.number,
                    page_size=page_size,
                    total_items=total_count,
                    message="Department list retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except BusinessLogicError as e:
            logger.error(f"Business logic error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve departments", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic()
    def post(self, request):
        """POST: Create new department (admin only)"""
        try:
            # Note: DRF permission class (IsAdmin) already verified this is admin user
            # No need to check again
            
            # Validate input
            serializer = DepartmentCreateUpdateSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.warning(f"Invalid department creation request: {serializer.errors}")
                return Response(
                    ResponseBuilder.error(
                        f"Validation failed: {serializer.errors}",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call service
            service = DepartmentService()
            dept = service.create_department(
                name=serializer.validated_data.get('name'),
                parent_id=serializer.validated_data.get('parent_id'),
                manager_id=serializer.validated_data.get('manager_id'),
                description=serializer.validated_data.get('description'),
                requested_by_user_id=str(request.user.id)
            )
            
            # Serialize response
            response_serializer = DepartmentDetailSerializer(dept)
            logger.info(f"Department created by {request.user.username}: {dept.name}")
            
            return Response(
                ResponseBuilder.success(
                    data=response_serializer.data,
                    message="Department created successfully",
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
            logger.error(f"Business logic error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to create department", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class DepartmentDetailView(APIView):
    """
    API - Department Detail, Update & Delete
    
    PUT    /api/v1/departments/{dept_id}   - Update department info
    DELETE /api/v1/departments/{dept_id}   - Soft delete department
    
    Response (PUT):
    {
        "success": true,
        "message": "Department updated successfully",
        "data": {...}
    }
    
    Response (DELETE):
    {
        "success": true,
        "message": "Department deleted successfully",
        "data": {
            "id": "uuid-...",
            "name": "Sales",
            "deleted_at": "2024-04-14T10:30:45Z"
        }
    }
    
    Error Examples (DELETE):
    - 404: Department not found
    - 409: Cannot delete - has users assigned
    """
    
    permission_classes = [IsAuthenticatedUser, IsAdmin]
    
    def get(self, request, dept_id):
        """
        GET: Get department detail with counts (BASIC view).
        
        Returns department info + member_count, folder_count, document_count,
        sub_department_count, sub_departments (recursive tree structure).
        
        Example Response:
        {
            "success": true,
            "data": {
                "id": "uuid-1",
                "name": "Sales",
                "parent_id": null,
                "manager": {...},
                "member_count": 10,
                "folder_count": 5,
                "document_count": 20,
                "sub_department_count": 2,
                "sub_departments": [{...}],
                "created_at": "...",
                "updated_at": "..."
            },
            "message": "Department detail retrieved successfully"
        }
        """
        try:
            service = DepartmentService()
            dept = service.get_department_detail_with_counts(dept_id)
            
            # Serialize with counts
            serializer = DepartmentDetailWithCountsSerializer(dept)
            
            logger.info(f"User {request.user.username} retrieved department detail: {dept_id}")
            
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message="Department detail retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            logger.warning(f"Not found error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except BusinessLogicError as e:
            logger.error(f"Business logic error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve department detail", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic()
    def put(self, request, dept_id):
        """PUT: Update department"""
        try:
            # Validate input
            serializer = DepartmentCreateUpdateSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.warning(f"Invalid department update request: {serializer.errors}")
                return Response(
                    ResponseBuilder.error(
                        f"Validation failed: {serializer.errors}",
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Call service
            service = DepartmentService()
            dept = service.update_department(
                dept_id=dept_id,
                name=serializer.validated_data.get('name'),
                description=serializer.validated_data.get('description'),
                manager_id=serializer.validated_data.get('manager_id'),
                requested_by_user_id=str(request.user.id) if request.user else None
            )
            
            # Serialize response
            response_serializer = DepartmentDetailSerializer(dept)
            logger.info(f"Department updated: {dept_id} by {request.user.username}")
            
            return Response(
                ResponseBuilder.success(
                    data=response_serializer.data,
                    message="Department updated successfully"
                ),
                status=status.HTTP_200_OK
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
            logger.error(f"Business logic error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to update department", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic()
    def delete(self, request, dept_id):
        """DELETE: Soft delete department"""
        try:
            # Get department (for response)
            service = DepartmentService()
            dept = service.get_department(dept_id)
            
            # Delete
            service.delete_department(
                dept_id=dept_id,
                requested_by_user_id=str(request.user.id) if request.user else None
            )
            
            logger.info(f"Department deleted: {dept_id} by {request.user.username}")
            
            # Response
            return Response(
                ResponseBuilder.success(
                    data={
                        "id": str(dept.id),
                        "name": dept.name,
                        "deleted_at": timezone.now().isoformat()
                    },
                    message="Department deleted successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            logger.warning(f"Not found error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except ConflictError as e:
            # 409 Conflict if has users or other cascade issues
            logger.warning(f"Conflict error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=409),
                status=status.HTTP_409_CONFLICT
            )
        except BusinessLogicError as e:
            logger.error(f"Business logic error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to delete department", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# HYBRID APPROACH - EXPANDED DETAIL VIEW
# ============================================================================

class DepartmentDetailExpandView(APIView):
    """
    API - Department Detail with Expanded Data (FULL view).
    
    GET /api/v1/departments/{id}/detail?expand=users,folders,documents
    
    Query Parameters:
    - expand: Comma-separated list (users, folders, documents) - optional
    - page: Page number for expanded items (default: 1)
    - page_size: Items per page (default: 10, max: 50)
    
    Example Response:
    {
        "success": true,
        "data": {
            "id": "uuid-1",
            "name": "Sales",
            "parent_id": null,
            "manager": {...},
            "member_count": 10,
            "folder_count": 5,
            "document_count": 20,
            "sub_departments": [{...}],
            "users": {
                "items": [...],
                "pagination": {...}
            },
            "folders": {
                "items": [...],
                "pagination": {...}
            },
            "documents": {
                "items": [...],
                "pagination": {...}
            }
        },
        "message": "Department detail retrieved successfully"
    }
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request, dept_id):
        """GET: Get department detail with expanded data"""
        try:
            # Parse query parameters
            expand_str = request.query_params.get('expand', '')
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 10)), 50)  # Max 50
            
            # Parse expand fields
            expand_fields = [f.strip() for f in expand_str.split(',') if f.strip()] if expand_str else []
            
            # Validate expand fields
            valid_fields = {'users', 'folders', 'documents'}
            expand_fields = [f for f in expand_fields if f in valid_fields]
            
            service = DepartmentService()
            data = service.get_department_with_expanded_data(
                dept_id=dept_id,
                expand_fields=expand_fields,
                page=page,
                page_size=page_size
            )
            
            # Serialize
            serializer = DepartmentExpandedSerializer(data)
            
            logger.info(
                f"User {request.user.username} retrieved expanded department detail: {dept_id} "
                f"(expand={','.join(expand_fields)})"
            )
            
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message="Department detail retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            logger.warning(f"Not found error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            logger.warning(f"Invalid query parameter: {e}")
            return Response(
                ResponseBuilder.error(f"Invalid query parameter: {str(e)}", status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except BusinessLogicError as e:
            logger.error(f"Business logic error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve department detail", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# HYBRID APPROACH - SUB-RESOURCE VIEWS
# ============================================================================

class DepartmentUsersView(APIView):
    """
    API - Get users in department.
    
    GET /api/v1/departments/{id}/users
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 50)
    
    Response:
    {
        "success": true,
        "data": {
            "items": [
                {
                    "id": "uuid",
                    "username": "john_doe",
                    "email": "john@example.com",
                    "full_name": "John Doe",
                    "avatar_url": "..."
                }
            ],
            "pagination": {...}
        },
        "message": "Users retrieved successfully"
    }
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request, dept_id):
        """GET: Get users in department with pagination"""
        try:
            # Parse query parameters
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 10)), 50)  # Max 50
            
            service = DepartmentService()
            data = service._get_department_users_paginated(
                dept_id=dept_id,
                page=page,
                page_size=page_size
            )
            
            logger.info(f"User {request.user.username} retrieved department users: {dept_id} - page {page}")
            
            return Response(
                ResponseBuilder.paginated(
                    items=data['items'],
                    page=data['pagination']['page'],
                    page_size=data['pagination']['page_size'],
                    total_items=data['pagination']['total_items'],
                    message="Users retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            logger.warning(f"Not found error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            logger.warning(f"Invalid query parameter: {e}")
            return Response(
                ResponseBuilder.error(f"Invalid query parameter: {str(e)}", status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except BusinessLogicError as e:
            logger.error(f"Business logic error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve users", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DepartmentFoldersView(APIView):
    """
    API - Get folders in department.
    
    GET /api/v1/departments/{id}/folders
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 50)
    
    Response:
    {
        "success": true,
        "data": {
            "items": [
                {
                    "id": "uuid",
                    "name": "Folder Name",
                    "parent_id": null,
                    "access_scope": "department",
                    "document_count": 5,
                    "subfolder_count": 2,
                    "created_at": "..."
                }
            ],
            "pagination": {...}
        },
        "message": "Folders retrieved successfully"
    }
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request, dept_id):
        """GET: Get folders in department with pagination"""
        try:
            # Parse query parameters
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 10)), 50)  # Max 50
            
            service = DepartmentService()
            data = service._get_department_folders_paginated(
                dept_id=dept_id,
                page=page,
                page_size=page_size
            )
            
            logger.info(f"User {request.user.username} retrieved department folders: {dept_id} - page {page}")
            
            return Response(
                ResponseBuilder.paginated(
                    items=data['items'],
                    page=data['pagination']['page'],
                    page_size=data['pagination']['page_size'],
                    total_items=data['pagination']['total_items'],
                    message="Folders retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            logger.warning(f"Not found error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            logger.warning(f"Invalid query parameter: {e}")
            return Response(
                ResponseBuilder.error(f"Invalid query parameter: {str(e)}", status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except BusinessLogicError as e:
            logger.error(f"Business logic error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve folders", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DepartmentDocumentsView(APIView):
    """
    API - Get documents in department.
    
    GET /api/v1/departments/{id}/documents
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 50)
    
    Response:
    {
        "success": true,
        "data": {
            "items": [
                {
                    "id": "uuid",
                    "filename": "document.pdf",
                    "original_name": "annual_report.pdf",
                    "file_type": "pdf",
                    "file_size": 1024000,
                    "status": "completed",
                    "uploader_id": "uuid",
                    "folder_id": "uuid",
                    "access_scope": "department",
                    "created_at": "..."
                }
            ],
            "pagination": {...}
        },
        "message": "Documents retrieved successfully"
    }
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request, dept_id):
        """GET: Get documents in department with pagination"""
        try:
            # Parse query parameters
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 10)), 50)  # Max 50
            
            service = DepartmentService()
            data = service._get_department_documents_paginated(
                dept_id=dept_id,
                page=page,
                page_size=page_size
            )
            
            logger.info(f"User {request.user.username} retrieved department documents: {dept_id} - page {page}")
            
            return Response(
                ResponseBuilder.paginated(
                    items=data['items'],
                    page=data['pagination']['page'],
                    page_size=data['pagination']['page_size'],
                    total_items=data['pagination']['total_items'],
                    message="Documents retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            logger.warning(f"Not found error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            logger.warning(f"Invalid query parameter: {e}")
            return Response(
                ResponseBuilder.error(f"Invalid query parameter: {str(e)}", status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except BusinessLogicError as e:
            logger.error(f"Business logic error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve documents", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FolderDocumentsView(APIView):
    """
    API - Get documents in a specific folder.
    
    GET /api/v1/folders/{id}/documents
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 50)
    
    Response:
    {
        "success": true,
        "data": {
            "items": [
                {
                    "id": "uuid",
                    "filename": "document.pdf",
                    "original_name": "annual_report.pdf",
                    "file_type": "pdf",
                    "file_size": 1024000,
                    "status": "completed",
                    "uploader_id": "uuid",
                    "folder_id": "uuid",
                    "access_scope": "department",
                    "created_at": "..."
                }
            ],
            "pagination": {...}
        },
        "message": "Documents retrieved successfully"
    }
    """
    
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request, folder_id):
        """GET: Get documents in folder with pagination"""
        try:
            # Parse query parameters
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 10)), 50)  # Max 50
            
            service = DepartmentService()
            data = service.get_folder_documents_paginated(
                folder_id=folder_id,
                page=page,
                page_size=page_size
            )
            
            logger.info(f"User {request.user.username} retrieved folder documents: {folder_id} - page {page}")
            
            return Response(
                ResponseBuilder.paginated(
                    items=data['items'],
                    page=data['pagination']['page'],
                    page_size=data['pagination']['page_size'],
                    total_items=data['pagination']['total_items'],
                    message="Documents retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except NotFoundError as e:
            logger.warning(f"Not found error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=404),
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            logger.warning(f"Invalid query parameter: {e}")
            return Response(
                ResponseBuilder.error(f"Invalid query parameter: {str(e)}", status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except BusinessLogicError as e:
            logger.error(f"Business logic error: {e}")
            return Response(
                ResponseBuilder.error(str(e), status_code=400),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to retrieve documents", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
