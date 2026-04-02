"""
Core Validators - Tập hợp các hàm kiểm tra dữ liệu tùy chỉnh.
Dùng trong Models hoặc Serializers.
"""
from django.core.exceptions import ValidationError
import re
import os

def validate_strong_password(value):
    """Kiểm tra mật khẩu mạnh (Ít nhất 8 ký tự, 1 chữ hoa, 1 số, 1 ký tự đặc biệt)"""
    if len(value) < 8:
        raise ValidationError("Mật khẩu phải có ít nhất 8 ký tự.")
    if not re.search(r'[A-Z]', value):
        raise ValidationError("Mật khẩu phải có ít nhất 1 chữ cái in hoa.")
    if not re.search(r'[0-9]', value):
        raise ValidationError("Mật khẩu phải có ít nhất 1 chữ số.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
        raise ValidationError("Mật khẩu phải có ít nhất 1 ký tự đặc biệt.")

def validate_phone_number(value):
    """Kiểm tra số điện thoại (Vietnam standard)"""
    pattern = r'^(0|84)(3|5|7|8|9)([0-9]{8})$'
    if not re.match(pattern, value):
        raise ValidationError("Số điện thoại không đúng định dạng Việt Nam.")

def validate_file_size(value):
    """Kiểm tra dung lượng file (Mặc định tối đa 50MB)"""
    limit = 50 * 1024 * 1024
    if value.size > limit:
        raise ValidationError("Dung lượng file không được vượt quá 50MB.")

def validate_file_extension(value, allowed_extensions=None):
    """Kiểm tra đuôi file"""
    if allowed_extensions is None:
        allowed_extensions = ['.pdf', '.docx', '.txt', '.md']
    
    ext = os.path.splitext(value.name)[1]
    if ext.lower() not in allowed_extensions:
        raise ValidationError(f"Định dạng file '{ext}' không được hỗ trợ. Chỉ hỗ trợ: {', '.join(allowed_extensions)}")
