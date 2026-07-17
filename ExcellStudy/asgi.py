"""
ASGI config for ExcellStudy project.
Includes Django Channels WebSocket routing for the playground.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ExcellStudy.settings')

# Initialize Django ASGI application first for side-effects
django_asgi_app = get_asgi_application()

try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from django.urls import re_path
    from apps.playground.consumers import PlaygroundConsumer

    application = ProtocolTypeRouter({
        'http': django_asgi_app,
        'websocket': AuthMiddlewareStack(
            URLRouter([
                re_path(r'ws/playground/(?P<session_id>\w+)/$', PlaygroundConsumer.as_asgi()),
            ])
        ),
    })
except ImportError:
    # Channels not installed — fall back to standard ASGI
    application = django_asgi_app
