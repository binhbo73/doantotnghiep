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
from pathlib import Path

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Setup Django
django_asgi_app = get_asgi_application()

# Optional: Import channels for WebSocket support
# Only import if channels is installed
try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from api.routing import websocket_urlpatterns
    
    application = ProtocolTypeRouter({
        # HTTP and WebSocket
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        ),
    })
except ImportError:
    # Fallback to standard Django ASGI if channels is not installed
    print("WARNING: django-channels not installed. WebSocket support disabled.")
    print("To enable WebSocket chat, install: pip install django-channels channels-redis daphne")
    application = django_asgi_app

