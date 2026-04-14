"""
Async Views Support - Async API endpoints for high-concurrency scenarios.

Django 3.1+ supports async views. When to use:
- High concurrent requests (>100 concurrent users)
- Async I/O operations (external APIs, streaming)
- Long-running operations with many concurrent requests

Usage:
    from rest_framework.decorators import api_view, permission_classes
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def get_user_from_db(user_id):
        # This will run in a thread pool
        return User.objects.get(id=user_id)
    
    async def async_view(request):
        user = await get_user_from_db(user_id)
        return Response({...})

Note: 
- With runserver, Django doesn't auto-upgrade to ASGI
- Use: `daphne` or `hypercorn` for async support
- Keep sync views if you're using Gunicorn with sync workers
"""

from asgiref.sync import sync_to_async
from django.db import models
import asyncio
import logging

logger = logging.getLogger(__name__)


@sync_to_async
def aget_object_or_404(model_class, **kwargs):
    """Async version of get_object_or_404"""
    try:
        return model_class.objects.get(**kwargs)
    except model_class.DoesNotExist:
        return None


@sync_to_async
def aget_list(queryset, limit=None, offset=None):
    """Async version of queryset.all()[:limit]"""
    qs = queryset
    if offset:
        qs = qs[offset:]
    if limit:
        qs = qs[:limit]
    return list(qs)


@sync_to_async
def acount(queryset):
    """Async version of queryset.count()"""
    return queryset.count()


@sync_to_async
def aexists(queryset):
    """Async version of queryset.exists()"""
    return queryset.exists()


class AsyncServiceWrapper:
    """
    Wrapper to run sync services in async context.
    
    Usage:
        async def async_view(request):
            service = UserService()
            wrapper = AsyncServiceWrapper(service)
            users = await wrapper.list_users(page=1, page_size=20)
    """
    
    def __init__(self, service):
        self.service = service
    
    async def __getattr__(self, name):
        """Dynamically wrap service methods"""
        attr = getattr(self.service, name)
        
        if callable(attr):
            async def async_method(*args, **kwargs):
                return await sync_to_async(attr)(*args, **kwargs)
            return async_method
        
        return await sync_to_async(lambda: attr)()


async def gather_async_operations(*coroutines):
    """
    Run multiple async operations concurrently.
    
    Usage:
        users = await aget_list(User.objects.all())
        roles = await aget_list(Role.objects.all())
        # Bad: roles only fetched after users
        
        users, roles = await gather_async_operations(
            aget_list(User.objects.all()),
            aget_list(Role.objects.all())
        )
        # Good: both fetched concurrently
    """
    return await asyncio.gather(*coroutines)
