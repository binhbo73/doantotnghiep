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

from api.routing import websocket_urlpatterns

# Fail fast if websocket stack is not available to avoid silent 404 on /ws/* routes.
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})

