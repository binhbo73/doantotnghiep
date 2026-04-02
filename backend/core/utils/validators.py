"""
Input Validators - Validate user inputs trước khi lưu vào database.
Các hàm kiểm tra email, password, file, etc.
"""
import re
import logging
from typing import Tuple, List
from django.core.exceptions import ValidationError as DjangoValidationError

logger = logging.getLogger(__name__)


class EmailValidator:
    """Email validation - RFC 5322 simplified"""
    
    PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    @staticmethod
    def validate(email: str) -> Tuple[bool, str]:
        """
        Validate email format
        
        Args:
            email: Email string to validate
            
        Returns:
            (is_valid, error_message)
        
        Example:
            is_valid, msg = EmailValidator.validate("user@example.com")
        """
        if not email or not isinstance(email, str):
            return False, "Email không được để trống"
        
        email = email.strip().lower()
        
        if len(email) > 254:
            return False, "Email quá dài (max 254 ký tự)"
        
        if not re.match(EmailValidator.PATTERN, email):
            return False, "Email không hợp lệ"
        
        return True, ""


class PasswordValidator:
    """Password validation - Enforce strong passwords"""
    
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    
    @staticmethod
    def validate(password: str) -> Tuple[bool, str]:
        """
        Validate password strength
        
        Requirements:
        - Min 8 characters
        - At least 1 uppercase letter
        - At least 1 digit
        - At least 1 special character (!@#$%^&*)
        
        Args:
            password: Password to validate
            
        Returns:
            (is_valid, error_message)
        
        Example:
            is_valid, msg = PasswordValidator.validate("Pass1234!")
        """
        if not password:
            return False, "Mật khẩu không được để trống"
        
        if len(password) < PasswordValidator.MIN_LENGTH:
            return False, f"Mật khẩu phải có ít nhất {PasswordValidator.MIN_LENGTH} ký tự"
        
        if PasswordValidator.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Mật khẩu phải chứa ít nhất 1 chữ hoa (A-Z)"
        
        if PasswordValidator.REQUIRE_DIGIT and not any(c.isdigit() for c in password):
            return False, "Mật khẩu phải chứa ít nhất 1 chữ số (0-9)"
        
        if PasswordValidator.REQUIRE_SPECIAL:
            special_chars = r"!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                return False, f"Mật khẩu phải chứa ít nhất 1 ký tự đặc biệt: {special_chars}"
        
        return True, ""


class FileValidator:
    """File validation - Size, type, etc."""
    
    MAX_FILE_SIZE_MB = 100  # 100 MB
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'text/plain',
        'text/markdown',
    }
    
    @staticmethod
    def validate_size(file_size_bytes: int, max_size_mb: int = None) -> Tuple[bool, str]:
        """
        Validate file size
        
        Args:
            file_size_bytes: File size in bytes
            max_size_mb: Max size in MB (default: MAX_FILE_SIZE_MB)
            
        Returns:
            (is_valid, error_message)
        """
        if max_size_mb is None:
            max_size_mb = FileValidator.MAX_FILE_SIZE_MB
        
        max_bytes = max_size_mb * 1024 * 1024
        
        if file_size_bytes > max_bytes:
            return False, f"File quá lớn (max: {max_size_mb}MB, actual: {file_size_bytes / (1024*1024):.1f}MB)"
        
        if file_size_bytes == 0:
            return False, "File không được để trống"
        
        return True, ""
    
    @staticmethod
    def validate_mime_type(mime_type: str, allowed_types: set = None) -> Tuple[bool, str]:
        """
        Validate file MIME type
        
        Args:
            mime_type: MIME type string (e.g., 'application/pdf')
            allowed_types: Set of allowed MIME types (default: ALLOWED_MIME_TYPES)
            
        Returns:
            (is_valid, error_message)
        """
        if allowed_types is None:
            allowed_types = FileValidator.ALLOWED_MIME_TYPES
        
        if not mime_type:
            return False, "Kiểu file không được xác định"
        
        if mime_type not in allowed_types:
            return False, f"Kiểu file không được hỗ trợ: {mime_type}"
        
        return True, ""
    
    @staticmethod
    def validate(file_obj, max_size_mb: int = None, allowed_types: set = None) -> Tuple[bool, str]:
        """
        Full file validation
        
        Args:
            file_obj: Django UploadedFile object
            max_size_mb: Max size in MB
            allowed_types: Allowed MIME types
            
        Returns:
            (is_valid, error_message)
        """
        # Check size
        is_valid, error_msg = FileValidator.validate_size(file_obj.size, max_size_mb)
        if not is_valid:
            return False, error_msg
        
        # Check MIME type
        mime_type = file_obj.content_type
        is_valid, error_msg = FileValidator.validate_mime_type(mime_type, allowed_types)
        if not is_valid:
            return False, error_msg
        
        return True, ""


