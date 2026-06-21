"""
Audit Log Serializers - Serialization for AuditLog model.
Used for API endpoints related to audit logs, activity history, and compliance tracking.

Flow: Repository → Service → Serializer → View → API Response
"""
from rest_framework import serializers
from django.utils import timezone
from apps.documents.models import Document, Folder
from apps.operations.models import AuditLog, Conversation
from apps.users.models import Account, Department, Permission, Role, UserProfile
from .base import SoftDeleteModelSerializer, TimestampedModelSerializer


# ============================================================
# AUDIT LOG SERIALIZERS
# ============================================================

ACTION_LABELS = {
    'CREATE_ROLE': 'Tạo vai trò',
    'UPDATE_ROLE': 'Cập nhật vai trò',
    'DELETE_ROLE': 'Xóa vai trò',
    'ASSIGN_PERMISSION': 'Gán quyền',
    'REMOVE_PERMISSION': 'Gỡ quyền',
    'CREATE_PERMISSION': 'Tạo quyền hạn',
    'UPDATE_PERMISSION': 'Cập nhật quyền hạn',
    'DELETE_PERMISSION': 'Xóa quyền hạn',
    'READ': 'Xem',
    'CREATE': 'Tạo',
    'UPDATE': 'Cập nhật',
    'DELETE': 'Xóa',
    'UPLOAD': 'Tải lên',
    'DOWNLOAD': 'Tải xuống',
    'MOVE': 'Di chuyển',
    'RESTORE': 'Khôi phục',
    'GRANT_PERMISSION': 'Cấp quyền',
    'REVOKE_PERMISSION': 'Thu hồi quyền',
    'UPDATE_PERMISSION': 'Cập nhật quyền',
    'CHAT_MESSAGE': 'Gửi tin nhắn chat',
    'FEEDBACK': 'Gửi phản hồi',
    'ACCESS_DENIED': 'Bị chặn quyền',
    'ERROR': 'Gặp lỗi',
    'LOGIN': 'Đăng nhập',
    'LOGOUT': 'Đăng xuất',
}

ACTION_LABELS.update({
    'CREATE_FOLDER': 'Tạo thư mục',
    'UPDATE_FOLDER': 'Cập nhật thư mục',
    'DELETE_FOLDER': 'Xóa thư mục',
    'MOVE_FOLDER': 'Di chuyển thư mục',
    'CREATE_DEPARTMENT': 'Tạo phòng ban',
    'UPDATE_DEPARTMENT': 'Cập nhật phòng ban',
    'DELETE_DEPARTMENT': 'Xóa phòng ban',
    'DOCUMENT_UPLOAD': 'Tải lên tài liệu',
    'DOCUMENT_DOWNLOAD': 'Tải xuống tài liệu',
    'CREATE_ROLE': 'Tạo vai trò',
    'UPDATE_ROLE': 'Cập nhật vai trò',
    'DELETE_ROLE': 'Xóa vai trò',
    'ASSIGN_PERMISSION': 'Gán quyền',
    'REMOVE_PERMISSION': 'Gỡ quyền',
    'CREATE_PERMISSION': 'Tạo quyền hạn',
    'UPDATE_PERMISSION': 'Cập nhật quyền hạn',
    'DELETE_PERMISSION': 'Xóa quyền hạn',
})


RESOURCE_TYPE_LABELS = {
    'iam_roles': 'Vai tro',
    'iam_permissions': 'Quyen',
    'Permission': 'Quyen',
    'documents': 'Tài liệu',
    'folders': 'Thư mục',
    'departments': 'Phòng ban',
    'users': 'Người dùng',
    'accounts': 'Tài khoản',
    'roles': 'Vai trò',
    'permissions': 'Quyền',
    'chat_sessions': 'Cuộc chat',
    'chat_messages': 'Tin nhắn chat',
    'deleted_documents': 'Tài liệu đã xóa',
    'deleted_folders': 'Thư mục đã xóa',
}


