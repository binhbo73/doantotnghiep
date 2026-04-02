"""
Core Constants - Define toàn bộ hằng số ứng dụng.
Tất cả file khác import từ module này để đảm bảo nhất quán.
"""

# ============================================================
# APPLICATION INFO
# ============================================================
APP_NAME = "RAG System"
APP_VERSION = "1.0.0"
APP_ENVIRONMENT = "development"  # development | staging | production


# ============================================================
# ROLE DEFINITIONS (Fixed IDs for Database)
# ============================================================
class RoleIds:
    """Role IDs - KHÔNG ĐƯỢC THAY ĐỔI sau khi deploy"""
    ADMIN = 1
    MANAGER = 2
    USER = 3

class RoleNames:
    """Role names"""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"

ROLES = {
    RoleIds.ADMIN: {
        "name": RoleNames.ADMIN,
        "description": "Administrator - Full access to system"
    },
    RoleIds.MANAGER: {
        "name": RoleNames.MANAGER,
        "description": "Department Manager - Manage department resources"
    },
    RoleIds.USER: {
        "name": RoleNames.USER,
        "description": "Regular User - Basic access"
    },
}


# ============================================================
# PERMISSION CODES (For Fine-grained Access Control)
# ============================================================
class PermissionCodes:
    """
    Permission codes follow pattern: {resource}_{action}
    Used in decorator: @require_permission(PermissionCodes.DOCUMENT_VIEW)
    """
    
    # User Management Permissions
    USER_CREATE = "user_create"
    USER_READ = "user_read"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_CHANGE_ROLE = "user_change_role"
    
    # Document Permissions
    DOCUMENT_CREATE = "document_create"
    DOCUMENT_READ = "document_read"
    DOCUMENT_UPDATE = "document_update"
    DOCUMENT_WRITE = "document_write"     # Alias for write/update operations
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_SHARE = "document_share"
    DOCUMENT_DOWNLOAD = "document_download"
    
    # Folder Permissions
    FOLDER_CREATE = "folder_create"
    FOLDER_READ = "folder_read"
    FOLDER_UPDATE = "folder_update"
    FOLDER_DELETE = "folder_delete"
    
    # Department Permissions
    DEPARTMENT_READ = "department_read"
    DEPARTMENT_UPDATE = "department_update"
    DEPARTMENT_MANAGE = "department_manage"
    
    # Permission Management
    PERMISSION_MANAGE = "permission_manage"
    ROLE_MANAGE = "role_manage"
    
    # AI/RAG Permissions
    RAG_QUERY = "rag_query"
    EMBEDDING_GENERATE = "embedding_generate"
    
    # Audit & System
    AUDIT_LOG_VIEW = "audit_log_view"
    SYSTEM_ADMIN = "system_admin"

# All permission codes as list (for validation)
ALL_PERMISSIONS = [
    # User
    PermissionCodes.USER_CREATE,
    PermissionCodes.USER_READ,
    PermissionCodes.USER_UPDATE,
    PermissionCodes.USER_DELETE,
    PermissionCodes.USER_CHANGE_ROLE,
    # Document
    PermissionCodes.DOCUMENT_CREATE,
    PermissionCodes.DOCUMENT_READ,
    PermissionCodes.DOCUMENT_UPDATE,
    PermissionCodes.DOCUMENT_WRITE,
    PermissionCodes.DOCUMENT_DELETE,
    PermissionCodes.DOCUMENT_SHARE,
    PermissionCodes.DOCUMENT_DOWNLOAD,
    # Folder
    PermissionCodes.FOLDER_CREATE,
    PermissionCodes.FOLDER_READ,
    PermissionCodes.FOLDER_UPDATE,
    PermissionCodes.FOLDER_DELETE,
    # Department
    PermissionCodes.DEPARTMENT_READ,
    PermissionCodes.DEPARTMENT_UPDATE,
    PermissionCodes.DEPARTMENT_MANAGE,
    # Administration
    PermissionCodes.PERMISSION_MANAGE,
    PermissionCodes.ROLE_MANAGE,
    # RAG
    PermissionCodes.RAG_QUERY,
    PermissionCodes.EMBEDDING_GENERATE,
    # Audit
    PermissionCodes.AUDIT_LOG_VIEW,
    PermissionCodes.SYSTEM_ADMIN,
]


