"""
Audit Log Views - REST API endpoints for audit logs and activity tracking.

Features:
1. Audit Log Management (List with filtering, Retrieve)
2. Recent Activity (for dashboard)
3. Statistics (audit log analytics)
4. Export

Endpoints:
- GET /api/v1/audit-logs - List audit logs (with filtering)
- GET /api/v1/audit-logs/{id} - Get audit log details
- GET /api/v1/audit-logs/recent-activity - Get recent activities (for dashboard)
- GET /api/v1/audit-logs/statistics - Get audit statistics
- GET /api/v1/audit-logs/export - Export audit logs (CSV/JSON)

Flow: Repository → Service → Serializer → View → API Response
"""
import logging
from datetime import datetime, timedelta

from django.utils import timezone
from django.db.models import Q, Count
from django.http import HttpResponse
from rest_framework import status, filters
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from apps.operations.models import AuditLog
from repositories.audit_log_repository import AuditLogRepository
from services.audit_service import AuditService

from api.views.base import BaseReadOnlyViewSet
from api.serializers.base import ResponseBuilder
from api.serializers.audit_serializers import (
    AuditLogSimpleSerializer,
    AuditLogDetailSerializer,
    AuditLogRecentActivitySerializer,
    AuditLogStatisticsSerializer,
    AuditLogExportSerializer,
)

logger = logging.getLogger(__name__)


# ============================================================
# PAGINATION
# ============================================================

