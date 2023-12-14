"""
ASGI config for manda_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from manda_project.mymiddleware import TokenAuthMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter
import manda_app.routing 

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'manda_project.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": TokenAuthMiddleware(  
        URLRouter(
            manda_app.routing.websocket_urlpatterns
        )
    ),
})