# ============================================================
# ACCOUNT STATUS
# ============================================================
class AccountStatus:
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"

ACCOUNT_STATUSES = [
    (AccountStatus.ACTIVE, "Active"),
    (AccountStatus.INACTIVE, "Inactive"),
    (AccountStatus.BLOCKED, "Blocked"),
]


# ============================================================
# ACCESS SCOPE (Folder Permission Inheritance)
# ============================================================
class AccessScope:
    """Folder/Resource access scope levels"""
    PERSONAL = "personal"       # Only owner
    DEPARTMENT = "department"   # Department members
    COMPANY = "company"         # All employees

ACCESS_SCOPES = [
    (AccessScope.PERSONAL, "Personal - Only Owner"),
    (AccessScope.DEPARTMENT, "Department - Department Members"),
    (AccessScope.COMPANY, "Company - All Employees"),
]


# ============================================================
# AUDIT LOG ACTION TYPES
# ============================================================
class AuditActionType:
    """Actions tracked in AuditLog"""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    ROLE_CHANGE = "ROLE_CHANGE"
    SHARE = "SHARE"
    DOWNLOAD = "DOWNLOAD"
    UPLOAD = "UPLOAD"
    EXPORT = "EXPORT"

AUDIT_ACTION_TYPES = [
    (AuditActionType.CREATE, "Create"),
    (AuditActionType.READ, "Read"),
    (AuditActionType.UPDATE, "Update"),
    (AuditActionType.DELETE, "Delete"),
    (AuditActionType.LOGIN, "Login"),
    (AuditActionType.LOGOUT, "Logout"),
    (AuditActionType.PERMISSION_CHANGE, "Permission Change"),
    (AuditActionType.ROLE_CHANGE, "Role Change"),
    (AuditActionType.SHARE, "Share"),
    (AuditActionType.DOWNLOAD, "Download"),
    (AuditActionType.UPLOAD, "Upload"),
    (AuditActionType.EXPORT, "Export"),
]


# ============================================================
# PAGINATION & LIST DEFAULTS
# ============================================================
DEFAULT_PAGE_SIZE = 10
DEFAULT_PAGE_SIZE_LARGE = 50
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1


# ============================================================
# FILE UPLOAD CONSTRAINTS
# ============================================================
MAX_FILE_SIZE = 52428800  # 50 MB (bytes)
MAX_FILE_NAME_LENGTH = 255
ALLOWED_FILE_EXTENSIONS = {
    # Documents
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xls': 'application/vnd.ms-excel',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'ppt': 'application/vnd.ms-powerpoint',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'txt': 'text/plain',
    'md': 'text/markdown',
    # Images
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
}


# ============================================================
# DOCUMENT PROCESSING (RAG)
# ============================================================
# Chunking strategy
CHUNK_SIZE = 512  # tokens per chunk
CHUNK_OVERLAP = 50  # overlap between chunks
MIN_CHUNK_SIZE = 100  # minimum chunk size

# Embedding
EMBEDDING_MODEL_NAME = "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
EMBEDDING_DIMENSION = 1536  # Vector dimension (depends on model)

# RAG Search
RAG_TOP_K = 5  # Retrieve top 5 similar documents
RAG_SIMILARITY_THRESHOLD = 0.5  # Minimum similarity score
RERANK_TOP_K = 3  # Re-rank top 3 results


