"""
Global Exception Handler - Catch tất cả exception và format lại thành StandardResponse.
Config này được đặt ở REST_FRAMEWORK['EXCEPTION_HANDLER'] trong settings.py
"""
import logging
from typing import Tuple
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    ValidationError as DRFValidationError,
    NotFound,
    PermissionDenied,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAcceptable,
    Throttled,
    ParseError,
)
from django.http import JsonResponse
from django.core.exceptions import ValidationError as DjangoValidationError, ObjectDoesNotExist
from django.db import IntegrityError as DjangoIntegrityError
from core.exceptions import (
    AppException,
    ValidationError,
    NotFoundError,
    PermissionDeniedError,
    AuthenticationError,
    InternalServerError,
)
from api.serializers.base import ResponseBuilder


logger = logging.getLogger("api")


class GlobalExceptionHandler:
    """Handle tất cả exception và format response chuẩn"""
    
    @staticmethod
    def handle_app_exception(exc: AppException, request):
        """Handle AppException (custom exceptions)"""
        data = exc.detail if exc.detail else {}
        response_data = ResponseBuilder.error(
            message=exc.message,
            status_code=exc.status_code,
            data=data,
            request_id=getattr(request, '_request_id', None)
        )
        logger.warning(
            f"AppException: {exc.message}",
            extra={
                'request_id': getattr(request, '_request_id', None),
                'user': getattr(request, 'user', None),
                'path': request.path,
                'method': request.method,
                'detail': data
            }
        )
        return Response(response_data, status=exc.status_code)
    
    @staticmethod
    def handle_drf_validation_error(exc: DRFValidationError, request):
        """Handle DRF ValidationError"""
        # Convert error format
        if isinstance(exc.detail, dict):
            data = exc.detail
        elif isinstance(exc.detail, list):
            data = {"detail": exc.detail}
        else:
            data = {"detail": [str(exc.detail)]}
        
        response_data = ResponseBuilder.error(
            message="Validation error",
            status_code=status.HTTP_400_BAD_REQUEST,
            data=data,
            request_id=getattr(request, '_request_id', None)
        )
        logger.warning(
            f"Validation error",
            extra={
                'request_id': getattr(request, '_request_id', None),
                'user': getattr(request, 'user', None),
                'errors': data
            }
        )
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
    
    @staticmethod
    def handle_drf_not_found(exc: NotFound, request):
        """Handle DRF NotFound"""
        response_data = ResponseBuilder.error(
            message="Resource not found",
            status_code=status.HTTP_404_NOT_FOUND,
            data={},
            request_id=getattr(request, '_request_id', None)
        )
        logger.info(
            f"Resource not found: {request.path}",
            extra={'request_id': getattr(request, '_request_id', None)}
        )
        return Response(response_data, status=status.HTTP_404_NOT_FOUND)
    
    @staticmethod
    def handle_drf_permission_denied(exc: PermissionDenied, request):
        """Handle DRF PermissionDenied"""
        response_data = ResponseBuilder.error(
            message=str(exc.detail) if exc.detail else "Permission denied",
            status_code=status.HTTP_403_FORBIDDEN,
            data={},
            request_id=getattr(request, '_request_id', None)
        )
        logger.warning(
            f"Permission denied",
            extra={
                'request_id': getattr(request, '_request_id', None),
                'user': getattr(request, 'user', None),
                'path': request.path
            }
        )
        return Response(response_data, status=status.HTTP_403_FORBIDDEN)
    
    @staticmethod
    def handle_drf_authentication_failed(exc: AuthenticationFailed, request):
        """Handle DRF AuthenticationFailed"""
        response_data = ResponseBuilder.error(
            message=str(exc.detail) if exc.detail else "Authentication failed",
            status_code=status.HTTP_401_UNAUTHORIZED,
            data={},
            request_id=getattr(request, '_request_id', None)
        )
        logger.warning(
            f"Authentication failed",
            extra={'request_id': getattr(request, '_request_id', None)}
        )
        return Response(response_data, status=status.HTTP_401_UNAUTHORIZED)
    
    @staticmethod
    def handle_drf_throttled(exc: Throttled, request):
        """Handle DRF Throttled (rate limit)"""
        retry_after = exc.wait() if hasattr(exc, 'wait') else 60
        response_data = ResponseBuilder.error(
            message=f"Rate limit exceeded. Retry after {int(retry_after)} seconds",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            data={},
            request_id=getattr(request, '_request_id', None)
        )
        return Response(
            response_data,
            status=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={'Retry-After': str(int(retry_after))}
        )
    
    @staticmethod
    def handle_django_validation_error(exc: DjangoValidationError, request):
        """Handle Django ValidationError"""
        if hasattr(exc, 'message_dict'):
            data = exc.message_dict
        elif hasattr(exc, 'messages'):
            data = {"detail": exc.messages}
        else:
            data = {"detail": [str(exc)]}
        
        response_data = ResponseBuilder.error(
            message="Validation error",
            status_code=status.HTTP_400_BAD_REQUEST,
            data=data,
            request_id=getattr(request, '_request_id', None)
        )
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
    
    @staticmethod
    def handle_integrity_error(exc: DjangoIntegrityError, request):
        """Handle Django IntegrityError (duplicate key, FK violation...)"""
        response_data = ResponseBuilder.error(
            message="Data conflict or constraint violation",
            status_code=status.HTTP_409_CONFLICT,
            data={},
            request_id=getattr(request, '_request_id', None)
        )
        logger.error(
            f"Database integrity error",
            exc_info=True,
            extra={'request_id': getattr(request, '_request_id', None)}
        )
        return Response(response_data, status=status.HTTP_409_CONFLICT)
    
    @staticmethod
    def handle_generic_exception(exc: Exception, request):
        """Handle generic/unexpected exceptions"""
        response_data = ResponseBuilder.error(
            message="Internal server error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            data={},
            request_id=getattr(request, '_request_id', None)
        )
        logger.error(
            f"Unhandled exception: {str(exc)}",
            exc_info=True,
            extra={
                'request_id': getattr(request, '_request_id', None),
                'user': getattr(request, 'user', None),
                'path': request.path,
                'method': request.method,
            }
        )
        return Response(response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def global_exception_handler(exc, context) -> Tuple[Response, int]:
    """
    Entry point cho DRF exception handler.
    Gọi từ settings: REST_FRAMEWORK['EXCEPTION_HANDLER']
    
    Args:
        exc: Exception object
        context: Dict with request, view, etc.
    
    Returns:
        (Response, status_code)
    """
    request = context.get('request')
    
    # Ensure request_id exists
    if not hasattr(request, '_request_id'):
        request._request_id = getattr(request, 'META', {}).get('HTTP_X_REQUEST_ID', '')
    
    # Handle AppException (Custom)
    if isinstance(exc, AppException):
        return GlobalExceptionHandler.handle_app_exception(exc, request), exc.status_code
    
    # Handle DRF Built-in Exceptions
    if isinstance(exc, DRFValidationError):
        return GlobalExceptionHandler.handle_drf_validation_error(exc, request), status.HTTP_400_BAD_REQUEST
    
    if isinstance(exc, NotFound):
        return GlobalExceptionHandler.handle_drf_not_found(exc, request), status.HTTP_404_NOT_FOUND
    
    if isinstance(exc, PermissionDenied):
        return GlobalExceptionHandler.handle_drf_permission_denied(exc, request), status.HTTP_403_FORBIDDEN
    
    if isinstance(exc, AuthenticationFailed):
        return GlobalExceptionHandler.handle_drf_authentication_failed(exc, request), status.HTTP_401_UNAUTHORIZED
    
    if isinstance(exc, Throttled):
        return GlobalExceptionHandler.handle_drf_throttled(exc, request), status.HTTP_429_TOO_MANY_REQUESTS
    
    if isinstance(exc, (MethodNotAllowed, NotAcceptable, ParseError)):
        response_data = ResponseBuilder.error(
            message=str(exc.detail),
            status_code=exc.status_code,
            data={},
            request_id=getattr(request, '_request_id', None)
        )
        return Response(response_data, status=exc.status_code), exc.status_code
    
    # Handle Django Exceptions
    if isinstance(exc, ObjectDoesNotExist):
        return GlobalExceptionHandler.handle_drf_not_found(exc, request), status.HTTP_404_NOT_FOUND

    if isinstance(exc, DjangoValidationError):
        return GlobalExceptionHandler.handle_django_validation_error(exc, request), status.HTTP_400_BAD_REQUEST
    
    if isinstance(exc, DjangoIntegrityError):
        return GlobalExceptionHandler.handle_integrity_error(exc, request), status.HTTP_409_CONFLICT
    
    # Handle unexpected exceptions
    return GlobalExceptionHandler.handle_generic_exception(exc, request), status.HTTP_500_INTERNAL_SERVER_ERROR