class UsernameValidator:
    """Username validation"""
    
    PATTERN = r"^[a-zA-Z0-9_-]{3,30}$"  # 3-30 chars, alphanumeric + underscore/hyphen
    
    @staticmethod
    def validate(username: str) -> Tuple[bool, str]:
        """
        Validate username format
        
        Requirements:
        - 3-30 characters
        - Only alphanumeric, underscore, hyphen
        
        Args:
            username: Username to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not username or not isinstance(username, str):
            return False, "Tên người dùng không được để trống"
        
        username = username.strip()
        
        if not re.match(UsernameValidator.PATTERN, username):
            return False, "Tên người dùng phải 3-30 ký tự, chỉ chứa chữ, số, _, -"
        
        return True, ""


class URLValidator:
    """URL validation"""
    
    PATTERN = r"^https?://[^\s/$.?#].[^\s]*$"
    
    @staticmethod
    def validate(url: str) -> Tuple[bool, str]:
        """
        Validate URL format
        
        Args:
            url: URL string
            
        Returns:
            (is_valid, error_message)
        """
        if not url or not isinstance(url, str):
            return False, "URL không được để trống"
        
        if not re.match(URLValidator.PATTERN, url):
            return False, "URL không hợp lệ"
        
        return True, ""


class PhoneValidator:
    """Phone number validation - Vietnam format"""
    
    # Vietnamese phone: 10-11 digits, starts with 0
    PATTERN = r"^[0][0-9]{9,10}$"
    
    @staticmethod
    def validate(phone: str) -> Tuple[bool, str]:
        """
        Validate Vietnamese phone number
        
        Args:
            phone: Phone number string
            
        Returns:
            (is_valid, error_message)
        """
        if not phone or not isinstance(phone, str):
            return False, "Số điện thoại không được để trống"
        
        phone = phone.strip().replace(" ", "").replace("-", "")
        
        if not re.match(PhoneValidator.PATTERN, phone):
            return False, "Số điện thoại không hợp lệ (định dạng: 0XXXXXXXXXX)"
        
        return True, ""


def validate_input(
    field_name: str,
    value: str,
    validator_type: str,
    **kwargs
) -> Tuple[bool, str]:
    """
    Unified input validation function
    
    Args:
        field_name: Field name for error message
        value: Value to validate
        validator_type: 'email', 'password', 'username', 'url', 'phone'
        **kwargs: Additional options (max_size_mb for file, etc.)
        
    Returns:
        (is_valid, error_message)
    
    Example:
        is_valid, msg = validate_input('email', 'user@example.com', 'email')
        is_valid, msg = validate_input('password', 'Pass1234!', 'password')
    """
    validators = {
        'email': EmailValidator.validate,
        'password': PasswordValidator.validate,
        'username': UsernameValidator.validate,
        'url': URLValidator.validate,
        'phone': PhoneValidator.validate,
    }
    
    if validator_type not in validators:
        return False, f"Loại validator không được hỗ trợ: {validator_type}"
    
    validator_func = validators[validator_type]
    is_valid, error_msg = validator_func(value)
    
    if not is_valid:
        return False, f"{field_name}: {error_msg}"
    
    return True, ""