RESOURCE_TYPE_LABELS.update({
    'iam_roles': 'Vai trò',
    'iam_permissions': 'Quyền hạn',
    'Permission': 'Quyền hạn',
    'deleted_departments': 'Phòng ban đã xóa',
    'deleted_users': 'Người dùng đã xóa',
    'deleted_accounts': 'Tài khoản đã xóa',
    'deleted_roles': 'Vai trò đã xóa',
    'deleted_permissions': 'Quyền hạn đã xóa',
})


def get_audit_action_label(action):
    return ACTION_LABELS.get(action or '', action or 'Thực hiện')


def _model_lookup(model, object_id, fields):
    if not object_id:
        return None

    manager = model.objects
    if hasattr(manager, 'all_records'):
        manager = manager.all_records()

    instance = manager.filter(id=object_id).first()
    if not instance:
        return None

    for field in fields:
        value = getattr(instance, field, None)
        if value:
            return str(value)

    return str(instance)


def _fallback_resource_type_label(resource_type):
    if not resource_type:
        return 'Dữ liệu hệ thống'
    return RESOURCE_TYPE_LABELS.get(resource_type, resource_type.replace('_', ' ').replace('-', ' ').title())


def _metadata(obj):
    value = getattr(obj, 'metadata', None) or {}
    return value if isinstance(value, dict) else {}


def _first_metadata_value(metadata, *keys):
    for key in keys:
        value = metadata.get(key)
        if value not in (None, '', [], {}):
            return value
    return None


def _chat_question_from_metadata(metadata):
    body_summary = metadata.get('body_summary') or {}
    if isinstance(body_summary, dict) and body_summary.get('chat_question'):
        return str(body_summary.get('chat_question'))
    question = metadata.get('chat_question') or metadata.get('latest_question')
    return str(question) if question else ''


def _context_suffix(metadata):
    parts = []
    context_label = metadata.get('context_label')
    if context_label:
        parts.append(str(context_label))

    hierarchy = metadata.get('department_hierarchy') or metadata.get('folder_hierarchy')
    if isinstance(hierarchy, list) and hierarchy:
        parts.append(' > '.join(str(item) for item in hierarchy if item))

    question = _chat_question_from_metadata(metadata)
    if question:
        parts.append(f'Câu hỏi: "{question}"')

    return ' | '.join(parts)


def resolve_audit_resource_label(obj):
    resource_type = obj.resource_type or ''
    resource_id = obj.resource_id
    metadata = _metadata(obj)

    metadata_label = _first_metadata_value(
        metadata,
        'resource_label',
        'resource_display',
        'resource_name',
        'conversation_title',
        'document_name',
        'folder_name',
        'department_name',
    )
    if metadata_label:
        label = str(metadata_label)
        suffix = _context_suffix(metadata)
        return f"{label} ({suffix})" if suffix and suffix not in label else label

    lookup_map = {
        'iam_roles': (Role, ['name', 'code']),
        'iam_permissions': (Permission, ['name', 'code']),
        'Permission': (Permission, ['name', 'code']),
        'documents': (Document, ['original_name', 'filename']),
        'deleted_documents': (Document, ['original_name', 'filename']),
        'folders': (Folder, ['name']),
        'deleted_folders': (Folder, ['name']),
        'departments': (Department, ['name']),
        'users': (UserProfile, ['full_name']),
        'accounts': (Account, ['username', 'email']),
        'roles': (Role, ['name', 'code']),
        'permissions': (Permission, ['name', 'code']),
        'chat_sessions': (Conversation, ['title']),
        'chat_conversations': (Conversation, ['title']),
    }

    if resource_type in lookup_map:
        model, fields = lookup_map[resource_type]
        name = _model_lookup(model, resource_id, fields)
        if name:
            return f"{_fallback_resource_type_label(resource_type)}: {name}"

    if resource_type.startswith('chat_'):
        question = _chat_question_from_metadata(metadata)
        if question:
            return f"Cuộc chat: {question}"

    if resource_type.startswith('chat_'):
        return 'Cuộc chat'

    label = _fallback_resource_type_label(resource_type)
    return f"{label}: {str(resource_id)[:8]}" if resource_id else label


