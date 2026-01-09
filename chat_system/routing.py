from django.urls import re_path
from .consumers import TeamChatConsumer,NotificationConsumer
websocket_urlpatterns = [
    re_path(
        r"ws/chat/team/(?P<team_id>\d+)/$",
        TeamChatConsumer.as_asgi(),
    ),
     re_path(
         r'ws/notifications/$', 
         NotificationConsumer.as_asgi()
    ),
]
