"""
Chat Routing - URL routing for WebSocket connections.

This file defines WebSocket URL patterns for django-channels.

WebSocket URLs:
- ws://localhost:8000/ws/chat/{conversation_id}/?token={auth_token}
"""
from django.urls import re_path
from api.consumers import ChatConsumer, PermissionConsumer

# UUID regex pattern
UUID_PATTERN = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

websocket_urlpatterns = [
    # WebSocket endpoint for chat
    # ws://localhost:8000/ws/chat/{conversation_id}/?token={jwt_token}
    re_path(
        rf'ws/chat/(?P<conversation_id>{UUID_PATTERN})/?$',
        ChatConsumer.as_asgi(),
        name='ws_chat'
    ),
    # WebSocket endpoint for permission updates
    # ws://localhost:8000/ws/permissions/?token={jwt_token}
    re_path(
        r'ws/permissions/?$',
        PermissionConsumer.as_asgi(),
        name='ws_permissions'
    ),
]
