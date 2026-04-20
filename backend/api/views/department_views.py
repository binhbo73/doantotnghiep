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