def resolve_audit_detail(obj):
    metadata = _metadata(obj)
    detail_parts = []

    context_label = metadata.get('context_label')
    if context_label:
        detail_parts.append(str(context_label))

    question = _chat_question_from_metadata(metadata)
    if question:
        detail_parts.append(f'Đang hỏi: "{question}"')

    body_summary = metadata.get('body_summary') or {}
    if isinstance(body_summary, dict):
        doc_count = body_summary.get('document_ids_count') or metadata.get('document_count')
        folder_count = body_summary.get('folder_ids_count') or metadata.get('folder_count')
    else:
        doc_count = metadata.get('document_count')
        folder_count = metadata.get('folder_count')

    if doc_count:
        detail_parts.append(f'{doc_count} tài liệu đính kèm')
    if folder_count:
        detail_parts.append(f'{folder_count} thư mục đính kèm')

    return ' | '.join(detail_parts)


def resolve_activity_summary(obj):
    action = get_audit_action_label(obj.action)
    resource_label = resolve_audit_resource_label(obj)
    detail = resolve_audit_detail(obj)

    if obj.status == 'denied':
        summary = f"Không được phép {action.lower()} {resource_label}"
    elif obj.status == 'failed':
        summary = f"Lỗi khi {action.lower()} {resource_label}"
    else:
        summary = f"{action} {resource_label}"

    return f"{summary} - {detail}" if detail else summary


class AuditLogSimpleSerializer(serializers.ModelSerializer):
    """Simple AuditLog serializer for list endpoints"""
    account_username = serializers.CharField(source='account.username', read_only=True, allow_null=True)
    account_id = serializers.UUIDField(source='account.id', read_only=True, allow_null=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    resource_label = serializers.SerializerMethodField()
    activity_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'account_id',
            'account_username',
            'action',
            'action_display',
            'activity_summary',
            'resource_id',
            'resource_type',
            'resource_label',
            'status',
            'http_method',
            'path',
            'status_code',
            'metadata',
            'query_text',
            'ip_address',
            'created_at',
        ]
        read_only_fields = fields

    def get_resource_label(self, obj):
        return resolve_audit_resource_label(obj)

    def get_activity_summary(self, obj):
        return resolve_activity_summary(obj)


class AuditLogDetailSerializer(serializers.ModelSerializer):
    """Detailed AuditLog serializer including full user information"""
    account = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    resource_label = serializers.SerializerMethodField()
    activity_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'account',
            'action',
            'action_display',
            'activity_summary',
            'resource_id',
            'resource_type',
            'resource_label',
            'status',
            'http_method',
            'path',
            'status_code',
            'metadata',
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

    def get_resource_label(self, obj):
        return resolve_audit_resource_label(obj)

    def get_activity_summary(self, obj):
        return resolve_activity_summary(obj)


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
        if obj.action in {'READ', 'CHAT_MESSAGE', 'CREATE', 'UPDATE', 'DELETE', 'UPLOAD', 'DOWNLOAD', 'MOVE', 'RESTORE'}:
            return f'{user}: {resolve_activity_summary(obj)}'

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
        detail = resolve_audit_detail(obj)
        if detail:
            return detail
        summary = resolve_activity_summary(obj)
        if summary:
            return summary
        
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
            'resource_type',
            'status',
            'http_method',
            'path',
            'status_code',
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
    status_breakdown = serializers.DictField()
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
            'resource_type',
            'status',
            'http_method',
            'path',
            'status_code',
            'metadata',
            'query_text',
            'ip_address',
            'user_agent',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
