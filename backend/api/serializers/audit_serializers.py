"""
Audit Log Serializers - Serialization for AuditLog model.
Used for API endpoints related to audit logs, activity history, and compliance tracking.

Flow: Repository → Service → Serializer → View → API Response
"""
from rest_framework import serializers
from django.utils import timezone
from apps.operations.models import AuditLog
from apps.users.models import Account
from .base import SoftDeleteModelSerializer, TimestampedModelSerializer


# ============================================================
# AUDIT LOG SERIALIZERS
# ============================================================

class AuditLogSimpleSerializer(serializers.ModelSerializer):
    """Simple AuditLog serializer for list endpoints"""
    account_username = serializers.CharField(source='account.username', read_only=True, allow_null=True)
    account_id = serializers.UUIDField(source='account.id', read_only=True, allow_null=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'account_id',
            'account_username',
            'action',
            'action_display',
            'resource_id',
            'query_text',
            'ip_address',
            'created_at',
        ]
        read_only_fields = fields


class AuditLogDetailSerializer(serializers.ModelSerializer):
    """Detailed AuditLog serializer including full user information"""
    account = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'account',
            'action',
            'action_display',
            'resource_id',
            'query_text',
            'ip_address',
            'user_agent',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
    
    def get_account(self, obj):
        """Get user information from account"""
        if obj.account:
            return {
                'id': str(obj.account.id),
                'username': obj.account.username,
                'email': obj.account.email,
                'first_name': obj.account.first_name,
                'last_name': obj.account.last_name,
            }
        return None


class AuditLogRecentActivitySerializer(serializers.ModelSerializer):
    """Serializer for recent activity card on dashboard"""
    id = serializers.CharField(read_only=True)
    avatarChar = serializers.SerializerMethodField()
    avatarBgColor = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    category = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'avatarChar',
            'avatarBgColor',
            'title',
            'description',
            'time',
            'category',
        ]
        read_only_fields = fields
    
    def get_avatarChar(self, obj):
        """Get first character of username for avatar"""
        if obj.account and obj.account.username:
            return obj.account.username[0].upper()
        return '?'
    
    def get_avatarBgColor(self, obj):
        """Get background color based on action type"""
        action_colors = {
            'LOGIN': '#0058be',
            'LOGOUT': '#727785',
            'CREATE': '#52c41a',
            'UPLOAD': '#faad14',
            'DELETE': '#f5222d',
            'QUERY': '#1890ff',
            'EDIT': '#eb2f96',
            'UPDATE': '#722ed1',
            'DOWNLOAD': '#13c2c2',
            'SHARE': '#fa541c',
            'IMPORT': '#1890ff',
            'DELETE_USER': '#f5222d',
            'CHANGE_ROLE': '#eb2f96',
            'CREATE_ROLE': '#52c41a',
            'FEEDBACK': '#faad14',
            'GRANT_ACL': '#52c41a',
            'REVOKE_ACL': '#f5222d',
            'MUTATION': '#1890ff',
        }
        return action_colors.get(obj.action, '#0058be')
    
    def get_title(self, obj):
        """Get activity title from action and resource"""
        user = obj.account.username if obj.account else 'Hệ thống'
        action_titles = {
            'LOGIN': f'{user} đã đăng nhập',
            'LOGOUT': f'{user} đã đăng xuất',
            'CREATE': f'{user} đã tạo {self._get_resource_name(obj.resource_id)}',
            'UPLOAD': f'{user} đã tải lên {self._get_resource_name(obj.resource_id)}',
            'DELETE': f'{user} đã xóa {self._get_resource_name(obj.resource_id)}',
            'QUERY': f'{user} đã truy vấn dữ liệu',
            'EDIT': f'{user} đã chỉnh sửa {self._get_resource_name(obj.resource_id)}',
            'UPDATE': f'{user} đã cập nhật {self._get_resource_name(obj.resource_id)}',
            'DOWNLOAD': f'{user} đã tải xuống {self._get_resource_name(obj.resource_id)}',
            'SHARE': f'{user} đã chia sẻ {self._get_resource_name(obj.resource_id)}',
            'IMPORT': f'{user} đã nhập dữ liệu',
            'DELETE_USER': f'{user} đã xóa người dùng',
            'CHANGE_ROLE': f'{user} đã thay đổi vai trò',
            'CREATE_ROLE': f'{user} đã tạo vai trò mới',
            'FEEDBACK': f'{user} đã gửi phản hồi',
            'GRANT_ACL': f'{user} đã cấp quyền truy cập',
            'REVOKE_ACL': f'{user} đã thu hồi quyền truy cập',
            'MUTATION': f'{user} đã thực hiện thay đổi dữ liệu',
        }
        return action_titles.get(obj.action, f'{user} thực hiện {obj.action}')
    
    def get_description(self, obj):
        """Get activity description"""
        if obj.query_text:
            return obj.query_text
        
        action_descriptions = {
            'LOGIN': 'Được chia sẻ bởi Team Marketing',
            'LOGOUT': 'Phiên làm việc kết thúc',
            'UPLOAD': f'ID tài nguyên: {obj.resource_id}',
            'CREATE': f'ID tài nguyên: {obj.resource_id}',
            'DELETE': f'ID tài nguyên: {obj.resource_id}',
        }
        return action_descriptions.get(obj.action, f'Địa chỉ IP: {obj.ip_address}' if obj.ip_address else 'Không có mô tả')
    
    def get_time(self, obj):
        """Get relative time string (e.g., '3 giờ trước')"""
        from django.utils.timesince import timesince
        return f"{timesince(obj.created_at, timezone.now())} trước"
    
    def _get_resource_name(self, resource_id):
        """Get resource name from resource_id"""
        return 'tài nguyên'


class AuditLogListQuerySerializer(serializers.Serializer):
    """Query parameters serializer for audit log list endpoint"""
    action = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Filter by action (e.g., LOGIN, UPLOAD, DELETE)'
    )
    account_id = serializers.UUIDField(
        required=False,
        help_text='Filter by user ID'
    )
    resource_id = serializers.UUIDField(
        required=False,
        help_text='Filter by resource ID'
    )
    start_date = serializers.DateTimeField(
        required=False,
        help_text='Filter logs from this date onwards'
    )
    end_date = serializers.DateTimeField(
        required=False,
        help_text='Filter logs up to this date'
    )
    search = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Search in query_text'
    )
    page = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        help_text='Page number (default: 1)'
    )
    page_size = serializers.IntegerField(
        required=False,
        default=20,
        min_value=1,
        max_value=100,
        help_text='Items per page (default: 20, max: 100)'
    )


class AuditLogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating audit logs (usually internal use only)"""
    class Meta:
        model = AuditLog
        fields = [
            'account',
            'action',
            'resource_id',
            'query_text',
            'ip_address',
            'user_agent',
        ]


class AuditLogStatisticsSerializer(serializers.Serializer):
    """Serializer for audit log statistics"""
    total_logs = serializers.IntegerField()
    logs_today = serializers.IntegerField()
    logs_this_week = serializers.IntegerField()
    logs_this_month = serializers.IntegerField()
    most_active_user = serializers.CharField(allow_null=True)
    most_common_action = serializers.CharField(allow_null=True)
    actions_breakdown = serializers.DictField()
    users_breakdown = serializers.DictField()


class AuditLogExportSerializer(serializers.ModelSerializer):
    """Serializer for exporting audit logs to CSV/Excel"""
    account_username = serializers.CharField(source='account.username', read_only=True, allow_null=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'account_username',
            'action',
            'action_display',
            'resource_id',
            'query_text',
            'ip_address',
            'user_agent',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
