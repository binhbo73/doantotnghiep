"""
Request-level audit logging.

This middleware is the safety net for audit coverage: every authenticated API
request is recorded with actor, action, resource, HTTP status and request
context. Service-level audit logs can still add richer domain events, but a
missing service call no longer creates a blind spot.
"""

import json
import logging
import re
from uuid import UUID
from typing import Any

from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin

from repositories.audit_log_repository import AuditLogRepository

logger = logging.getLogger(__name__)


class AuditLoggingMiddleware(MiddlewareMixin):
    AUDIT_METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE,
    )
    API_PREFIX_PARTS = {'api', 'v1'}
    SENSITIVE_KEYS = {
        'password',
        'old_password',
        'new_password',
        'confirm_password',
        'token',
        'access',
        'refresh',
        'authorization',
        'secret',
    }
    SKIP_PATH_MARKERS = (
        '/audit-logs',
        '/auth/me',
        '/auth/login',
        '/auth/refresh',
        '/auth/change-password',
        '/auth/forgot-password',
        '/auth/reset-password',
    )

    def process_request(self, request: HttpRequest):
        if not self._should_inspect_body(request):
            request._audit_body_keys = []
            request._audit_json = {}
            return None

        try:
            payload = json.loads(request.body or b'{}')
            request._audit_body_keys = self._safe_body_keys(payload)
            request._audit_json = self._safe_json_payload(payload)
        except Exception:
            request._audit_body_keys = []
            request._audit_json = {}

        return None

    def process_response(self, request: HttpRequest, response):
        if not self._should_audit(request, response):
            return response

        try:
            self._log_audit(request, response)
        except Exception as exc:
            logger.error("Error in audit logging: %s", exc, exc_info=True)

        return response

    def _should_inspect_body(self, request: HttpRequest) -> bool:
        return (
            request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}
            and 'application/json' in (request.content_type or '')
        )

    def _should_audit(self, request: HttpRequest, response) -> bool:
        if getattr(request, '_skip_request_audit', False):
            return False

        if request.method not in self.AUDIT_METHODS:
            return False

        path = request.path or ''
        if '/api/' not in path and not path.startswith('/api'):
            return False

        if any(marker in path for marker in self.SKIP_PATH_MARKERS):
            return False

        user = getattr(request, 'user', None)
        is_authenticated = bool(user and user.is_authenticated)
        is_security_failure = response.status_code in (401, 403)

        if request.method == 'GET' and not is_security_failure and not self._is_meaningful_read(request):
            return False

        return is_authenticated or is_security_failure

    def _log_audit(self, request: HttpRequest, response):
        attempted_action = self._infer_action(request.method, request.path)
        status_value = self._status_from_code(response.status_code)
        action = attempted_action
        if status_value == 'denied':
            action = 'ACCESS_DENIED'
        elif response.status_code >= 500:
            action = 'ERROR'

        resource_type, resource_id = self._extract_resource_from_path(request.path)
        resource_type, resource_id = self._resource_from_body_if_needed(
            attempted_action,
            resource_type,
            resource_id,
            request,
        )
        account = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        metadata = self._build_metadata(request, response, attempted_action)
        metadata.update(self._build_resource_context(resource_type, resource_id, request.path))
        description = self._build_description(
            attempted_action=attempted_action,
            resource_type=resource_type,
            resource_id=resource_id,
            path=request.path,
            status_value=status_value,
            status_code=response.status_code,
        )

        AuditLogRepository().log_action(
            account=account,
            action=action,
            resource_id=resource_id,
            resource_type=resource_type,
            query_text=description,
            ip_address=self._get_client_ip(request),
            user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:1000],
            details={
                **metadata,
                'http_method': request.method,
                'path': request.path,
                'status_code': response.status_code,
            },
            status=status_value,
            http_method=request.method,
            path=request.path,
            status_code=response.status_code,
        )

    def _infer_action(self, method: str, path: str) -> str:
        lower_path = path.lower()

        if 'preview' in lower_path:
            return 'READ'
        if 'chat/messages' in lower_path:
            if 'feedback' in lower_path:
                return 'FEEDBACK'
            return 'CHAT_MESSAGE'
        if 'download' in lower_path:
            return 'DOWNLOAD'
        if 'upload' in lower_path:
            return 'UPLOAD'
        if 'restore' in lower_path:
            return 'RESTORE'
        if 'move' in lower_path:
            return 'MOVE'
        if 'import' in lower_path:
            return 'IMPORT'
        if 'permissions' in lower_path:
            if method == 'POST':
                return 'GRANT_PERMISSION'
            if method == 'DELETE':
                return 'REVOKE_PERMISSION'
            if method in {'PUT', 'PATCH'}:
                return 'UPDATE_PERMISSION'

        if method == 'GET':
            return 'READ'
        if method == 'POST':
            return 'CREATE'
        if method in {'PUT', 'PATCH'}:
            return 'UPDATE'
        if method == 'DELETE':
            return 'DELETE'
        return 'MUTATION'

    def _is_meaningful_read(self, request: HttpRequest) -> bool:
        path = request.path or ''
        lower_path = path.lower()
        if any(keyword in lower_path for keyword in ('download', 'preview', 'export')):
            return True

        parts = self._normalized_path_parts(path)
        if not parts:
            return False

        if self._is_contextual_collection_read(parts):
            return True

        if self._is_supporting_collection_read(parts):
            return False

        resource_type, resource_id = self._extract_resource_from_path(path)
        if not resource_type or not resource_id:
            return False

        if len(parts) != 2:
            return False

        return resource_type in {
            'documents',
            'folders',
            'users',
            'departments',
            'roles',
            'permissions',
            'chat_sessions',
            'chat_messages',
            'deleted_documents',
            'deleted_folders',
        }

    def _extract_resource_from_path(self, path: str) -> tuple[str | None, str | None]:
        parts = self._normalized_path_parts(path)

        if not parts:
            return None, None

        resource_id = next((part for part in parts if self.UUID_PATTERN.match(part)), None)
        if parts[:2] == ['documents', 'shared-with-me']:
            return 'documents', resource_id
        if parts[0] == 'chat' and len(parts) > 1:
            if parts[1] == 'conversations':
                return 'chat_sessions', resource_id
            return f"chat_{parts[1]}", resource_id
        if len(parts) > 1 and parts[0] == 'iam':
            if parts[1] == 'roles':
                return 'roles', resource_id
            if parts[1] == 'permissions':
                return 'permissions', resource_id
        if parts[0] == 'deleted' and len(parts) > 1:
            return f"deleted_{parts[1]}", resource_id
        if parts[0] in {'documents', 'folders', 'accounts', 'users', 'departments', 'roles', 'permissions'}:
            return parts[0], resource_id
        if len(parts) > 1 and parts[0] in {'iam', 'auth'}:
            return f"{parts[0]}_{parts[1]}", resource_id
        return parts[0], resource_id

    def _resource_from_body_if_needed(
        self,
        attempted_action: str,
        resource_type: str | None,
        resource_id: str | None,
        request: HttpRequest,
    ) -> tuple[str | None, str | None]:
        if resource_id or attempted_action not in {'CHAT_MESSAGE', 'FEEDBACK'}:
            return resource_type, resource_id

        payload = getattr(request, '_audit_json', {}) or {}
        conversation_id = payload.get('conversation_id')
        if conversation_id and self._is_uuid(conversation_id):
            return 'chat_sessions', str(conversation_id)

        message_id = payload.get('message_id')
        if message_id and self._is_uuid(message_id):
            return 'chat_messages', str(message_id)

        return resource_type, resource_id

    def _normalized_path_parts(self, path: str) -> list[str]:
        parts = [part for part in path.strip('/').split('/') if part]
        while parts and parts[0].lower() in self.API_PREFIX_PARTS:
            parts.pop(0)
        return parts

    def _is_contextual_collection_read(self, parts: list[str]) -> bool:
        if parts in (
            ['users'],
            ['accounts'],
            ['departments'],
            ['folders'],
            ['documents'],
            ['documents', 'shared-with-me'],
            ['folders', 'permissions'],
            ['documents', 'permissions'],
            ['chat', 'conversations'],
            ['chat', 'available-attachments'],
        ):
            return True

        if parts in (['iam', 'roles'], ['iam', 'permissions']):
            return True

        if len(parts) == 2 and parts[0] == 'deleted':
            return True

        if (
            len(parts) >= 4
            and parts[0] == 'iam'
            and parts[1] == 'roles'
            and self.UUID_PATTERN.match(parts[2]) is not None
            and parts[3] == 'permissions'
        ):
            return True

        if (
            len(parts) >= 4
            and parts[0] == 'chat'
            and parts[1] == 'conversations'
            and self.UUID_PATTERN.match(parts[2]) is not None
            and parts[3] in {'messages', 'attachments'}
        ):
            return True

        if len(parts) < 3 or self.UUID_PATTERN.match(parts[1]) is None:
            return False

        parent, child = parts[0], parts[2]
        return (
            (parent == 'departments' and child in {'detail', 'users', 'folders', 'documents'})
            or (parent == 'folders' and child in {'documents', 'permissions'})
            or (parent == 'documents' and child in {'permissions', 'versions', 'assets'})
        )

    def _is_supporting_collection_read(self, parts: list[str]) -> bool:
        if len(parts) < 3:
            return False

        supporting_children = {
            'assets',
            'attachments',
            'chunks',
            'documents',
            'folders',
            'messages',
            'permissions',
            'users',
            'versions',
        }
        return self.UUID_PATTERN.match(parts[1]) is not None and parts[2] in supporting_children

    def _build_description(
        self,
        attempted_action: str,
        resource_type: str | None,
        resource_id: str | None,
        path: str,
        status_value: str,
        status_code: int,
    ) -> str:
        resource_label = self._resource_label(resource_type)
        action_labels = {
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
            'IMPORT': 'Nhập dữ liệu',
        }

        action_label = action_labels.get(attempted_action, attempted_action)
        target = resource_label or self._fallback_resource_from_path(path)
        status_suffix = '' if status_value == 'success' else f" - {status_value} ({status_code})"

        if attempted_action in {'CHAT_MESSAGE', 'FEEDBACK'}:
            return f"{action_label}{status_suffix}"

        return f"{action_label} {target}{status_suffix}".strip()

    def _resource_label(self, resource_type: str | None) -> str:
        labels = {
            'documents': 'tài liệu',
            'folders': 'thư mục',
            'users': 'người dùng',
            'accounts': 'tài khoản',
            'departments': 'phòng ban',
            'roles': 'vai trò',
            'permissions': 'quyền',
            'chat_sessions': 'cuộc chat',
            'chat_messages': 'tin nhắn chat',
            'deleted_documents': 'tài liệu đã xóa',
            'deleted_folders': 'thư mục đã xóa',
        }
        return labels.get(resource_type or '', resource_type or '')

    def _fallback_resource_from_path(self, path: str) -> str:
        parts = [part for part in path.strip('/').split('/') if part]
        while parts and parts[0].lower() in self.API_PREFIX_PARTS:
            parts.pop(0)
        return parts[0].replace('-', ' ') if parts else 'dữ liệu'

    def _status_from_code(self, status_code: int) -> str:
        if status_code in (401, 403):
            return 'denied'
        if status_code >= 400:
            return 'failed'
        return 'success'

    def _build_metadata(self, request: HttpRequest, response, attempted_action: str) -> dict[str, Any]:
        query_params = {
            key: self._sanitize_value(value)
            for key, value in request.GET.items()
            if key.lower() not in self.SENSITIVE_KEYS
        }
        body = getattr(request, '_audit_json', {}) or {}
        body_summary = self._body_summary(body)
        return {
            'attempted_action': attempted_action,
            'request_id': getattr(request, 'request_id', None),
            'query_params': query_params,
            'body_keys': getattr(request, '_audit_body_keys', []),
            'body_summary': body_summary,
            'content_type': request.content_type or '',
            'response_reason': getattr(response, 'reason_phrase', ''),
        }

    def _build_resource_context(self, resource_type: str | None, resource_id: str | None, path: str) -> dict[str, Any]:
        parts = self._normalized_path_parts(path)
        context: dict[str, Any] = {
            'api_label': self._api_label(parts),
        }
        if not resource_type or not resource_id:
            context.update(self._collection_context(resource_type, parts))
            return context

        try:
            if resource_type in {'departments'}:
                context.update(self._department_context(resource_id, parts))
            elif resource_type in {'folders', 'deleted_folders'}:
                context.update(self._folder_context(resource_id, parts))
            elif resource_type in {'documents', 'deleted_documents'}:
                context.update(self._document_context(resource_id, parts))
            elif resource_type == 'chat_sessions':
                context.update(self._conversation_context(resource_id, parts))
            elif resource_type == 'chat_messages':
                context.update(self._message_context(resource_id, parts))
            elif resource_type in {'accounts', 'users'}:
                context.update(self._account_context(resource_id, parts))
            elif resource_type == 'roles':
                context.update(self._simple_model_context(resource_id, 'roles', parts))
            elif resource_type == 'permissions':
                context.update(self._simple_model_context(resource_id, 'permissions', parts))
        except Exception as exc:
            logger.debug("Could not enrich audit resource context: %s", exc, exc_info=True)

        return {key: value for key, value in context.items() if value not in (None, '', [], {})}

    def _department_context(self, resource_id: str, parts: list[str]) -> dict[str, Any]:
        from apps.users.models import Department

        department = self._get_by_id(Department, resource_id)
        if not department:
            return {}

        hierarchy = self._department_hierarchy(department)
        context_label = self._department_view_label(parts)
        return {
            'resource_name': department.name,
            'resource_label': f"Phòng ban: {' > '.join(hierarchy)}",
            'context_label': context_label,
            'department_name': department.name,
            'department_hierarchy': hierarchy,
            'parent_department_name': getattr(department.parent, 'name', None),
        }

    def _folder_context(self, resource_id: str, parts: list[str]) -> dict[str, Any]:
        from apps.documents.models import Folder

        folder = self._get_by_id(Folder, resource_id)
        if not folder:
            return {}

        folder_hierarchy = self._folder_hierarchy(folder)
        department_name = getattr(getattr(folder, 'department', None), 'name', None)
        path_parts = ([department_name] if department_name else []) + folder_hierarchy
        return {
            'resource_name': folder.name,
            'resource_label': f"Thư mục: {' > '.join(path_parts)}",
            'context_label': self._folder_view_label(parts),
            'folder_name': folder.name,
            'folder_hierarchy': folder_hierarchy,
            'department_name': department_name,
            'parent_folder_name': getattr(folder.parent, 'name', None),
        }

    def _document_context(self, resource_id: str, parts: list[str]) -> dict[str, Any]:
        from apps.documents.models import Document

        document = self._get_by_id(Document, resource_id)
        if not document:
            return {}

        folder = getattr(document, 'folder', None)
        department = getattr(document, 'department', None)
        folder_hierarchy = self._folder_hierarchy(folder) if folder else []
        department_name = getattr(department, 'name', None) or getattr(getattr(folder, 'department', None), 'name', None)
        return {
            'resource_name': document.original_name or document.filename,
            'resource_label': f"Tài liệu: {document.original_name or document.filename}",
            'context_label': self._document_view_label(parts),
            'document_name': document.original_name or document.filename,
            'folder_name': getattr(folder, 'name', None),
            'folder_hierarchy': folder_hierarchy,
            'department_name': department_name,
            'file_type': document.file_type,
            'version': document.version,
        }

    def _conversation_context(self, resource_id: str, parts: list[str]) -> dict[str, Any]:
        from apps.operations.models import Conversation

        conversation = self._get_by_id(Conversation, resource_id)
        if not conversation:
            return {}

        latest_user_message = conversation.messages.filter(
            role='user',
            is_deleted=False,
        ).order_by('-created_at').first()
        return {
            'resource_name': conversation.title,
            'resource_label': f"Cuộc chat: {conversation.title}",
            'context_label': self._chat_view_label(parts),
            'conversation_title': conversation.title,
            'latest_question': self._sanitize_value(getattr(latest_user_message, 'content', '') or ''),
        }

    def _message_context(self, resource_id: str, parts: list[str]) -> dict[str, Any]:
        from apps.operations.models import Message

        message = self._get_by_id(Message, resource_id)
        if not message:
            return {}

        conversation = getattr(message, 'conversation', None)
        question = message.content if message.role == 'user' else ''
        if not question and conversation:
            previous_user_message = conversation.messages.filter(
                role='user',
                created_at__lte=message.created_at,
                is_deleted=False,
            ).order_by('-created_at').first()
            question = getattr(previous_user_message, 'content', '') or ''

        return {
            'resource_name': getattr(conversation, 'title', None) or str(message.id),
            'resource_label': f"Tin nhắn chat: {getattr(conversation, 'title', None) or str(message.id)}",
            'context_label': self._chat_view_label(parts),
            'conversation_title': getattr(conversation, 'title', None),
            'chat_question': self._sanitize_value(question),
            'message_role': message.role,
        }

    def _account_context(self, resource_id: str, parts: list[str]) -> dict[str, Any]:
        from apps.users.models import Account, UserProfile

        if parts and parts[0] == 'users':
            profile = UserProfile.objects.filter(id=resource_id).select_related('account', 'department').first()
            account = getattr(profile, 'account', None)
        else:
            account = self._get_by_id(Account, resource_id)
            profile = UserProfile.objects.filter(account_id=resource_id).select_related('department').first()
        display_name = (
            getattr(profile, 'full_name', None)
            or getattr(account, 'username', None)
            or getattr(account, 'email', None)
        )
        return {
            'resource_name': display_name,
            'resource_label': f"Người dùng: {display_name}" if display_name else None,
            'context_label': self._api_label(parts),
            'department_name': getattr(getattr(profile, 'department', None), 'name', None),
        }

    def _simple_model_context(self, resource_id: str, resource_type: str, parts: list[str]) -> dict[str, Any]:
        from apps.users.models import Permission, Role

        model = Role if resource_type == 'roles' else Permission
        instance = self._get_by_id(model, resource_id)
        if not instance:
            return {}
        name = getattr(instance, 'name', None) or getattr(instance, 'code', None) or str(instance)
        label = 'Vai trò' if resource_type == 'roles' else 'Quyền'
        return {
            'resource_name': name,
            'resource_label': f"{label}: {name}",
            'context_label': self._iam_view_label(resource_type, parts),
        }

    def _collection_context(self, resource_type: str | None, parts: list[str]) -> dict[str, Any]:
        if parts == ['users'] or parts == ['accounts']:
            return {
                'resource_name': 'Danh sách người dùng',
                'resource_label': 'Danh sách người dùng',
                'context_label': 'Xem danh sách người dùng',
            }
        if parts == ['departments']:
            return {
                'resource_name': 'Danh sách phòng ban',
                'resource_label': 'Danh sách phòng ban',
                'context_label': 'Xem sơ đồ/danh sách phòng ban',
            }
        if parts == ['folders']:
            return {
                'resource_name': 'Kho thư mục',
                'resource_label': 'Kho thư mục',
                'context_label': 'Xem kho thư mục',
            }
        if parts == ['folders', 'permissions']:
            return {
                'resource_name': 'Quyền truy cập thư mục',
                'resource_label': 'Quyền truy cập thư mục',
                'context_label': 'Xem tổng quan quyền truy cập thư mục',
            }
        if parts == ['documents']:
            return {
                'resource_name': 'Danh sách tài liệu',
                'resource_label': 'Danh sách tài liệu',
                'context_label': 'Xem danh sách tài liệu',
            }
        if parts == ['documents', 'shared-with-me']:
            return {
                'resource_name': 'Tài liệu được chia sẻ với tôi',
                'resource_label': 'Tài liệu được chia sẻ với tôi',
                'context_label': 'Xem tài liệu được chia sẻ với tôi',
            }
        if parts == ['documents', 'permissions']:
            return {
                'resource_name': 'Quyền truy cập tài liệu',
                'resource_label': 'Quyền truy cập tài liệu',
                'context_label': 'Xem tổng quan quyền truy cập tài liệu',
            }
        if parts == ['chat', 'conversations']:
            return {
                'resource_name': 'Danh sách cuộc chat',
                'resource_label': 'Danh sách cuộc chat',
                'context_label': 'Xem danh sách cuộc chat',
            }
        if parts == ['chat', 'available-attachments']:
            return {
                'resource_name': 'Tài liệu/thư mục có thể đính kèm chat',
                'resource_label': 'Tài liệu/thư mục có thể đính kèm chat',
                'context_label': 'Xem tài liệu/thư mục có thể dùng trong chat',
            }
        if len(parts) == 2 and parts[0] == 'deleted':
            deleted_labels = {
                'documents': 'Tài liệu đã xóa',
                'folders': 'Thư mục đã xóa',
                'departments': 'Phòng ban đã xóa',
                'users': 'Người dùng đã xóa',
                'accounts': 'Tài khoản đã xóa',
                'roles': 'Vai trò đã xóa',
                'permissions': 'Quyền hạn đã xóa',
            }
            label = deleted_labels.get(parts[1], 'Dữ liệu đã xóa')
            return {
                'resource_name': label,
                'resource_label': label,
                'context_label': f'Xem thùng rác: {label.lower()}',
            }
        if resource_type == 'roles':
            return {
                'resource_name': 'Danh sách vai trò',
                'resource_label': 'Danh sách vai trò',
                'context_label': 'Xem danh sách vai trò và quyền hạn',
            }
        if resource_type == 'permissions':
            return {
                'resource_name': 'Danh sách quyền hạn',
                'resource_label': 'Danh sách quyền hạn',
                'context_label': 'Xem danh sách quyền hạn hệ thống',
            }
        return {}

    def _iam_view_label(self, resource_type: str, parts: list[str]) -> str:
        if resource_type == 'roles':
            if len(parts) >= 4 and parts[0] == 'iam' and parts[1] == 'roles' and parts[3] == 'permissions':
                return 'Xem các quyền đang gán cho vai trò'
            return 'Xem chi tiết vai trò'
        if resource_type == 'permissions':
            return 'Xem chi tiết quyền hạn'
        return self._api_label(parts)

    def _get_by_id(self, model, object_id: str):
        manager = model.objects
        if hasattr(manager, 'all_records'):
            manager = manager.all_records()
        return manager.filter(id=object_id).first()

    def _department_hierarchy(self, department) -> list[str]:
        chain = []
        current = department
        seen = set()
        while current and current.id not in seen:
            seen.add(current.id)
            chain.append(current.name)
            current = current.parent
        return list(reversed(chain))

    def _folder_hierarchy(self, folder) -> list[str]:
        if not folder:
            return []
        chain = []
        current = folder
        seen = set()
        while current and current.id not in seen:
            seen.add(current.id)
            chain.append(current.name)
            current = current.parent
        return list(reversed(chain))

    def _department_view_label(self, parts: list[str]) -> str:
        if len(parts) < 3:
            return 'Xem chi tiết phòng ban'
        return {
            'detail': 'Xem tổng quan phòng ban',
            'users': 'Xem nhân sự trong phòng ban',
            'folders': 'Xem kho thư mục của phòng ban',
            'documents': 'Xem tài liệu trong phòng ban',
        }.get(parts[2], self._api_label(parts))

    def _folder_view_label(self, parts: list[str]) -> str:
        if len(parts) >= 3:
            return {
                'documents': 'Xem tài liệu trong thư mục',
                'permissions': 'Xem quyền truy cập thư mục',
                'move': 'Di chuyển thư mục',
            }.get(parts[2], self._api_label(parts))
        return 'Xem chi tiết thư mục'

    def _document_view_label(self, parts: list[str]) -> str:
        if len(parts) >= 3:
            return {
                'download': 'Tải xuống tài liệu',
                'preview': 'Xem trước tài liệu',
                'permissions': 'Xem quyền truy cập tài liệu',
                'versions': 'Xem phiên bản tài liệu',
                'assets': 'Xem ảnh/bảng biểu trích xuất từ tài liệu',
                'move': 'Di chuyển tài liệu',
                'status': 'Xem trạng thái xử lý tài liệu',
                'reprocess': 'Lập chỉ mục lại tài liệu',
            }.get(parts[2], self._api_label(parts))
        return 'Xem chi tiết tài liệu'

    def _chat_view_label(self, parts: list[str]) -> str:
        if len(parts) >= 4 and parts[3] == 'messages':
            return 'Xem lịch sử tin nhắn của cuộc chat'
        if len(parts) >= 4 and parts[3] == 'attachments':
            return 'Xem tài liệu/thư mục đính kèm cuộc chat'
        if len(parts) >= 2 and parts[1] == 'messages':
            return 'Gửi câu hỏi chat'
        return 'Xem cuộc chat'

    def _api_label(self, parts: list[str]) -> str:
        if not parts:
            return 'Dữ liệu hệ thống'
        return ' / '.join(parts)

    def _body_summary(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}

        summary: dict[str, Any] = {}
        content = payload.get('content') or payload.get('query') or payload.get('question')
        if content:
            summary['chat_question'] = self._sanitize_value(content)

        for key in ('conversation_id', 'document_ids', 'folder_ids', 'rag_mode', 'retrieval_mode', 'current_page', 'currentPage'):
            if key not in payload:
                continue
            value = payload.get(key)
            if isinstance(value, list):
                summary[key] = [self._sanitize_value(item) for item in value[:10]]
                summary[f'{key}_count'] = len(value)
            else:
                summary[key] = self._sanitize_value(value)

        return summary

    def _safe_body_keys(self, payload: Any) -> list[str]:
        if isinstance(payload, dict):
            return sorted(
                key for key in payload.keys()
                if str(key).lower() not in self.SENSITIVE_KEYS
            )
        if isinstance(payload, list):
            return ['list']
        return []

    def _safe_json_payload(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        return {
            key: value
            for key, value in payload.items()
            if str(key).lower() not in self.SENSITIVE_KEYS
        }

    def _sanitize_value(self, value: Any) -> str:
        if value is None:
            return ''
        return str(value)[:200]

    def _is_uuid(self, value: Any) -> bool:
        try:
            UUID(str(value))
            return True
        except (TypeError, ValueError):
            return False

    def _get_client_ip(self, request: HttpRequest) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()[:45]

        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip[:45]

        return (request.META.get('REMOTE_ADDR') or '')[:45]
