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
1. Permission check (permission code)
2. Input validation (Serializer)
3. Call Service (business logic)
4. Serialize response
5. Return standard response
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import transaction
from django.utils import timezone
import logging

from core.permissions.drf_permissions import IsAuthenticatedUser, user_has_any_permission, user_has_permission
from core.utils.response_builder import ResponseBuilder
from core.constants import PermissionCodes
from core.exceptions import (
    ValidationError,
    NotFoundError,
    DepartmentNotFoundError,
    BusinessLogicError,
    ConflictError,
)
from apps.users.models import Department
from services.department_service import DepartmentService
from services.user_service import UserService
from api.serializers.department_serializers import (
    DepartmentTreeSerializer,
    DepartmentDetailSerializer,
    DepartmentCreateUpdateSerializer,
    DepartmentListSerializer,
    DepartmentDetailWithCountsSerializer,
    DepartmentExpandedSerializer,
)

logger = logging.getLogger(__name__)

DEPARTMENT_READ_PERMISSIONS = [
    PermissionCodes.DEPARTMENT_READ,
    PermissionCodes.DEPARTMENT_UPDATE,
    PermissionCodes.DEPARTMENT_MANAGE,
]


def _has_department_read(user):
    return user_has_any_permission(user, DEPARTMENT_READ_PERMISSIONS)


def _has_permission(user, permission_code):
    return user_has_permission(user, permission_code)


