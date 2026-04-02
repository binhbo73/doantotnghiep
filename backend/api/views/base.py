"""
Base ViewSet - Lớp cơ sở cho toàn bộ API ViewSets.
Cung cấp các tiện ích: phân trang chuẩn, trả về response thống nhất.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from api.serializers.base import ResponseBuilder
import logging

logger = logging.getLogger(__name__)


class BaseViewSet(viewsets.GenericViewSet):
    """
    Base ViewSet tích hợp ResponseBuilder.
    Dùng khi bạn muốn tự định nghĩa logic phản hồi.
    """
    
    def get_paginated_response_data(self, queryset, serializer_class, message="Success", **filters):
        """Helper để lấy dữ liệu phân trang chuẩn ResponseBuilder"""
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializer_class(page, many=True)
            # Lấy thông tin phân trang từ DRF Paginator
            paginator = self.paginator
            return ResponseBuilder.paginated(
                items=serializer.data,
                page=paginator.page.number,
                page_size=paginator.page.paginator.per_page,
                total_items=paginator.page.paginator.count,
                message=message
            )

        serializer = serializer_class(queryset, many=True)
        return ResponseBuilder.success(data=serializer.data, message=message)

    def success_response(self, data=None, message="Success", status_code=status.HTTP_200_OK):
        """Trả về response thành công chuẩn"""
        return Response(
            ResponseBuilder.success(data, message, status_code),
            status=status_code
        )

    def error_response(self, message="Error", status_code=status.HTTP_400_BAD_REQUEST, data=None):
        """Trả về response lỗi chuẩn"""
        return Response(
            ResponseBuilder.error(message, status_code, data),
            status=status_code
        )


class BaseReadOnlyViewSet(BaseViewSet, viewsets.ReadOnlyModelViewSet):
    """ViewSet chỉ cho phép đọc (List, Retrieve) với response chuẩn"""
    pass


class BaseCRUDViewSet(BaseViewSet, viewsets.ModelViewSet):
    """ViewSet cho phép đầy đủ CRUD với response chuẩn"""
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(self.get_paginated_response_data(queryset, self.get_serializer_class()))

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return self.success_response(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return self.success_response(
            data=serializer.data, 
            message="Created successfully", 
            status_code=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return self.success_response(data=serializer.data, message="Updated successfully")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return self.success_response(message="Deleted successfully", status_code=status.HTTP_204_NO_CONTENT)