class AuditLogPagination(PageNumberPagination):
    """Pagination cho audit logs"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ============================================================
# AUDIT LOG VIEWS
# ============================================================

class AuditLogListView(BaseReadOnlyViewSet):
    """
    GET /api/v1/audit-logs - List audit logs with filtering
    """
    queryset = AuditLog.objects.select_related('account').order_by('-created_at')
    serializer_class = AuditLogSimpleSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AuditLogPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['query_text', 'account__username']
    ordering_fields = ['created_at', 'action']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Apply filters to queryset"""
        queryset = super().get_queryset()
        
        # Get query parameters
        action = self.request.query_params.get('action', '').strip()
        account_id = self.request.query_params.get('account_id', '').strip()
        resource_id = self.request.query_params.get('resource_id', '').strip()
        start_date = self.request.query_params.get('start_date', '').strip()
        end_date = self.request.query_params.get('end_date', '').strip()
        
        if action:
            queryset = queryset.filter(action=action.upper())
        
        if account_id:
            try:
                queryset = queryset.filter(account_id=account_id)
            except (ValueError, TypeError):
                pass
        
        if resource_id:
            try:
                queryset = queryset.filter(resource_id=resource_id)
            except (ValueError, TypeError):
                pass
        
        if start_date:
            try:
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(created_at__gte=start)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(created_at__lte=end)
            except (ValueError, TypeError):
                pass
        
        return queryset
    
    def list(self, request: Request) -> Response:
        """List audit logs with applied filters"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return Response(
                ResponseBuilder.paginated(
                    items=serializer.data,
                    page=self.paginator.page.number,
                    page_size=self.paginator.page.paginator.per_page,
                    total_items=self.paginator.page.paginator.count,
                    message="Audit logs retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            ResponseBuilder.success(
                data=serializer.data,
                message="Audit logs retrieved successfully"
            ),
            status=status.HTTP_200_OK
        )


class AuditLogDetailView(BaseReadOnlyViewSet):
    """GET /api/v1/audit-logs/{id} - Get audit log details"""
    queryset = AuditLog.objects.select_related('account')
    serializer_class = AuditLogDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def retrieve(self, request: Request, id=None) -> Response:
        """Get detailed audit log information"""
        try:
            audit_log = self.get_object()
            serializer = self.get_serializer(audit_log)
            
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message="Audit log retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        except AuditLog.DoesNotExist:
            return Response(
                ResponseBuilder.error(
                    message="Audit log not found",
                    status_code=status.HTTP_404_NOT_FOUND
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving audit log: {str(e)}")
            return Response(
                ResponseBuilder.error(
                    message="Failed to retrieve audit log",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecentActivityView(APIView):
    """GET /api/v1/audit-logs/recent-activity - Get recent activities for dashboard"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        """Get recent activities"""
        try:
            limit = min(int(request.query_params.get('limit', 10)), 50)
            user_id = request.query_params.get('user_id', '').strip()
            
            queryset = AuditLog.objects.select_related('account').order_by('-created_at')
            
            if user_id:
                queryset = queryset.filter(account_id=user_id)
            
            activities = queryset[:limit]
            serializer = AuditLogRecentActivitySerializer(activities, many=True)
            
            return Response(
                ResponseBuilder.success(
                    data={
                        'items': serializer.data,
                        'count': len(serializer.data)
                    },
                    message="Recent activities retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error getting recent activities: {str(e)}")
            return Response(
                ResponseBuilder.error(
                    message="Failed to retrieve recent activities",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditLogStatisticsView(APIView):
    """GET /api/v1/audit-logs/statistics - Get audit log statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        """Get audit log statistics"""
        try:
            now = timezone.now()
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            total_logs = AuditLog.objects.count()
            logs_today = AuditLog.objects.filter(created_at__gte=today).count()
            logs_this_week = AuditLog.objects.filter(created_at__gte=week_ago).count()
            logs_this_month = AuditLog.objects.filter(created_at__gte=month_ago).count()
            
            most_active = AuditLog.objects.filter(
                account__isnull=False
            ).values('account__username').annotate(
                count=Count('id')
            ).order_by('-count').first()
            most_active_user = most_active['account__username'] if most_active else None
            
            most_common = AuditLog.objects.values('action').annotate(
                count=Count('id')
            ).order_by('-count').first()
            most_common_action = most_common['action'] if most_common else None
            
            actions = AuditLog.objects.values('action').annotate(
                count=Count('id')
            ).order_by('-count')
            actions_breakdown = {item['action']: item['count'] for item in actions}
            
            users = AuditLog.objects.filter(
                account__isnull=False
            ).values('account__username').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            users_breakdown = {item['account__username']: item['count'] for item in users}
            
            stats_data = {
                'total_logs': total_logs,
                'logs_today': logs_today,
                'logs_this_week': logs_this_week,
                'logs_this_month': logs_this_month,
                'most_active_user': most_active_user,
                'most_common_action': most_common_action,
                'actions_breakdown': actions_breakdown,
                'users_breakdown': users_breakdown,
            }
            
            serializer = AuditLogStatisticsSerializer(stats_data)
            
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message="Statistics retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return Response(
                ResponseBuilder.error(
                    message="Failed to retrieve statistics",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditLogExportView(APIView):
    """GET /api/v1/audit-logs/export - Export audit logs as CSV/JSON"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request: Request) -> Response:
        """Export audit logs"""
        try:
            import csv
            
            action = request.query_params.get('action', '').strip()
            start_date = request.query_params.get('start_date', '').strip()
            end_date = request.query_params.get('end_date', '').strip()
            file_format = request.query_params.get('format', 'csv').lower()
            
            queryset = AuditLog.objects.select_related('account').order_by('-created_at')
            
            if action:
                queryset = queryset.filter(action=action.upper())
            
            if start_date:
                try:
                    start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    queryset = queryset.filter(created_at__gte=start)
                except (ValueError, TypeError):
                    pass
            
            if end_date:
                try:
                    end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    queryset = queryset.filter(created_at__lte=end)
                except (ValueError, TypeError):
                    pass
            
            if file_format == 'csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
                
                writer = csv.writer(response)
                writer.writerow([
                    'ID', 'User', 'Action', 'Resource ID', 'Query Text',
                    'IP Address', 'Created At'
                ])
                
                for log in queryset:
                    writer.writerow([
                        str(log.id),
                        log.account.username if log.account else 'System',
                        log.action,
                        str(log.resource_id) if log.resource_id else '',
                        log.query_text or '',
                        log.ip_address or '',
                        log.created_at.isoformat(),
                    ])
                
                return response
            
            serializer = AuditLogExportSerializer(queryset, many=True)
            return Response(
                ResponseBuilder.success(
                    data=serializer.data,
                    message="Audit logs exported successfully"
                ),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error exporting audit logs: {str(e)}")
            return Response(
                ResponseBuilder.error(
                    message="Failed to export audit logs",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