def _forbidden(message="You don't have permission to access this department"):
    return Response(
        ResponseBuilder.error(message, status_code=403),
        status=status.HTTP_403_FORBIDDEN,
    )


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
    POST /api/v1/departments       - Create new department (department_manage only)
    
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
            if not user_has_any_permission(request.user, DEPARTMENT_READ_PERMISSIONS):
                return _forbidden("You need department_read permission to view departments")

            service = DepartmentService()

            # Restrict the list to departments the current user is allowed to see.
            departments = service.get_accessible_departments_queryset(request.user).order_by('name')
            
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
        """POST: Create new department (department_create or department_manage)"""
        try:
            if not user_has_any_permission(request.user, [PermissionCodes.DEPARTMENT_CREATE, PermissionCodes.DEPARTMENT_MANAGE]):
                return _forbidden("You need department_create or department_manage permission to create departments")
            
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
    
    permission_classes = [IsAuthenticatedUser]
    
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
            if not user_has_any_permission(request.user, DEPARTMENT_READ_PERMISSIONS):
                return _forbidden("You need department_read permission to view departments")

            service = DepartmentService()
            if not service.can_access_department(request.user, dept_id):
                return _forbidden()
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
            if not user_has_any_permission(
                request.user,
                [PermissionCodes.DEPARTMENT_UPDATE, PermissionCodes.DEPARTMENT_MANAGE],
            ):
                return _forbidden("You need department_update permission to update departments")

            service = DepartmentService()
            if not service.can_edit_department(request.user, dept_id):
                return _forbidden("You don't have permission to update this department")

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
            if not user_has_permission(request.user, PermissionCodes.DEPARTMENT_MANAGE):
                return _forbidden("You need department_manage permission to delete departments")

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
                ResponseBuilder.error(
                    str(e),
                    status_code=409,
                    data=e.detail,
                ),
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
            if not _has_department_read(request.user):
                return _forbidden("You need department_read permission to view departments")

            service = DepartmentService()
            if not service.can_access_department(request.user, dept_id):
                return _forbidden()

            # Parse query parameters
            expand_str = request.query_params.get('expand', '')
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 10)), 50)  # Max 50
            
            # Parse expand fields
            expand_fields = [f.strip() for f in expand_str.split(',') if f.strip()] if expand_str else []
            
            # Validate expand fields
            valid_fields = {'users', 'folders', 'documents'}
            expand_fields = [f for f in expand_fields if f in valid_fields]

            missing_permissions = []
            if 'users' in expand_fields and not _has_permission(request.user, PermissionCodes.USER_READ):
                missing_permissions.append(PermissionCodes.USER_READ)
            if 'folders' in expand_fields and not _has_permission(request.user, PermissionCodes.FOLDER_READ):
                missing_permissions.append(PermissionCodes.FOLDER_READ)
            if 'documents' in expand_fields and not _has_permission(request.user, PermissionCodes.DOCUMENT_READ):
                missing_permissions.append(PermissionCodes.DOCUMENT_READ)
            if missing_permissions:
                return _forbidden(
                    f"You need these permissions for expanded department data: {', '.join(missing_permissions)}"
                )
            
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
            if not _has_department_read(request.user):
                return _forbidden("You need department_read permission to view department users")
            if not _has_permission(request.user, PermissionCodes.USER_READ):
                return _forbidden("You need user_read permission to view department users")

            service = DepartmentService()
            if not service.can_access_department(request.user, dept_id):
                return _forbidden()

            # Parse query parameters
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 10)), 50)  # Max 50

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

    @transaction.atomic()
    def post(self, request, dept_id):
        """
        POST: Add many accounts to this department.

        Body:
        {
            "account_ids": ["account-uuid-1", "account-uuid-2"],
            "reason": "optional audit note"
        }
        """
        try:
            if not user_has_any_permission(request.user, [PermissionCodes.DEPARTMENT_UPDATE, PermissionCodes.DEPARTMENT_MANAGE]):
                return _forbidden("You need department_update or department_manage permission to add users to a department")
            if not _has_permission(request.user, PermissionCodes.USER_UPDATE):
                return _forbidden("You need user_update permission to add users to a department")

            service = DepartmentService()
            if not service.can_edit_department(request.user, dept_id):
                return _forbidden("You don't have permission to update this department")

            department = Department.objects.filter(id=dept_id, is_deleted=False).first()
            if not department:
                return Response(
                    ResponseBuilder.error(f"Department {dept_id} not found", status_code=404),
                    status=status.HTTP_404_NOT_FOUND,
                )

            account_ids = request.data.get('account_ids', request.data.get('user_ids'))
            if not isinstance(account_ids, list):
                return Response(
                    ResponseBuilder.error("Field 'account_ids' must be a list", status_code=400),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not account_ids:
                return Response(
                    ResponseBuilder.error("Field 'account_ids' must contain at least one account", status_code=400),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if len(account_ids) > 100:
                return Response(
                    ResponseBuilder.error("Cannot add more than 100 users at once", status_code=400),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            reason = request.data.get('reason', '')
            user_service = UserService()
            added = []
            errors = []
            seen_account_ids = set()

            for index, account_id in enumerate(account_ids):
                account_id = str(account_id).strip() if account_id else ''
                if not account_id:
                    errors.append({
                        'index': index,
                        'account_id': account_id,
                        'message': 'Account ID is required',
                    })
                    continue
                if account_id in seen_account_ids:
                    errors.append({
                        'index': index,
                        'account_id': account_id,
                        'message': 'Duplicate account ID in request',
                    })
                    continue
                seen_account_ids.add(account_id)

                try:
                    profile = user_service.change_user_department(account_id=account_id, department_id=dept_id)
                    added.append({
                        'index': index,
                        'account_id': str(account_id),
                        'profile_id': str(profile.id),
                        'department_id': str(profile.department_id),
                        'department_name': profile.department.name if profile.department else department.name,
                    })
                except Exception as e:
                    errors.append({
                        'index': index,
                        'account_id': account_id,
                        'message': str(e),
                    })

            try:
                user_service.audit_log_action(
                    action='UPDATE_USER_PROFILE',
                    user_id=request.user.id,
                    resource_id=str(dept_id),
                    query_text=(
                        f"Added {len(added)} users to department {department.name} ({dept_id}). "
                        f"Errors: {len(errors)}. Reason: {reason}"
                    ),
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                )
            except Exception as e:
                logger.error(f"Failed to log department user assignment: {str(e)}")

            response_data = {
                'department_id': str(dept_id),
                'department_name': department.name,
                'added': added,
                'errors': errors,
                'added_count': len(added),
                'error_count': len(errors),
                'requested_count': len(account_ids),
            }

            if not added:
                return Response(
                    ResponseBuilder.error("No users were added to department", data=response_data, status_code=400),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                ResponseBuilder.success(
                    data=response_data,
                    message=f"Added {len(added)} of {len(account_ids)} users to department",
                    status_code=status.HTTP_201_CREATED if not errors else 207,
                ),
                status=status.HTTP_201_CREATED if not errors else 207,
            )

        except Exception as e:
            logger.error(f"Unexpected error adding users to department: {e}", exc_info=True)
            return Response(
                ResponseBuilder.error("Failed to add users to department", status_code=500),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


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
            if not _has_department_read(request.user):
                return _forbidden("You need department_read permission to view department folders")
            if not _has_permission(request.user, PermissionCodes.FOLDER_READ):
                return _forbidden("You need folder_read permission to view department folders")

            service = DepartmentService()
            if not service.can_access_department(request.user, dept_id):
                return _forbidden()

            # Parse query parameters
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 10)), 50)  # Max 50

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
            if not _has_department_read(request.user):
                return _forbidden("You need department_read permission to view department documents")
            if not _has_permission(request.user, PermissionCodes.DOCUMENT_READ):
                return _forbidden("You need document_read permission to view department documents")

            service = DepartmentService()
            if not service.can_access_department(request.user, dept_id):
                return _forbidden()

            # Parse query parameters
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 10)), 50)  # Max 50

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
            if not _has_permission(request.user, PermissionCodes.FOLDER_READ):
                return _forbidden("You need folder_read permission to view folder documents")
            if not _has_permission(request.user, PermissionCodes.DOCUMENT_READ):
                return _forbidden("You need document_read permission to view folder documents")

            # Parse query parameters
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 10)), 50)  # Max 50
            
            service = DepartmentService()
            is_admin = user_has_permission(request.user, PermissionCodes.DEPARTMENT_MANAGE)
            
            data = service.get_folder_documents_paginated(
                folder_id=folder_id,
                user_id=str(request.user.id),
                is_admin=is_admin,
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
