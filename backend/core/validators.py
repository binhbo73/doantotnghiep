"""
Core Validators - Tập hợp các hàm kiểm tra dữ liệu tùy chỉnh.
Dùng trong Models hoặc Serializers.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
import re
import os

# ============================================================
# PASSWORD VALIDATORS
# ============================================================

def validate_strong_password(value):
    """Kiểm tra mật khẩu mạnh (Ít nhất 8 ký tự, 1 chữ hoa, 1 số, 1 ký tự đặc biệt)"""
    if len(value) < 8:
        raise serializers.ValidationError("Mật khẩu phải có ít nhất 8 ký tự.")
    if not re.search(r'[A-Z]', value):
        raise serializers.ValidationError("Mật khẩu phải có ít nhất 1 chữ cái in hoa.")
    if not re.search(r'[0-9]', value):
        raise serializers.ValidationError("Mật khẩu phải có ít nhất 1 chữ số.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
        raise serializers.ValidationError("Mật khẩu phải có ít nhất 1 ký tự đặc biệt.")
    return value


def validate_password_length(value, min_length=8):
    """Kiểm tra độ dài mật khẩu tối thiểu"""
    if len(value) < min_length:
        raise serializers.ValidationError(f"Mật khẩu phải có ít nhất {min_length} ký tự.")
    return value


# ============================================================
# EMAIL & USERNAME VALIDATORS
# ============================================================

# validate_username_unique removed - use Service layer for database checks
# Serializer should only validate FORMAT, not EXISTENCE
# Service layer will handle uniqueness validation via Repository


# validate_email_unique removed - use Service layer for database checks
# Serializer should only validate FORMAT, not EXISTENCE
# Service layer will handle uniqueness validation via Repository


def validate_email_format(value):
    """Kiểm tra format email"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        raise serializers.ValidationError("Email không đúng định dạng.")
    return value


# ============================================================
# PHONE VALIDATORS
# ============================================================

def validate_phone_number(value):
    """Kiểm tra số điện thoại (Vietnam standard)"""
    pattern = r'^(0|84)(3|5|7|8|9)([0-9]{8})$'
    if not re.match(pattern, value):
        raise serializers.ValidationError("Số điện thoại không đúng định dạng Việt Nam (ví dụ: 0912345678).")
    return value


# ============================================================
# FILE VALIDATORS
# ============================================================

def validate_file_size(value, max_size_mb=50):
    """Kiểm tra dung lượng file"""
    limit = max_size_mb * 1024 * 1024
    if value.size > limit:
        raise serializers.ValidationError(f"Dung lượng file không được vượt quá {max_size_mb}MB.")
    return value


def validate_file_extension(value, allowed_extensions=None):
    """Kiểm tra đuôi file"""
    if allowed_extensions is None:
        allowed_extensions = ['.pdf', '.docx', '.txt', '.md']
    
    ext = os.path.splitext(value.name)[1]
    if ext.lower() not in allowed_extensions:
        raise serializers.ValidationError(f"Định dạng file '{ext}' không được hỗ trợ. Chỉ hỗ trợ: {', '.join(allowed_extensions)}")
    return value
