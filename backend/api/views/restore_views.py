from django.apps import apps
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.constants import PermissionCodes
from core.exceptions import BusinessLogicError, ConflictError, NotFoundError
from core.permissions.drf_permissions import user_has_permission
from core.utils.response_builder import ResponseBuilder


RESOURCE_CONFIG = {
    "accounts": {
        "app": "users",
        "model": "Account",
        "permission": PermissionCodes.USER_DELETE,
        "label": "account",
    },
    "user_profiles": {
        "app": "users",
        "model": "UserProfile",
        "permission": PermissionCodes.USER_DELETE,
        "label": "user_profile",
        "parents": [
            {"field": "account_id", "app": "users", "model": "Account", "label": "account"},
            {"field": "department_id", "app": "users", "model": "Department", "label": "department"},
        ],
    },
    "password_reset_tokens": {
        "app": "users",
        "model": "PasswordResetToken",
        "permission": PermissionCodes.USER_RESET_PASSWORD,
        "label": "password_reset_token",
        "parents": [
            {"field": "account_id", "app": "users", "model": "Account", "label": "account"},
        ],
    },
    "departments": {
        "app": "users",
        "model": "Department",
        "permission": PermissionCodes.DEPARTMENT_MANAGE,
        "label": "department",
        "parents": [
            {"field": "parent_id", "app": "users", "model": "Department", "label": "parent department"},
        ],
    },
    "roles": {
        "app": "users",
        "model": "Role",
        "permission": PermissionCodes.ROLE_MANAGE,
        "label": "role",
    },
    "permissions": {
        "app": "users",
        "model": "Permission",
        "permission": PermissionCodes.PERMISSION_MANAGE,
        "label": "permission",
    },
    "role_permissions": {
        "app": "users",
        "model": "RolePermission",
        "permission": PermissionCodes.ROLE_MANAGE,
        "label": "role_permission",
        "parents": [
            {"field": "role_id", "app": "users", "model": "Role", "label": "role"},
            {"field": "permission_id", "app": "users", "model": "Permission", "label": "permission"},
        ],
    },
    "account_roles": {
        "app": "users",
        "model": "AccountRole",
        "permission": PermissionCodes.USER_CHANGE_ROLE,
        "label": "account_role",
        "parents": [
            {"field": "account_id", "app": "users", "model": "Account", "label": "account"},
            {"field": "role_id", "app": "users", "model": "Role", "label": "role"},
        ],
    },
    "companies": {
        "app": "users",
        "model": "Company",
        "permission": PermissionCodes.SYSTEM_ADMIN,
        "label": "company",
    },
    "folders": {
        "app": "documents",
        "model": "Folder",
        "permission": PermissionCodes.FOLDER_DELETE,
        "label": "folder",
        "parents": [
            {"field": "parent_id", "app": "documents", "model": "Folder", "label": "parent folder"},
            {"field": "department_id", "app": "users", "model": "Department", "label": "department"},
            {"field": "created_by_id", "app": "users", "model": "Account", "label": "creator account"},
        ],
    },
    "tags": {
        "app": "documents",
        "model": "Tag",
        "permission": PermissionCodes.DOCUMENT_UPDATE,
        "label": "tag",
        "parents": [
            {"field": "created_by_id", "app": "users", "model": "Account", "label": "creator account"},
        ],
    },
    "documents": {
        "app": "documents",
        "model": "Document",
        "permission": PermissionCodes.DOCUMENT_DELETE,
        "label": "document",
        "parents": [
            {"field": "uploader_id", "app": "users", "model": "Account", "label": "uploader account"},
            {"field": "department_id", "app": "users", "model": "Department", "label": "department"},
            {"field": "folder_id", "app": "documents", "model": "Folder", "label": "folder"},
            {"field": "previous_version_id", "app": "documents", "model": "Document", "label": "previous document version"},
        ],
    },
    "document_chunks": {
        "app": "documents",
        "model": "DocumentChunk",
        "permission": PermissionCodes.DOCUMENT_DELETE,
        "label": "document_chunk",
        "parents": [
            {"field": "document_id", "app": "documents", "model": "Document", "label": "document"},
            {"field": "parent_node_id", "app": "documents", "model": "DocumentChunk", "label": "parent chunk"},
            {"field": "previous_version_chunk_id", "app": "documents", "model": "DocumentChunk", "label": "previous version chunk"},
        ],
    },
    "chunk_revision_links": {
        "app": "documents",
        "model": "ChunkRevisionLink",
        "permission": PermissionCodes.DOCUMENT_DELETE,
        "label": "chunk_revision_link",
        "parents": [
            {"field": "from_chunk_id", "app": "documents", "model": "DocumentChunk", "label": "source chunk"},
            {"field": "to_chunk_id", "app": "documents", "model": "DocumentChunk", "label": "target chunk"},
        ],
    },
    "document_permissions": {
        "app": "documents",
        "model": "DocumentPermission",
        "permission": PermissionCodes.DOCUMENT_SHARE,
        "label": "document_permission",
        "parents": [
            {"field": "document_id", "app": "documents", "model": "Document", "label": "document"},
            {"field": "granted_by_id", "app": "users", "model": "Account", "label": "granting account"},
        ],
    },
    "folder_permissions": {
        "app": "documents",
        "model": "FolderPermission",
        "permission": PermissionCodes.FOLDER_UPDATE,
        "label": "folder_permission",
        "parents": [
            {"field": "folder_id", "app": "documents", "model": "Folder", "label": "folder"},
            {"field": "granted_by_id", "app": "users", "model": "Account", "label": "granting account"},
        ],
    },
    "document_embeddings": {
        "app": "documents",
        "model": "DocumentEmbedding",
        "permission": PermissionCodes.DOCUMENT_DELETE,
        "label": "document_embedding",
        "parents": [
            {"field": "chunk_id", "app": "documents", "model": "DocumentChunk", "label": "document chunk"},
        ],
    },
    "document_assets": {
        "app": "documents",
        "model": "DocumentAsset",
        "permission": PermissionCodes.DOCUMENT_DELETE,
        "label": "document_asset",
        "parents": [
            {"field": "document_id", "app": "documents", "model": "Document", "label": "document"},
            {"field": "chunk_id", "app": "documents", "model": "DocumentChunk", "label": "document chunk"},
        ],
    },
    "conversations": {
        "app": "operations",
        "model": "Conversation",
        "permission": PermissionCodes.CHAT_CREATE,
        "label": "conversation",
        "parents": [
            {"field": "account_id", "app": "users", "model": "Account", "label": "account"},
        ],
    },
    "conversation_documents": {
        "app": "operations",
        "model": "ConversationAttachedDocument",
        "permission": PermissionCodes.CHAT_CREATE,
        "label": "conversation_document",
        "parents": [
            {"field": "conversation_id", "app": "operations", "model": "Conversation", "label": "conversation"},
            {"field": "document_id", "app": "documents", "model": "Document", "label": "document"},
        ],
    },
    "conversation_folders": {
        "app": "operations",
        "model": "ConversationAttachedFolder",
        "permission": PermissionCodes.CHAT_CREATE,
        "label": "conversation_folder",
        "parents": [
            {"field": "conversation_id", "app": "operations", "model": "Conversation", "label": "conversation"},
            {"field": "folder_id", "app": "documents", "model": "Folder", "label": "folder"},
        ],
    },
    "messages": {
        "app": "operations",
        "model": "Message",
        "permission": PermissionCodes.CHAT_SEND,
        "label": "message",
        "parents": [
            {"field": "conversation_id", "app": "operations", "model": "Conversation", "label": "conversation"},
        ],
    },
    "human_feedback": {
        "app": "operations",
        "model": "HumanFeedback",
        "permission": PermissionCodes.CHAT_SEND,
        "label": "human_feedback",
        "parents": [
            {"field": "message_id", "app": "operations", "model": "Message", "label": "message"},
            {"field": "account_id", "app": "users", "model": "Account", "label": "account"},
        ],
    },
    "audit_logs": {
        "app": "operations",
        "model": "AuditLog",
        "permission": PermissionCodes.AUDIT_LOG_VIEW,
        "label": "audit_log",
        "parents": [
            {"field": "account_id", "app": "users", "model": "Account", "label": "account"},
        ],
    },
    "async_tasks": {
        "app": "operations",
        "model": "AsyncTask",
        "permission": PermissionCodes.SYSTEM_ADMIN,
        "label": "async_task",
        "parents": [
            {"field": "document_id", "app": "documents", "model": "Document", "label": "document"},
            {"field": "chunk_id", "app": "documents", "model": "DocumentChunk", "label": "document chunk"},
        ],
    },
    "user_document_caches": {
        "app": "operations",
        "model": "UserDocumentCache",
        "permission": PermissionCodes.SYSTEM_ADMIN,
        "label": "user_document_cache",
        "parents": [
            {"field": "account_id", "app": "users", "model": "Account", "label": "account"},
            {"field": "document_id", "app": "documents", "model": "Document", "label": "document"},
        ],
    },
}


