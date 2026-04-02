# Application utilities
import logging

logger = logging.getLogger(__name__)

# Import validators
from .validators import (
    EmailValidator,
    PasswordValidator,
    FileValidator,
    UsernameValidator,
    URLValidator,
    PhoneValidator,
    validate_input,
)

# Import pagination
from .pagination import (
    CustomPageNumberPagination,
    SmallPagePagination,
    MediumPagePagination,
    LargePagePagination,
    CustomCursorPagination,
    SearchResultsPagination,
    DocumentListPagination,
    ChatHistoryPagination,
    get_pagination_class,
)

__all__ = [
    # Validators
    'EmailValidator',
    'PasswordValidator',
    'FileValidator',
    'UsernameValidator',
    'URLValidator',
    'PhoneValidator',
    'validate_input',
    # Pagination
    'CustomPageNumberPagination',
    'SmallPagePagination',
    'MediumPagePagination',
    'LargePagePagination',
    'CustomCursorPagination',
    'SearchResultsPagination',
    'DocumentListPagination',
    'ChatHistoryPagination',
    'get_pagination_class',
    # Utils
    'sanitize_input',
    'paginate_queryset',
]

def sanitize_input(input_text: str, max_length: int = 1000) -> str:
    """Sanitize user input"""
    if not isinstance(input_text, str):
        return ""
    return input_text.strip()[:max_length]

def paginate_queryset(queryset, page: int = 1, page_size: int = 10):
    """Paginate queryset (deprecated - use pagination classes instead)"""
    start = (page - 1) * page_size
    end = start + page_size
    return queryset[start:end]
