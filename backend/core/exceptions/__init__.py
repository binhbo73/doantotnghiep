"""
Core Exception Classes - Toàn bộ exception tùy chỉnh cho ứng dụng.
Mỗi exception có HTTP status code để mapping sang REST response.
"""
from rest_framework import status


class AppException(Exception):
    """
    Base exception cho ứng dụng.
    
    Attributes:
        status_code: HTTP status code
        message: Chi tiết lỗi
        detail: Thêm thông tin (dict hoặc list)
    """
    
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "Internal server error"
    
    def __init__(self, message=None, detail=None):
        self.message = message or self.default_message
        self.detail = detail  # Có thể là dict chứa field-specific errors
        super().__init__(self.message)


# ============================================================
# VALIDATION ERRORS (400)
# ============================================================
class ValidationError(AppException):
    """Dữ liệu input không hợp lệ"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Validation failed"


class InvalidInputError(AppException):
    """Input không hợp lệ"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Invalid input provided"


class InvalidFileFormatError(ValidationError):
    """File format không được hỗ trợ"""
    default_message = "Invalid file format. Allowed formats: PDF, DOCX, TXT, MD"


class FileSizeExceededError(ValidationError):
    """File quá lớn"""
    default_message = "File size exceeds maximum limit (50 MB)"


class DuplicateError(ValidationError):
    """Resource đã tồn tại"""
    status_code = status.HTTP_409_CONFLICT
    default_message = "Resource already exists"


class ConflictError(AppException):
    """Conflict khi thực hiện hành động"""
    status_code = status.HTTP_409_CONFLICT
    default_message = "Resource conflict"


# ============================================================
# AUTHENTICATION ERRORS (401)
# ============================================================
class AuthenticationError(AppException):
    """Xác thực thất bại"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = "Authentication failed"


class InvalidCredentialsError(AuthenticationError):
    """Username/password sai"""
    default_message = "Invalid username or password"


class TokenExpiredError(AuthenticationError):
    """Token hết hạn"""
    default_message = "Token has expired"


class InvalidTokenError(AuthenticationError):
    """Token không hợp lệ"""
    default_message = "Invalid token"


class UserNotActiveError(AuthenticationError):
    """Account bị disable"""
    default_message = "User account is not active"


class UserBlockedError(AuthenticationError):
    """Account bị block"""
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "User account is blocked"


# ============================================================
# PERMISSION ERRORS (403)
# ============================================================
class PermissionDeniedError(AppException):
    """Quyền bị từ chối"""
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "Permission denied"


class UnauthorizedError(AppException):
    """Không có quyền truy cập tài nguyên"""
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "You do not have permission to access this resource"


class InsufficientPermissionError(PermissionDeniedError):
    """Không đủ quyền"""
    default_message = "Insufficient permissions for this action"


class NotOwnerError(PermissionDeniedError):
    """Không phải chủ sở hữu resource"""
    default_message = "You are not the owner of this resource"


class RoleRequiredError(PermissionDeniedError):
    """Cần role nhất định"""
    default_message = "This action requires specific role"


# ============================================================
# RESOURCE NOT FOUND ERRORS (404)
# ============================================================
class NotFoundError(AppException):
    """Resource không tồn tại"""
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Resource not found"


class UserNotFoundError(NotFoundError):
    """User không tồn tại"""
    default_message = "User not found"


class DocumentNotFoundError(NotFoundError):
    """Document không tồn tại"""
    default_message = "Document not found"


class FolderNotFoundError(NotFoundError):
    """Folder không tồn tại"""
    default_message = "Folder not found"


class DepartmentNotFoundError(NotFoundError):
    """Department không tồn tại"""
    default_message = "Department not found"


class RoleNotFoundError(NotFoundError):
    """Role không tồn tại"""
    default_message = "Role not found"


class PermissionNotFoundError(NotFoundError):
    """Permission không tồn tại"""
    default_message = "Permission not found"


# ============================================================
# BUSINESS LOGIC ERRORS (422)
# ============================================================
class BusinessLogicError(AppException):
    """Lỗi logic kinh doanh"""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_message = "Business logic error"


class InvalidOperationError(BusinessLogicError):
    """Hành động không hợp lệ"""
    default_message = "Invalid operation"


class CannotDeleteError(BusinessLogicError):
    """Không thể xóa resource"""
    default_message = "Cannot delete this resource"


class CannotModifyError(BusinessLogicError):
    """Không thể sửa resource"""
    default_message = "Cannot modify this resource"


class DocumentProcessingError(BusinessLogicError):
    """Lỗi xử lý document"""
    default_message = "Error processing document"


class EmbeddingGenerationError(BusinessLogicError):
    """Lỗi tạo embedding"""
    default_message = "Error generating embeddings"


# ============================================================
# EXTERNAL SERVICE ERRORS (502, 503)
# ============================================================
class ExternalServiceError(AppException):
    """Lỗi từ external service (LLM, Vector DB...)"""
    status_code = status.HTTP_502_BAD_GATEWAY
    default_message = "External service error"


class LLMServiceError(ExternalServiceError):
    """LLM service không khả dụng hoặc lỗi"""
    default_message = "LLM service is unavailable"


class VectorDatabaseError(ExternalServiceError):
    """Qdrant vector DB lỗi"""
    default_message = "Vector database error"


class PermissionServiceError(ExternalServiceError):
    """Permission service lỗi"""
    default_message = "Permission service error"


class ServiceUnavailableError(AppException):
    """Service không khả dụng"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message = "Service unavailable"


# ============================================================
# DATABASE ERRORS (500)
# ============================================================
class DatabaseError(AppException):
    """Lỗi database"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "Database error"


class IntegrityError(DatabaseError):
    """Violation ràng buộc dữ liệu"""
    default_message = "Data integrity error"


class QueryError(DatabaseError):
    """Lỗi query database"""
    default_message = "Database query error"


# ============================================================
# INTERNAL SERVER ERRORS (500)
# ============================================================
class InternalServerError(AppException):
    """Internal server error"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "Internal server error"


class ConfigurationError(InternalServerError):
    """Lỗi cấu hình"""
    default_message = "Configuration error"


class NotImplementedError(InternalServerError):
    """Feature chưa implement"""
    status_code = status.HTTP_501_NOT_IMPLEMENTED
    default_message = "Feature not implemented"


# ============================================================
# HTTP-like Error Responses (for consistent API format)
# ============================================================
class ErrorResponse:
    """
    Định dạng error response chuẩn.
    Được dùng bởi global exception handler.
    """
    
    def __init__(self, exception: AppException, request_id: str = None):
        self.exception = exception
        self.request_id = request_id
        self.status_code = exception.status_code
        self.message = exception.message
        self.detail = exception.detail or {}
    
    def to_dict(self):
        """Convert sang dict để trả về JSON"""
        return {
            "success": False,
            "status_code": self.status_code,
            "message": self.message,
            "data": self.detail,
            "request_id": self.request_id,
        }
