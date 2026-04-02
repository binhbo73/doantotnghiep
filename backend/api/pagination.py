"""
Custom Pagination - Định dạng phân trang đồng bộ với ResponseBuilder.
Dùng trong ViewSets.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from api.serializers.base import ResponseBuilder

class StandardPagination(PageNumberPagination):
    """Phân trang chuẩn ResponseBuilder (Data inside 'items' and 'pagination')"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        """Override để trả về format JSON chuẩn của hệ thống"""
        return Response(
            ResponseBuilder.paginated(
                items=data,
                page=self.page.number,
                page_size=self.get_page_size(self.request),
                total_items=self.page.paginator.count
            )
        )

class LargePagination(StandardPagination):
    """Phân trang dùng cho danh sách dài (50 items/page)"""
    page_size = 50
