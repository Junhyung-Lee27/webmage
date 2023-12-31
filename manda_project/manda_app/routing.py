from django.urls import re_path

from .consumers import chat_consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_number>\d+)/$", chat_consumers.ChatConsumer.as_asgi()),
]

