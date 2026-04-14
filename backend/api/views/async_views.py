"""
Async API Views - High-concurrency endpoints.

These are optional async views for better performance with high concurrent requests.

IMPORTANT: To use async views, you need to run with ASGI server:
- Daphne: pip install daphne
  Run: daphne -b 0.0.0.0 -p 8000 config.asgi:application
  
- Uvicorn: pip install uvicorn
  Run: uvicorn config.asgi:application --host 0.0.0.0 --port 8000

Default Django dev server (runserver) can also handle async views by converting to ASGI.

When to use async views:
✅ High concurrent requests (100+ simultaneous)
✅ Long I/O operations (external APIs, databases)
✅ Streaming responses
✅ WebSocket connections

When NOT to use:
❌ Simple CRUD with low concurrency
❌ CPU-intensive operations
❌ When using Gunicorn with sync workers only

Performance: Async can 2-10x faster for I/O-bound operations!
"""

from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import sync_to_async
from api.serializers.base import ResponseBuilder
from services.user_service import UserService
from api.serializers.user_serializers import UserListSerializer
import logging

logger = logging.getLogger(__name__)


# ============================================================
# ASYNC HELPER FUNCTIONS
# ============================================================

@sync_to_async
def async_list_users(page=1, page_size=20, search=None):
    """Async wrapper for UserService.list_users()"""
    service = UserService()
    return service.list_users(page=page, page_size=page_size, search_query=search)


@sync_to_async
def async_get_user(user_id):
    """Async wrapper for UserService.get_by_id()"""
    service = UserService()
    return service.get_by_id(user_id)


# ============================================================
# ASYNC API ENDPOINTS (Optional - for high concurrency)
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def async_user_list(request):
    """
    ✅ ASYNC Endpoint: GET /api/v1/async/users/
    
    For high-concurrency scenarios. This endpoint handles the request
    without blocking other requests while waiting for database queries.
    
    Performance: Can handle 2-10x more concurrent requests than sync version.
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20)
    - search: Search query
    
    Usage: Same as sync version, but runs in async context.
    """
    try:
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        search = request.query_params.get('search', '')
        
        logger.info(f"[ASYNC] Listing users - page={page}, page_size={page_size}")
        
        # ✅ Run in thread pool (doesn't block other requests)
        result = await async_list_users(
            page=page,
            page_size=page_size,
            search=search if search else None
        )
        
        serializer = UserListSerializer(result['items'], many=True)
        
        return Response(
            ResponseBuilder.paginated(
                items=serializer.data,
                page=result['page'],
                page_size=result['page_size'],
                total_items=result['total'],
                message="✅ [ASYNC] Users list retrieved"
            ),
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"[ASYNC] Error listing users: {str(e)}", exc_info=True)
        return Response(
            ResponseBuilder.error(message=f"Error: {str(e)}"),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def async_user_detail(request, user_id):
    """
    ✅ ASYNC Endpoint: GET /api/v1/async/users/{user_id}/
    
    For high-concurrency scenarios.
    
    Usage: Same as sync version, but runs in async context.
    """
    try:
        logger.info(f"[ASYNC] Getting user detail: {user_id}")
        
        # ✅ Run in thread pool
        user = await async_get_user(user_id)
        
        from api.serializers.user_serializers import AccountSerializer
        serializer = AccountSerializer(user)
        
        return Response(
            ResponseBuilder.success(
                data=serializer.data,
                message="✅ [ASYNC] User detail retrieved"
            ),
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"[ASYNC] Error getting user detail: {str(e)}", exc_info=True)
        return Response(
            ResponseBuilder.error(message=f"Error: {str(e)}"),
            status=status.HTTP_404_NOT_FOUND
        )


# ============================================================
# NOTE: Async Class-Based Views
# ============================================================

"""
For async class-based views, use:

from rest_framework.views import APIView
from asgiref.sync import sync_to_async

class AsyncUserListView(APIView):
    permission_classes = [IsAuthenticated]
    
    async def get(self, request):
        result = await async_list_users()
        return Response(result)
    
    async def post(self, request):
        # Create async
        return Response(...)

# URL registration:
path('async/users/', AsyncUserListView.as_view(), name='async_user_list'),
"""
