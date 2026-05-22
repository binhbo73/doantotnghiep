"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/

To run with WebSocket support (django-channels):
    # Option 1: Using Daphne
    daphne -b 0.0.0.0 -p 8000 config.asgi:application
    
    # Option 2: Using Uvicorn
    uvicorn config.asgi:application --host 0.0.0.0 --port 8000
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

# Setup Django
django_asgi_app = get_asgi_application()

try:
    from django.conf import settings
    if getattr(settings, "EMBEDDING_PRELOAD_ENABLED", True):
        from services.ai.embedding_client import warmup_embedding_model
        warmup_embedding_model(source="asgi")
except Exception:
    import logging
    logging.getLogger(__name__).exception("[EMBEDDING_WARMUP] failed during ASGI startup")
    fail_fast = bool(
        "settings" in locals()
        and getattr(settings, "EMBEDDING_PRELOAD_FAIL_FAST", False)
    )
    if fail_fast:
        raise

from api.routing import websocket_urlpatterns

# Fail fast if websocket stack is not available to avoid silent 404 on /ws/* routes.
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})