class DeletedRecordsView(APIView):
    """
    List soft-deleted records for admin restore screens.

    GET /api/v1/deleted/{resource}
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, resource):
        config = RESOURCE_CONFIG.get(resource)
        if not config:
            return Response(
                ResponseBuilder.error(
                    message="Unsupported deleted resource",
                    status_code=status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        if not self._has_restore_permission(request.user, config["permission"]):
            return Response(
                ResponseBuilder.error(
                    message="You do not have permission to view deleted records",
                    status_code=status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        model_class = self._get_model(config)
        page = max(int(request.query_params.get("page", 1)), 1)
        page_size = min(max(int(request.query_params.get("page_size", 20)), 1), 100)
        offset = (page - 1) * page_size

        queryset = (
            model_class.objects.all_records()
            .filter(is_deleted=True)
            .order_by("-deleted_at", "-created_at")
        )
        if resource == "folders":
            FolderDeletionOperation = apps.get_model(
                "documents",
                "FolderDeletionOperation",
            )
            active_operations = FolderDeletionOperation.objects.filter(
                status=FolderDeletionOperation.STATUS_DELETED,
            ).values("root_folder_id", "snapshot")
            cascade_child_ids = set()
            for operation in active_operations:
                root_id = str(operation["root_folder_id"])
                cascade_child_ids.update(
                    str(folder_id)
                    for folder_id in (operation["snapshot"] or {}).get("folder_ids", [])
                    if str(folder_id) != root_id
                )
            if cascade_child_ids:
                queryset = queryset.exclude(id__in=cascade_child_ids)

        total = queryset.count()
        items = [self._serialize_deleted_record(obj, config["label"]) for obj in queryset[offset:offset + page_size]]

        return Response(
            ResponseBuilder.success(
                data={
                    "items": items,
                    "page": page,
                    "page_size": page_size,
                    "total_items": total,
                    "total_pages": (total + page_size - 1) // page_size,
                },
                message=f"Deleted {resource} retrieved",
            ),
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _get_model(config):
        return apps.get_model(config["app"], config["model"])

    @staticmethod
    def _has_restore_permission(user, permission_code):
        return (
            getattr(user, "is_superuser", False)
            or user_has_permission(user, PermissionCodes.SYSTEM_ADMIN)
            or user_has_permission(user, permission_code)
        )

    @staticmethod
    def _serialize_deleted_record(obj, resource_type):
        name = (
            getattr(obj, "original_name", None)
            or getattr(obj, "name", None)
            or getattr(obj, "username", None)
            or getattr(obj, "code", None)
            or str(obj)
        )
        return {
            "id": str(obj.id),
            "type": resource_type,
            "name": name,
            "deleted_at": obj.deleted_at,
            "created_at": getattr(obj, "created_at", None),
        }


class RestoreRecordView(APIView):
    """
    Restore a soft-deleted record.

    POST /api/v1/deleted/{resource}/{id}/restore
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, resource, object_id):
        config = RESOURCE_CONFIG.get(resource)
        if not config:
            return Response(
                ResponseBuilder.error(
                    message="Unsupported restore resource",
                    status_code=status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        if not DeletedRecordsView._has_restore_permission(request.user, config["permission"]):
            return Response(
                ResponseBuilder.error(
                    message="You do not have permission to restore this resource",
                    status_code=status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        model_class = DeletedRecordsView._get_model(config)
        try:
            obj = model_class.objects.all_records().get(id=object_id)
        except model_class.DoesNotExist:
            return Response(
                ResponseBuilder.error(
                    message=f"Deleted {config['label']} not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        if not obj.is_deleted:
            return Response(
                ResponseBuilder.error(
                    message=f"{config['label'].title()} is already active",
                    status_code=status.HTTP_409_CONFLICT,
                ),
                status=status.HTTP_409_CONFLICT,
            )

        conflict = self._restore_conflict(obj, resource, config)
        if conflict:
            return Response(
                ResponseBuilder.error(
                    message=conflict,
                    status_code=status.HTTP_409_CONFLICT,
                ),
                status=status.HTTP_409_CONFLICT,
            )

        if resource in {"departments", "folders"}:
            try:
                if resource == "departments":
                    from services.department_service import DepartmentService

                    restore_result = DepartmentService().restore_deleted_department(
                        dept_id=str(obj.id),
                        requested_by_user_id=str(request.user.id),
                    )
                else:
                    from services.folder_service import FolderService

                    FolderDeletionOperation = apps.get_model(
                        "documents",
                        "FolderDeletionOperation",
                    )
                    has_cascade_operation = FolderDeletionOperation.objects.filter(
                        root_folder_id=obj.id,
                        status=FolderDeletionOperation.STATUS_DELETED,
                    ).exists()
                    if has_cascade_operation:
                        restore_result = FolderService().restore_deleted_folder(
                            folder_id=str(obj.id),
                            requested_by_user_id=str(request.user.id),
                        )
                    else:
                        obj.restore()
                        restore_result = {
                            "id": str(obj.id),
                            "type": config["label"],
                            "is_deleted": obj.is_deleted,
                            "deleted_at": obj.deleted_at,
                        }
            except ConflictError as exc:
                return Response(
                    ResponseBuilder.error(
                        message=str(exc),
                        status_code=status.HTTP_409_CONFLICT,
                    ),
                    status=status.HTTP_409_CONFLICT,
                )
            except NotFoundError as exc:
                return Response(
                    ResponseBuilder.error(
                        message=str(exc),
                        status_code=status.HTTP_404_NOT_FOUND,
                    ),
                    status=status.HTTP_404_NOT_FOUND,
                )
            except BusinessLogicError as exc:
                return Response(
                    ResponseBuilder.error(
                        message=str(exc),
                        status_code=status.HTTP_400_BAD_REQUEST,
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            obj.restore()
            restore_result = {
                "id": str(obj.id),
                "type": config["label"],
                "is_deleted": obj.is_deleted,
                "deleted_at": obj.deleted_at,
            }
        self._log_restore(request, obj, config["label"])

        return Response(
            ResponseBuilder.success(
                data=restore_result,
                message=f"{config['label'].title()} restored successfully",
            ),
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _restore_conflict(obj, resource, config):
        for parent_config in config.get("parents", []):
            parent_id = getattr(obj, parent_config["field"], None)
            if not parent_id:
                continue

            parent_model = apps.get_model(parent_config["app"], parent_config["model"])
            parent = parent_model.objects.all_records().filter(id=parent_id).first()
            if not parent:
                return f"Cannot restore {config['label']} because its {parent_config['label']} no longer exists"
            if getattr(parent, "is_deleted", False):
                return f"Cannot restore {config['label']} while its {parent_config['label']} is deleted"

        if resource in {"document_permissions", "folder_permissions"}:
            subject_conflict = RestoreRecordView._subject_restore_conflict(obj, config)
            if subject_conflict:
                return subject_conflict

        return None

    @staticmethod
    def _subject_restore_conflict(obj, config):
        subject_type = getattr(obj, "subject_type", None)
        subject_id = getattr(obj, "subject_id", None)
        if not subject_type or not subject_id:
            return None

        if subject_type == "account":
            subject_model = apps.get_model("users", "Account")
        elif subject_type == "role":
            subject_model = apps.get_model("users", "Role")
        else:
            return f"Cannot restore {config['label']} with unsupported subject type '{subject_type}'"

        subject = subject_model.objects.all_records().filter(id=subject_id).first()
        if not subject:
            return f"Cannot restore {config['label']} because its {subject_type} subject no longer exists"
        if subject.is_deleted:
            return f"Cannot restore {config['label']} while its {subject_type} subject is deleted"

        return None

    @staticmethod
    def _log_restore(request, obj, resource_type):
        try:
            AuditLog = apps.get_model("operations", "AuditLog")
            AuditLog.log_action(
                account=request.user,
                action="UPDATE",
                resource_id=str(obj.id),
                query_text=f"Restored {resource_type} {obj.id}",
                request=request,
            )
        except Exception:
            pass
