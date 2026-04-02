"""
Custom Pagination - DRF pagination classes với response format chuẩn.
"""
from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.response import Response
from collections import OrderedDict
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CustomPageNumberPagination(PageNumberPagination):
    """
    Page number pagination - /api/items/?page=2&page_size=10
    
    Features:
    - Customizable page size
    - Max page size limit (prevent abuse)
    - Custom response format
    """
    
    page_size = 10  # Default page size
    page_size_query_param = 'page_size'  # Allow ?page_size=20
    page_size_query_description = 'Number of results per page'
    
    max_page_size = 100  # Max 100 items per page
    
    page_query_param = 'page'
    page_query_description = 'Page number'
    
    def get_paginated_response(self, data):
        """
        Build paginated response with standard format
        
        Format:
        {
            "success": true,
            "status_code": 200,
            "data": {
                "items": [...],
                "pagination": {
                    "page": 1,
                    "page_size": 10,
                    "total_items": 100,
                    "total_pages": 10,
                    "has_next": true,
                    "has_previous": false
                }
            }
        }
        """
        from api.serializers.base import ResponseBuilder
        
        total_items = self.page.paginator.count
        total_pages = self.page.paginator.num_pages
        current_page = self.page.number
        
        response_data = ResponseBuilder.paginated(
            items=data,
            page=current_page,
            page_size=self.page_size,
            total_items=total_items,
            message="List records"
        )
        
        return Response(response_data)


class SmallPagePagination(CustomPageNumberPagination):
    """Small page pagination - 5 items per page"""
    page_size = 5
    max_page_size = 20


class MediumPagePagination(CustomPageNumberPagination):
    """Medium page pagination - 10 items per page (default)"""
    page_size = 10
    max_page_size = 50


class LargePagePagination(CustomPageNumberPagination):
    """Large page pagination - 50 items per page"""
    page_size = 50
    max_page_size = 200


class CustomCursorPagination(CursorPagination):
    """
    Cursor pagination - More efficient for large datasets
    Format: /api/items/?cursor=abc123
    
    Advantages:
    - O(1) instead of O(n) for offset-based pagination  
    - Better for real-time data
    - Prevents issues with concurrent inserts/deletes
    
    Usage:
        class ItemViewSet(viewsets.ModelViewSet):
            pagination_class = CustomCursorPagination
            # Must specify ordering
            ordering = ['-created_at']
    """
    
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    ordering = '-created_at'  # Must be set on ViewSet
    
    cursor_query_description = 'Cursor for pagination'
    template = None  # Disable HTML form for API
    
    def get_paginated_response(self, data):
        """Build cursor pagination response"""
        from api.serializers.base import ResponseBuilder
        
        response_data = ResponseBuilder.success(
            data={
                "items": data,
                "cursor": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                }
            },
            message="List records using cursor pagination"
        )
        
        return Response(response_data)


class SearchResultsPagination(CustomPageNumberPagination):
    """
    Pagination for search results - Optimized for search APIs
    """
    page_size = 20
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """Build search results response"""
        from api.serializers.base import ResponseBuilder
        
        total_items = self.page.paginator.count
        total_pages = self.page.paginator.num_pages
        current_page = self.page.number
        
        response_data = ResponseBuilder.paginated(
            items=data,
            page=current_page,
            page_size=self.page_size,
            total_items=total_items,
            message=f"Found {total_items} results"
        )
        
        return Response(response_data)


class DocumentListPagination(CustomPageNumberPagination):
    """
    Pagination for document listing - Default 15 items
    """
    page_size = 15
    max_page_size = 100


class ChatHistoryPagination(CustomPageNumberPagination):
    """
    Pagination for chat history - Load recent first + small page
    """
    page_size = 20  # More chat messages per page
    max_page_size = 100
    # ViewSet should set: ordering = ['-created_at']


# ============================================================
# HELPER FUNCTION
# ============================================================
def get_pagination_class(pagination_type: str = 'default'):
    """
    Get pagination class by type
    
    Args:
        pagination_type: 'default', 'small', 'medium', 'large', 'cursor', 'search'
        
    Returns:
        Pagination class
    
    Example:
        PaginationClass = get_pagination_class('large')
        
        class MyViewSet(viewsets.ModelViewSet):
            pagination_class = PaginationClass
    """
    pagination_classes = {
        'default': CustomPageNumberPagination,
        'small': SmallPagePagination,
        'medium': MediumPagePagination,
        'large': LargePagePagination,
        'cursor': CustomCursorPagination,
        'search': SearchResultsPagination,
        'documents': DocumentListPagination,
        'chat': ChatHistoryPagination,
    }
    
    pagination_class = pagination_classes.get(pagination_type, CustomPageNumberPagination)
    logger.debug(f"Using pagination: {pagination_class.__name__}")
    
    return pagination_class
