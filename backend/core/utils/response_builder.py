"""
ResponseBuilder - Standard response format for all API responses
"""

from typing import Optional, Any, Dict
from datetime import datetime
import uuid


class ResponseBuilder:
    """
    Build standard API responses in format:
    {
        "success": bool,
        "status_code": int,
        "message": str,
        "data": object,
        "timestamp": str,
        "request_id": str
    }
    """
    
    @staticmethod
    def success(data: Any = None, message: str = "Success", 
                status_code: int = 200, request_id: str = None) -> Dict:
        """
        Build successful response.
        
        Args:
            data: Response data (can be object, list, dict, etc.)
            message: Success message
            status_code: HTTP status code (default 200)
            request_id: Request ID for tracking (default: auto-generated)
        
        Returns:
            Standard response dict
        
        Example:
            return Response(ResponseBuilder.success(
                data={'user': {...}},
                message='User created successfully',
                status_code=201
            ), status=status.HTTP_201_CREATED)
        """
        return {
            'success': True,
            'status_code': status_code,
            'message': message,
            'data': data,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'request_id': request_id or str(uuid.uuid4())
        }
    
    @staticmethod
    def error(message: str = "Error", status_code: int = 400,
              data: Any = None, errors: Dict = None,
              request_id: str = None) -> Dict:
        """
        Build error response.
        
        Args:
            message: Error message
            status_code: HTTP status code (default 400)
            data: Additional error data
            errors: Validation errors dict
            request_id: Request ID for tracking
        
        Returns:
            Standard error response dict
        
        Example:
            return Response(ResponseBuilder.error(
                message='Validation failed',
                status_code=400,
                errors=serializer.errors
            ), status=status.HTTP_400_BAD_REQUEST)
        """
        response = {
            'success': False,
            'status_code': status_code,
            'message': message,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'request_id': request_id or str(uuid.uuid4())
        }
        
        if errors:
            response['errors'] = errors
        if data:
            response['data'] = data
        
        return response
    
    @staticmethod
    def paginated(items: list, page: int = 1, page_size: int = 20,
                  total_items: int = 0, message: str = "Success",
                  request_id: str = None) -> Dict:
        """
        Build paginated response.
        
        Args:
            items: List of items for this page
            page: Current page number
            page_size: Items per page
            total_items: Total number of items
            message: Response message
            request_id: Request ID
        
        Returns:
            Paginated response with metadata
        
        Example:
            return Response(ResponseBuilder.paginated(
                items=serializer.data,
                page=page,
                page_size=page_size,
                total_items=total,
                message='Users retrieved'
            ))
        """
        # Calculate pagination metadata
        total_pages = (total_items + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        return {
            'success': True,
            'status_code': 200,
            'message': message,
            'data': {
                'items': items,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_items': total_items,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_prev': has_prev
                }
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'request_id': request_id or str(uuid.uuid4())
        }
    
    @staticmethod
    def created(data: Any = None, resource_type: str = "Resource",
                request_id: str = None) -> Dict:
        """
        Build created (201) response.
        
        Args:
            data: Created resource data
            resource_type: Type of resource created
            request_id: Request ID
        
        Returns:
            201 created response
        """
        return ResponseBuilder.success(
            data=data,
            message=f'{resource_type} created successfully',
            status_code=201,
            request_id=request_id
        )
    
    @staticmethod
    def deleted(resource_type: str = "Resource", request_id: str = None) -> Dict:
        """
        Build deleted (204) response.
        
        Args:
            resource_type: Type of resource deleted
            request_id: Request ID
        
        Returns:
            204 no content response
        """
        return ResponseBuilder.success(
            message=f'{resource_type} deleted successfully',
            status_code=204,
            request_id=request_id
        )
    
    @staticmethod
    def unauthorized(message: str = "Unauthorized",
                    request_id: str = None) -> Dict:
        """Build 401 unauthorized response"""
        return ResponseBuilder.error(
            message=message,
            status_code=401,
            request_id=request_id
        )
    
    @staticmethod
    def forbidden(message: str = "Permission denied",
                 request_id: str = None) -> Dict:
        """Build 403 forbidden response"""
        return ResponseBuilder.error(
            message=message,
            status_code=403,
            request_id=request_id
        )
    
    @staticmethod
    def not_found(resource_type: str = "Resource",
                 request_id: str = None) -> Dict:
        """Build 404 not found response"""
        return ResponseBuilder.error(
            message=f'{resource_type} not found',
            status_code=404,
            request_id=request_id
        )
    
    @staticmethod
    def conflict(message: str = "Conflict",
                data: Any = None,
                request_id: str = None) -> Dict:
        """Build 409 conflict response"""
        return ResponseBuilder.error(
            message=message,
            status_code=409,
            data=data,
            request_id=request_id
        )
    
    @staticmethod
    def internal_error(message: str = "Internal server error",
                      request_id: str = None) -> Dict:
        """Build 500 internal server error response"""
        return ResponseBuilder.error(
            message=message,
            status_code=500,
            request_id=request_id
        )