# ============================================================
# CACHE TIMEOUTS (Seconds)
# ============================================================
CACHE_TIMEOUT_SHORT = 300  # 5 minutes
CACHE_TIMEOUT_MEDIUM = 3600  # 1 hour
CACHE_TIMEOUT_LONG = 86400  # 1 day
CACHE_TIMEOUT_VERY_LONG = 604800  # 1 week

# Cache keys
CACHE_KEY_PERMISSIONS = "permissions:{user_id}"
CACHE_KEY_USER_ROLES = "user_roles:{user_id}"
CACHE_KEY_DEPARTMENT_TREE = "dept_tree:{dept_id}"


# ============================================================
# JWT & AUTHENTICATION
# ============================================================
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_LIFETIME_MINUTES = 15  # 15 minutes
JWT_REFRESH_TOKEN_LIFETIME_DAYS = 7  # 7 days
JWT_AUTH_HEADER_PREFIX = "Bearer"


# ============================================================
# API RESPONSE CODES & MESSAGES
# ============================================================
class ApiStatusCode:
    """API response status codes (like HTTP but more granular)"""
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    VALIDATION_ERROR = 422
    INTERNAL_ERROR = 500
    SERVICE_UNAVAILABLE = 503


class ApiMessage:
    """Standard API response messages"""
    SUCCESS = "Success"
    CREATED = "Created successfully"
    UPDATED = "Updated successfully"
    DELETED = "Deleted successfully"
    
    # Errors
    INVALID_INPUT = "Invalid input"
    UNAUTHORIZED = "Unauthorized"
    FORBIDDEN = "Forbidden"
    NOT_FOUND = "Resource not found"
    CONFLICT = "Resource already exists"
    SERVER_ERROR = "Internal server error"
    
    # Validation
    FIELD_REQUIRED = "This field is required"
    INVALID_EMAIL = "Invalid email address"
    INVALID_PHONE = "Invalid phone number"
    PASSWORD_TOO_SHORT = "Password must be at least 8 characters"
    PASSWORDS_NOT_MATCH = "Passwords do not match"


# ============================================================
# VALIDATION CONSTRAINTS
# ============================================================
# User
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 50
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# Document
MIN_DOCUMENT_NAME_LENGTH = 1
MAX_DOCUMENT_NAME_LENGTH = 255

# Folder
MIN_FOLDER_NAME_LENGTH = 1
MAX_FOLDER_NAME_LENGTH = 100

# Department
MAX_DEPARTMENT_NAME_LENGTH = 100


# ============================================================
# TIMEOUT CONFIGURATIONS (Seconds)
# ============================================================
TIMEOUT_DATABASE_QUERY = 30
TIMEOUT_AI_REQUEST = 120  # LLM/Embedding requests can be long
TIMEOUT_VECTOR_SEARCH = 30
TIMEOUT_FILE_UPLOAD = 600  # 10 minutes


# ============================================================
# LOGGING
# ============================================================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# ============================================================
# REDIS CONFIGURATIONS
# ============================================================
REDIS_CONNECTION_POOL_SIZE = 10
REDIS_SOCKET_TIMEOUT = 5
REDIS_SOCKET_CONNECT_TIMEOUT = 5


# ============================================================
# QDRANT VECTOR DATABASE
# ============================================================
QDRANT_COLLECTION_NAME = "documents"
QDRANT_VECTOR_SIZE = 1536  # Should match EMBEDDING_DIMENSION
QDRANT_REPLICATION_FACTOR = 1
QDRANT_SHARD_NUMBER = 1


# ============================================================
# LLM CONFIGURATION
# ============================================================
LLM_MODEL_NAME = "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
LLM_TEMPERATURE = 0.7
LLM_TOP_P = 0.9
LLM_MAX_TOKENS = 2048
LLM_CONTEXT_WINDOW = 8192


# ============================================================
# DEFAULT ORGANIZATION SETTINGS
# ============================================================
DEFAULT_COMPANY_NAME = "RAG System Company"
DEFAULT_ROOT_DEPARTMENT_NAME = "Root"
