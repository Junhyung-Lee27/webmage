from django.urls import re_path
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

from .consumers import chat_consumers, noti_consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_number>\d+)/$", chat_consumers.ChatConsumer.as_asgi()),
    re_path(r"ws/notifications/(?P<user_id>\d+)/$", noti_consumers.FollowConsumer.as_asgi()),
]