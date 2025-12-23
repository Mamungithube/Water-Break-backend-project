from django.urls import re_path
from .consumers import TeamChatConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/chat/team/(?P<team_id>\d+)/$",
        TeamChatConsumer.as_asgi(),
    ),
]
